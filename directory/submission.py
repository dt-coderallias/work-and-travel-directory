"""Build and send submissions.

The payload keeps public and private fields in separate objects. Apps Script
copies only `public` to the directory, so contact details cannot leak by way of
a column mix-up. The token is sent from the server and never reaches a browser.
"""

import datetime as dt
import uuid
from dataclasses import dataclass, field

import requests

from directory import config
from directory.text import mask_contacts

MIN_DETAIL_LENGTH = 20
STARS_ONLY_TEXT = "Rated using the quick form. No written details were given."


class SubmissionError(Exception):
    """The submission could not be delivered."""


@dataclass
class Submission:
    submission_type: str = ""
    entity_type: str = "employer"
    name: str = ""
    state: str = ""
    city: str = ""
    position: str = ""
    stars: dict[str, int | None] = field(default_factory=dict)
    chips: list[str] = field(default_factory=list)
    year: str = ""
    details: str = ""
    pay_rate: str = ""
    housing: str = ""
    sponsor: str = ""
    link: str = ""
    contact: str = ""
    declared: bool = False


def clean(value: str | None) -> str:
    return (value or "").strip()


def ratings_text(stars: dict[str, int | None]) -> str:
    """st.feedback gives 0-4, or None when unrated. Store as 1-5."""
    return ";".join(f"{name}={value + 1}" for name, value in stars.items() if value is not None)


def has_rating(entry: Submission) -> bool:
    return any(value is not None for value in entry.stars.values())


def missing_fields(entry: Submission) -> list[str]:
    """Plain-language problems that stop a submission from being sent."""
    problems = []
    if entry.submission_type not in config.SUBMISSION_TYPES:
        problems.append("Choose what you are adding.")
    if not clean(entry.name):
        problems.append("Enter the employer or agency name.")
    if not clean(entry.state):
        problems.append("Choose a state.")

    written = len(clean(entry.details)) >= MIN_DETAIL_LENGTH
    if entry.submission_type == "review":
        if not written and not has_rating(entry) and not entry.chips:
            problems.append("Give at least one star rating, or write a few words.")
    elif entry.submission_type in ("report", "job_opportunity") and not written:
        problems.append(f"Add a few more details (at least {MIN_DETAIL_LENGTH} characters).")

    if not entry.declared:
        problems.append("Tick the declaration to confirm.")
    return problems


def compose_description(entry: Submission) -> str:
    """Public text: the visitor's words, plus anything they tapped."""
    parts = []
    if entry.chips:
        parts.append("Issues selected: " + ", ".join(entry.chips) + ".")
    if entry.submission_type == "job_opportunity":
        job_fields = [
            ("Pay rate", entry.pay_rate), ("Housing", entry.housing),
            ("Agency or sponsor", entry.sponsor), ("Link", entry.link),
        ]
        parts += [f"{label}: {clean(value)}" for label, value in job_fields if clean(value)]
    if clean(entry.details):
        parts.append(clean(entry.details))
    return "\n\n".join(parts) or STARS_ONLY_TEXT


def default_status(entry: Submission) -> str:
    return config.UNVERIFIED if entry.submission_type == "job_opportunity" else "community_reported"


def build_payload(entry: Submission, token: str) -> dict:
    today =dt.datetime.now(dt.timezone.utc).date().isoformat()
    return {
        "token": token,
        "kind": "submission",
        "nonce": uuid.uuid4().hex,
        "public": {
            "employer_name": clean(entry.name),
            "entity_type": entry.entity_type,
            "state": clean(entry.state),
            "city": clean(entry.city),
            "position": clean(entry.position),
            "report_description": mask_contacts(compose_description(entry)),
            "ratings": ratings_text(entry.stars),
            "experience_period": entry.year,
            "submission_type": entry.submission_type,
            "date_reported": today,
            "last_updated": today,
            "verification_status": default_status(entry),
            "review_state": "unreviewed",
            "source": config.SOURCE_FORM,
        },
        "private": {
            "original_details": clean(entry.details),
            "contact": clean(entry.contact),
        },
    }


def build_correction(record_id: str, role: str, problem: str, proposed: str, evidence: str,
                     contact: str, token: str) -> dict:
    return {
        "token": token,
        "kind": "correction",
        "nonce": uuid.uuid4().hex,
        "private": {
            "record_id": clean(record_id),
            "role": clean(role),
            "problem": clean(problem),
            "proposed": clean(proposed),
            "evidence": clean(evidence),
            "contact": clean(contact),
        },
    }


def send(payload: dict, url: str) -> dict:
    """Post to the Apps Script endpoint and return its JSON reply."""
    if not url:
        raise SubmissionError("Submission address is not configured")
    try:
        response = requests.post(url, json=payload, timeout=config.SUBMIT_TIMEOUT_SECONDS)
        response.raise_for_status()
        reply = response.json()
    except (requests.RequestException, ValueError) as error:
        raise SubmissionError("Could not reach the submission service") from error
    if not reply.get("ok"):
        raise SubmissionError(f"Submission was refused: {reply.get('error', 'unknown')}")
    return reply
