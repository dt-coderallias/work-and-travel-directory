"""Drive the real app with Streamlit's test runner."""

from pathlib import Path

import pytest
import requests
from streamlit.testing.v1 import AppTest

from conftest import SAMPLE_RECORDS, record, to_csv
from directory import config, data

APP =str(Path(__file__).resolve().parents[1] / "app.py")


def open_app(location, submit_url="https://example.invalid/exec", params=None):
    app = AppTest.from_file(APP, default_timeout=30)
    app.secrets["public_csv_url"] = location
    app.secrets["submit_url"] = submit_url
    app.secrets["submit_token"] = "test-token"
    for key, value in (params or {}).items():
        app.query_params[key] = value
    return app.run()


def captions(app):
    return [element.value for element in app.caption]


def report_count(app):
    return next(text for text in captions(app) if text.endswith(("report", "reports")))


def button(app, key):
    return app.button(key=key)


@pytest.fixture
def app(sample_path):
    running = open_app(sample_path)
    assert not running.exception
    return running


def test_home_shows_all_records(app):
    assert report_count(app) == f"{len(SAMPLE_RECORDS)} reports"
    assert app.title[0].value == config.APP_HEADLINE


def test_home_has_a_disclaimer_and_add_button(app):
    assert any("accounts and allegations" in text for text in captions(app))
    assert button(app, "add_top").label == "Add information"


def test_search_narrows_results(app):
    app.text_input(key="f_query").input("pine").run()
    assert report_count(app) == "1 report"


def test_state_and_position_filters_combine(app):
    app.selectbox(key="f_state").select("Idaho").run()
    assert report_count(app) == "2 reports"
    app.selectbox(key="f_position").select("Housekeeping").run()
    assert report_count(app) == "2 reports"
    app.text_input(key="f_query").input("lodge").run()
    assert report_count(app) == "1 report"


def test_city_list_follows_state(app):
    app.selectbox(key="f_state").select("Texas").run()
    assert app.selectbox(key="f_city").options == ["Corpus Christi", "Port Aransas"]


def test_changing_state_clears_city(app):
    app.selectbox(key="f_state").select("Texas").run()
    app.selectbox(key="f_city").select("Port Aransas").run()
    app.selectbox(key="f_state").select("Idaho").run()
    assert app.selectbox(key="f_city").value is None


def test_empty_state_says_no_results_does_not_mean_fine(app):
    app.text_input(key="f_query").input("zzzzzz").run()
    assert app.info[0].value == "No reports match your search."
    assert any("does not mean an employer is fine" in m.value for m in app.markdown)


def test_did_you_mean_fixes_the_search(app):
    app.text_input(key="f_query").input("Pine Logde").run()
    button(app, "suggest_Pine Lodge").click().run()
    assert report_count(app) == "1 report"


def test_clear_filters_restores_results(app):
    app.text_input(key="f_query").input("zzzzzz").run()
    button(app, "clear_empty").click().run()
    assert report_count(app) == f"{len(SAMPLE_RECORDS)} reports"


def test_opening_a_report_shows_its_reference(app):
    button(app, "open_T-0001").click().run()
    assert not app.exception
    assert "Reference: T-0001" in captions(app)


def test_shared_link_opens_the_report(sample_path):
    app = open_app(sample_path, params={"record": "T-0002"})
    assert not app.exception
    assert "Reference: T-0002" in captions(app)


def test_shared_link_to_a_removed_report_says_so(sample_path):
    app = open_app(sample_path, params={"record": "T-9999"})
    assert app.warning[0].value == "That report is no longer in the directory."


def test_show_more_pages_through_results(tmp_path):
    rows = [record(f"T-{n:04d}", f"Employer {n}", report_description=f"Report number {n}") for n in range(45)]
    path = tmp_path / "many.csv"
    path.write_text(to_csv(rows), encoding="utf-8")
    app = open_app(str(path))
    opened = [b for b in app.button if str(b.key).startswith("open_")]
    assert len(opened) == config.PAGE_SIZE
    button(app, "show_more").click().run()
    opened = [b for b in app.button if str(b.key).startswith("open_")]
    assert len(opened) == config.PAGE_SIZE * 2


def test_map_has_a_tile_for_every_state(app):
    tiles = [b for b in app.button if str(b.key).startswith("state_")]
    assert len(tiles) == len(config.STATE_TILES)


def test_map_tile_filters_and_a_second_tap_clears(app):
    button(app, "state_ID").click().run()
    assert report_count(app) == "2 reports"
    assert app.selectbox(key="f_state").value == "Idaho"
    button(app, "state_ID").click().run()
    assert report_count(app) == f"{len(SAMPLE_RECORDS)} reports"
    assert app.selectbox(key="f_state").value is None


def test_map_tile_with_no_reports_can_be_chosen(app):
    button(app, "state_NE").click().run()
    assert not app.exception
    assert app.selectbox(key="f_state").value == "Nebraska"


def test_map_tile_clears_a_city_from_another_state(app):
    app.selectbox(key="f_state").select("Texas").run()
    app.selectbox(key="f_city").select("Port Aransas").run()
    button(app, "state_ID").click().run()
    assert app.selectbox(key="f_city").value is None


def test_summary_explains_multiple_state_records(app):
    button(app, "state_ID").click().run()
    assert any("1 in Idaho, 1 across several states" in block.value for block in app.html)


def test_map_counts_follow_other_filters(app):
    assert button(app, "state_ID").label.strip() == "**ID** 1"
    app.text_input(key="f_query").input("pat's").run()
    assert button(app, "state_ID").label.strip() == "**ID**"
    assert button(app, "state_NJ").label.strip() == "**NJ** 1"


def test_filter_chip_clears_its_filter(app):
    app.selectbox(key="f_state").select("Idaho").run()
    assert button(app, "chip_state").label == "Idaho"
    button(app, "chip_state").click().run()
    assert report_count(app) == f"{len(SAMPLE_RECORDS)} reports"


def test_topic_chip_removes_only_that_topic(app):
    app.button_group(key="f_topics").set_value(["Overtime", "Second job"]).run()
    assert app.info[0].value == "No reports match your search."
    button(app, "chip_topic_Second job").click().run()
    assert app.button_group(key="f_topics").value == ["Overtime"]
    assert report_count(app) == "1 report"


def test_experience_filter_counts_and_chip(app):
    pills = app.button_group(key="f_experience")
    assert any("Jobs to Avoid list 4" in option.content for option in pills.proto.options)
    pills.set_value(["bad"]).run()
    assert report_count(app) == "1 report"
    button(app, "chip_experience_bad").click().run()
    assert app.button_group(key="f_experience").value == []
    assert report_count(app) == f"{len(SAMPLE_RECORDS)} reports"


def test_experience_counts_ignore_their_own_selection(app):
    app.button_group(key="f_experience").set_value(["bad"]).run()
    options = app.button_group(key="f_experience").proto.options
    assert any("Jobs to Avoid list 4" in option.content for option in options)


def test_clear_all_removes_every_filter(app):
    app.selectbox(key="f_state").select("Idaho").run()
    app.text_input(key="f_query").input("lodge").run()
    button(app, "clear_all").click().run()
    assert report_count(app) == f"{len(SAMPLE_RECORDS)} reports"
    assert app.text_input(key="f_query").value == ""


def test_topic_selection_survives_its_count_changing(app):
    app.button_group(key="f_topics").set_value(["Overtime"]).run()
    app.text_input(key="f_query").input("marketplace").run()
    assert app.button_group(key="f_topics").value == ["Overtime"]
    assert report_count(app) == "1 report"


def test_searched_text_stays_out_of_button_labels(app):
    app.text_input(key="f_query").input("$12 **taxi**").run()
    assert not app.exception
    assert button(app, "chip_query").label == "Search"


def test_full_report_includes_others_under_the_same_name(tmp_path):
    rows = [
        record("T-0001", "Acme Hotel"),
        record("T-0002", "ACME hotel", report_description="Another account of the place"),
    ]
    path = tmp_path / "same_name.csv"
    path.write_text(to_csv(rows), encoding="utf-8")
    app = open_app(str(path))
    button(app, "open_T-0001").click().run()
    assert not app.exception
    assert "Reference: T-0002" in captions(app)


def test_failed_source_with_no_copy_shows_friendly_error(tmp_path):
    app = open_app(str(tmp_path / "missing.csv"))
    assert not app.exception
    assert "temporarily unavailable" in app.error[0].value


def test_html_instead_of_csv_is_a_failure(tmp_path):
    path = tmp_path / "page.csv"
    path.write_text("<!DOCTYPE html><html><body>Sign in</body></html>", encoding="utf-8")
    app = open_app(str(path))
    assert "temporarily unavailable" in app.error[0].value


def test_failed_source_with_a_copy_shows_banner(tmp_path, sample_text):
    path = tmp_path / "live.csv"
    path.write_text(sample_text, encoding="utf-8")
    app = open_app(str(path))
    assert report_count(app) == f"{len(SAMPLE_RECORDS)} reports"

    data.fetch_directory.clear()
    path.unlink()
    app.run()
    assert not app.exception
    assert report_count(app) == f"{len(SAMPLE_RECORDS)} reports"
    assert "Showing data from" in app.warning[0].value


@pytest.fixture
def form(sample_path):
    app = open_app(sample_path)
    app.switch_page("views/submit.py").run()
    assert not app.exception
    return app


def key_of(app, suffix):
    version = app.session_state["form_version"] if "form_version" in app.session_state else 0
    return f"sub{version}_{suffix}"


def fill_report(app):
    app.button_group(key=key_of(app, "type")).set_value("report").run()
    app.button_group(key=key_of(app, "overall")).set_value("bad").run()
    app.selectbox(key=key_of(app, "name")).set_value("Pine Lodge").run()
    app.selectbox(key=key_of(app, "state")).set_value("Florida").run()
    app.text_area(key=key_of(app, "details")).input("Hours were cut every single week.").run()
    app.checkbox(key=key_of(app, "declared")).check().run()


def test_form_starts_with_only_the_first_question(form):
    assert not form.selectbox


def page_html(app):
    return " ".join(block.value for block in app.html)


def test_preview_shows_masking_before_anything_is_sent(form):
    form.button_group(key=key_of(form, "type")).set_value("report").run()
    assert "Your words will appear here." in page_html(form)
    form.text_area(key=key_of(form, "details")).input("Call the boss on 876 555 0199 about hours.").run()
    assert "[number removed]" in page_html(form)
    assert "876 555 0199" not in page_html(form)


def test_still_needed_list_shrinks_as_fields_are_filled(form):
    form.button_group(key=key_of(form, "type")).set_value("report").run()
    assert "Enter the employer or agency name." in page_html(form)
    form.selectbox(key=key_of(form, "name")).set_value("Pine Lodge").run()
    assert "Enter the employer or agency name." not in page_html(form)
    assert "Ready to publish." not in page_html(form)
    fill_report(form)
    assert "Ready to publish." in page_html(form)


def test_form_stops_when_required_fields_are_missing(form):
    form.button_group(key=key_of(form, "type")).set_value("report").run()
    button(form, key_of(form, "send")).click().run()
    errors = [element.value for element in form.error]
    assert any("employer or agency name" in text for text in errors)
    assert any("declaration" in text for text in errors)


def test_state_list_is_fixed_and_complete(form):
    form.button_group(key=key_of(form, "type")).set_value("report").run()
    options = form.selectbox(key=key_of(form, "state")).options
    assert "Florida" in options
    assert config.MULTIPLE_STATES in options
    assert len(options) == 52


def test_lists_accept_new_entries_except_state(form):
    """AppTest can't type a new entry, so this checks the setting; a browser test covers typing."""
    form.button_group(key=key_of(form, "type")).set_value("report").run()
    for name in ("name", "city", "position"):
        assert form.selectbox(key=key_of(form, name)).proto.accept_new_options
    assert not form.selectbox(key=key_of(form, "state")).proto.accept_new_options


def test_agency_gets_agency_star_categories(form):
    form.button_group(key=key_of(form, "type")).set_value("review").run()
    assert any(m.value == "Pay" for m in form.markdown)
    form.button_group(key=key_of(form, "entity")).set_value("agency").run()
    assert any(m.value == "Communication" for m in form.markdown)
    assert not any(m.value == "Pay" for m in form.markdown)


def test_job_opportunity_hides_stars(form):
    form.button_group(key=key_of(form, "type")).set_value("job_opportunity").run()
    assert form.text_input(key=key_of(form, "pay")) is not None
    assert not any(m.value == "Pay" for m in form.markdown)
    assert "Choose good, neutral or bad." not in page_html(form)


def text_input_keys(app):
    return [str(widget.key) for widget in app.text_input]


def test_job_opportunity_has_no_numbers_section(form):
    form.button_group(key=key_of(form, "type")).set_value("job_opportunity").run()
    assert not any("The numbers" in m.value for m in form.markdown)
    assert key_of(form, "exp_pay") not in text_input_keys(form)


@pytest.mark.parametrize("kind", ["report", "review"])
def test_numbers_fields_appear_for_reports_and_reviews(form, kind):
    form.button_group(key=key_of(form, "type")).set_value(kind).run()
    assert any("The numbers" in m.value for m in form.markdown)
    keys = text_input_keys(form)
    assert key_of(form, "exp_pay") in keys
    assert key_of(form, "rent") in keys
    assert form.selectbox(key=key_of(form, "hours")).options == config.HOURS_RANGES


def test_numbers_are_optional(form):
    form.button_group(key=key_of(form, "type")).set_value("report").run()
    assert "numbers" not in " ".join(e.value for e in form.error).lower()


def test_numbers_appear_in_the_preview(form):
    form.button_group(key=key_of(form, "type")).set_value("report").run()
    form.text_input(key=key_of(form, "exp_pay")).input("$16/hr").run()
    form.selectbox(key=key_of(form, "hours")).select("30 to 34").run()
    form.text_input(key=key_of(form, "rent")).input("$120").run()
    html = page_html(form)
    assert "Pay $16/hr" in html
    assert "30 to 34 hours a week" in html
    assert "Rent $120 a week" in html


def chips_on_offer(app, overall):
    options = app.button_group(key=key_of(app, f"chips_{overall}")).proto.options
    return [option.content for option in options]


@pytest.mark.parametrize("overall, shown, hidden", [
    ("good", "Good pay", "Low pay"),
    ("bad", "Low pay", "Good pay"),
])
def test_chips_follow_the_rating(form, overall, shown, hidden):
    form.button_group(key=key_of(form, "type")).set_value("review").run()
    form.button_group(key=key_of(form, "overall")).set_value(overall).run()
    assert not form.exception
    assert shown in chips_on_offer(form, overall)
    assert hidden not in chips_on_offer(form, overall)


def test_neutral_offers_both_kinds_of_chip(form):
    form.button_group(key=key_of(form, "type")).set_value("review").run()
    form.button_group(key=key_of(form, "overall")).set_value("neutral").run()
    assert {"Good pay", "Low pay"} <= set(chips_on_offer(form, "neutral"))


def test_chips_tapped_for_a_bad_review_do_not_carry_over_to_a_good_one(form):
    form.button_group(key=key_of(form, "type")).set_value("review").run()
    form.button_group(key=key_of(form, "overall")).set_value("bad").run()
    form.button_group(key=key_of(form, "chips_bad")).set_value(["Low pay"]).run()
    form.button_group(key=key_of(form, "overall")).set_value("good").run()
    assert not form.exception
    assert form.button_group(key=key_of(form, "chips_good")).value == []
    assert "Low pay" not in page_html(form)


def test_preview_shows_the_chosen_rating(form):
    form.button_group(key=key_of(form, "type")).set_value("review").run()
    assert "Choose good, neutral or bad." in page_html(form)
    form.button_group(key=key_of(form, "overall")).set_value("good").run()
    assert "Good experience" in page_html(form)
    assert "Choose good, neutral or bad." not in page_html(form)


def test_successful_submission_confirms_and_resets(form, monkeypatch):
    class Reply:
        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": True, "status": "Live", "record_id": "S-0001"}

    sent = []
    monkeypatch.setattr(requests, "post", lambda url, json, timeout: sent.append(json) or Reply())

    fill_report(form)
    button(form, key_of(form, "send")).click().run()
    assert not form.exception
    assert "will appear in about 10 minutes" in form.success[0].value
    assert sent[0]["public"]["employer_name"] == "Pine Lodge"
    assert sent[0]["public"]["ratings"] == "Overall=bad"
    assert sent[0]["token"] == "test-token"
    assert form.session_state["form_version"] == 1


def test_pay_hours_and_rent_reach_the_payload(form, monkeypatch):
    class Reply:
        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": True, "status": "Live"}

    sent = []
    monkeypatch.setattr(requests, "post", lambda url, json, timeout: sent.append(json) or Reply())

    fill_report(form)
    form.text_input(key=key_of(form, "exp_pay")).input("$16/hr").run()
    form.selectbox(key=key_of(form, "hours")).select("30 to 34").run()
    form.text_input(key=key_of(form, "rent")).input("$120").run()
    button(form, key_of(form, "send")).click().run()
    assert sent[0]["public"]["pay_rate"] == "$16/hr"
    assert sent[0]["public"]["avg_hours"] == "30 to 34"
    assert sent[0]["public"]["rent_per_week"] == "$120"


def test_held_submission_says_it_is_waiting(form, monkeypatch):
    class Reply:
        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": True, "status": "Held"}

    monkeypatch.setattr(requests, "post", lambda *a, **k: Reply())
    fill_report(form)
    button(form, key_of(form, "send")).click().run()
    assert "waiting for review" in form.success[0].value


def test_send_failure_keeps_what_was_entered(form, monkeypatch):
    def fail(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(requests, "post", fail)
    fill_report(form)
    button(form, key_of(form, "send")).click().run()
    assert not form.exception
    assert "Nothing you entered has been lost" in form.error[0].value
    assert form.selectbox(key=key_of(form, "name")).value == "Pine Lodge"
    assert "Hours were cut" in form.text_area(key=key_of(form, "details")).value


def test_form_still_works_when_the_directory_is_down(tmp_path):
    app = open_app(str(tmp_path / "missing.csv"))
    app.switch_page("views/submit.py").run()
    assert not app.exception
    app.button_group(key=key_of(app, "type")).set_value("report").run()
    assert app.selectbox(key=key_of(app, "state")).options


@pytest.mark.parametrize("page, heading", [
    ("views/how_it_works.py", "How it works"),
    ("views/privacy.py", "Privacy"),
    ("views/corrections.py", "Corrections and disputes"),
])
def test_information_pages_load(app, page, heading):
    app.switch_page(page).run()
    assert not app.exception
    assert app.title[0].value == heading


def test_how_it_works_only_explains_badges_in_use(app):
    app.switch_page("views/how_it_works.py").run()
    assert "Multiple reports" in page_html(app)
    assert "Independently verified" in page_html(app)
    assert "Community-reported" not in page_html(app)
    assert "Not verified" not in page_html(app)
    assert "Not yet reviewed" not in page_html(app)


def test_correction_needs_a_problem_and_contact(app):
    app.switch_page("views/corrections.py").run()
    button(app, "cor0_send").click().run()
    assert "how to reach you" in app.error[0].value


def test_correction_is_sent_privately(app, monkeypatch):
    class Reply:
        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": True}

    sent = []
    monkeypatch.setattr(requests, "post", lambda url, json, timeout: sent.append(json) or Reply())
    app.switch_page("views/corrections.py").run()
    app.text_area(key="cor0_problem").input("This is wrong").run()
    app.text_input(key="cor0_contact").input("me@example.com").run()
    button(app, "cor0_send").click().run()
    assert sent[0]["kind"] == "correction"
    assert "public" not in sent[0]
    assert "has been received" in app.success[0].value
