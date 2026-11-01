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


def test_reviews_with_no_words_survive_when_their_ratings_differ():
    rows = [
        record("T-1", "Acme", report_description="Rated.", ratings="Overall=good"),
        record("T-2", "Acme", report_description="Rated.", ratings="Overall=bad"),
    ]
    assert data.parse_directory(to_csv(rows))["record_id"].tolist() == ["T-1", "T-2"]


@pytest.mark.parametrize("ratings, source, expected", [
    ("Overall=good;Pay=4", config.SOURCE_FORM, "good"),
    ("Overall=neutral", config.SOURCE_FORM, "neutral"),
    ("Pay=4;Overall=bad", config.SOURCE_FORM, "bad"),
    (" Overall = Good ", config.SOURCE_FORM, "good"),
    ("", config.SOURCE_LEGACY, config.FROM_LIST),
    ("Overall=bad", config.SOURCE_LEGACY, "bad"),
    ("", config.SOURCE_FORM, ""),
    ("Pay=4", config.SOURCE_FORM, ""),
    ("Overall=terrible", config.SOURCE_FORM, ""),
    ("Overall=<b>", config.SOURCE_FORM, ""),
])
def test_experience_of(ratings, source, expected):
    assert data.experience_of(ratings, source) == expected


def test_every_record_gets_its_experience(sample_text):
    frame = data.parse_directory(sample_text)
    markers = dict(zip(frame["record_id"], frame["experience"]))
    assert markers["T-0003"] == "bad"
    assert markers["T-0001"] == config.FROM_LIST


def test_a_source_with_only_a_header_still_loads():
    assert data.parse_directory(to_csv([])).empty


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
    ("Overall=good;Pay=4", [("Pay", 4)]),
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


@pytest.mark.parametrize("experience, label", [
    ("good", "Good experience"),
    ("neutral", "Neutral experience"),
    ("bad", "Bad experience"),
])
def test_rating_badge_appears_on_card_and_full_report(row, experience, label):
    row["experience"] = experience
    assert f'badge-{experience}">{label}' in render.card_html(row)
    assert f'badge-{experience}">{label}' in render.detail_html(row)


def test_no_marker_for_a_record_without_one(row):
    assert 'class="experience"' not in render.card_html(row)
    row["experience"] = '"><script>'
    assert "script" not in render.card_html(row)


def test_list_records_only_mention_where_the_data_was_pulled_from(row):
    row["experience"] = config.FROM_LIST
    for output in (render.card_html(row), render.detail_html(row)):
        assert "Data pulled from the Jobs to Avoid list" in output
        assert 'class="experience"' not in output


def test_list_wording_never_passes_judgement():
    wording = " ".join(config.EXPERIENCE_LABELS[config.FROM_LIST]).lower()
    assert "complaint" not in wording
    assert "marked" not in wording


def test_full_report_says_what_the_list_is(row):
    row["experience"] = config.FROM_LIST
    assert "a spreadsheet shared in the community in 2026" in render.detail_html(row)


def test_full_report_says_a_rating_is_the_writers_view(row):
    row["experience"] = "bad"
    assert "isn&#x27;t the directory&#x27;s view" in render.detail_html(row)


def test_card_shows_review_note_only_when_unreviewed(row):
    assert "Not yet reviewed" not in render.card_html(row)
    row["review_state"] = "unreviewed"
    assert "Not yet reviewed" in render.card_html(row)


def test_missing_date_shows_only_in_the_full_report(row):
    assert "Date not recorded" not in render.card_html(row)
    assert "Date not recorded" in render.detail_html(row)
    row["date_reported"] = "2026-06-01"
    assert "Reported 2026-06-01" in render.card_html(row)


def test_card_prompt_is_left_out_of_the_form_preview(row):
    assert "Read full report" in render.card_html(row)
    assert "Read full report" not in render.card_html(row, linked=False)


def test_topic_tags_appear_on_the_card(row):
    assert 'class="tags"' not in render.card_html(row)
    tagged = {**row.to_dict(), "topics": ["Housing", "Pay"]}
    assert render.card_html(tagged).count('class="tag"') == 2


@pytest.mark.parametrize("count, highest, level", [
    (0, 10, 0), (1, 10, 1), (5, 10, 2), (10, 10, 4), (1, 1, 1),
])
def test_tile_level_scales_to_the_busiest_state(count, highest, level):
    assert render.tile_level(count, highest) == level


def test_selected_tile_overrides_its_shade():
    counts = dict.fromkeys(config.STATE_TILES, 0)
    css = render.state_map_css(counts, "Texas")
    assert "--tile: var(--tile-selected)" in css
    assert css.count("grid-area") == len(config.STATE_TILES)


def test_state_split_escapes_the_state_name():
    assert "<b>" not in render.state_split_html("<b>Texas</b>", 2, 1)


def test_excerpt_cuts_on_a_word():
    assert render.excerpt("word " * 100, 20) == "word word word word…"


def test_detail_shows_full_text_and_explanation(row):
    row["report_description"] = "First line\n\n" + "long " * 200
    output = render.detail_html(row)
    assert output.count("<p>") >= 2
    assert "not a finding of fact" in output
