import streamlit as st

from directory import config

st.title("Privacy")
st.write(f"This directory is run by {config.OPERATOR_NAME}.")

st.header("What we collect")
st.write(
    "You don't need an account. When you add information, we store what you enter. If you "
    "choose to leave contact details, we keep them privately and use them only to clarify your "
    "report or respond to a correction request. They are never published."
)

st.header("What becomes public")
st.write(
    "Everything you enter on the Add information page appears publicly, straight away, except "
    "your contact details. Please don't include your own name, other people's names, phone "
    "numbers, addresses or identification documents."
)

st.header("Where it is stored")
st.write(
    "Submissions are stored in Google Sheets. The site is hosted on Streamlit Community Cloud "
    "in the United States."
)

st.header("Removing information")
st.write("To have something corrected or removed, including your own report, use the Corrections page.")
if st.button("Go to Corrections"):
    st.switch_page("views/corrections.py")
