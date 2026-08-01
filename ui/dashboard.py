"""오늘의 매물 현황 화면."""

import streamlit as st

from storage.database import DATABASE_PATH, get_database_summary


def render_dashboard(go_to_listing) -> None:
    st.subheader("오늘의 매물 현황")
    st.markdown("<p class='section-note'>오늘 확인하거나 처리할 매물을 보는 화면입니다.</p>", unsafe_allow_html=True)
    try:
        summary = get_database_summary()
        st.caption(f"데이터 파일: {DATABASE_PATH} · 건물 {summary['buildings']}건 · 호실 {summary['units']}건 · 매물 {summary['listings']}건")
    except FileNotFoundError as error:
        st.error(str(error))
    st.markdown("""<div class="empty-panel"><h2>아직 등록된 매물이 없습니다</h2><p>현재 운영할 첫 매물부터 등록하면, 이후에는 이곳에서 오늘 할 일을 확인할 수 있습니다.</p></div>""", unsafe_allow_html=True)
    _, button_column, _ = st.columns([3, 2, 3])
    with button_column:
        st.button("현재 운영할 첫 매물 등록", type="primary", use_container_width=True, on_click=go_to_listing)
