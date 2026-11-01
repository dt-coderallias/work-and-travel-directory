import streamlit as st

from directory import config, render

STEPS = [
    (
        "Someone reports",
        "Reports are written by people who have taken part in J-1 Work & Travel programs or "
        "have experience with employers and agencies.",
    ),
    ("It goes live", "New reports go live automatically."),
    ("Moderators read it", "Moderators read new reports after they go live."),
    ("It can be changed", "Moderators can correct or remove a report."),
]

DETAILS = [
    (
        "Where the information comes from",
        f"The data for the first entries was pulled from the {config.LIST_NAME} list, a "
        "spreadsheet shared in the community in 2026. It has no ratings. "
        "New reports are added by visitors.",
    ),
    (
        "Good, neutral or bad",
        "Everyone adding an experience says how it went overall, so a name in this directory "
        "isn't automatically a complaint. That rating is one person's view of one job, not ours.",
    ),
    (
        "Star ratings",
        "Stars show what one person gave on one report. We don't calculate averages, overall "
        "scores or rankings, because a few anonymous ratings aren't a fair verdict on anyone.",
    ),
    (
        "Moderation",
        "Moderators remove personal details such as names and phone numbers, and material that "
        "is malicious, discriminatory, or plainly unsupported. Text they take out is marked "
        f"{config.REDACTION_MARKER}. Otherwise, reports keep the writer's own words.",
    ),
]

render.page_band("How it works", "From a report being written to what happens if it's wrong.")

st.subheader("Reports appear straight away", anchor=False)
st.html(render.tiles_html(STEPS, numbered=True))

st.subheader("What the labels mean", anchor=False)
st.html(render.label_legend_html())
st.write(
    "A report in this directory is someone's account or allegation. It is not a finding that "
    "an employer has done anything wrong, unless it is marked as independently verified. "
    "Having no reports does not mean an employer is fine."
)

st.subheader("The details", anchor=False)
st.html(render.tiles_html(DETAILS))
if st.button("See something wrong? Request a correction"):
    st.switch_page("views/corrections.py")
