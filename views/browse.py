import streamlit as st

from directory import config, data, render, search

FILTER_DEFAULTS = {"f_query": "", "f_topics": [], "f_state": None, "f_city": None, "f_position": None}


def clear_filters() -> None:
    for key, value in FILTER_DEFAULTS.items():
        st.session_state[key] = value


def use_suggestion(text: str) -> None:
    clear_filters()
    st.session_state["f_query"] = text


def clear_city() -> None:
    st.session_state["f_city"] = None


@st.dialog("Full report", width="large")
def show_record(record) -> None:
    st.html(render.detail_html(record))
    st.page_link(
        "views/corrections.py",
        label="Is this wrong? Request a correction",
        query_params={"record": record["record_id"]},
    )
    st.caption(f"Reference: {record['record_id']}")


def open_linked_record(frame) -> None:
    """Open a report from a shared `?record=L-0042` link, once per visit."""
    record_id = st.query_params.get("record")
    if not record_id or st.session_state.get("opened_link") == record_id:
        return
    st.session_state["opened_link"] = record_id
    matches = frame[frame["record_id"] == record_id]
    if matches.empty:
        st.warning("That report is no longer in the directory.")
    else:
        show_record(matches.iloc[0])


def show_filters(frame) -> None:
    st.text_input(
        "Search",
        key="f_query",
        placeholder="Employer, job, city or concern",
        label_visibility="collapsed",
    )
    st.pills(
        "Reports mention",
        list(config.TOPICS),
        selection_mode="multi",
        key="f_topics",
    )
    active = any(st.session_state.get(key) for key in ("f_state", "f_city", "f_position"))
    with st.expander("State, city and position", expanded=active):
        state_column, city_column, position_column = st.columns(3)
        state = state_column.selectbox(
            "State",
            search.state_options(frame),
            index=None,
            placeholder="All states",
            key="f_state",
            on_change=clear_city,
        )
        city_column.selectbox(
            "City",
            search.city_options(frame, state),
            index=None,
            placeholder="All cities",
            key="f_city",
        )
        position_column.selectbox(
            "Position",
            search.position_options(frame),
            index=None,
            placeholder="All positions",
            key="f_position",
        )


def show_empty_state(frame, query: str) -> None:
    st.info("No reports match your search.")
    st.markdown(
        "**No results does not mean an employer is fine.** "
        "It only means nobody has reported it here yet."
    )
    for suggestion in search.suggest(frame, query):
        st.button(
            f"Did you mean {suggestion}?",
            key=f"suggest_{suggestion}",
            on_click=use_suggestion,
            args=(suggestion,),
        )
    st.button("Clear search and filters", on_click=clear_filters, key="clear_empty")
    if st.button("Add information", key="add_empty"):
        st.switch_page("views/submit.py")


def show_results(results) -> None:
    signature = str(results["record_id"].tolist()[:50]) + str(len(results))
    if st.session_state.get("result_signature") != signature:
        st.session_state["result_signature"] = signature
        st.session_state["visible"] = config.PAGE_SIZE

    visible = st.session_state.get("visible", config.PAGE_SIZE)
    noun = "report" if len(results) == 1 else "reports"
    st.caption(f"{len(results)} {noun}")

    for _, record in results.head(visible).iterrows():
        with st.container(border=True):
            st.html(render.card_html(record))
            if st.button("Read full report", key=f"open_{record['record_id']}"):
                show_record(record)

    if visible < len(results) and st.button("Show more", key="show_more"):
        st.session_state["visible"] = visible + config.PAGE_SIZE
        st.rerun()


def show_data_status(result: data.DirectoryResult) -> None:
    if result.stale and result.loaded_at:
        loaded = result.loaded_at.strftime("%H:%M UTC")
        st.warning(f"We can't reach the latest data right now. Showing data from {loaded}.")


def show_unavailable() -> None:
    st.error("The directory is temporarily unavailable. Please try again in a few minutes.")
    if st.button("Add information", key="add_unavailable"):
        st.switch_page("views/submit.py")


def show_refresh(result: data.DirectoryResult) -> None:
    updated_column, button_column = st.columns([3, 1])
    if result.loaded_at:
        updated_column.caption(f"Updated {result.loaded_at.strftime('%H:%M UTC')}")
    if button_column.button("Refresh", key="refresh"):
        if data.request_refresh():
            st.rerun()
        st.toast("Already refreshed in the last minute.")


def show_directory(result: data.DirectoryResult) -> None:
    frame = result.frame
    show_data_status(result)
    open_linked_record(frame)
    show_filters(frame)

    matches = search.apply_filters(
        frame,
        query=st.session_state.get("f_query", ""),
        state=st.session_state.get("f_state"),
        city=st.session_state.get("f_city"),
        position_group=st.session_state.get("f_position"),
        topics=st.session_state.get("f_topics"),
    )
    if matches.empty:
        show_empty_state(frame, st.session_state.get("f_query", ""))
    else:
        show_results(matches)
    show_refresh(result)


st.title(config.APP_NAME)
st.write(config.APP_TAGLINE)
if st.button("Add information", type="primary", key="add_top"):
    st.switch_page("views/submit.py")
render.disclaimer()

directory_result = data.load_directory()
if directory_result.frame is None:
    show_unavailable()
else:
    show_directory(directory_result)
