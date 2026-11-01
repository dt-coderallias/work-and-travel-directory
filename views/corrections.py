import streamlit as st

from directory import data, render, submission

ROLES = ["Employer or agency", "The person who reported", "Someone else"]

NEXT_STEPS = [
    ("You send this request", "No account is needed."),
    ("Moderators review it", "Moderators review every request."),
    ("The report may change", "They may correct, label or remove the report."),
]


def field_key(name: str) -> str:
    return f"cor{st.session_state.get('correction_version', 0)}_{name}"


render.page_band("Corrections and disputes", "If something in the directory is wrong, tell us here.")

if st.session_state.get("correction_sent"):
    st.success("Thank you. Your request has been received and will be reviewed.")

form_column, side_column = st.columns([7, 5], gap="large")

with side_column, st.container(key="next_steps"):
    st.subheader("What happens next", anchor=False)
    st.html(render.tiles_html(NEXT_STEPS, numbered=True))

with form_column:
    record_id = st.text_input(
        "Report reference",
        value=st.query_params.get("record", ""),
        placeholder="e.g. L-0042, shown at the bottom of each full report",
        key=field_key("record"),
    )
    role = st.pills("Who are you?", ROLES, key=field_key("role"))
    problem = st.text_area("What is inaccurate?", key=field_key("problem"))
    proposed = st.text_area("What should it say instead? (optional)", key=field_key("proposed"))
    evidence = st.text_input("Link to supporting information (optional)", key=field_key("evidence"))
    contact = st.text_input(
        "How can we reach you?",
        key=field_key("contact"),
        help="Private. Never published. Only used to respond to this request.",
    )

    if st.button("Send request", type="primary", key=field_key("send")):
        if not problem.strip() or not contact.strip():
            st.error("Tell us what is inaccurate and how to reach you.")
        else:
            payload = submission.build_correction(
                record_id, role or "", problem, proposed, evidence, contact,
                data.get_secret("submit_token"),
            )
            try:
                submission.send(payload, data.get_secret("submit_url"))
            except submission.SubmissionError:
                st.error("We couldn't send that just now. Please try again in a moment.")
            else:
                st.session_state["correction_sent"] = True
                st.session_state["correction_version"] = st.session_state.get("correction_version", 0) + 1
                st.rerun()
