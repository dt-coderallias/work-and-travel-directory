"""Load, validate and cache the public directory.

The app reads one thing: the public sheet published as CSV. It holds no Google
credential and has no route to the private workbook.
"""

import datetime as dt
import io
import logging
import re
import time
from dataclasses import dataclass

import pandas as pd
import requests
import streamlit as st

from directory import config
from directory.text import employer_key, mask_contacts

logger = logging.getLogger(__name__)

MASKED_COLUMNS = [
    "employer_name", "city", "position", "report_description",
    "pay_rate", "avg_hours", "rent_per_week",
]


class DataSourceError(Exception):
    """The source could not be read as a directory."""


@dataclass
class DirectoryResult:
    frame: pd.DataFrame | None
    loaded_at: dt.datetime | None
    stale: bool


def get_secret(name: str) -> str:
    try:
        return str(st.secrets.get(name, ""))
    except FileNotFoundError:
        return ""
    except st.errors.StreamlitSecretNotFoundError:
        return ""


def read_source(location: str) -> str:
    """Fetch the CSV text. A plain path is allowed for local development."""
    if location.startswith(("http://", "https://")):
        response = requests.get(location, timeout=config.FETCH_TIMEOUT_SECONDS)
        response.raise_for_status()
        response.encoding = "utf-8"
        return response.text
    with open(location, encoding="utf-8") as handle:
        return handle.read()


def matching_labels(text: str, patterns: dict[str, str]) -> list[str]:
    return [label for label, pattern in patterns.items() if re.search(pattern, text, re.IGNORECASE)]


def experience_of(ratings: str, source: str) -> str:
    """The record's key in config.EXPERIENCE_LABELS, or "" if it has no marker."""
    for part in str(ratings).split(";"):
        name, _, value = part.partition("=")
        if name.strip() == config.OVERALL_RATING and value.strip().lower() in config.OVERALL_CHOICES:
            return value.strip().lower()
    return config.FROM_LIST if source == config.SOURCE_LEGACY else ""


def parse_directory(text: str) -> pd.DataFrame:
    """Turn CSV text into validated records, or raise DataSourceError.

    Google can answer an unpublished sheet with an HTML page and status 200.
    The column check catches that, so it is reported as a failure rather than
    shown as an empty directory.
    """
    try:
        raw = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        raise DataSourceError("Source is not readable as CSV") from error

    required = [column for column in config.PUBLIC_COLUMNS if column not in config.OPTIONAL_COLUMNS]
    missing = [column for column in required if column not in raw.columns]
    if missing:
        raise DataSourceError(f"Source is missing columns: {missing}")

    frame = raw.reindex(columns=config.PUBLIC_COLUMNS, fill_value="").astype(object)
    for column in config.PUBLIC_COLUMNS:
        frame[column] = frame[column].map(lambda value: str(value).strip())

    has_required = (frame[config.REQUIRED_VALUES] != "").all(axis=1)
    if not has_required.all():
        logger.warning("Dropped %d records missing required values", (~has_required).sum())
    frame = frame[has_required].copy()

    for column in MASKED_COLUMNS:
        frame[column] = frame[column].map(mask_contacts)

    frame["employer_key"] = frame["employer_name"].map(employer_key)
    frame = frame.drop_duplicates(subset="record_id", keep="first")
    # Ratings count, because reviews with no written words all share the same text.
    frame = frame.drop_duplicates(
        subset=["employer_key", "state", "city", "report_description", "ratings"], keep="first"
    )

    known = frame["verification_status"].isin(config.VERIFICATION_LABELS)
    frame.loc[~known, "verification_status"] = config.UNVERIFIED
    frame.loc[frame["review_state"] != "reviewed", "review_state"] = "unreviewed"

    frame["experience"] = [
        experience_of(ratings, source) for ratings, source in zip(frame["ratings"], frame["source"])
    ]
    frame["position_groups"] = frame["position"].map(
        lambda position: matching_labels(position, config.POSITION_GROUPS)
    )
    frame["topics"] = frame["report_description"].map(
        lambda description: matching_labels(description, config.TOPICS)
    )
    frame["search_text"] = (
        frame["employer_name"] + " " + frame["employer_key"] + " " + frame["position"] + " "
        + frame["city"] + " " + frame["state"] + " " + frame["report_description"] + " "
        + frame["pay_rate"] + " " + frame["avg_hours"] + " " + frame["rent_per_week"]
    ).str.lower()

    ordered = frame.sort_values(
        ["date_reported", "employer_key", "record_id"], ascending=[False, True, True]
    )
    return ordered.reset_index(drop=True)


@st.cache_data(ttl=config.DATA_TTL_SECONDS, show_spinner=False)
def fetch_directory(location: str) -> tuple[pd.DataFrame, dt.datetime]:
    return parse_directory(read_source(location)), dt.datetime.now(dt.timezone.utc)


@st.cache_resource(show_spinner=False)
def shared_state() -> dict:
    """Process-wide state: the last good copy and the retry and refresh timers."""
    return {"frame": None, "loaded_at": None, "retry_after": 0.0, "refresh_after": 0.0}


def load_directory() -> DirectoryResult:
    """Return the directory, falling back to the last good copy on failure."""
    state = shared_state()
    location = get_secret("public_csv_url")
    if time.time() < state["retry_after"]:
        return DirectoryResult(state["frame"], state["loaded_at"], stale=True)
    if not location:
        logger.error("public_csv_url is not configured")
        return DirectoryResult(None, None, stale=True)

    try:
        frame, loaded_at = fetch_directory(location)
    except (requests.RequestException, OSError, DataSourceError) as error:
        logger.warning("Directory source unavailable: %s", error)
        state["retry_after"] = time.time() + config.RETRY_COOLDOWN_SECONDS
        return DirectoryResult(state["frame"], state["loaded_at"], stale=True)

    state["frame"], state["loaded_at"] = frame, loaded_at
    return DirectoryResult(frame, loaded_at, stale=False)


def request_refresh() -> bool:
    """Clear the cache, at most once per cooldown across all visitors."""
    state = shared_state()
    now = time.time()
    if now < state["refresh_after"]:
        return False
    state["refresh_after"] = now + config.REFRESH_COOLDOWN_SECONDS
    state["retry_after"] = 0.0
    fetch_directory.clear()
    return True
