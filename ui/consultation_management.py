"""매물 회차별 상담 CRM 화면."""

from __future__ import annotations

from datetime import date

import streamlit as st

from services.consultation_service import CONSULTATION_STATUSES, CONSULTATION_TYPES, save_consultation, save_consultation_changes, validate_consultation
from storage.consultation_repository import get_consultation_detail, get_consultations
from storage.listing_repository import search_listing_rounds


def _listing_label(item: dict) -> str:
    unit = item["unit_number"] if item["unit_number"].endswith("호") else f"{item['unit_number']}호"
    return f"{item['building_name']} · {item['lot_address']} · {unit} · 접수일 {item['received_date']} · {item['listing_status']}"


def _rows(items: list[dict]) -> list[dict]:
    today = date.today().isoformat()
    return [{
        "건물명": item["building_name"], "호실": item["unit_number"], "고객 이름": item["customer_name"],
        "매물 접수일": item["received_date"], "상담일": item["consulted_date"], "상담 종류": item["consultation_type"],
        "상담 상태": item["consultation_status"], "다음 연락일": item["next_contact_date"] or "-",
        "다음 연락 필요": "확인 필요" if item["next_contact_date"] and item["next_contact_date"] <= today and item["consultation_status"] != "종료" else "-",
        "상담 내용": item["consultation_note"],
    } for item in items]


def _render_registration() -> None:
    st.markdown("#### 상담 등록")
    st.caption("상담할 당시의 매물 기록을 선택한 뒤 새 상담을 추가합니다. 기존 상담 기록은 바꾸지 않습니다.")
    query = st.text_input("연결할 매물 회차 찾기", key="consultation_listing_query", placeholder="건물명·지번·호수 중 2글자 이상")
    selected = st.session_state.get("consultation_selected_listing")
    if selected is None:
        if len(query.strip()) < 2:
            st.info("상담할 매물 기록을 찾기 위해 2글자 이상 입력해 주세요.")
            return
        results = search_listing_rounds(query)
        if not results:
            st.info("조건에 맞는 매물 기록이 없습니다.")
            return
        for item in results:
            if st.button(_listing_label(item), key=f"consultation_listing_{item['listing_id']}", use_container_width=True):
                st.session_state["consultation_selected_listing"] = item
                st.rerun()
        return
    st.success(f"선택한 매물 기록: {_listing_label(selected)}")
    if st.button("다른 매물 기록 선택", key="clear_consultation_listing"):
        st.session_state.pop("consultation_selected_listing", None)
        st.rerun()
    with st.form(f"consultation_create_{selected['listing_id']}"):
        left, middle, right = st.columns(3)
        with left:
            customer_name = st.text_input("고객 이름 *")
            customer_phone = st.text_input("고객 연락처 *", placeholder="예: 010-1234-5678")
        with middle:
            consulted_date = st.date_input("상담일 *", value=date.today())
            consultation_type = st.selectbox("상담 종류 *", CONSULTATION_TYPES)
        with right:
            consultation_status = st.selectbox("상담 상태 *", CONSULTATION_STATUSES)
            next_contact = st.date_input("다음 연락일", value=None)
        note = st.text_area("상담 내용 *", placeholder="예: 방문 일정 협의, 가격 안내")
        confirmed = st.checkbox("선택한 매물 기록에 새 상담을 추가하는 것을 확인했습니다.")
        submitted = st.form_submit_button("새 상담 등록", type="primary", disabled=not confirmed)
    if submitted:
        consultation, errors = validate_consultation({
            "customer_name": customer_name, "customer_phone": customer_phone, "consulted_date": consulted_date,
            "consultation_type": consultation_type, "consultation_note": note,
            "next_contact_date": next_contact, "consultation_status": consultation_status,
        })
        if errors:
            for error in errors: st.error(error)
            return
        try:
            save_consultation(selected["listing_id"], consultation)
        except ValueError as error:
            st.error(str(error))
        else:
            st.success("새 상담 기록을 추가했습니다. 기존 상담과 매물 기록은 변경되지 않았습니다.")
            st.session_state.pop("consultation_selected_listing", None)
            st.rerun()


def _render_lookup() -> None:
    st.markdown("#### 상담 조회·수정")
    with st.form("consultation_search_form"):
        query_column, status_column = st.columns([2, 2])
        with query_column:
            query = st.text_input("건물명·지번·호수·고객 이름 검색", key="consultation_query")
        with status_column:
            statuses = st.multiselect("상담 상태", CONSULTATION_STATUSES, key="consultation_status_filter")
        due_only = st.checkbox("다음 연락 필요만 보기", key="consultation_due_only")
        searched = st.form_submit_button("상담 조회", type="primary")
    if searched: st.session_state["consultation_has_searched"] = True
    items = get_consultations(query=query, statuses=statuses, due_only=due_only)
    if not st.session_state.get("consultation_has_searched"):
        st.info("조건을 입력한 뒤 `상담 조회`를 누르면 상담 목록이 표시됩니다.")
        return
    st.caption(f"조회된 상담 {len(items)}건")
    if not items:
        st.info("조건에 맞는 상담 기록이 없습니다.")
        return
    st.dataframe(_rows(items), use_container_width=True, hide_index=True)
    labels = [f"{_listing_label(item)} · {item['customer_name']} · 상담일 {item['consulted_date']}" for item in items]
    chosen = st.selectbox("상세·수정할 상담", labels, key="consultation_target")
    detail = get_consultation_detail(items[labels.index(chosen)]["consultation_id"])
    if detail is None:
        st.error("선택한 상담 기록을 찾을 수 없습니다.")
        return
    st.markdown("#### 상담 상세·수정")
    phone_key = f"show_consultation_phone_{detail['consultation_id']}"
    if st.button("연락처 보기", key=f"consultation_phone_button_{detail['consultation_id']}"):
        st.session_state[phone_key] = True
    with st.form(f"consultation_edit_{detail['consultation_id']}"):
        left, middle, right = st.columns(3)
        with left:
            customer_name = st.text_input("고객 이름", value=detail["customer_name"])
            customer_phone = detail["customer_phone"]
            if st.session_state.get(phone_key):
                customer_phone = st.text_input("고객 연락처", value=detail["customer_phone"])
        with middle:
            status_index = CONSULTATION_STATUSES.index(detail["consultation_status"])
            status = st.selectbox("상담 상태", CONSULTATION_STATUSES, index=status_index)
            next_contact = st.date_input("다음 연락일", value=date.fromisoformat(detail["next_contact_date"]) if detail["next_contact_date"] else None)
        with right:
            st.caption(f"상담일: {detail['consulted_date']}\n\n상담 종류: {detail['consultation_type']}")
        note = st.text_area("상담 내용", value=detail["consultation_note"])
        submitted = st.form_submit_button("상담 정보 저장", type="primary")
    if submitted:
        try:
            save_consultation_changes(detail["consultation_id"], {
                "customer_name": customer_name, "customer_phone": customer_phone, "consultation_note": note,
                "next_contact_date": next_contact, "consultation_status": status,
            })
        except ValueError as error:
            st.error(str(error))
        else:
            st.success("상담 기록은 유지한 채 정보를 수정했습니다.")
            st.rerun()


def render_consultation_management() -> None:
    st.subheader("상담관리")
    st.markdown("<p class='section-note'>매물별 상담 이력과 다음 연락일을 관리합니다. 고객 연락처는 상담 상세에서만 확인합니다.</p>", unsafe_allow_html=True)
    mode = st.radio("상담관리 메뉴", ["상담 등록", "상담 조회·수정"], horizontal=True, key="consultation_management_mode")
    if mode == "상담 등록":
        _render_registration()
    else:
        _render_lookup()
