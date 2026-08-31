"""건물 공통정보, 호실 고정정보와 매물 이력 관리 화면."""

from __future__ import annotations

from datetime import date

import streamlit as st

from services.record_number import contract_number, listing_number
from services.listing_service import ROOM_TYPES
from services.backup_service import create_daily_backup
from storage.building_repository import (
    get_building_management_detail,
    get_building_password,
    get_building_units,
    get_current_listing_price,
    get_unit_listing_history,
    get_unit_management_detail,
    get_unit_password,
    search_buildings,
    rename_unit,
    update_building_management_detail,
    update_current_listing_price,
    update_unit_management_detail,
)
from storage.contract_repository import get_contracts
from services.lot_address_service import combine_lot_address, split_lot_address


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
        if st.button("검색 초기화", key="building_management_reset", width="stretch"):
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
        if st.button(label, key=f"manage_building_{building['id']}", width="stretch"):
            st.session_state["building_management_selected"] = building
            st.rerun()
    return None


def _render_building_edit(building: dict) -> None:
    building_id = building["id"]
    lot_area, lot_number = split_lot_address(building["lot_address"])
    with st.expander("건물 공통정보 수정"):
        with st.form(f"building_edit_{building_id}"):
            edited_building_name = st.text_input("건물명", value=building["building_name"], key=f"building_name_{building_id}", help="비우면 `건물명 미입력`으로 저장됩니다.")
            address_left, address_right = st.columns(2)
            with address_left:
                edited_lot_area = st.text_input("지번 지역 *", value=lot_area, key=f"building_lot_area_{building_id}")
            with address_right:
                edited_lot_number = st.text_input("번지 번호 *", value=lot_number, key=f"building_lot_number_{building_id}")
            if not lot_number:
                st.caption("기존 지번 형식을 자동으로 나누지 못했습니다. 지번 지역과 번지 번호를 확인한 뒤 저장해 주세요.")
            left, middle = st.columns(2)
            with left:
                elevator = st.selectbox("엘리베이터", ["확인 필요", "있음", "없음"], index=_index(["확인 필요", "있음", "없음"], building["has_elevator"]), key=f"building_elevator_{building_id}")
            with middle:
                parking = st.selectbox("주차", ["확인 필요", "가능", "제한적", "불가"], index=_index(["확인 필요", "가능", "제한적", "불가"], building["parking_status"]), key=f"building_parking_{building_id}")
            building_note = st.text_area("건물 메모", value=building["internal_note"] or "", key=f"building_note_{building_id}")
            password_action = st.selectbox(
                "공동현관 비밀번호",
                ["기존 비밀번호 유지", "새 비밀번호로 변경", "비밀번호 삭제"],
                key=f"building_password_action_{building_id}",
            )
            new_password = ""
            if password_action == "새 비밀번호로 변경":
                new_password = st.text_input("새 공동현관 비밀번호", key=f"building_password_{building_id}")
            submitted = st.form_submit_button("건물 기본정보 저장", type="primary")
        if submitted:
            address_was_not_split = not lot_number and edited_lot_area == lot_area and not edited_lot_number.strip()
            if not address_was_not_split and (not edited_lot_area.strip() or not edited_lot_number.strip()):
                st.error("지번 지역과 번지 번호를 모두 입력해 주세요.")
                return
            if password_action == "새 비밀번호로 변경" and not new_password.strip():
                st.error("새 비밀번호를 입력하거나 ‘기존 비밀번호 유지’를 선택해 주세요.")
                return
            update_building_management_detail(building_id, {
                "building_name": edited_building_name,
                "lot_address": building["lot_address"] if address_was_not_split else combine_lot_address(edited_lot_area, edited_lot_number),
                "has_elevator": elevator, "parking_status": parking, "internal_note": building_note or None,
                "common_entrance_password": new_password.strip() if password_action == "새 비밀번호로 변경" else None,
                "clear_common_entrance_password": password_action == "비밀번호 삭제",
            })
            create_daily_backup()
            st.session_state["building_management_selected"] = {**st.session_state.get("building_management_selected", {}), "building_name": edited_building_name.strip() or "건물명 미입력"}
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
    password = get_unit_password(unit_id)
    st.info(f"방문 비밀번호: {password or '등록되지 않음'}")

    with st.expander("호실 기본정보 수정", expanded=True):
        with st.form(f"unit_edit_{unit_id}"):
            left, middle, right = st.columns(3)
            with left:
                floor = st.number_input("층", min_value=0, step=1, value=unit["floor_number"], key=f"unit_floor_{unit_id}")
                room_type_options = [unit["room_type"], *ROOM_TYPES] if unit["room_type"] == "분리형 원룸" else ROOM_TYPES
                room_type = st.selectbox("룸 형태", room_type_options, index=_index(room_type_options, unit["room_type"]), key=f"unit_room_type_{unit_id}")
            with middle:
                access_method = st.selectbox("방문 방법", ACCESS_METHODS, index=_index(ACCESS_METHODS, unit["access_method"]), key=f"unit_access_{unit_id}")
            with right:
                options = st.text_area("옵션 호실 메모", value=unit["unit_options"] or "", key=f"unit_options_{unit_id}")
                password_action = st.selectbox(
                    "방문 비밀번호",
                    ["기존 비밀번호 유지", "새 비밀번호로 변경", "비밀번호 삭제"],
                    key=f"unit_password_action_{unit_id}",
                )
                new_password = ""
                if password_action == "새 비밀번호로 변경":
                    new_password = st.text_input("새 방문 비밀번호", key=f"unit_password_{unit_id}")
            submitted = st.form_submit_button("호실 기본정보 저장", type="primary")
        if submitted:
            if password_action == "새 비밀번호로 변경" and not new_password.strip():
                st.error("새 비밀번호를 입력하거나 ‘기존 비밀번호 유지’를 선택해 주세요.")
                return
            update_unit_management_detail(unit_id, {
                "floor_number": floor, "room_type": room_type, "unit_options": options or None, "access_method": access_method,
                "unit_access_password": new_password.strip() if password_action == "새 비밀번호로 변경" else None,
                "clear_unit_access_password": password_action == "비밀번호 삭제",
            })
            create_daily_backup()
            st.success("호실 기본정보를 저장했습니다.")
            st.rerun()

    with st.expander("호실 번호 정정"):
        st.caption("오입력한 호실 번호만 정정합니다. 연결된 매물·계약·상담 이력은 유지되며, 같은 건물에 이미 있는 호실 번호로는 바꿀 수 없습니다.")
        new_unit_number = st.text_input("새 호실 번호", value=unit["unit_number"], key=f"unit_rename_{unit_id}")
        rename_confirmed = st.checkbox("매물·계약·상담 이력은 유지한 채 호실 번호만 정정하는 것을 확인했습니다.", key=f"unit_rename_confirm_{unit_id}")
        if st.button("호실 번호 정정 저장", type="primary", disabled=not rename_confirmed, key=f"unit_rename_save_{unit_id}"):
            try:
                old_unit_number = rename_unit(unit_id, new_unit_number)
            except ValueError as error:
                st.error(str(error))
            else:
                create_daily_backup()
                st.success(f"{old_unit_number}호를 {new_unit_number.strip().removesuffix('호')}호로 정정했습니다. 연결된 이력은 유지됩니다.")
                st.rerun()

    current_listing = get_current_listing_price(unit_id)
    with st.expander("최신 매물 가격 수정", expanded=True):
        if current_listing is None:
            st.info("현재 운영 중인 매물이 없어 가격을 수정할 수 없습니다. 과거 매물 조건은 아래 이력에서만 확인할 수 있습니다.")
        else:
            st.caption(f"수정 대상: {listing_number(current_listing['id'])} · 현재 운영 중인 매물만 변경하며, 과거 매물 이력은 유지됩니다.")
            with st.form(f"current_listing_price_{unit_id}"):
                deposit_column, rent_column = st.columns(2)
                with deposit_column:
                    deposit = st.number_input("보증금 (만원, 선택)", min_value=0, step=10, value=current_listing["deposit_manwon"], key=f"current_deposit_{unit_id}")
                with rent_column:
                    monthly_rent = st.number_input("월세 (만원, 선택)", min_value=0, step=1, value=current_listing["monthly_rent_manwon"], key=f"current_monthly_rent_{unit_id}")
                submitted = st.form_submit_button("보증금·월세 저장", type="primary")
            if submitted:
                if deposit is not None and deposit <= 0:
                    st.error("보증금을 입력할 때는 0보다 큰 숫자를 입력해 주세요.")
                elif monthly_rent is not None and monthly_rent <= 0:
                    st.error("월세를 입력할 때는 0보다 큰 숫자를 입력해 주세요.")
                else:
                    try:
                        updated_listing_id = update_current_listing_price(unit_id, deposit, monthly_rent)
                    except ValueError as error:
                        st.error(str(error))
                    else:
                        create_daily_backup()
                        st.success(f"{listing_number(updated_listing_id)}의 보증금·월세를 저장했습니다.")
                        st.rerun()

    history = get_unit_listing_history(unit_id)
    st.markdown("#### 매물 이력")
    if history:
        rows = [{
            "매물번호": listing_number(item["id"]), "접수일": item["received_date"], "상태": item["listing_status"],
            "보증금": item["deposit_manwon"] if item["deposit_manwon"] is not None else "-", "월세": item["monthly_rent_manwon"] if item["monthly_rent_manwon"] is not None else "-",
            "관리비": item["management_fee_manwon"] or "-", "입주 가능": item["availability_type"],
            "종료 확인일": item["closed_date"] or "-", "종료 사유": item["close_reason"] or "-",
            "매물 메모": item["listing_note"] or "-",
        } for item in history]
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info("등록된 매물 이력이 없습니다.")

    contracts = get_contracts(unit_id=unit_id)
    st.markdown("#### 계약 이력")
    if contracts:
        st.dataframe([{
            "계약번호": contract_number(item["contract_id"]), "매물번호": listing_number(item["listing_id"]), "매물 접수일": item["received_date"], "계약 유형": item["contract_type"],
            "시작일": item["contract_start_date"], "종료일": item["contract_end_date"] or "-",
            "기간(개월)": item["term_months"] or "-", "계약 상태": item["contract_status"],
            "메모": item["contract_note"] or "-",
        } for item in contracts], width="stretch", hide_index=True)
    else:
        st.info("등록된 계약 이력이 없습니다. 계약 등록과 상태 변경은 계약관리 탭에서 합니다.")


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
    st.caption(f"엘리베이터: {building['has_elevator'] or '확인 필요'} · 주차: {building['parking_status'] or '확인 필요'}")
    password = get_building_password(building["id"])
    st.info(f"공동현관 비밀번호: {password or '등록되지 않음'}")
    _render_building_edit(building)

    st.markdown("#### 등록 호실")
    units = get_building_units(building["id"])
    if not units:
        st.info("등록된 호실이 없습니다.")
        return
    st.dataframe([{
        "호실": item["unit_number"], "최근 매물번호": listing_number(item["listing_id"]), "룸 형태": item["room_type"] or "미입력",
        "최근 조건": f"{item['deposit_manwon'] or '확인 필요'}/{item['monthly_rent_manwon'] or '확인 필요'}",
        "최근 상태": item["listing_status"] or "-", "마지막 접수일": item["received_date"] or "-",
    } for item in units], width="stretch", hide_index=True)
    unit_columns = st.columns(min(len(units), 4))
    for index, unit in enumerate(units):
        with unit_columns[index % len(unit_columns)]:
            unit_label = unit["unit_number"] if unit["unit_number"].endswith("호") else f"{unit['unit_number']}호"
            if st.button(f"{unit_label} 관리", key=f"manage_unit_{unit['id']}", width="stretch"):
                st.session_state["building_management_unit_id"] = unit["id"]
                st.rerun()
    if unit_id := st.session_state.get("building_management_unit_id"):
        _render_unit_detail(unit_id)
