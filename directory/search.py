"""Search and filter the directory. No Streamlit here, so it is easy to test."""

import difflib

import pandas as pd

from directory import config
from directory.text import employer_key

# Lets the Add information form still work while the directory can't be loaded.
EMPTY_FRAME = pd.DataFrame(columns=["employer_name", "state", "city", "position"], dtype=object)


def state_options(frame: pd.DataFrame) -> list[str]:
    present = set(frame["state"]) - {"", config.MULTIPLE_STATES}
    return sorted(present)


def state_choices(frame: pd.DataFrame) -> list[str]:
    """Every state, so a map tile with no reports can still be chosen."""
    return sorted(set(config.US_STATES) | set(state_options(frame)))


def state_counts(frame: pd.DataFrame) -> dict[str, int]:
    """Reports placed in each state.

    Multi-state records are left out here, unlike in_state, or every state
    would look reported.
    """
    counts = frame["state"].value_counts()
    return {state: int(counts.get(state, 0)) for state in config.STATE_TILES}


def topic_counts(frame: pd.DataFrame) -> dict[str, int]:
    return {
        topic: int(frame["topics"].map(lambda values: topic in values).sum())
        for topic in config.TOPICS
    }


def experience_counts(frame: pd.DataFrame) -> dict[str, int]:
    counts = frame["experience"].value_counts()
    return {experience: int(counts.get(experience, 0)) for experience in config.EXPERIENCE_LABELS}


def directory_stats(frame: pd.DataFrame) -> dict[str, int]:
    return {
        "reports": len(frame),
        "employers": len(employer_options(frame)),
        "states": len(state_options(frame)),
    }


def other_reports(frame: pd.DataFrame, record) -> pd.DataFrame:
    """Other reports under the same employer name.

    "Employer not named" is a placeholder, so those reports aren't related.
    """
    if record["employer_name"] == config.EMPLOYER_NOT_NAMED:
        return frame.iloc[0:0]
    same_name = frame["employer_key"] == record["employer_key"]
    return frame[same_name & (frame["record_id"] != record["record_id"])]


def split_cities(city: str) -> list[str]:
    return [part.strip() for part in city.split(" / ") if part.strip() and part.strip() != "All locations"]


def in_state(frame: pd.DataFrame, state: str) -> pd.Series:
    """Records reported across several states apply to every state."""
    return frame["state"].isin([state, config.MULTIPLE_STATES])


def city_options(frame: pd.DataFrame, state: str | None = None) -> list[str]:
    rows = frame[frame["state"] == state] if state else frame
    return sorted({city for value in rows["city"] for city in split_cities(value)})


def position_options(frame: pd.DataFrame) -> list[str]:
    present = {group for groups in frame["position_groups"] for group in groups}
    return [group for group in config.POSITION_GROUPS if group in present]


def employer_options(frame: pd.DataFrame) -> list[str]:
    names = set(frame["employer_name"]) - {config.EMPLOYER_NOT_NAMED}
    return sorted((name for name in names if "(area-wide" not in name), key=str.lower)


def form_position_options(frame: pd.DataFrame) -> list[str]:
    """Common positions first, then anything visitors have added."""
    seen = list(config.COMMON_POSITIONS)
    added = {part.strip() for value in frame["position"] for part in value.split(",") if part.strip()}
    return seen + sorted(added - set(seen), key=str.lower)


def matches_query(frame: pd.DataFrame, query: str) -> pd.Series:
    """Every word must appear, or the whole query must match an employer name."""
    words = query.lower().split()
    if not words:
        return pd.Series(True, index=frame.index)

    every_word = pd.Series(True, index=frame.index)
    for word in words:
        every_word &= frame["search_text"].str.contains(word, regex=False)

    key = employer_key(query)
    if not key:
        return every_word
    return every_word | frame["employer_key"].str.contains(key, regex=False)


def apply_filters(
    frame: pd.DataFrame,
    query: str = "",
    state: str | None = None,
    city: str | None = None,
    position_group: str | None = None,
    topics: list[str] | None = None,
    experience: list[str] | None = None,
) -> pd.DataFrame:
    keep = matches_query(frame, query)
    if experience:
        keep &= frame["experience"].isin(experience)
    if state:
        keep &= in_state(frame, state)
    if city:
        keep &= frame["city"].map(lambda value: city in split_cities(value))
    if position_group:
        keep &= frame.apply(
            lambda row: position_group in row["position_groups"]
            or row["position"] == config.ALL_POSITIONS,
            axis=1,
        )
    for topic in topics or []:
        keep &= frame["topics"].map(lambda values: topic in values)
    return frame[keep]


def suggest(frame: pd.DataFrame, query: str, limit: int = 3) -> list[str]:
    """Close spellings of employers, cities or states, for the empty state."""
    query = query.strip()
    if len(query) < 3:
        return []

    names = employer_options(frame) + city_options(frame) + state_options(frame)
    by_key = {employer_key(name): name for name in reversed(names)}
    close = difflib.get_close_matches(employer_key(query), list(by_key), n=limit, cutoff=0.6)
    return [by_key[key] for key in close]
