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
    assert app.title[0].value == config.APP_NAME


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
    app.selectbox(key=key_of(app, "name")).set_value("Pine Lodge").run()
    app.selectbox(key=key_of(app, "state")).set_value("Florida").run()
    app.text_area(key=key_of(app, "details")).input("Hours were cut every single week.").run()
    app.checkbox(key=key_of(app, "declared")).check().run()


def test_form_starts_with_only_the_first_question(form):
    assert not form.selectbox


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
    assert sent[0]["token"] == "test-token"
    assert form.session_state["form_version"] == 1


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
