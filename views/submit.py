import datetime as dt

import streamlit as st

from directory import config, data, search, submission


def field_key(name: str) -> str:
    """Widget keys carry a version, so a finished form can start fresh."""
    return f"sub{st.session_state.get('form_version', 0)}_{name}"


def rating_row(name: str):
    # A horizontal container stays on one line on phones; st.columns would stack.
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown(name, width=140)
        return st.feedback("stars", key=field_key(f"star_{name}"))


def job_fields(entry: submission.Submission) -> None:
    entry.pay_rate = st.text_input("Pay rate", key=field_key("pay"), placeholder="e.g. $16 an hour")
    entry.housing = st.text_input("Housing provided?", key=field_key("housing"))
    entry.sponsor = st.text_input("Agency or sponsor", key=field_key("sponsor"))
    entry.link = st.text_input("Link to the listing", key=field_key("link"))


def rating_fields(entry: submission.Submission) -> None:
    categories = (
        config.AGENCY_RATINGS if entry.entity_type == "agency" else config.EMPLOYER_RATINGS
    )
    st.markdown("**Rate what you know** (5 stars is best)")
    entry.stars = {name: rating_row(name) for name in categories}
    entry.chips = st.pills(
        "What stood out?",
        config.ISSUE_CHIPS,
        selection_mode="multi",
        key=field_key("chips"),
    )


def period_fields(entry: submission.Submission) -> None:
    this_year = dt.date.today().year
    year = st.selectbox(
        "What year was this?",
        list(range(this_year, this_year - 8, -1)),
        index=None,
        placeholder="Year",
        key=field_key("year"),
    )
    entry.year = str(year) if year else ""


@st.fragment
def show_form(frame) -> None:
    entry = submission.Submission()

    entry.submission_type = st.pills(
        "What are you adding?",
        list(config.SUBMISSION_TYPES),
        format_func=config.SUBMISSION_TYPES.get,
        key=field_key("type"),
    ) or ""
    if not entry.submission_type:
        return

    entry.entity_type = st.pills(
        "Is this about an employer or an agency?",
        list(config.ENTITY_TYPES),
        format_func=config.ENTITY_TYPES.get,
        default="employer",
        required=True,
        key=field_key("entity"),
    )

    entry.name = st.selectbox(
        "Name",
        search.employer_options(frame),
        index=None,
        accept_new_options=True,
        placeholder="Start typing, or enter a new name",
        key=field_key("name"),
    ) or ""

    entry.state = st.selectbox(
        "State",
        config.US_STATES + [config.MULTIPLE_STATES],
        index=None,
        placeholder="Start typing a state",
        key=field_key("state"),
    ) or ""

    city_column, position_column = st.columns(2)
    entry.city = city_column.selectbox(
        "City",
        search.city_options(frame, entry.state or None),
        index=None,
        accept_new_options=True,
        placeholder="Start typing",
        key=field_key("city"),
    ) or ""
    entry.position = position_column.selectbox(
        "Position",
        search.form_position_options(frame),
        index=None,
        accept_new_options=True,
        placeholder="Start typing",
        key=field_key("position"),
    ) or ""

    if entry.submission_type == "job_opportunity":
        job_fields(entry)
    else:
        rating_fields(entry)
        period_fields(entry)

    optional = entry.submission_type == "review"
    entry.details = st.text_area(
        "Details (optional)" if optional else "Details",
        key=field_key("details"),
        placeholder="What happened? Please don't name individuals or include phone numbers.",
    )
    entry.contact = st.text_input(
        "Contact (optional)",
        key=field_key("contact"),
        help="Private. Never published. Only used if we need to clarify your report.",
    )
    entry.declared = st.checkbox(
        "This is truthful to the best of my knowledge, and I understand it will appear "
        "publicly straight away.",
        key=field_key("declared"),
    )

    if st.button("Publish", type="primary", key=field_key("send")):
        submit(entry)


def submit(entry: submission.Submission) -> None:
    problems = submission.missing_fields(entry)
    if problems:
        for problem in problems:
            st.error(problem)
        return

    payload = submission.build_payload(entry, data.get_secret("submit_token"))
    try:
        with st.spinner("Sending..."):
            reply = submission.send(payload, data.get_secret("submit_url"))
    except submission.SubmissionError:
        st.error(
            "We couldn't send that just now. Nothing you entered has been lost, "
            "so please try again in a moment."
        )
        return

    st.session_state["receipt"] = {"status": reply.get("status"), "name": entry.name}
    st.session_state["form_version"] = st.session_state.get("form_version", 0) + 1
    st.rerun()


def show_receipt() -> None:
    receipt = st.session_state.get("receipt")
    if not receipt:
        return
    if receipt["status"] == "Held":
        st.success(f"Thank you. Your report on {receipt['name']} was received and is waiting for review.")
    else:
        st.success(f"Thank you. Your report on {receipt['name']} will appear in about 10 minutes.")


st.title("Add information")
st.write("No account needed. Most of this is a few taps.")
show_receipt()

result = data.load_directory()
show_form(result.frame if result.frame is not None else search.EMPTY_FRAME)
