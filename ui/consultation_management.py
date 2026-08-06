"""매물 회차별 상담 CRM 화면."""

from __future__ import annotations

from datetime import date

import streamlit as st

from services.contact_format import format_phone_number
from services.consultation_service import CONSULTATION_CATEGORIES, CONSULTATION_STATUSES, CONSULTATION_TYPES, delete_consultation, link_consultation_to_listing, save_consultation, save_consultation_changes, validate_consultation
from storage.consultation_repository import get_consultation_detail, get_consultations
from storage.listing_repository import search_listing_rounds


def _listing_label(item: dict) -> str:
    if not item.get("listing_id"):
        return "일반 상담 · 연결 매물 없음"
    unit = item["unit_number"] if item["unit_number"].endswith("호") else f"{item['unit_number']}호"
    return f"{item['building_name']} · {item['lot_address']} · {unit} · 접수일 {item['received_date']} · {item['listing_status']}"


def _task_text(item: dict, today: str) -> str:
    """상담 상태와 연락 기한에서 바로 처리할 일을 만든다."""
    tasks: list[str] = []
    if item["consultation_status"] == "확인 필요":
        tasks.append("상담 확인 필요")
    if item["next_contact_date"] and item["next_contact_date"] <= today and item["consultation_status"] != "종료":
        tasks.append("다음 연락 필요")
    return " · ".join(tasks) or "-"


def _rows(items: list[dict]) -> list[dict]:
    today = date.today().isoformat()
    return [{
        "상담 구분": item["consultation_category"], "건물명": item["building_name"] or "-", "호실": item["unit_number"] or "-",
        "매물 접수일": item["received_date"], "상담일": item["consulted_date"], "상담 종류": item["consultation_type"],
        "상담 상태": item["consultation_status"], "다음 연락일": item["next_contact_date"] or "-",
        "해야 할 일": _task_text(item, today),
        "희망 조건": " · ".join(filter(None, [item["desired_area"], item["desired_room_type"], f"{item['desired_deposit_manwon']}/{item['desired_monthly_rent_manwon']}" if item["desired_deposit_manwon"] is not None or item["desired_monthly_rent_manwon"] is not None else None])) or "-", "상담 내용": item["consultation_note"],
    } for item in items]


def _render_registration() -> None:
    st.markdown("#### 상담 등록")
    registration_notice = st.session_state.pop("consultation_registration_notice", None)
    if registration_notice:
        st.success(registration_notice)
    category = st.radio("상담 구분", CONSULTATION_CATEGORIES, horizontal=True, key="consultation_category")
    if category == "일반 상담":
        st.caption("아직 연결할 매물이 없거나 여러 매물을 함께 보는 상담을 기록합니다.")
        with st.form("general_consultation_create"):
            left, middle, right = st.columns(3)
            with left:
                customer_phone = st.text_input("고객 연락처", placeholder="예: 010-1234-5678")
            with middle:
                consulted_date = st.date_input("상담일", value=date.today())
                consultation_type = st.selectbox("상담 종류", CONSULTATION_TYPES)
            with right:
                consultation_status = st.selectbox("상담 상태", CONSULTATION_STATUSES)
                next_contact = st.date_input("다음 연락일", value=None)
            st.markdown("##### 희망 조건 (선택)")
            desired_left, desired_middle, desired_right, desired_last = st.columns(4)
            with desired_left: desired_area = st.text_input("희망 지역", placeholder="예: 배방읍")
            with desired_middle: desired_room_type = st.text_input("희망 방 형태", placeholder="예: 투룸")
            with desired_right: desired_deposit = st.number_input("희망 보증금 (만원)", min_value=0, step=100, value=None)
            with desired_last: desired_monthly_rent = st.number_input("희망 월세 (만원)", min_value=0, step=5, value=None)
            note = st.text_area("상담 내용", placeholder="예: 원하는 지역·입주 시기·특이사항")
            submitted = st.form_submit_button("일반 상담 등록", type="primary")
        if submitted:
            customer_phone = format_phone_number(customer_phone)
            consultation, errors = validate_consultation({
                "consultation_category": category, "customer_phone": customer_phone,
                "consulted_date": consulted_date, "consultation_type": consultation_type, "consultation_note": note,
                "desired_area": desired_area, "desired_room_type": desired_room_type,
                "desired_deposit_manwon": desired_deposit, "desired_monthly_rent_manwon": desired_monthly_rent,
                "next_contact_date": next_contact, "consultation_status": consultation_status,
            })
            if errors:
                for error in errors: st.error(error)
                return
            try:
                save_consultation(None, consultation)
            except ValueError as error:
                st.error(str(error))
            else:
                st.session_state["consultation_registration_notice"] = "일반 상담 등록을 완료했습니다. 상담 조회·수정에서 등록 내용과 해야 할 일을 확인할 수 있습니다."
                st.rerun()
        return

    st.caption("상담할 당시의 매물 기록을 선택한 뒤 새 상담을 추가합니다.")
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
            if st.button(_listing_label(item), key=f"consultation_listing_{item['listing_id']}", width="stretch"):
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
            customer_phone = st.text_input("고객 연락처", placeholder="예: 010-1234-5678")
        with middle:
            consulted_date = st.date_input("상담일", value=date.today())
            consultation_type = st.selectbox("상담 종류", CONSULTATION_TYPES)
        with right:
            consultation_status = st.selectbox("상담 상태", CONSULTATION_STATUSES)
            next_contact = st.date_input("다음 연락일", value=None)
        st.markdown("##### 희망 조건 (선택)")
        desired_left, desired_middle, desired_right, desired_last = st.columns(4)
        with desired_left: desired_area = st.text_input("희망 지역", placeholder="예: 배방읍")
        with desired_middle: desired_room_type = st.text_input("희망 방 형태", placeholder="예: 투룸")
        with desired_right: desired_deposit = st.number_input("희망 보증금 (만원)", min_value=0, step=100, value=None)
        with desired_last: desired_monthly_rent = st.number_input("희망 월세 (만원)", min_value=0, step=5, value=None)
        note = st.text_area("상담 내용", placeholder="예: 방문 일정 협의, 가격 안내")
        submitted = st.form_submit_button("새 상담 등록", type="primary")
    if submitted:
        customer_phone = format_phone_number(customer_phone)
        consultation, errors = validate_consultation({
            "consultation_category": category, "customer_phone": customer_phone, "consulted_date": consulted_date,
            "consultation_type": consultation_type, "consultation_note": note,
            "desired_area": desired_area, "desired_room_type": desired_room_type,
            "desired_deposit_manwon": desired_deposit, "desired_monthly_rent_manwon": desired_monthly_rent,
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
            st.session_state["consultation_registration_notice"] = "매물 상담 등록을 완료했습니다. 기존 상담과 매물 기록은 변경되지 않았습니다."
            st.session_state.pop("consultation_selected_listing", None)
            st.rerun()


def _render_lookup() -> None:
    st.markdown("#### 상담 조회·수정")
    with st.form("consultation_search_form"):
        query_column, status_column = st.columns([2, 2])
        with query_column:
            query = st.text_input("건물명·지번·호수·희망 지역 검색", key="consultation_query")
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
    st.dataframe(_rows(items), width="stretch", hide_index=True)
    labels = [f"{_listing_label(item)} · 상담일 {item['consulted_date']} · 상담 #{item['consultation_id']}" for item in items]
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
            customer_phone = detail["customer_phone"]
            if st.session_state.get(phone_key):
                customer_phone = st.text_input("고객 연락처", value=detail["customer_phone"])
        with middle:
            status_index = CONSULTATION_STATUSES.index(detail["consultation_status"])
            status = st.selectbox("상담 상태", CONSULTATION_STATUSES, index=status_index)
            next_contact = st.date_input("다음 연락일", value=date.fromisoformat(detail["next_contact_date"]) if detail["next_contact_date"] else None)
        with right:
            st.caption(f"상담 구분: {detail['consultation_category']}\n\n상담일: {detail['consulted_date']}\n\n상담 종류: {detail['consultation_type']}")
        note = st.text_area("상담 내용", value=detail["consultation_note"])
        st.markdown("##### 희망 조건 (선택)")
        desired_left, desired_middle, desired_right, desired_last = st.columns(4)
        with desired_left: desired_area = st.text_input("희망 지역", value=detail["desired_area"] or "")
        with desired_middle: desired_room_type = st.text_input("희망 방 형태", value=detail["desired_room_type"] or "")
        with desired_right: desired_deposit = st.number_input("희망 보증금 (만원)", min_value=0, step=100, value=detail["desired_deposit_manwon"])
        with desired_last: desired_monthly_rent = st.number_input("희망 월세 (만원)", min_value=0, step=5, value=detail["desired_monthly_rent_manwon"])
        submitted = st.form_submit_button("상담 정보 저장", type="primary")
    if submitted:
        try:
            customer_phone = format_phone_number(customer_phone)
            save_consultation_changes(detail["consultation_id"], {
                "consultation_category": detail["consultation_category"], "customer_name": detail["customer_name"], "customer_phone": customer_phone, "consultation_note": note,
                "desired_area": desired_area, "desired_room_type": desired_room_type,
                "desired_deposit_manwon": desired_deposit, "desired_monthly_rent_manwon": desired_monthly_rent,
                "next_contact_date": next_contact, "consultation_status": status,
            })
        except ValueError as error:
            st.error(str(error))
        else:
            st.success("상담 기록은 유지한 채 정보를 수정했습니다.")
            st.rerun()

    if detail["consultation_category"] == "일반 상담" and detail["listing_id"] is None:
        with st.expander("이 일반 상담에 매물 연결"):
            st.caption("고객에게 맞는 매물이 정해진 뒤에만 연결합니다. 연결 전까지는 일반 상담으로 유지됩니다.")
            link_query = st.text_input("연결할 매물 회차 찾기", key=f"general_consultation_link_query_{detail['consultation_id']}", placeholder="건물명·지번·호수 중 2글자 이상")
            if len(link_query.strip()) >= 2:
                results = search_listing_rounds(link_query)
                if not results:
                    st.info("조건에 맞는 매물 기록이 없습니다.")
                for item in results:
                    if st.button(_listing_label(item), key=f"link_consultation_{detail['consultation_id']}_{item['listing_id']}", width="stretch"):
                        try:
                            link_consultation_to_listing(detail["consultation_id"], item["listing_id"])
                        except ValueError as error:
                            st.error(str(error))
                            return
                        st.success("일반 상담에 매물 기록을 연결했습니다.")
                        st.rerun()

    with st.expander("이 상담 기록 완전 삭제"):
        st.error("선택한 상담 기록만 삭제됩니다. 매물과 계약 기록은 남습니다.")
        confirmed = st.checkbox("이 상담 기록을 완전히 삭제하는 것을 확인했습니다.", key=f"delete_consultation_confirm_{detail['consultation_id']}")
        if st.button("상담 기록 삭제", type="secondary", disabled=not confirmed, key=f"delete_consultation_{detail['consultation_id']}"):
            try:
                delete_consultation(detail["consultation_id"])
            except ValueError as error:
                st.error(str(error))
                return
            st.success("상담 기록을 삭제했습니다.")
            st.rerun()


def render_consultation_management() -> None:
    st.subheader("상담관리")
    st.markdown("<p class='section-note'>매물별 상담 이력과 다음 연락일을 관리합니다. 고객 연락처는 상담 상세에서만 확인합니다.</p>", unsafe_allow_html=True)
    mode = st.radio("상담관리 메뉴", ["상담 등록", "상담 조회·수정"], horizontal=True, key="consultation_management_mode")
    if mode == "상담 등록":
        _render_registration()
    else:
        _render_lookup()
