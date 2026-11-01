import pandas as pd
import pytest
import requests

from conftest import SAMPLE_RECORDS, record, to_csv
from directory import config, data, render
from directory.text import employer_key, mask_contacts


def test_parse_keeps_valid_records(sample_text):
    assert len(data.parse_directory(sample_text)) == len(SAMPLE_RECORDS)


def test_stray_columns_never_load():
    rows = [record("T-1", "Acme", reviewer_notes="private note", contact="me@example.com")]
    text = to_csv(rows, config.PUBLIC_COLUMNS + ["reviewer_notes", "contact"])
    frame = data.parse_directory(text)
    assert "reviewer_notes" not in frame.columns
    assert "contact" not in frame.columns
    assert "private note" not in frame.to_csv()


def test_html_page_is_a_failure_not_an_empty_directory():
    with pytest.raises(data.DataSourceError):
        data.parse_directory("<!DOCTYPE html><html><body>Sign in</body></html>")


def test_empty_source_is_a_failure():
    with pytest.raises(data.DataSourceError):
        data.parse_directory("")


def test_missing_column_is_a_failure(sample_text):
    with pytest.raises(data.DataSourceError):
        data.parse_directory(sample_text.replace("verification_status", "status"))


def test_records_missing_required_values_are_dropped():
    frame = data.parse_directory(to_csv([record("", "Acme"), record("T-2", "Beta")]))
    assert frame["record_id"].tolist() == ["T-2"]


def test_duplicate_ids_are_dropped():
    frame = data.parse_directory(to_csv([record("T-1", "Acme"), record("T-1", "Beta")]))
    assert frame["employer_name"].tolist() == ["Acme"]


def test_identical_reports_are_dropped_but_other_employers_are_kept():
    rows = [record("T-1", "Acme"), record("T-2", "ACME"), record("T-3", "Beta")]
    assert data.parse_directory(to_csv(rows))["record_id"].tolist() == ["T-1", "T-3"]


@pytest.mark.parametrize("status", ["", "confirmed", "VERIFIED", "verified!"])
def test_unknown_status_shows_the_lowest_label(status):
    frame = data.parse_directory(to_csv([record("T-1", "Acme", verification_status=status)]))
    assert frame.iloc[0]["verification_status"] == config.UNVERIFIED


def test_unknown_review_state_counts_as_unreviewed():
    frame = data.parse_directory(to_csv([record("T-1", "Acme", review_state="")]))
    assert frame.iloc[0]["review_state"] == "unreviewed"


def test_text_like_none_is_kept():
    frame = data.parse_directory(to_csv([record("T-1", "None", state="NA")]))
    assert frame.iloc[0]["employer_name"] == "None"
    assert frame.iloc[0]["state"] == "NA"


def test_contacts_are_masked_on_load():
    text = to_csv([record("T-1", "Acme", report_description="Call 876-555-1234 or a@b.com today")])
    description = data.parse_directory(text).iloc[0]["report_description"]
    assert "555-1234" not in description
    assert "a@b.com" not in description


@pytest.mark.parametrize("text", [
    "Rate was $13.25 an hour",
    "cut from 40 to 15 hrs/wk",
    "9am to 2 or 4pm",
    "Waited over a month, 30 - 40+ hours",
    "Taxi $12 and bus $20",
])
def test_masking_leaves_ordinary_numbers_alone(text):
    assert mask_contacts(text) == text


@pytest.mark.parametrize("name, key", [
    ("Blue Lake", "bluelake"),
    ("Pat's Marketplace", "patsmarketplace"),
    ("  A-One Bar & Grill ", "aonebargrill"),
])
def test_employer_key(name, key):
    assert employer_key(name) == key


def test_load_falls_back_to_last_good_copy(sample_path, monkeypatch):
    monkeypatch.setattr(data, "get_secret", lambda name: sample_path)
    assert data.load_directory().stale is False

    def fail(location):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(data, "read_source", fail)
    data.fetch_directory.clear()
    result = data.load_directory()
    assert result.stale is True
    assert len(result.frame) == len(SAMPLE_RECORDS)


def test_load_with_no_good_copy_reports_nothing(monkeypatch):
    monkeypatch.setattr(data, "get_secret", lambda name: "https://example.invalid/x.csv")

    def fail(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(data.requests, "get", fail)
    result = data.load_directory()
    assert result.frame is None and result.stale is True


def test_failed_source_is_not_retried_during_cooldown(monkeypatch):
    calls = []

    def fail(location):
        calls.append(location)
        raise requests.ConnectionError("down")

    monkeypatch.setattr(data, "get_secret", lambda name: "https://example.invalid/x.csv")
    monkeypatch.setattr(data, "read_source", fail)
    data.load_directory()
    data.load_directory()
    assert len(calls) == 1


def test_refresh_is_limited_to_once_per_cooldown():
    assert data.request_refresh() is True
    assert data.request_refresh() is False


@pytest.mark.parametrize("ratings, expected", [
    ("Pay=2;Hours=1", [("Pay", 2), ("Hours", 1)]),
    ("Pay=9;Hours=0", []),
    ("Pay=two;=3;junk", []),
    ("", []),
])
def test_parse_ratings(ratings, expected):
    assert render.parse_ratings(ratings) == expected


@pytest.fixture
def row():
    return pd.Series(record("T-1", "Acme"))


def test_markup_in_community_text_is_escaped(row):
    row["employer_name"] = "<script>alert(1)</script>"
    row["report_description"] = '<img src=x onerror="alert(1)">'
    row["city"] = "<b>City</b>"
    row["ratings"] = "<i>Pay</i>=3"
    for output in (render.card_html(row), render.detail_html(row)):
        assert "<script" not in output
        assert "<img" not in output
        assert "<b>" not in output
        assert "<i>" not in output


def test_dollar_signs_stay_as_plain_text(row):
    row["report_description"] = "$12 taxi and $12 back"
    assert "$12 taxi and $12 back" in render.detail_html(row)


def test_unknown_status_in_badge_is_safe(row):
    row["verification_status"] = '"><script>'
    output = render.badge_html(row)
    assert "script" not in output
    assert "Not verified" in output


def test_card_shows_review_note_only_when_unreviewed(row):
    assert "Not yet reviewed" not in render.card_html(row)
    row["review_state"] = "unreviewed"
    assert "Not yet reviewed" in render.card_html(row)


def test_card_shows_missing_date_plainly(row):
    assert "Date not recorded" in render.card_html(row)
    row["date_reported"] = "2026-06-01"
    assert "Reported 2026-06-01" in render.card_html(row)


def test_excerpt_cuts_on_a_word():
    assert render.excerpt("word " * 100, 20) == "word word word word…"


def test_detail_shows_full_text_and_explanation(row):
    row["report_description"] = "First line\n\n" + "long " * 200
    output = render.detail_html(row)
    assert output.count("<p>") >= 2
    assert "not a finding of fact" in output
