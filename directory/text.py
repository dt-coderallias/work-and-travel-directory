"""Text helpers with no Streamlit dependency, shared with the migration script."""

import re

EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_PATTERN = re.compile(r"(?<![\w$.])\+?\d[\d\s().-]{7,}\d(?!\w)")


def clean_text(value: object) -> str:
    """Trim a cell and collapse runs of spaces, keeping line breaks."""
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ").replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def employer_key(name: str) -> str:
    """Lowercase letters and digits only, so `Blue Lake` matches `bluelake`."""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def mask_contacts(text: str) -> str:
    """Hide email addresses and phone numbers. Prices and hours are untouched."""
    text = EMAIL_PATTERN.sub("[email removed]", text)
    return PHONE_PATTERN.sub("[number removed]", text)
