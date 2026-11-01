"""Send the cleaned data to the Google workbooks. This works once.

Usage: python scripts/load_seed.py

The seed and archive must be in data/private/. The address and token come from
.streamlit/secrets.toml. The web app closes this import after the first success.
"""

import csv
import sys
import tomllib
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from directory import config  # noqa: E402

PRIVATE = ROOT / "data" / "private"
SEED = PRIVATE / "public_directory_seed.csv"
ARCHIVE = PRIVATE / "legacy_archive.csv"
SECRETS = ROOT / ".streamlit" / "secrets.toml"
TIMEOUT_SECONDS = 120


def read_rows(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def queue_order(row: dict) -> tuple:
    """Priority rows first, then unreviewed, then the rest."""
    return (not row["priority"], row["review_state"] == "reviewed", row["record_id"])


def queue_rows(archive: list[dict]) -> list[list[str]]:
    rows = [row for row in archive if row["outcome"] != "header_not_published"]
    return [
        [
            row["record_id"], row["employer_name"], row["state"], "",
            "Reviewed" if row["review_state"] == "reviewed" else "Live",
            row["priority"], "", "", "",
        ]
        for row in sorted(rows, key=queue_order)
    ]


def build_payload(token: str) -> dict:
    _, seed = read_rows(SEED)
    archive_columns, archive = read_rows(ARCHIVE)
    return {
        "token": token,
        "kind": "seed",
        "public": [[row[column] for column in config.PUBLIC_COLUMNS] for row in seed],
        "queue": queue_rows(archive),
        "archive": [archive_columns] + [[row[c] for c in archive_columns] for row in archive],
    }


def main() -> None:
    secrets = tomllib.loads(SECRETS.read_text(encoding="utf-8"))
    payload = build_payload(secrets["submit_token"])
    response = requests.post(secrets["submit_url"], json=payload, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    print(response.json())


if __name__ == "__main__":
    main()
