import streamlit as st

from directory import config, render

st.set_page_config(page_title=config.APP_NAME, layout="centered", initial_sidebar_state="collapsed")
render.load_styles()

page = st.navigation(
    [
        st.Page("views/browse.py", title="Directory", default=True),
        st.Page("views/submit.py", title="Add information", url_path="add"),
        st.Page("views/how_it_works.py", title="How it works", url_path="how-it-works"),
        st.Page("views/privacy.py", title="Privacy", url_path="privacy"),
        st.Page("views/corrections.py", title="Corrections", url_path="corrections"),
    ],
    position="top",
)
page.run()
render.footer()
