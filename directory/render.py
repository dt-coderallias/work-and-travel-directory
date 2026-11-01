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
SCRIPT_PATH = Path(__file__).with_name("live_typing.js")


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
    if status not in config.BADGED_STATUSES:
        return ""
    label, _ = status_label(status)
    return f'<span class="badge badge-{status}">{html.escape(label)}</span>'


def experience_html(record) -> str:
    experience = record.get("experience", "")
    if experience not in config.OVERALL_CHOICES:
        return ""
    label, _ = config.EXPERIENCE_LABELS[experience]
    return f'<p class="experience"><span class="badge badge-{experience}">{html.escape(label)}</span></p>'


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


def footnote_html(record, show_missing_date: bool = True) -> str:
    parts = []
    if record.get("experience") == config.FROM_LIST:
        parts.append(config.EXPERIENCE_LABELS[config.FROM_LIST][0])
    if record["date_reported"] or show_missing_date:
        parts.append(date_text(record))
    if record["experience_period"]:
        parts.append(f"Experience: {record['experience_period']}")
    if not parts:
        return ""
    text = " · ".join(html.escape(part) for part in parts)
    return f'<p class="footnote">{text}</p>'


def topic_tags_html(record) -> str:
    tags = "".join(f'<span class="tag">{html.escape(topic)}</span>' for topic in record.get("topics", []))
    return f'<div class="tags">{tags}</div>' if tags else ""


def card_html(record, linked: bool = True) -> str:
    """A report card. `linked` adds the prompt for cards that open the full report."""
    prompt = '<p class="card-prompt">Read full report</p>' if linked else ""
    return (
        '<div class="record">'
        f'<div class="record-head"><h3>{html.escape(record["employer_name"])}</h3>{badge_html(record)}</div>'
        f"{meta_html(record)}"
        f"{experience_html(record)}"
        f'<p class="excerpt">{html.escape(excerpt(record["report_description"]))}</p>'
        f"{stars_html(record)}"
        f"{topic_tags_html(record)}"
        f"{footnote_html(record, show_missing_date=False)}"
        f"{prompt}"
        "</div>"
    )


def paragraphs_html(text: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n+", text) if part.strip()]
    return "".join(f"<p>{html.escape(part)}</p>" for part in paragraphs)


def detail_html(record) -> str:
    _, explanation = status_label(record["verification_status"])
    _, experience_note = config.EXPERIENCE_LABELS.get(record.get("experience", ""), ("", ""))
    return (
        '<div class="record record-detail">'
        f'<div class="record-head"><h3>{html.escape(record["employer_name"])}</h3>{badge_html(record)}</div>'
        f"{meta_html(record)}"
        f"{experience_html(record)}"
        f'<div class="full-text">{paragraphs_html(record["report_description"])}</div>'
        f"{stars_html(record)}"
        f"{footnote_html(record)}"
        f'<p class="explanation">{html.escape(explanation)} {html.escape(experience_note)} '
        "This is an account from a member of the community, not a finding of fact.</p>"
        "</div>"
    )


def eyebrow_html() -> str:
    return f'<p class="eyebrow">{html.escape(config.APP_NAME)}</p>'


def stats_html(stats: dict[str, int]) -> str:
    items = "".join(f"<div><strong>{value}</strong>{name}</div>" for name, value in stats.items())
    return f'<div class="stats">{items}</div>'


def tile_level(count: int, highest: int) -> int:
    """0 for no reports, then 1 to 4 relative to the busiest state."""
    if not count:
        return 0
    return 1 + 3 * (count - 1) // max(highest - 1, 1)


def state_map_css(counts: dict[str, int], selected: str | None) -> str:
    """Place each tile on the grid and set its colour, using its st-key class."""
    highest = max(counts.values(), default=0)
    rules = []
    for state, (abbreviation, row, column) in config.STATE_TILES.items():
        level = "selected" if state == selected else tile_level(counts[state], highest)
        rules.append(
            f".st-key-state_{abbreviation} {{ grid-area: {row + 1} / {column + 1}; "
            f"--tile: var(--tile-{level}); --tile-ink: var(--tile-{level}-ink); }}"
        )
    return f"<style>{''.join(rules)}</style>"


def state_split_html(state: str, in_state: int, across: int) -> str:
    return (
        f'<p class="results-note">{in_state} in {html.escape(state)}, '
        f"{across} across several states</p>"
    )


def step_heading_html(number: int, title: str) -> str:
    return f'<h3 class="step-heading"><span>{number}</span>{html.escape(title)}</h3>'


def checklist_html(missing: list[str]) -> str:
    if not missing:
        return '<p class="ready">Ready to publish.</p>'
    items = "".join(f"<li>{html.escape(item)}</li>" for item in missing)
    return f'<div class="still-needed"><h4>Still needed</h4><ul>{items}</ul></div>'


def tiles_html(tiles: list[tuple[str, str]], numbered: bool = False) -> str:
    """A row of titled panels. Text here is ours, never community text."""
    items = []
    for number, (title, body) in enumerate(tiles, start=1):
        mark = f'<span class="tile-number">{number}</span>' if numbered else ""
        items.append(f'<div class="tile">{mark}<h3>{html.escape(title)}</h3><p>{html.escape(body)}</p></div>')
    return f'<div class="tiles">{"".join(items)}</div>'


def label_legend_html() -> str:
    items = []
    for status in config.BADGED_STATUSES:
        label, explanation = status_label(status)
        items.append(
            f'<div class="tile"><span class="badge badge-{status}">{html.escape(label)}</span>'
            f"<p>{html.escape(explanation)}</p></div>"
        )
    return f'<div class="tiles">{"".join(items)}</div>'


def load_styles() -> None:
    st.html(STYLE_PATH)


def load_script() -> None:
    with st.container(key="scripts"):
        st.html(f"<script>{SCRIPT_PATH.read_text(encoding='utf-8')}</script>", unsafe_allow_javascript=True)


def compact_on_phones() -> None:
    """Once a filter is on, results matter more than the overview."""
    st.html(
        "<style>@media (max-width: 640px) { "
        '[data-testid="stLayoutWrapper"]:has(> .st-key-map_panel), .stats { display: none; } '
        "}</style>"
    )


def page_band(title: str, intro: str) -> None:
    with st.container(key="band"):
        st.title(title, anchor=False)
        st.write(intro)


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
