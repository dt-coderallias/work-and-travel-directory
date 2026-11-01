import streamlit as st

from directory import config, data, render, search

FILTER_DEFAULTS = {
    "f_query": "", "f_experience": [], "f_topics": [], "f_state": None, "f_city": None, "f_position": None,
}


def clear_filters() -> None:
    for key, value in FILTER_DEFAULTS.items():
        st.session_state[key] = value


def use_suggestion(text: str) -> None:
    clear_filters()
    st.session_state["f_query"] = text


def clear_city() -> None:
    st.session_state["f_city"] = None


def toggle_state(state: str) -> None:
    """Tapping the selected tile again clears it."""
    clear_city()
    st.session_state["f_state"] = None if st.session_state.get("f_state") == state else state


def clear_filter(key: str) -> None:
    st.session_state[key] = FILTER_DEFAULTS[key]
    if key == "f_state":
        clear_city()


def remove_choice(key: str, choice: str) -> None:
    st.session_state[key] = [item for item in st.session_state[key] if item != choice]


def current_filters(**overrides) -> dict:
    filters = {
        "query": st.session_state.get("f_query", ""),
        "state": st.session_state.get("f_state"),
        "city": st.session_state.get("f_city"),
        "position_group": st.session_state.get("f_position"),
        "topics": st.session_state.get("f_topics"),
        "experience": st.session_state.get("f_experience"),
    }
    return filters | overrides


def show_report(record) -> None:
    st.html(render.detail_html(record))
    st.page_link(
        "views/corrections.py",
        label="Is this wrong? Request a correction",
        query_params={"record": record["record_id"]},
    )
    st.caption(f"Reference: {record['record_id']}")


@st.dialog("Full report", width="large")
def show_record(record, frame) -> None:
    show_report(record)
    others = search.other_reports(frame, record)
    if not others.empty:
        st.subheader("Other reports under this name", anchor=False)
        for _, other in others.iterrows():
            show_report(other)


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
        show_record(matches.iloc[0], frame)


def show_hero(frame) -> None:
    with st.container(key="hero"):
        st.html(render.eyebrow_html())
        st.title(config.APP_HEADLINE, anchor=False)
        st.write(config.APP_TAGLINE)
        if frame is not None:
            st.text_input(
                "Search",
                key="f_query",
                placeholder="Search an employer, job, city or topic",
                label_visibility="collapsed",
                icon=":material/search:",
            )
        with st.container(horizontal=True, key="hero_row"):
            if frame is not None:
                st.html(render.stats_html(search.directory_stats(frame)), width="content")
            if st.button("Add information", type="primary", key="add_top"):
                st.switch_page("views/submit.py")
        render.disclaimer()


def show_map(frame) -> None:
    """Counts ignore the state and city chosen, so other tiles stay meaningful."""
    counts = search.state_counts(search.apply_filters(frame, **current_filters(state=None, city=None)))
    with st.container(key="map_panel"):
        st.subheader("Where was the job?", anchor=False)
        with st.container(key="state_map"):
            for state, (abbreviation, _, _) in config.STATE_TILES.items():
                count = counts[state]
                noun = "report" if count == 1 else "reports"
                st.button(
                    f"**{abbreviation}** {count or ''}",
                    key=f"state_{abbreviation}",
                    help=f"{state}: {count} {noun}",
                    on_click=toggle_state,
                    args=(state,),
                )
        st.html(render.state_map_css(counts, st.session_state.get("f_state")))
        st.caption("More reports usually means more participants went there, not that a state is worse.")


def experience_pill(experience: str, count: int) -> str:
    label, _ = config.EXPERIENCE_LABELS[experience]
    return f"{config.EXPERIENCE_ICONS[experience]} {label} {count}"


def show_experience_filter(frame) -> None:
    """Counts ignore this filter, so choosing one leaves the others meaningful."""
    counts = search.experience_counts(search.apply_filters(frame, **current_filters(experience=None)))
    st.pills(
        "Show only",
        list(config.EXPERIENCE_LABELS),
        selection_mode="multi",
        key="f_experience",
        format_func=lambda experience: experience_pill(experience, counts[experience]),
    )


def show_filters(frame, matches) -> None:
    show_experience_filter(frame)
    counts = search.topic_counts(matches)
    st.pills(
        "Reports mention",
        list(config.TOPICS),
        selection_mode="multi",
        key="f_topics",
        format_func=lambda topic: f"{config.TOPIC_ICONS[topic]} {topic} {counts[topic]}",
    )
    active = any(st.session_state.get(key) for key in ("f_city", "f_position"))
    with st.expander("City, position and state list", expanded=active):
        state = st.selectbox(
            "State",
            search.state_choices(frame),
            index=None,
            placeholder="All states",
            key="f_state",
            on_change=clear_city,
        )
        st.selectbox(
            "City",
            search.city_options(frame, state),
            index=None,
            placeholder="All cities",
            key="f_city",
        )
        st.selectbox(
            "Position",
            search.position_options(frame),
            index=None,
            placeholder="All positions",
            key="f_position",
        )


def active_chips() -> list[tuple]:
    """Each filter in use as (name, label, action, args).

    Button labels render as Markdown, so the visitor's search and community-
    written city names appear only as "Search" and "City".
    """
    chips = []
    if st.session_state.get("f_query"):
        chips.append(("query", "Search", clear_filter, ("f_query",)))
    state = st.session_state.get("f_state")
    if state:
        chips.append(("state", state if state in config.STATE_TILES else "State", clear_filter, ("f_state",)))
    if st.session_state.get("f_city"):
        chips.append(("city", "City", clear_filter, ("f_city",)))
    position = st.session_state.get("f_position")
    if position:
        chips.append(("position", position, clear_filter, ("f_position",)))
    for experience in st.session_state.get("f_experience") or []:
        label, _ = config.EXPERIENCE_LABELS[experience]
        chips.append((f"experience_{experience}", label, remove_choice, ("f_experience", experience)))
    for topic in st.session_state.get("f_topics") or []:
        chips.append((f"topic_{topic}", topic, remove_choice, ("f_topics", topic)))
    return chips


def show_filter_chips() -> None:
    chips = active_chips()
    if not chips:
        return
    with st.container(horizontal=True, key="filter_chips"):
        for name, label, action, args in chips:
            st.button(
                label,
                key=f"chip_{name}",
                icon=":material/close:",
                icon_position="right",
                on_click=action,
                args=args,
            )
        if len(chips) > 1:
            st.button("Clear all", key="clear_all", type="tertiary", on_click=clear_filters)


def show_empty_state(frame, query: str) -> None:
    with st.container(key="empty_panel"):
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


def show_results_head(results) -> None:
    noun = "report" if len(results) == 1 else "reports"
    state = st.session_state.get("f_state")
    across = int((results["state"] == config.MULTIPLE_STATES).sum())
    with st.container(key="results_head"):
        st.caption(f"{len(results)} {noun}")
        if state and across:
            st.html(render.state_split_html(state, len(results) - across, across))
        show_filter_chips()


def show_results(results, frame) -> None:
    signature = str(results["record_id"].tolist()[:50]) + str(len(results))
    if st.session_state.get("result_signature") != signature:
        st.session_state["result_signature"] = signature
        st.session_state["visible"] = config.PAGE_SIZE

    visible = st.session_state.get("visible", config.PAGE_SIZE)
    show_results_head(results)

    for _, record in results.head(visible).iterrows():
        with st.container(key=f"card_{record['record_id']}"):
            st.html(render.card_html(record))
            if st.button("Read full report", key=f"open_{record['record_id']}"):
                show_record(record, frame)

    if visible < len(results) and st.button("Show more", key="show_more", width="stretch"):
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

    matches = search.apply_filters(frame, **current_filters())
    if any(st.session_state.get(key) for key in FILTER_DEFAULTS):
        render.compact_on_phones()

    rail, main = st.columns([5, 7], gap="large")
    with rail, st.container(key="rail"):
        show_map(frame)
        show_filters(frame, matches)
    with main:
        if matches.empty:
            show_results_head(matches)
            show_empty_state(frame, st.session_state.get("f_query", ""))
        else:
            show_results(matches, frame)
        show_refresh(result)


directory_result = data.load_directory()
show_hero(directory_result.frame)
if directory_result.frame is None:
    show_unavailable()
else:
    show_directory(directory_result)
