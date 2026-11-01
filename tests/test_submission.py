import pytest
import requests

from directory import config, data, submission
from directory.submission import Submission


def report(**values):
    base = dict(
        submission_type="report", name="Acme", state="Ohio", overall="bad",
        details="They cut everyone's hours in June.", declared=True,
    )
    return Submission(**{**base, **values})


def test_stars_convert_to_one_through_five():
    assert submission.ratings_text({"Pay": 0, "Hours": 4, "Housing": None}) == "Pay=1;Hours=5"


def test_no_stars_gives_blank_ratings():
    assert submission.ratings_text({"Pay": None}) == ""


def test_overall_rating_comes_before_the_stars():
    assert submission.ratings_text({"Pay": 3}, "good") == "Overall=good;Pay=4"


@pytest.mark.parametrize("overall", config.OVERALL_CHOICES)
def test_overall_reaches_the_public_record_as_a_marker(overall):
    public = submission.build_payload(report(overall=overall), "t")["public"]
    assert data.experience_of(public["ratings"], public["source"]) == overall


@pytest.mark.parametrize("kind", ["report", "review"])
def test_experiences_must_say_how_it_went(kind):
    problems = submission.missing_fields(report(submission_type=kind, overall=""))
    assert "Choose good, neutral or bad." in problems


def test_job_opportunities_have_no_overall_rating():
    entry = report(submission_type="job_opportunity", overall="")
    assert submission.missing_fields(entry) == []
    assert submission.build_payload(entry, "t")["public"]["ratings"] == ""


def test_complete_report_passes():
    assert submission.missing_fields(report()) == []


@pytest.mark.parametrize("values, phrase", [
    ({"submission_type": ""}, "what you are adding"),
    ({"name": "  "}, "employer or agency name"),
    ({"state": ""}, "state"),
    ({"details": "short"}, "more details"),
    ({"declared": False}, "declaration"),
])
def test_report_requirements(values, phrase):
    assert any(phrase in problem for problem in submission.missing_fields(report(**values)))


def test_review_can_be_stars_only():
    entry = report(submission_type="review", details="", stars={"Pay": 2})
    assert submission.missing_fields(entry) == []


def test_review_can_be_chips_only():
    entry = report(submission_type="review", details="", chips=["Low pay"])
    assert submission.missing_fields(entry) == []


def test_empty_review_is_refused():
    entry = report(submission_type="review", details="", stars={"Pay": None})
    assert submission.missing_fields(entry)


def test_job_opportunity_needs_details():
    assert submission.missing_fields(report(submission_type="job_opportunity", details=""))


def test_description_includes_chips_and_words():
    text = submission.compose_description(report(chips=["Low pay", "Hours cut"]))
    assert text.startswith("What stood out: Low pay, Hours cut.")
    assert "cut everyone's hours" in text


def test_stars_only_review_has_honest_text():
    entry = report(submission_type="review", details="", stars={"Pay": 2})
    assert submission.compose_description(entry) == submission.STARS_ONLY_TEXT


def test_job_fields_appear_in_description():
    entry = report(submission_type="job_opportunity", pay_rate="$16", sponsor="Example Sponsor")
    text = submission.compose_description(entry)
    assert "Pay rate: $16" in text
    assert "Agency or sponsor: Example Sponsor" in text


def test_contact_details_never_reach_the_public_payload():
    entry = report(contact="private-contact@example.com")
    payload = submission.build_payload(entry, "token")
    assert "private-contact" not in str(payload["public"])
    assert payload["private"]["contact"] == "private-contact@example.com"


def test_public_payload_only_holds_public_columns():
    payload = submission.build_payload(report(), "token")
    assert set(payload["public"]) <= set(config.PUBLIC_COLUMNS)


def test_token_stays_out_of_the_public_object():
    payload = submission.build_payload(report(), "secret-token")
    assert "secret-token" not in str(payload["public"])
    assert "secret-token" not in str(payload["private"])


def test_public_text_has_contacts_masked():
    payload = submission.build_payload(report(details="Call the boss on 876-555-1234 right now"), "t")
    assert "555-1234" not in payload["public"]["report_description"]
    assert "876-555-1234" in payload["private"]["original_details"]


def test_new_reports_are_unreviewed_and_never_verified():
    public = submission.build_payload(report(), "t")["public"]
    assert public["review_state"] == "unreviewed"
    assert public["verification_status"] == "community_reported"
    assert public["source"] == config.SOURCE_FORM


def test_job_opportunities_start_as_not_verified():
    public = submission.build_payload(report(submission_type="job_opportunity"), "t")["public"]
    assert public["verification_status"] == config.UNVERIFIED


def test_each_payload_has_a_new_nonce():
    assert submission.build_payload(report(), "t")["nonce"] != submission.build_payload(report(), "t")["nonce"]


def test_experience_period_is_the_year():
    public = submission.build_payload(report(year="2026"), "t")["public"]
    assert public["experience_period"] == "2026"


def test_correction_is_entirely_private():
    payload = submission.build_correction("L-0001", "Employer", "Wrong", "", "", "a@b.com", "t")
    assert "public" not in payload
    assert payload["kind"] == "correction"


class FakeResponse:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        if self.body is None:
            raise ValueError("not json")
        return self.body


def test_send_returns_the_reply(monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse({"ok": True, "status": "Live"}))
    assert submission.send({}, "https://example.invalid")["status"] == "Live"


@pytest.mark.parametrize("response", [
    FakeResponse({"ok": False, "error": "bad token"}),
    FakeResponse({"ok": True}, status=500),
    FakeResponse(None),
])
def test_send_raises_on_a_bad_reply(monkeypatch, response):
    monkeypatch.setattr(requests, "post", lambda *a, **k: response)
    with pytest.raises(submission.SubmissionError):
        submission.send({}, "https://example.invalid")


def test_send_raises_when_unreachable(monkeypatch):
    def fail(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(requests, "post", fail)
    with pytest.raises(submission.SubmissionError):
        submission.send({}, "https://example.invalid")


def test_send_refuses_without_an_address():
    with pytest.raises(submission.SubmissionError):
        submission.send({}, "")
