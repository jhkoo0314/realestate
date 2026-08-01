"""신규 건물·호실·첫 매물 등록 화면."""

from __future__ import annotations

from datetime import date

import streamlit as st

from services.listing_service import (
    AVAILABILITY_TYPES,
    LISTING_STATUSES,
    ROOM_TYPES,
    listing_summary,
    save_confirmed_first_listing,
    validate_first_listing,
)


INPUT_KEYS = [
    "building_name", "lot_address", "admin_address", "road_address", "common_entrance_password",
    "has_elevator", "parking_status", "building_internal_note", "unit_number", "floor_number",
    "room_type", "direction", "access_method", "unit_access_password", "photo_folder_url",
    "unit_highlights", "listing_status", "deposit_manwon", "monthly_rent_manwon",
    "management_fee_manwon", "received_date", "availability_type", "available_from_date", "move_out_due_date",
    "photo_status", "listing_note", "next_check_date",
]


def _clear_registration_inputs() -> None:
    for key in INPUT_KEYS:
        st.session_state.pop(f"registration_{key}", None)
    st.session_state.pop("pending_first_listing", None)


def _field_value(name: str):
    return st.session_state.get(f"registration_{name}")


def _collect_input() -> dict:
    return {key: _field_value(key) for key in INPUT_KEYS}


def _show_input_fields() -> None:
    st.markdown("#### 1. 건물 정보")
    building_left, building_right = st.columns(2)
    with building_left:
        st.text_input("건물명 *", key="registration_building_name", placeholder="예: 대성빌")
    with building_right:
        st.text_input("지번 *", key="registration_lot_address", placeholder="예: 북수리 1026")
    st.text_input("공동현관 비밀번호 (내부정보)", key="registration_common_entrance_password", type="password")
    with st.expander("건물 상세정보"):
        detail_left, detail_right = st.columns(2)
        with detail_left:
            st.text_input("행정주소", key="registration_admin_address")
            st.selectbox("엘리베이터", ["확인 필요", "있음", "없음"], key="registration_has_elevator")
        with detail_right:
            st.text_input("도로명주소", key="registration_road_address")
            st.selectbox("주차", ["확인 필요", "가능", "제한적", "불가"], key="registration_parking_status")
        st.text_area("건물 내부 메모 (외부 공유 금지)", key="registration_building_internal_note")

    st.divider()
    st.markdown("#### 2. 호실 정보")
    unit_left, unit_middle, unit_right = st.columns(3)
    with unit_left:
        st.text_input("호수 *", key="registration_unit_number", placeholder="예: 302")
    with unit_middle:
        st.selectbox("룸 형태", ROOM_TYPES, key="registration_room_type")
    with unit_right:
        st.number_input("층", min_value=0, step=1, value=None, key="registration_floor_number")
    with st.expander("호실 상세정보"):
        detail_left, detail_right = st.columns(2)
        with detail_left:
            st.selectbox("방향", ["확인 필요", "동", "서", "남", "북", "남동", "남서", "북동", "북서"], key="registration_direction")
            st.selectbox("방문 방법", ["확인 필요", "비밀번호", "열쇠", "세입자 협의", "관리인 문의"], key="registration_access_method")
            st.text_input("방문 비밀번호 (내부정보)", key="registration_unit_access_password", type="password")
        with detail_right:
            st.text_input("사진 폴더 링크", key="registration_photo_folder_url", placeholder="Google Drive 폴더 링크")
            st.text_area("구조상 장점", key="registration_unit_highlights", placeholder="예: 안방 양창, 수납 넉넉함")

    st.divider()
    st.markdown("#### 3. 이번 매물 조건")
    listing_left, listing_middle, listing_right = st.columns(3)
    with listing_left:
        st.selectbox("매물 상태 *", LISTING_STATUSES, index=1, key="registration_listing_status")
        st.number_input("보증금 (만원) *", min_value=0, step=10, value=None, key="registration_deposit_manwon")
    with listing_middle:
        st.selectbox("입주 가능 유형 *", AVAILABILITY_TYPES, key="registration_availability_type")
        st.number_input("월세 (만원) *", min_value=0, step=1, value=None, key="registration_monthly_rent_manwon")
    with listing_right:
        st.date_input("매물 접수일", value=date.today(), key="registration_received_date", help="기본값은 오늘입니다. 실제 접수일이 다르면 바꿔 주세요.")
        st.number_input("관리비 (만원)", min_value=0, step=1, value=None, key="registration_management_fee_manwon")
        st.selectbox("사진 상태", ["확인 필요", "촬영 필요", "촬영 완료", "기존 사진 사용"], key="registration_photo_status")

    if _field_value("availability_type") == "날짜 지정":
        st.date_input("입주 가능일 *", value=None, key="registration_available_from_date")
    st.date_input("퇴실 예정일", value=None, key="registration_move_out_due_date")
    st.date_input("재확인 예정일", value=None, key="registration_next_check_date")
    st.text_area("이번 매물 메모", key="registration_listing_note", placeholder="예: 세입자와 방문시간 협의 필요")


def _show_confirmation(payload: dict) -> None:
    st.success("입력한 내용을 확인해 주세요. 아래 버튼을 눌러야 실제로 저장됩니다.")
    st.markdown(f"**{listing_summary(payload)}**")
    st.caption("비밀번호와 내부 메모는 이 요약에 표시하지 않습니다.")
    save_column, edit_column = st.columns(2)
    with save_column:
        if st.button("건물·호실·첫 매물 등록", type="primary", use_container_width=True):
            try:
                save_confirmed_first_listing(payload)
            except Exception as error:
                st.error(f"저장하지 못했습니다. 입력 내용을 확인해 주세요. ({error})")
                return
            unit_number = payload["unit"]["unit_number"]
            building_name = payload["building"]["building_name"]
            _clear_registration_inputs()
            st.session_state["registration_success"] = f"{building_name} {unit_number}호가 등록되었습니다."
            st.rerun()
    with edit_column:
        if st.button("입력 계속하기", use_container_width=True):
            st.session_state.pop("pending_first_listing", None)
            st.rerun()


def render_listing_form() -> None:
    st.subheader("매물 등록·수정")
    st.markdown("새 건물과 첫 매물을 등록하는 화면입니다. 기존 건물 검색과 재등록은 다음 단계에서 연결합니다.")

    if success_message := st.session_state.pop("registration_success", None):
        st.success(success_message)

    pending = st.session_state.get("pending_first_listing")
    if pending:
        _show_confirmation(pending)
        return

    _show_input_fields()
    st.divider()
    if st.button("입력 내용 확인", type="primary"):
        payload, errors = validate_first_listing(_collect_input())
        if errors:
            for error in errors:
                st.error(error)
            return
        st.session_state["pending_first_listing"] = payload
        st.rerun()
