"""Turn records into HTML.

Community text is untrusted, so every value goes through html.escape and is
shown with st.html, never as Markdown. This also protects reports like
"$12 taxi ... $12 each", which Streamlit Markdown would render as LaTeX.
"""

import html
import re
from pathlib import Path

import streamlit as st

from directory import config

STYLE_PATH = Path(__file__).with_name("style.css")


def parse_ratings(ratings: str) -> list[tuple[str, int]]:
    """Read `Pay=2;Hours=1`, ignoring anything malformed or out of range."""
    parsed = []
    for part in str(ratings).split(";"):
        name, separator, value = part.partition("=")
        if separator and value.strip() in {"1", "2", "3", "4", "5"} and name.strip():
            parsed.append((name.strip(), int(value)))
    return parsed


def excerpt(text: str, length: int = config.EXCERPT_LENGTH) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    if len(flat) <= length:
        return flat
    return flat[:length].rsplit(" ", 1)[0].rstrip(" ,.;:") + "…"


def location_text(record) -> str:
    parts = [record["city"], record["state"]]
    return ", ".join(part for part in parts if part) or "Location not stated"


def date_text(record) -> str:
    if record["date_reported"]:
        return f"Reported {record['date_reported']}"
    return "Date not recorded"


def status_label(status: str) -> tuple[str, str]:
    return config.VERIFICATION_LABELS.get(status, config.VERIFICATION_LABELS[config.UNVERIFIED])


def badge_html(record) -> str:
    status = record["verification_status"]
    known = status if status in config.VERIFICATION_LABELS else config.UNVERIFIED
    label, _ = status_label(status)
    return f'<span class="badge badge-{known}">{html.escape(label)}</span>'


def stars_html(record) -> str:
    items = []
    for name, value in parse_ratings(record["ratings"]):
        stars = "★" * value + "☆" * (5 - value)
        items.append(
            f'<li><span class="rating-name">{html.escape(name)}</span> '
            f'<span class="rating-stars" role="img" '
            f'aria-label="{value} out of 5 stars">{stars}</span></li>'
        )
    return f'<ul class="ratings">{"".join(items)}</ul>' if items else ""


def meta_html(record) -> str:
    parts = [record["position"], location_text(record)]
    if record["submission_type"] != "report":
        parts.insert(0, config.SUBMISSION_TYPES.get(record["submission_type"], ""))
    text = " · ".join(html.escape(part) for part in parts if part)
    return f'<p class="meta">{text}</p>'


def footnote_html(record) -> str:
    parts = [date_text(record)]
    if record["experience_period"]:
        parts.append(f"Experience: {record['experience_period']}")
    if record["review_state"] != "reviewed":
        parts.append("Not yet reviewed by a moderator")
    text = " · ".join(html.escape(part) for part in parts)
    return f'<p class="footnote">{text}</p>'


def card_html(record) -> str:
    return (
        '<div class="record">'
        f'<div class="record-head"><h3>{html.escape(record["employer_name"])}</h3>{badge_html(record)}</div>'
        f"{meta_html(record)}"
        f'<p class="excerpt">{html.escape(excerpt(record["report_description"]))}</p>'
        f"{stars_html(record)}"
        f"{footnote_html(record)}"
        "</div>"
    )


def paragraphs_html(text: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n+", text) if part.strip()]
    return "".join(f"<p>{html.escape(part)}</p>" for part in paragraphs)


def detail_html(record) -> str:
    _, explanation = status_label(record["verification_status"])
    return (
        '<div class="record record-detail">'
        f'<div class="record-head"><h3>{html.escape(record["employer_name"])}</h3>{badge_html(record)}</div>'
        f"{meta_html(record)}"
        f'<div class="full-text">{paragraphs_html(record["report_description"])}</div>'
        f"{stars_html(record)}"
        f"{footnote_html(record)}"
        f'<p class="explanation">{html.escape(explanation)} '
        "This is an account from a member of the community, not a finding of fact.</p>"
        "</div>"
    )


def load_styles() -> None:
    st.html(STYLE_PATH)


def disclaimer() -> None:
    st.caption(
        "Reports here are written by members of the community. They are accounts and "
        "allegations, not established facts, unless marked as independently verified."
    )


def footer() -> None:
    """On phones the top menu collapses, so these stay easy to find."""
    st.divider()
    with st.container(horizontal=True):
        st.page_link("views/how_it_works.py", label="How it works")
        st.page_link("views/privacy.py", label="Privacy")
        st.page_link("views/corrections.py", label="Corrections")
