import datetime as dt

import streamlit as st

from directory import config, data, render, search, submission

PREVIEW_NAME = "Employer name"
PREVIEW_TEXT = "Your words will appear here."
BEFORE_YOU_START = [
    (
        "It goes live straight away",
        "What you add appears publicly as soon as you publish. Moderators read it afterwards.",
    ),
    ("Keep people out of it", "Please don't name individuals or include phone numbers."),
    (
        "Your contact stays private",
        "Never published. Only used if we need to clarify your report.",
    ),
]


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


def chip_choices(overall: str) -> list[str]:
    """A neutral experience can have both, and so can a form with no rating yet."""
    chips = {"good": config.GOOD_CHIPS, "bad": config.ISSUE_CHIPS}
    return chips.get(overall, config.GOOD_CHIPS + config.ISSUE_CHIPS)


def rating_fields(entry: submission.Submission) -> None:
    entry.overall = st.pills(
        "How was it overall?",
        config.OVERALL_CHOICES,
        format_func=lambda overall: f"{config.EXPERIENCE_ICONS[overall]} {overall.capitalize()}",
        key=field_key("overall"),
    ) or ""
    categories = (
        config.AGENCY_RATINGS if entry.entity_type == "agency" else config.EMPLOYER_RATINGS
    )
    st.markdown("**Rate what you know** (5 stars is best)")
    entry.stars = {name: rating_row(name) for name in categories}
    # Keyed by rating, so complaints already tapped don't carry over to a good review.
    entry.chips = st.pills(
        "What stood out?",
        chip_choices(entry.overall),
        selection_mode="multi",
        key=field_key(f"chips_{entry.overall}"),
    )


def numbers_fields(entry: submission.Submission) -> None:
    """Optional, so a visitor who doesn't know the numbers can still submit."""
    st.markdown("**The numbers** (optional)")
    pay_column, hours_column, rent_column = st.columns(3)
    entry.pay_rate = pay_column.text_input(
        "Pay rate", key=field_key("exp_pay"), placeholder="e.g. $16/hr",
    )
    entry.avg_hours = hours_column.selectbox(
        "Hours a week", config.HOURS_RANGES, index=None, placeholder="Choose", key=field_key("hours"),
    ) or ""
    entry.rent_per_week = rent_column.text_input(
        "Rent a week", key=field_key("rent"), placeholder="e.g. $120",
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


def preview_record(entry: submission.Submission) -> dict:
    """The record as it would be published, including contact masking."""
    public = submission.build_payload(entry, "")["public"]
    public["employer_name"] = public["employer_name"] or PREVIEW_NAME
    if public["report_description"] == submission.STARS_ONLY_TEXT and not submission.has_rating(entry):
        public["report_description"] = PREVIEW_TEXT
    public["topics"] = data.matching_labels(public["report_description"], config.TOPICS)
    public["experience"] = data.experience_of(public["ratings"], public["source"])
    return public


def show_preview(entry: submission.Submission) -> None:
    st.subheader("How it will look", anchor=False)
    st.html(render.card_html(preview_record(entry), linked=False))
    st.caption("This appears publicly as soon as you publish.")
    st.html(render.checklist_html(submission.missing_fields(entry)))


def job_section(entry: submission.Submission, frame) -> None:
    st.html(render.step_heading_html(1, "Who and where"))
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


def words_section(entry: submission.Submission) -> None:
    st.html(render.step_heading_html(3, "In your words"))
    optional = entry.submission_type == "review"
    entry.details = st.text_area(
        "Details (optional)" if optional else "Details",
        key=field_key("details"),
        placeholder="What was it like? Please don't name individuals or include phone numbers.",
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


@st.fragment
def show_form(frame) -> None:
    entry = submission.Submission()

    with st.container(key="type_picker"):
        entry.submission_type = st.pills(
            "What are you adding?",
            list(config.SUBMISSION_TYPES),
            format_func=lambda kind: f"{config.SUBMISSION_ICONS[kind]} {config.SUBMISSION_TYPES[kind]}",
            key=field_key("type"),
            width="stretch",
        ) or ""
    if not entry.submission_type:
        st.html(render.tiles_html(BEFORE_YOU_START))
        return

    form_column, preview_column = st.columns([7, 5], gap="large")
    with form_column:
        with st.container(key="step_job"):
            job_section(entry, frame)
        with st.container(key="step_detail"):
            if entry.submission_type == "job_opportunity":
                st.html(render.step_heading_html(2, "About the job"))
                job_fields(entry)
            else:
                st.html(render.step_heading_html(2, "Your experience"))
                rating_fields(entry)
                numbers_fields(entry)
                period_fields(entry)
        with st.container(key="step_words"):
            words_section(entry)
        if st.button("Publish", type="primary", key=field_key("send"), width="stretch"):
            submit(entry)

    with preview_column, st.container(key="preview"):
        show_preview(entry)


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


render.page_band("Add information", "No account needed. Most of this is a few taps.")
show_receipt()

result = data.load_directory()
show_form(result.frame if result.frame is not None else search.EMPTY_FRAME)
