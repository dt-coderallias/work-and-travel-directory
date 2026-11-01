import csv
import io
import sys
from pathlib import Path

import pytest
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from directory import config  # noqa: E402


def record(record_id, employer, **values):
    row = dict.fromkeys(config.PUBLIC_COLUMNS, "")
    row.update(
        record_id=record_id,
        employer_name=employer,
        entity_type="employer",
        report_description="No hours given and the housing was poor.",
        submission_type="report",
        last_updated="2026-01-01",
        verification_status="community_reported",
        review_state="reviewed",
        source=config.SOURCE_LEGACY,
    )
    row.update(values)
    return row


SAMPLE_RECORDS = [
    record("T-0001", "Sample Drug", state="South Dakota", city="Wall", position="Retail sales"),
    record("T-0002", "Pat's Marketplace", state="New Jersey", city="Beach Haven",
           position=config.ALL_POSITIONS, report_description="Overtime is never paid."),
    record("T-0003", "Pine Lodge", state="Idaho", city="McCall", position="Housekeeping",
           report_description="Taxi is $12 each, and $12 back again.",
           ratings="Overall=bad;Pay=2;Hours=1", review_state="unreviewed", date_reported="2026-06-01",
           source=config.SOURCE_FORM),
    record("T-0004", "Global Parks", state=config.MULTIPLE_STATES, position=config.ALL_POSITIONS,
           report_description="Second job is hard to find."),
    record("T-0005", "Harbor Hotel", state="Texas", city="Corpus Christi / Port Aransas",
           position="Server, Front desk", verification_status="multiple_reports"),
]


def to_csv(records, columns=None):
    columns = columns or config.PUBLIC_COLUMNS
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


@pytest.fixture
def sample_text():
    return to_csv(SAMPLE_RECORDS)


@pytest.fixture
def sample_path(tmp_path, sample_text):
    path = tmp_path / "sample.csv"
    path.write_text(sample_text, encoding="utf-8")
    return str(path)


@pytest.fixture(autouse=True)
def clear_streamlit_caches():
    st.cache_data.clear()
    st.cache_resource.clear()
    yield
