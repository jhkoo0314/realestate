"""건물 공통정보, 호실 고정정보와 매물 이력 관리 화면."""

from __future__ import annotations

from datetime import date

import streamlit as st

from services.listing_service import ROOM_TYPES
from storage.database import (
    get_building_management_detail,
    get_building_password,
    get_building_units,
    get_unit_listing_history,
    get_unit_management_detail,
    get_unit_password,
    search_buildings,
    update_building_management_detail,
    update_current_listing_option_note,
    update_unit_management_detail,
)


INFO_STATUSES = ["기본등록", "일부확인", "확인완료", "재확인 필요"]
DIRECTIONS = ["확인 필요", "동", "서", "남", "북", "남동", "남서", "북동", "북서"]
ACCESS_METHODS = ["확인 필요", "비밀번호", "열쇠", "세입자 협의", "관리인 문의"]


def _clear_selection() -> None:
    for key in ("building_management_selected", "building_management_unit_id", "building_management_search"):
        st.session_state.pop(key, None)


def _date_value(value: str | None):
    return date.fromisoformat(value) if value else None


def _index(options: list[str], value: str | None, default: int = 0) -> int:
    return options.index(value) if value in options else default


def _render_search() -> dict | None:
    search_column, reset_column = st.columns([4, 1])
    with search_column:
        query = st.text_input("건물명·지번 검색", key="building_management_search", placeholder="예: 아델리오 또는 북수리 1404")
    with reset_column:
        st.markdown("<div style='height: 1.75rem'></div>", unsafe_allow_html=True)
        if st.button("검색 초기화", key="building_management_reset", use_container_width=True):
            _clear_selection()
            st.rerun()

    selected = st.session_state.get("building_management_selected")
    if selected:
        return selected
    if len(query.strip()) < 2:
        st.info("건물명 또는 지번을 2글자 이상 입력해 주세요.")
        return None
    results = search_buildings(query)
    if not results:
        st.info("조건에 맞는 등록 건물이 없습니다.")
        return None
    st.caption("관리할 건물을 선택해 주세요.")
    for building in results:
        label = f"{building['building_name']} · {building['lot_address']} · 호실 {building['unit_count']}개"
        if st.button(label, key=f"manage_building_{building['id']}", use_container_width=True):
            st.session_state["building_management_selected"] = building
            st.rerun()
    return None


def _render_building_edit(building: dict) -> None:
    building_id = building["id"]
    with st.expander("건물 공통정보 수정"):
        with st.form(f"building_edit_{building_id}"):
            left, middle, right = st.columns(3)
            with left:
                admin_address = st.text_input("행정주소", value=building["admin_address"] or "", key=f"building_admin_{building_id}")
                elevator = st.selectbox("엘리베이터", ["확인 필요", "있음", "없음"], index=_index(["확인 필요", "있음", "없음"], building["has_elevator"]), key=f"building_elevator_{building_id}")
                cctv = st.selectbox("CCTV", ["확인 필요", "있음", "없음"], index=_index(["확인 필요", "있음", "없음"], building["has_cctv"]), key=f"building_cctv_{building_id}")
            with middle:
                road_address = st.text_input("도로명주소", value=building["road_address"] or "", key=f"building_road_{building_id}")
                parking = st.selectbox("주차", ["확인 필요", "가능", "제한적", "불가"], index=_index(["확인 필요", "가능", "제한적", "불가"], building["parking_status"]), key=f"building_parking_{building_id}")
                pet_policy = st.selectbox("반려동물", ["확인 필요", "가능", "불가", "협의"], index=_index(["확인 필요", "가능", "불가", "협의"], building["pet_policy"]), key=f"building_pet_{building_id}")
            with right:
                move_in = st.selectbox("전입신고", ["확인 필요", "가능", "불가", "협의"], index=_index(["확인 필요", "가능", "불가", "협의"], building["move_in_registration_policy"]), key=f"building_movein_{building_id}")
                short_term = st.selectbox("단기계약", ["확인 필요", "가능", "불가", "협의"], index=_index(["확인 필요", "가능", "불가", "협의"], building["short_term_policy"]), key=f"building_shortterm_{building_id}")
                info_status = st.selectbox("정보 상태", INFO_STATUSES, index=_index(INFO_STATUSES, building["info_status"]), key=f"building_status_{building_id}")
            common_fee = st.text_input("공통 관리비 메모", value=building["common_fee_note"] or "", key=f"building_fee_{building_id}")
            highlights = st.text_area("건물 공통 장점", value=building["building_highlights"] or "", key=f"building_highlights_{building_id}")
            next_check = st.date_input("건물 재확인 예정일", value=_date_value(building["next_check_date"]), key=f"building_next_check_{building_id}")
            password_action = st.selectbox(
                "공동현관 비밀번호",
                ["기존 비밀번호 유지", "새 비밀번호로 변경", "비밀번호 삭제"],
                key=f"building_password_action_{building_id}",
            )
            new_password = ""
            if password_action == "새 비밀번호로 변경":
                new_password = st.text_input("새 공동현관 비밀번호", type="password", key=f"building_password_{building_id}")
            submitted = st.form_submit_button("건물 기본정보 저장", type="primary")
        if submitted:
            if password_action == "새 비밀번호로 변경" and not new_password.strip():
                st.error("새 비밀번호를 입력하거나 ‘기존 비밀번호 유지’를 선택해 주세요.")
                return
            update_building_management_detail(building_id, {
                "admin_address": admin_address or None, "road_address": road_address or None, "has_elevator": elevator,
                "parking_status": parking, "has_cctv": cctv, "pet_policy": pet_policy,
                "move_in_registration_policy": move_in, "short_term_policy": short_term, "common_fee_note": common_fee or None,
                "building_highlights": highlights or None, "info_status": info_status,
                "next_check_date": next_check.isoformat() if next_check else None,
                "common_entrance_password": new_password.strip() if password_action == "새 비밀번호로 변경" else None,
                "clear_common_entrance_password": password_action == "비밀번호 삭제",
            })
            st.success("건물 기본정보를 저장했습니다.")
            st.rerun()


def _render_unit_detail(unit_id: int) -> None:
    unit = get_unit_management_detail(unit_id)
    if unit is None:
        st.error("선택한 호실을 찾을 수 없습니다.")
        return
    st.markdown(f"#### {unit['unit_number']}호 상세")
    if st.button("호실 선택 해제", key=f"clear_unit_{unit_id}"):
        st.session_state.pop("building_management_unit_id", None)
        st.rerun()
    password_key = f"show_unit_password_{unit_id}"
    if st.button("방문 비밀번호 보기", key=f"unit_password_button_{unit_id}"):
        st.session_state[password_key] = True
    if st.session_state.get(password_key):
        password = get_unit_password(unit_id)
        st.warning(f"방문 비밀번호: {password or '등록되지 않음'}")

    with st.expander("호실 기본정보 수정", expanded=True):
        with st.form(f"unit_edit_{unit_id}"):
            left, middle, right = st.columns(3)
            with left:
                floor = st.number_input("층", min_value=0, step=1, value=unit["floor_number"], key=f"unit_floor_{unit_id}")
                room_type = st.selectbox("룸 형태", ROOM_TYPES, index=_index(ROOM_TYPES, unit["room_type"]), key=f"unit_room_type_{unit_id}")
            with middle:
                direction = st.selectbox("방향", DIRECTIONS, index=_index(DIRECTIONS, unit["direction"]), key=f"unit_direction_{unit_id}")
                access_method = st.selectbox("방문 방법", ACCESS_METHODS, index=_index(ACCESS_METHODS, unit["access_method"]), key=f"unit_access_{unit_id}")
            with right:
                options = st.text_area("호실 옵션 (쉼표로 구분)", value=unit["unit_options"] or "", key=f"unit_options_{unit_id}")
                password_action = st.selectbox(
                    "방문 비밀번호",
                    ["기존 비밀번호 유지", "새 비밀번호로 변경", "비밀번호 삭제"],
                    key=f"unit_password_action_{unit_id}",
                )
                new_password = ""
                if password_action == "새 비밀번호로 변경":
                    new_password = st.text_input("새 방문 비밀번호", type="password", key=f"unit_password_{unit_id}")
            highlights = st.text_area("구조상 장점", value=unit["unit_highlights"] or "", key=f"unit_highlights_{unit_id}")
            cautions = st.text_area("구조상 유의점", value=unit["unit_cautions"] or "", key=f"unit_cautions_{unit_id}")
            submitted = st.form_submit_button("호실 기본정보 저장", type="primary")
        if submitted:
            if password_action == "새 비밀번호로 변경" and not new_password.strip():
                st.error("새 비밀번호를 입력하거나 ‘기존 비밀번호 유지’를 선택해 주세요.")
                return
            update_unit_management_detail(unit_id, {
                "floor_number": floor, "room_type": room_type, "direction": direction, "unit_options": options or None,
                "unit_highlights": highlights or None, "unit_cautions": cautions or None, "access_method": access_method,
                "unit_access_password": new_password.strip() if password_action == "새 비밀번호로 변경" else None,
                "clear_unit_access_password": password_action == "비밀번호 삭제",
            })
            st.success("호실 기본정보를 저장했습니다.")
            st.rerun()

    with st.expander("이번 매물에만 다른 옵션"):
        st.caption("이 내용은 호실 기본 옵션을 바꾸지 않고 현재 매물 기록에만 남습니다.")
        option_note = st.text_area("이번 매물 옵션 변경 메모", key=f"option_note_{unit_id}")
        if st.button("이번 매물 메모 저장", key=f"option_note_save_{unit_id}"):
            try:
                update_current_listing_option_note(unit_id, option_note or None)
            except ValueError as error:
                st.info(str(error))
            else:
                st.success("이번 매물에만 옵션 변경 메모를 저장했습니다.")

    history = get_unit_listing_history(unit_id)
    st.markdown("#### 매물 이력")
    if history:
        rows = [{
            "접수일": item["received_date"], "상태": item["listing_status"],
            "보증금": item["deposit_manwon"] or "확인 필요", "월세": item["monthly_rent_manwon"] or "확인 필요",
            "관리비": item["management_fee_manwon"] or "-", "입주 가능": item["availability_type"],
            "종료일": item["closed_date"] or "-", "종료 사유": item["close_reason"] or "-",
            "이번 매물 옵션 변경": item["option_change_note"] or "-",
        } for item in history]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("등록된 매물 이력이 없습니다.")


def render_building_management() -> None:
    st.subheader("건물·호실 관리")
    st.markdown("<p class='section-note'>건물 공통정보와 호실 고정정보를 수정하고, 매물 이력을 확인하는 화면입니다.</p>", unsafe_allow_html=True)
    try:
        selected = _render_search()
    except FileNotFoundError as error:
        st.error(str(error))
        return
    if not selected:
        return

    building = get_building_management_detail(selected["id"])
    if building is None:
        st.error("선택한 건물을 찾을 수 없습니다. 다시 검색해 주세요.")
        _clear_selection()
        return
    if st.button("다른 건물 검색", key=f"change_building_{building['id']}"):
        _clear_selection()
        st.rerun()
    st.info(f"선택한 건물: {building['building_name']} · {building['lot_address']}")
    st.caption(f"행정주소: {building['admin_address'] or '미입력'} · 엘리베이터: {building['has_elevator'] or '확인 필요'} · 주차: {building['parking_status'] or '확인 필요'}")
    password_key = f"show_building_password_{building['id']}"
    if st.button("공동현관 비밀번호 보기", key=f"building_password_button_{building['id']}"):
        st.session_state[password_key] = True
    if st.session_state.get(password_key):
        password = get_building_password(building["id"])
        st.warning(f"공동현관 비밀번호: {password or '등록되지 않음'}")
    _render_building_edit(building)

    st.markdown("#### 등록 호실")
    units = get_building_units(building["id"])
    if not units:
        st.info("등록된 호실이 없습니다.")
        return
    st.dataframe([{
        "호실": item["unit_number"], "룸 형태": item["room_type"] or "미입력", "방향": item["direction"] or "미입력",
        "최근 조건": f"{item['deposit_manwon'] or '확인 필요'}/{item['monthly_rent_manwon'] or '확인 필요'}",
        "최근 상태": item["listing_status"] or "-", "마지막 접수일": item["received_date"] or "-",
    } for item in units], use_container_width=True, hide_index=True)
    unit_columns = st.columns(min(len(units), 4))
    for index, unit in enumerate(units):
        with unit_columns[index % len(unit_columns)]:
            unit_label = unit["unit_number"] if unit["unit_number"].endswith("호") else f"{unit['unit_number']}호"
            if st.button(f"{unit_label} 관리", key=f"manage_unit_{unit['id']}", use_container_width=True):
                st.session_state["building_management_unit_id"] = unit["id"]
                st.rerun()
    if unit_id := st.session_state.get("building_management_unit_id"):
        _render_unit_detail(unit_id)
