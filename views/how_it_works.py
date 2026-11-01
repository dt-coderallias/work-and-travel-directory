import streamlit as st

from directory import config

st.title("How it works")

st.header("Where the information comes from")
st.write(
    "Reports are written by people who have taken part in J-1 Work & Travel programs or have "
    "experience with employers and agencies. The first entries come from a spreadsheet shared "
    "in the community in 2026. New reports are added by visitors."
)

st.header("Reports appear straight away")
st.write(
    "New reports go live automatically. Moderators read them afterwards and can correct or "
    "remove them. A report marked \"Not yet reviewed by a moderator\" hasn't been read yet."
)

st.header("What the labels mean")
for label, explanation in config.VERIFICATION_LABELS.values():
    st.markdown(f"**{label}:** {explanation}")
st.write(
    "A report in this directory is someone's account or allegation. It is not a finding that "
    "an employer has done anything wrong, unless it is marked as independently verified. "
    "Having no reports does not mean an employer is fine."
)

st.header("Star ratings")
st.write(
    "Stars show what one person gave on one report. We don't calculate averages, overall "
    "scores or rankings, because a few anonymous ratings aren't a fair verdict on anyone."
)

st.header("Moderation")
st.write(
    "Moderators remove personal details such as names and phone numbers, and material that is "
    "malicious, discriminatory, or plainly unsupported. Text they take out is marked "
    f"{config.REDACTION_MARKER}. Otherwise, reports keep the writer's own words."
)
if st.button("See something wrong? Request a correction"):
    st.switch_page("views/corrections.py")
