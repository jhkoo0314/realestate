"""부동산 매물관리 도구의 입구: 공통 화면과 메뉴 전환만 담당한다."""

import streamlit as st

from services.backup_service import get_backup_status
from services.listing_status_service import apply_past_due_move_out_statuses
from ui.building_management import render_building_management
from ui.advertisement_management import render_advertisement_management
from ui.contract_management import render_contract_management
from ui.consultation_management import render_consultation_management
from ui.dashboard import render_dashboard
from ui.listing_form import render_listing_form, reset_for_new_listing
from ui.today_tasks import render_today_tasks


PAGE_TODAY = "오늘 할 일"
PAGE_DASHBOARD = "매물 현황 리스트"
PAGE_LISTING = "매물 등록·수정"
PAGE_BUILDINGS = "건물·호실 관리"
PAGE_CONTRACTS = "계약관리"
PAGE_CONSULTATIONS = "상담관리"
PAGE_ADVERTISEMENTS = "광고관리"
PAGES = [PAGE_TODAY, PAGE_DASHBOARD, PAGE_LISTING, PAGE_BUILDINGS, PAGE_CONTRACTS, PAGE_CONSULTATIONS, PAGE_ADVERTISEMENTS]

st.set_page_config(page_title="매물관리", page_icon="🏠", layout="wide", initial_sidebar_state="collapsed")


def go_to_listing() -> None:
    reset_for_new_listing()
    st.session_state.selected_page = PAGE_LISTING


def apply_task_shortcut() -> None:
    """오늘 할 일 표의 계약·상담 바로가기를 해당 상세 화면으로 연결한다."""
    task_type = st.query_params.get("open_task")
    raw_record_id = st.query_params.get("record_id")
    if task_type not in {"contract", "consultation"}:
        return
    try:
        record_id = int(str(raw_record_id))
    except (TypeError, ValueError):
        record_id = 0
    if record_id <= 0:
        st.query_params.clear()
        return

    if task_type == "contract":
        st.session_state.selected_page = PAGE_CONTRACTS
        st.session_state["contract_management_mode"] = "계약 조회·수정"
        st.session_state["contract_has_searched"] = True
        st.session_state["contract_edit_target_id"] = record_id
        for key, value in {
            "contract_query": "",
            "contract_status_filter": [],
            "contract_end_start": None,
            "contract_end_end": None,
            "contract_expiring_soon": False,
        }.items():
            st.session_state[key] = value
    else:
        st.session_state.selected_page = PAGE_CONSULTATIONS
        st.session_state["consultation_management_mode"] = "상담 조회·수정"
        st.session_state["consultation_has_searched"] = True
        st.session_state["consultation_edit_target_id"] = record_id
        for key, value in {
            "consultation_query": "",
            "consultation_category_filter": [],
            "consultation_status_filter": [],
            "consultation_stage_filter": [],
            "consultation_closed_reason_filter": [],
            "consultation_start": None,
            "consultation_end": None,
            "consultation_due_only": False,
        }.items():
            st.session_state[key] = value
    st.query_params.clear()


def apply_styles() -> None:
    st.markdown("""<style>
    header[data-testid="stHeader"] { visibility: hidden; height: 0rem; }
    .block-container { max-width: 1440px; padding-top: 1rem; padding-bottom: 2.5rem; }
    [data-testid="stSidebar"] { display: none; }
    .app-title { font-size: 1.5rem; font-weight: 700; margin: 0; line-height: 1.3; }
    .app-subtitle, .section-note { color: #667085; font-size: 0.88rem; margin-top: 0.15rem; }
    .status-line { color: #475467; font-size: 0.88rem; padding: 0.6rem 0.85rem; background: #f8fafc; border: 1px solid #e4e7ec; border-radius: 0.45rem; margin: 0.75rem 0 1.25rem; }
    .empty-panel { border: 1px solid #d0d5dd; border-radius: 0.65rem; background: #ffffff; padding: 2.3rem 1.8rem; text-align: center; margin-top: 1.25rem; }
    .empty-panel h2 { font-size: 1.25rem; margin: 0 0 0.6rem; }
    .empty-panel p { color: #475467; margin: 0; }
    div[data-testid="stRadio"] > div { gap: 0.25rem; }
    div[data-testid="stRadio"] label { border: 1px solid #d0d5dd; border-radius: 0.4rem; padding: 0.45rem 0.75rem; min-height: auto; }
    </style>""", unsafe_allow_html=True)


def render_backup_status() -> None:
    status = get_backup_status()
    if not status:
        st.caption("백업 상태: 아직 자동 백업 기록이 없습니다.")
        return
    if status.get("success"):
        size = status.get("backup_size", 0)
        st.caption(f"백업 상태: {status.get('completed_at', status['recorded_at'])} · 완료 · {size:,}바이트")
    else:
        st.warning(f"저장은 완료됐지만 자동 백업에 실패했습니다. {status.get('message', '백업 상태를 확인해 주세요.')}")


def main() -> None:
    apply_styles()
    if "selected_page" not in st.session_state:
        st.session_state.selected_page = PAGE_TODAY
    requested_page = st.session_state.pop("requested_page", None)
    if requested_page in PAGES:
        st.session_state.selected_page = requested_page
    apply_task_shortcut()
    try:
        past_due_move_out_count = apply_past_due_move_out_statuses()
    except FileNotFoundError:
        past_due_move_out_count = 0

    title_column, action_column = st.columns([4, 1])
    with title_column:
        st.markdown("<p class='app-title'>🏠 매물관리</p><p class='app-subtitle'>사무실 내부용 · 원룸·투룸 매물 관리</p>", unsafe_allow_html=True)
    with action_column:
        if st.session_state.selected_page != PAGE_BUILDINGS:
            st.button("＋ 새 매물 등록", type="primary", width="stretch", on_click=go_to_listing)

    st.radio("주요 메뉴", PAGES, horizontal=True, key="selected_page", label_visibility="collapsed")
    st.markdown("<div class='status-line'>실행 상태: 신규 등록·재등록·현재 매물 수정 가능 · 매물 현황 리스트에서 조회·필터와 확인 업무를 처리할 수 있습니다.</div>", unsafe_allow_html=True)
    if past_due_move_out_count:
        st.info(f"퇴실 예정일이 지난 매물 {past_due_move_out_count}건을 공실로 자동 변경했습니다.")
    render_backup_status()

    if st.session_state.selected_page == PAGE_TODAY:
        render_today_tasks()
    elif st.session_state.selected_page == PAGE_DASHBOARD:
        render_dashboard(go_to_listing)
    elif st.session_state.selected_page == PAGE_LISTING:
        render_listing_form()
    elif st.session_state.selected_page == PAGE_BUILDINGS:
        render_building_management()
    elif st.session_state.selected_page == PAGE_CONTRACTS:
        render_contract_management()
    elif st.session_state.selected_page == PAGE_CONSULTATIONS:
        render_consultation_management()
    else:
        render_advertisement_management()


if __name__ == "__main__":
    main()
