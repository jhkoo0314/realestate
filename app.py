"""부동산 매물관리 도구의 입구: 공통 화면과 메뉴 전환만 담당한다."""

import streamlit as st

from ui.building_management import render_building_management
from ui.dashboard import render_dashboard
from ui.listing_form import render_listing_form


PAGE_DASHBOARD = "오늘의 매물 현황"
PAGE_LISTING = "매물 등록·수정"
PAGE_BUILDINGS = "건물·호실 관리"
PAGES = [PAGE_DASHBOARD, PAGE_LISTING, PAGE_BUILDINGS]

st.set_page_config(page_title="매물관리", page_icon="🏠", layout="wide", initial_sidebar_state="collapsed")


def go_to_listing() -> None:
    st.session_state.selected_page = PAGE_LISTING


def apply_styles() -> None:
    st.markdown("""<style>
    .block-container { max-width: 1440px; padding-top: 2rem; padding-bottom: 3rem; }
    [data-testid="stSidebar"] { display: none; }
    .app-title { font-size: 1.65rem; font-weight: 700; margin: 0; }
    .app-subtitle, .section-note { color: #667085; font-size: 0.93rem; margin-top: 0.2rem; }
    .status-line { color: #475467; font-size: 0.88rem; padding: 0.65rem 0.85rem; background: #f8fafc; border: 1px solid #e4e7ec; border-radius: 0.45rem; margin: 0.8rem 0 1.4rem; }
    .empty-panel { border: 1px solid #d0d5dd; border-radius: 0.65rem; background: #ffffff; padding: 2.3rem 1.8rem; text-align: center; margin-top: 1.25rem; }
    .empty-panel h2 { font-size: 1.25rem; margin: 0 0 0.6rem; }
    .empty-panel p { color: #475467; margin: 0; }
    div[data-testid="stRadio"] > div { gap: 0.25rem; }
    div[data-testid="stRadio"] label { border: 1px solid #d0d5dd; border-radius: 0.4rem; padding: 0.45rem 0.75rem; min-height: auto; }
    </style>""", unsafe_allow_html=True)


def main() -> None:
    apply_styles()
    if "selected_page" not in st.session_state:
        st.session_state.selected_page = PAGE_DASHBOARD

    title_column, action_column = st.columns([4, 1])
    with title_column:
        st.markdown("<p class='app-title'>🏠 매물관리</p><p class='app-subtitle'>사무실 내부용 · 원룸·투룸 매물 관리</p>", unsafe_allow_html=True)
    with action_column:
        st.button("＋ 새 매물 등록", type="primary", use_container_width=True, on_click=go_to_listing)

    st.radio("주요 메뉴", PAGES, horizontal=True, key="selected_page", label_visibility="collapsed")
    st.markdown("<div class='status-line'>실행 상태: 신규 매물 등록 가능 · 기존 건물 검색과 재등록은 다음 단계에서 연결합니다.</div>", unsafe_allow_html=True)

    if st.session_state.selected_page == PAGE_DASHBOARD:
        render_dashboard(go_to_listing)
    elif st.session_state.selected_page == PAGE_LISTING:
        render_listing_form()
    else:
        render_building_management()


if __name__ == "__main__":
    main()
