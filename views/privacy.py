import streamlit as st

from directory import config, render

SECTIONS = [
    (
        "What we collect",
        "You don't need an account. When you add information, we store what you enter. If you "
        "choose to leave contact details, we keep them privately and use them only to clarify "
        "your report or respond to a correction request. They are never published.",
    ),
    (
        "What becomes public",
        "Everything you enter on the Add information page appears publicly, straight away, "
        "except your contact details. Please don't include your own name, other people's names, "
        "phone numbers, addresses or identification documents.",
    ),
    (
        "Where it is stored",
        "Submissions are stored in Google Sheets. The site is hosted on Streamlit Community "
        "Cloud in the United States.",
    ),
    (
        "Removing information",
        "To have something corrected or removed, including your own report, use the "
        "Corrections page.",
    ),
]

render.page_band("Privacy", f"This directory is run by {config.OPERATOR_NAME}.")
st.html(render.tiles_html(SECTIONS))
if st.button("Go to Corrections"):
    st.switch_page("views/corrections.py")
