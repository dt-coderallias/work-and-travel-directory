import pytest

from conftest import record, to_csv
from directory import config, data, search


@pytest.fixture
def frame(sample_text):
    return data.parse_directory(sample_text)


def ids(results):
    return sorted(results["record_id"])


def test_no_filters_returns_everything(frame):
    assert len(search.apply_filters(frame)) == len(frame)


@pytest.mark.parametrize("query, expected", [
    ("sample drug", ["T-0001"]),
    ("sampledrug", ["T-0001"]),
    ("SAMPLE", ["T-0001"]),
    ("pats", ["T-0002"]),
    ("pat's", ["T-0002"]),
    ("overtime", ["T-0002"]),
    ("housekeeping", ["T-0003"]),
    ("mccall", ["T-0003"]),
    ("harbor corpus", ["T-0005"]),
])
def test_query(frame, query, expected):
    assert ids(search.apply_filters(frame, query=query)) == expected


def test_regex_characters_in_a_query_are_literal(frame):
    assert search.apply_filters(frame, query="(((").empty
    assert ids(search.apply_filters(frame, query="$12")) == ["T-0003"]


def test_state_filter_includes_multiple_state_records(frame):
    assert ids(search.apply_filters(frame, state="Idaho")) == ["T-0003", "T-0004"]


def test_city_filter_matches_each_city_in_a_pair(frame):
    assert ids(search.apply_filters(frame, city="Port Aransas")) == ["T-0005"]
    assert ids(search.apply_filters(frame, city="Corpus Christi")) == ["T-0005"]


def test_position_filter_includes_all_position_records(frame):
    assert ids(search.apply_filters(frame, position_group="Housekeeping")) == [
        "T-0002", "T-0003", "T-0004",
    ]


def test_topics_must_all_match(frame):
    assert "T-0001" in ids(search.apply_filters(frame, topics=["Hours", "Housing"]))
    assert "T-0002" not in ids(search.apply_filters(frame, topics=["Hours", "Housing"]))


def test_experience_filter_separates_ratings_from_the_list(frame):
    assert ids(search.apply_filters(frame, experience=["bad"])) == ["T-0003"]
    assert "T-0003" not in ids(search.apply_filters(frame, experience=[config.FROM_LIST]))
    assert search.apply_filters(frame, experience=["good"]).empty


def test_choosing_several_experiences_widens_the_results(frame):
    results = search.apply_filters(frame, experience=["bad", config.FROM_LIST])
    assert len(results) == len(frame)


def test_experience_counts_cover_every_marker(frame):
    assert search.experience_counts(frame) == {"good": 0, "neutral": 0, "bad": 1, config.FROM_LIST: 4}


def test_filters_combine(frame):
    results = search.apply_filters(
        frame, query="hotel", state="Texas", position_group="Front desk", topics=["Hours"],
    )
    assert ids(results) == ["T-0005"]


def test_filters_can_exclude_everything(frame):
    assert search.apply_filters(frame, query="sample", state="Texas").empty


def test_state_options_are_sorted_and_exclude_blank_and_multiple(frame):
    options = search.state_options(frame)
    assert options == sorted(options)
    assert config.MULTIPLE_STATES not in options
    assert "" not in options


def test_city_options_follow_state_and_split_pairs(frame):
    assert search.city_options(frame, "Texas") == ["Corpus Christi", "Port Aransas"]
    assert "McCall" in search.city_options(frame)


def test_employer_options_leave_out_placeholders():
    frame = data.parse_directory(
        "record_id,employer_name,entity_type,state,city,position,report_description,ratings,"
        "experience_period,submission_type,date_reported,last_updated,verification_status,"
        "review_state,source\n"
        "1,Acme,,,,,text one,,,,,,,,\n"
        f"2,{config.EMPLOYER_NOT_NAMED},,,,,text two,,,,,,,,\n"
        "3,Town (area-wide comment),,,,,text three,,,,,,,,\n"
    )
    assert search.employer_options(frame) == ["Acme"]


def test_new_positions_join_the_form_list(frame):
    options = search.form_position_options(frame)
    assert options[: len(config.COMMON_POSITIONS)] == config.COMMON_POSITIONS
    assert "Retail sales" in options


def test_form_options_work_with_no_directory():
    assert search.employer_options(search.EMPTY_FRAME) == []
    assert search.city_options(search.EMPTY_FRAME, "Texas") == []
    assert search.form_position_options(search.EMPTY_FRAME) == config.COMMON_POSITIONS


def test_state_tiles_cover_every_state_once():
    assert set(config.STATE_TILES) == set(config.US_STATES)
    positions = [(row, column) for _, row, column in config.STATE_TILES.values()]
    assert len(set(positions)) == len(positions)


def test_state_counts_leave_out_multiple_state_and_blank_records(frame):
    counts = search.state_counts(frame)
    assert counts["Idaho"] == (frame["state"] == "Idaho").sum()
    assert sum(counts.values()) == frame["state"].isin(config.US_STATES).sum()
    assert config.MULTIPLE_STATES not in counts


def test_topic_counts_follow_the_frame_they_are_given(frame):
    everything = search.topic_counts(frame)
    narrowed = search.topic_counts(search.apply_filters(frame, topics=["Housing"]))
    assert narrowed["Housing"] == everything["Housing"] > 0
    assert sum(narrowed.values()) <= sum(everything.values())


def test_directory_stats_leave_out_placeholders():
    rows = [
        record("T-1", "Acme", state="Texas"),
        record("T-2", config.EMPLOYER_NOT_NAMED, state=config.MULTIPLE_STATES),
    ]
    stats = search.directory_stats(data.parse_directory(to_csv(rows)))
    assert stats == {"reports": 2, "employers": 1, "states": 1}


def test_state_choices_include_states_with_no_reports(frame):
    assert "Nebraska" not in search.state_options(frame)
    assert "Nebraska" in search.state_choices(frame)


def test_other_reports_share_a_name_but_not_a_record():
    rows = [
        record("T-1", "Acme Hotel"), record("T-2", "ACME hotel", report_description="Another account"),
        record("T-3", "Pine Lodge"),
    ]
    frame = data.parse_directory(to_csv(rows))
    first = frame[frame["record_id"] == "T-1"].iloc[0]
    assert search.other_reports(frame, first)["record_id"].tolist() == ["T-2"]


def test_employer_not_named_reports_are_not_related():
    rows = [
        record("T-1", config.EMPLOYER_NOT_NAMED),
        record("T-2", config.EMPLOYER_NOT_NAMED, report_description="A different account"),
    ]
    frame = data.parse_directory(to_csv(rows))
    assert search.other_reports(frame, frame.iloc[0]).empty


def test_suggest_finds_a_close_employer(frame):
    assert "Pine Lodge" in search.suggest(frame, "Pine Logde")


def test_suggest_ignores_very_short_queries(frame):
    assert search.suggest(frame, "pi") == []
