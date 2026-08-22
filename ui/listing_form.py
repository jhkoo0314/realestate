"""신규 건물 또는 기존 건물의 새 호실·첫 매물 등록 화면."""

from __future__ import annotations

from datetime import date
import re

import streamlit as st

from services.listing_service import (
    AVAILABILITY_TYPES,
    LISTING_HOLDERS,
    LISTING_STATUSES,
    ROOM_TYPES,
    listing_summary,
    save_confirmed_existing_building_listing,
    save_confirmed_first_listing,
    save_current_listing_for_existing_unit,
    save_current_listing_changes,
    close_listing,
    delete_listing,
    validate_new_building_listing,
    validate_relisting,
    validate_current_listing,
)
from services.contact_format import format_phone_number
from services.lot_address_service import split_lot_address
from services.record_number import listing_number
from storage.building_repository import get_building_units, get_unit_listing_history, search_buildings
from storage.listing_create_repository import building_has_unit
from storage.listing_write_repository import deactivate_unit, delete_unit, get_current_listing, get_unit_deletion_summary, get_unit_relisting_context


INPUT_KEYS = [
    "building_name", "lot_address", "lot_area", "lot_number", "common_entrance_password",
    "has_elevator", "building_internal_note", "unit_number", "floor_number",
    "room_type", "direction", "access_method", "unit_access_password",
    "listing_status", "deposit_manwon", "monthly_rent_manwon",
    "management_fee_manwon", "received_date", "availability_type", "available_from_date", "move_out_due_date",
    "has_listing_photos",
    "listing_holder_choice", "listing_holder_custom", "listing_note", "landlord_contact", "tenant_contact", "next_check_date",
]

PHOTO_AVAILABILITY = ["있음", "없음", "확인 필요"]
REGISTRATION_ROOM_TYPES = ROOM_TYPES


def _clear_registration_inputs() -> None:
    for key in INPUT_KEYS:
        st.session_state.pop(f"registration_{key}", None)
    st.session_state.pop("registration_auto_floor_number", None)
    st.session_state.pop("pending_registration", None)


def _clear_relisting_inputs() -> None:
    """현재 매물 등록 화면을 벗어날 때 이전 입력값을 남기지 않는다."""
    for key in list(st.session_state):
        if key.startswith("relisting_"):
            st.session_state.pop(key, None)


def _clear_current_listing_inputs() -> None:
    for key in list(st.session_state):
        if key.startswith(("edit_", "close_")):
            st.session_state.pop(key, None)


def _status_index(options: list[str], value: str | None) -> int:
    return options.index(value) if value in options else 0


def _format_phone_input(key: str) -> None:
    st.session_state[key] = format_phone_number(str(st.session_state.get(key, "")))


def _floor_from_unit_number(unit_number: str | None) -> int | None:
    """일반적인 세 자리 이상 호수(302, 1001)에서 층수를 안전하게 추정한다."""
    matched = re.fullmatch(r"\s*(\d{3,})(?:호)?\s*", str(unit_number or ""))
    return int(matched.group(1)[:-2]) if matched else None


def _fill_floor_from_unit_number() -> None:
    """호수에서 자동으로 넣은 값만 다음 호수 입력 때 갱신하고 직접 입력값은 보존한다."""
    floor = _floor_from_unit_number(st.session_state.get("registration_unit_number"))
    if floor is None:
        return
    floor_key = "registration_floor_number"
    auto_key = "registration_auto_floor_number"
    current_floor = st.session_state.get(floor_key)
    previous_auto_floor = st.session_state.get(auto_key)
    if current_floor is None or current_floor == previous_auto_floor:
        st.session_state[floor_key] = floor
        st.session_state[auto_key] = floor


def _render_management_fields(key_prefix: str, values: dict | None = None) -> None:
    """사진 보유 여부와 재확인 예정일을 입력한다."""
    values = values or {}
    st.markdown("##### 확인·관리 사항")
    st.caption("사진 보유 여부와 재확인 예정일을 저장하면 현황 조회와 확인 업무에 반영됩니다.")
    left, right = st.columns(2)
    with left:
        st.selectbox("사진 보유 여부", PHOTO_AVAILABILITY, index=_status_index(PHOTO_AVAILABILITY, values.get("has_listing_photos")), key=f"{key_prefix}_has_listing_photos", help="없음이면 사진 촬영 필요, 확인 필요면 사진 확인 필요로 자동 표시됩니다.")
    with right:
        st.date_input("재확인 예정일", value=_date_value(values.get("next_check_date")), key=f"{key_prefix}_next_check_date")


def _render_listing_holder_fields(key_prefix: str, current_value: str | None = None) -> None:
    """이번 매물 회차의 보유처를 선택하거나 직접 입력한다."""
    options = ["미입력"] + LISTING_HOLDERS
    initial_choice = current_value if current_value in LISTING_HOLDERS else ("직접입력" if current_value else "미입력")
    choice_key = f"{key_prefix}_listing_holder_choice"
    custom_key = f"{key_prefix}_listing_holder_custom"
    choice = st.selectbox("매물 보유처 *", options, index=options.index(initial_choice), key=choice_key)
    st.text_input("매물 보유처 직접입력", value=current_value if initial_choice == "직접입력" else "", disabled=choice != "직접입력", key=custom_key, placeholder="예: 지역 주택관리업체")


def _field_value(name: str):
    return st.session_state.get(f"registration_{name}")


def _selected_building() -> dict | None:
    return st.session_state.get("selected_registration_building")


def _collect_input() -> dict:
    values = {key: _field_value(key) for key in INPUT_KEYS}
    if building := _selected_building():
        values["building_name"] = building["building_name"]
        values["lot_address"] = building["lot_address"]
        values["lot_area"], values["lot_number"] = split_lot_address(building["lot_address"])
    return values


def _clear_selected_building() -> None:
    st.session_state.pop("selected_registration_building", None)
    st.session_state.pop("selected_registration_unit_id", None)
    _clear_relisting_inputs()
    _clear_current_listing_inputs()
    st.session_state.pop("registration_unit_number", None)


def reset_for_new_listing() -> None:
    """상단의 새 매물 등록을 눌렀을 때 이전 작업 흔적을 모두 지운다."""
    _clear_registration_inputs()
    _clear_selected_building()
    st.session_state.pop("registration_building_search", None)
    for key in list(st.session_state):
        if key.startswith(("relisting_", "edit_", "close_reason", "close_date")):
            st.session_state.pop(key, None)


def _select_building(building: dict) -> None:
    st.session_state["selected_registration_building"] = building
    st.session_state.pop("pending_registration", None)


def _select_unit_for_relisting(unit_id: int) -> None:
    _clear_relisting_inputs()
    _clear_current_listing_inputs()
    st.session_state["selected_registration_unit_id"] = unit_id
    st.session_state.pop("pending_registration", None)


def _render_building_search() -> dict | None:
    st.markdown("#### 1. 먼저 기존 건물을 찾아보세요")
    st.caption("건물명 또는 지번을 2글자 이상 입력하면, 이미 등록된 건물을 먼저 보여 드립니다.")
    search_column, reset_column = st.columns([4, 1])
    with search_column:
        query = st.text_input("건물명·지번 검색", key="registration_building_search", placeholder="예: 대성빌 또는 북수리 1026")
    with reset_column:
        st.markdown("<div style='height: 1.75rem'></div>", unsafe_allow_html=True)
        if st.button("검색 초기화", width="stretch"):
            reset_for_new_listing()
            st.rerun()
    selected = _selected_building()

    if selected:
        st.success(f"선택한 기존 건물: {selected['building_name']} · {selected['lot_address']}")
        if st.button("다른 건물 찾기 또는 새 건물 등록", width="stretch"):
            _clear_selected_building()
            st.rerun()
        return selected

    if len(query.strip()) >= 2:
        results = search_buildings(query)
        if results:
            st.info("같은 건물을 새로 만들지 않도록, 아래 결과에서 먼저 선택해 주세요.")
            for building in results:
                label = f"{building['building_name']} · {building['lot_address']} · 등록 호실 {building['unit_count']}개"
                if st.button(label, key=f"select_building_{building['id']}", width="stretch"):
                    _select_building(building)
                    st.rerun()
        else:
            st.caption("등록된 건물이 없습니다. 아래에서 새 건물 정보를 입력해 주세요.")
    return None


def _render_new_building_fields() -> None:
    st.markdown("#### 2. 새 건물 정보")
    building_left, building_right = st.columns(2)
    with building_left:
        st.text_input("건물명 (선택)", key="registration_building_name", placeholder="예: 대성빌 · 모르면 비워 두세요")
    with building_right:
        area_column, number_column = st.columns(2)
        with area_column:
            st.text_input("지번 지역 *", key="registration_lot_area", placeholder="예: 북수리")
        with number_column:
            st.text_input("번지 번호 *", key="registration_lot_number", placeholder="예: 1026, 산 12-3")
    st.caption("건물명을 모르면 비워 두세요. 지번 지역과 번지 번호, 호수로 등록하며 목록에는 `건물명 미입력`으로 표시됩니다.")
    st.text_input("공동현관 비밀번호 (내부정보)", key="registration_common_entrance_password")
    with st.expander("건물 상세정보"):
        st.selectbox("엘리베이터", ["확인 필요", "있음", "없음"], key="registration_has_elevator")
        st.text_area("건물 내부 메모 (외부 공유 금지)", key="registration_building_internal_note")


def _render_existing_building_summary(building: dict) -> None:
    st.markdown("#### 2. 선택한 건물")
    st.caption(f"{building['building_name']} · {building['lot_address']} · 등록 호실 {building['unit_count']}개")
    units = get_building_units(building["id"])
    if units:
        st.dataframe(
            [{
                "호실": row["unit_number"], "룸 형태": row["room_type"] or "미입력", "층": row["floor_number"] or "-",
                "최근 조건": f"{row['deposit_manwon'] or '확인 필요'}/{row['monthly_rent_manwon'] or '확인 필요'}",
                "최근 상태": row["listing_status"] or "-", "마지막 접수일": row["received_date"] or "-",
            } for row in units],
            width="stretch",
            hide_index=True,
        )
        st.caption("같은 호실이 다시 매물로 나왔다면 아래에서 선택하세요. 이번 매물 입력칸이 바로 열립니다.")
        unit_columns = st.columns(min(len(units), 4))
        for index, unit in enumerate(units):
            with unit_columns[index % len(unit_columns)]:
                if st.button(f"{unit['unit_number']} 최신 정보 수정", key=f"relist_unit_{unit['id']}", width="stretch"):
                    _select_unit_for_relisting(unit["id"])
                    st.rerun()
    st.info("새 호실을 등록합니다. 주소·공동현관·엘리베이터·주차 정보는 다시 입력하지 않습니다.")


def _render_unit_and_listing_fields(building: dict | None) -> bool:
    st.divider()
    st.markdown("#### 3. 새 호실 정보")
    unit_left, unit_middle, unit_right = st.columns(3)
    with unit_left:
        st.text_input("호수 *", key="registration_unit_number", placeholder="예: 302", on_change=_fill_floor_from_unit_number)
    with unit_middle:
        st.selectbox("룸 형태", REGISTRATION_ROOM_TYPES, key="registration_room_type")
    with unit_right:
        st.number_input("층 (호수 입력 시 자동)", min_value=0, step=1, value=None, key="registration_floor_number")

    duplicate_unit = False
    if building and (unit_number := _field_value("unit_number")):
        duplicate_unit = building_has_unit(building["id"], str(unit_number))
        if duplicate_unit:
            st.error(f"{unit_number}는 이미 등록된 호실입니다. 위 목록에서 해당 호실의 ‘최신 정보 수정’을 선택해 주세요.")

    with st.expander("호실 상세정보"):
        st.selectbox("방향", ["확인 필요", "동", "서", "남", "북", "남동", "남서", "북동", "북서"], key="registration_direction")
        st.selectbox("방문 방법", ["확인 필요", "비밀번호", "열쇠", "세입자 협의", "관리인 문의"], key="registration_access_method")
        st.text_input("방문 비밀번호 (내부정보)", key="registration_unit_access_password")

    st.divider()
    st.markdown("#### 4. 이번 매물 조건")
    listing_left, listing_middle, listing_right = st.columns(3)
    with listing_left:
        st.selectbox("매물 상태 *", LISTING_STATUSES, index=LISTING_STATUSES.index("공실"), key="registration_listing_status")
        st.number_input("보증금 (만원, 선택)", min_value=0, step=10, value=None, key="registration_deposit_manwon")
    with listing_middle:
        st.selectbox("입주 가능 유형 *", AVAILABILITY_TYPES, key="registration_availability_type")
        st.number_input("월세 (만원, 선택)", min_value=0, step=1, value=None, key="registration_monthly_rent_manwon")
    with listing_right:
        st.date_input("매물 접수일", value=date.today(), key="registration_received_date", help="기본값은 오늘입니다. 실제 접수일이 다르면 바꿔 주세요.")
        st.number_input("관리비 (만원)", min_value=0, step=1, value=None, key="registration_management_fee_manwon")
    st.caption("보증금과 월세는 선택 입력입니다. 전세 매물은 월세를 비워 두세요.")
    _render_listing_holder_fields("registration")

    if _field_value("availability_type") == "날짜 지정":
        st.date_input("입주 가능일 *", value=None, key="registration_available_from_date")
    st.date_input("퇴실 예정일", value=None, key="registration_move_out_due_date")
    _render_management_fields("registration")
    st.text_area("이번 매물 메모", key="registration_listing_note", placeholder="예: 세입자와 방문시간 협의 필요")
    with st.expander("임대인·세입자 연락처 (내부정보)"):
        contact_left, contact_right = st.columns(2)
        with contact_left:
            st.text_input("임대인 연락처", key="registration_landlord_contact", placeholder="예: 010-1234-5678", on_change=_format_phone_input, args=("registration_landlord_contact",))
        with contact_right:
            st.text_input("세입자 연락처", key="registration_tenant_contact", placeholder="예: 010-1234-5678", on_change=_format_phone_input, args=("registration_tenant_contact",))
        st.caption("기본 매물 목록과 엑셀 파일에는 포함하지 않습니다.")
    return duplicate_unit


def _show_confirmation(pending: dict) -> None:
    payload = pending["payload"]
    building_id = pending.get("building_id")
    button_label = "새 호실·첫 매물 등록" if building_id else "건물·호실·첫 매물 등록"
    st.success("입력한 내용을 확인해 주세요. 아래 버튼을 눌러야 실제로 저장됩니다.")
    st.markdown(f"**{listing_summary(payload)}**")
    st.caption("비밀번호와 내부 메모는 이 요약에 표시하지 않습니다.")
    save_column, edit_column = st.columns(2)
    with save_column:
        if st.button(button_label, type="primary", width="stretch"):
            try:
                if building_id:
                    _, listing_id = save_confirmed_existing_building_listing(building_id, payload)
                else:
                    _, _, listing_id = save_confirmed_first_listing(payload)
            except Exception as error:
                st.error(f"저장하지 못했습니다. 입력 내용을 확인해 주세요. ({error})")
                return
            unit_number = payload["unit"]["unit_number"]
            building_name = payload["building"]["building_name"]
            _clear_registration_inputs()
            _clear_selected_building()
            st.session_state["registration_success"] = f"{building_name} {unit_number}호가 등록되었습니다. 매물번호는 {listing_number(listing_id)}입니다."
            st.rerun()
    with edit_column:
        if st.button("입력 계속하기", width="stretch"):
            st.session_state.pop("pending_registration", None)
            st.rerun()


def _date_value(value: str | None):
    return date.fromisoformat(value) if value else None


def _render_unit_complete_delete(unit_id: int, context: dict) -> None:
    summary = get_unit_deletion_summary(unit_id)
    unit_label = context["unit_number"] if context["unit_number"].endswith("호") else f"{context['unit_number']}호"
    with st.expander("이 호실 완전 삭제"):
        st.error(f"{context['building_name']} {unit_label}와 연결된 매물 {summary['listings']}건, 계약 {summary['contracts']}건, 상담 {summary['consultations']}건을 복구할 수 없게 삭제합니다. 건물 정보는 남습니다.")
        confirmed = st.checkbox("이 호실과 연결된 모든 기록을 완전히 삭제하는 것을 확인했습니다.", key=f"delete_unit_confirm_{unit_id}")
        if st.button("호실 완전 삭제", type="secondary", disabled=not confirmed, key=f"delete_unit_{unit_id}"):
            try:
                deleted = delete_unit(unit_id)
            except Exception as error:
                st.error(f"호실을 삭제하지 못했습니다. ({error})")
                return
            _clear_current_listing_inputs()
            _clear_relisting_inputs()
            st.session_state.pop("selected_registration_unit_id", None)
            st.success(f"호실을 삭제했습니다. 매물 {deleted['listings']}건, 계약 {deleted['contracts']}건, 상담 {deleted['consultations']}건도 함께 삭제했습니다. 건물 정보는 남아 있습니다.")
            st.rerun()


def _render_current_listing_edit(unit_id: int) -> None:
    context = get_unit_relisting_context(unit_id)
    listing = get_current_listing(unit_id)
    if context is None or listing is None:
        _render_relisting_form(unit_id)
        return

    unit_label = context["unit_number"] if context["unit_number"].endswith("호") else f"{context['unit_number']}호"
    st.markdown("#### 기존 호실 최신 정보 수정")
    st.info(f"수정 대상: {listing_number(listing['id'])} · {context['building_name']} · {unit_label} · 최초 접수일 {listing['received_date']}")
    if listing.get("closed_date") or listing.get("listing_status") in ("계약 완료", "종료"):
        st.warning("마지막 매물은 종료 상태입니다. 아래에서 저장하면 종료 상태를 지우고 최신 매물 상태로 바꿉니다.")
    else:
        st.caption("저장하면 새 매물 기록을 만들지 않고, 이 호실의 최신 매물 정보만 바꿉니다. 연결된 계약·상담 기록은 유지됩니다.")
    if st.button("다른 호실 선택", key="back_to_relisting"):
        st.session_state.pop("selected_registration_unit_id", None)
        _clear_current_listing_inputs()
        st.rerun()

    left, middle, right = st.columns(3)
    with left:
        status_index = LISTING_STATUSES.index(listing["listing_status"]) if listing["listing_status"] in LISTING_STATUSES else 0
        st.selectbox("매물 상태 *", LISTING_STATUSES, index=status_index, key="edit_listing_status")
        st.number_input("보증금 (만원, 선택)", min_value=0, step=10, value=listing["deposit_manwon"], key="edit_deposit_manwon")
        st.number_input("월세 (만원, 선택)", min_value=0, step=1, value=listing["monthly_rent_manwon"], key="edit_monthly_rent_manwon")
    with middle:
        availability_index = AVAILABILITY_TYPES.index(listing["availability_type"]) if listing["availability_type"] in AVAILABILITY_TYPES else 0
        st.selectbox("입주 가능 유형 *", AVAILABILITY_TYPES, index=availability_index, key="edit_availability_type")
        st.number_input("관리비 (만원)", min_value=0, step=1, value=listing["management_fee_manwon"], key="edit_management_fee_manwon")
    with right:
        if st.session_state.get("edit_availability_type", listing["availability_type"]) == "날짜 지정":
            st.date_input("입주 가능일 *", value=_date_value(listing["available_from_date"]), key="edit_available_from_date")
        st.date_input("퇴실 예정일", value=_date_value(listing["move_out_due_date"]), key="edit_move_out_due_date")
    _render_listing_holder_fields("edit", listing.get("listing_holder"))
    _render_management_fields("edit", listing)
    st.text_area("이번 매물 메모", value=listing["listing_note"] or "", key="edit_listing_note")
    with st.expander("임대인·세입자 연락처 (내부정보)"):
        contact_left, contact_right = st.columns(2)
        with contact_left:
            st.text_input("임대인 연락처", value=listing["landlord_contact"] or "", key="edit_landlord_contact", on_change=_format_phone_input, args=("edit_landlord_contact",))
        with contact_right:
            st.text_input("세입자 연락처", value=listing["tenant_contact"] or "", key="edit_tenant_contact", on_change=_format_phone_input, args=("edit_tenant_contact",))
        st.caption("기본 매물 목록과 엑셀 파일에는 포함하지 않습니다.")

    if st.button("최신 정보 저장", type="primary"):
        raw = {
            "listing_status": st.session_state.get("edit_listing_status"),
            "deposit_manwon": st.session_state.get("edit_deposit_manwon"),
            "monthly_rent_manwon": st.session_state.get("edit_monthly_rent_manwon"),
            "management_fee_manwon": st.session_state.get("edit_management_fee_manwon"),
            "availability_type": st.session_state.get("edit_availability_type"),
            "available_from_date": st.session_state.get("edit_available_from_date"),
            "move_out_due_date": st.session_state.get("edit_move_out_due_date"),
            "has_listing_photos": st.session_state.get("edit_has_listing_photos"),
            "cleaning_status": listing["cleaning_status"],
            "wallpaper_status": listing["wallpaper_status"],
            "repair_status": listing["repair_status"],
            "listing_holder_choice": st.session_state.get("edit_listing_holder_choice"),
            "listing_holder_custom": st.session_state.get("edit_listing_holder_custom"),
            "next_check_date": st.session_state.get("edit_next_check_date"),
            "listing_note": st.session_state.get("edit_listing_note"),
            "landlord_contact": st.session_state.get("edit_landlord_contact"),
            "tenant_contact": st.session_state.get("edit_tenant_contact"),
        }
        updated, errors = validate_current_listing(raw)
        if errors:
            for error in errors:
                st.error(error)
            return
        try:
            save_current_listing_changes(listing["id"], updated)
        except Exception as error:
            st.error(f"수정하지 못했습니다. 입력 내용은 유지됩니다. ({error})")
            return
        _clear_current_listing_inputs()
        st.session_state.pop("selected_registration_unit_id", None)
        st.success(f"최신 매물 정보를 저장했습니다. 매물번호 {listing_number(listing['id'])}는 유지되며, 새 매물 기록은 만들지 않았고 계약·상담 기록은 유지됩니다.")
        st.rerun()

    with st.expander("이 매물 종료 처리"):
        st.warning("종료해도 기록은 삭제되지 않고 과거 이력에 남습니다.")
        close_reason = st.selectbox("종료 사유", ["계약 완료", "타 부동산 계약", "임대인 보류", "광고 중단", "정보 오류", "기타"], key="close_reason")
        close_date = st.date_input("종료일", value=date.today(), key="close_date")
        if st.button("종료 처리", type="secondary"):
            try:
                close_listing(listing["id"], close_date, close_reason)
            except Exception as error:
                st.error(f"종료 처리하지 못했습니다. ({error})")
                return
            _clear_current_listing_inputs()
            st.session_state.pop("selected_registration_unit_id", None)
            st.success("매물을 종료 처리했습니다. 기록은 과거 이력에 남아 있습니다.")
            st.rerun()

    with st.expander("이 매물 완전 삭제"):
        st.error("이 매물은 복구할 수 없게 삭제됩니다. 연결된 계약·상담 기록도 함께 삭제됩니다.")
        confirmed = st.checkbox("이 매물과 연결 기록을 완전히 삭제하는 것을 확인했습니다.", key=f"delete_listing_confirm_{listing['id']}")
        if st.button("매물 완전 삭제", type="secondary", disabled=not confirmed, key=f"delete_listing_{listing['id']}"):
            try:
                deleted = delete_listing(listing["id"])
            except Exception as error:
                st.error(f"매물을 삭제하지 못했습니다. ({error})")
                return
            st.session_state.pop("selected_registration_unit_id", None)
            st.success(f"매물을 삭제했습니다. 연결된 계약 {deleted['contracts']}건, 상담 {deleted['consultations']}건도 함께 삭제했습니다.")
            st.rerun()

    _render_unit_complete_delete(unit_id, context)


def _render_relisting_form(unit_id: int) -> None:
    context = get_unit_relisting_context(unit_id)
    if context is None:
        st.error("선택한 호실을 찾을 수 없습니다. 다시 선택해 주세요.")
        return
    history = get_unit_listing_history(unit_id)
    previous = history[0] if history else None

    st.markdown("#### 기존 호실 현재 매물 등록")
    if st.button("다른 호실 선택", key="change_relisting_unit"):
        st.session_state.pop("selected_registration_unit_id", None)
        _clear_relisting_inputs()
        st.rerun()

    unit_label = context["unit_number"] if context["unit_number"].endswith("호") else f"{context['unit_number']}호"
    st.info(f"선택한 호실: {context['building_name']} · {context['lot_address']} · {unit_label}")
    st.caption(
        f"고정정보: {context['room_type'] or '룸 형태 미입력'} · {context['floor_number'] or '층 미입력'}층 · "
        f"{context['direction'] or '방향 미입력'} · 방문 방법 {context['access_method'] or '미입력'}"
    )
    if context["unit_options"] or context["unit_highlights"]:
        st.caption(f"옵션·특징: {context['unit_options'] or '옵션 미입력'} · {context['unit_highlights'] or '특징 미입력'}")
    st.info(f"공동현관 비밀번호: {context['common_entrance_password'] or '등록되지 않음'} · 방문 비밀번호: {context['unit_access_password'] or '등록되지 않음'}")

    if previous:
        price = f"{previous['deposit_manwon'] or '확인 필요'}/{previous['monthly_rent_manwon'] or '확인 필요'}"
        st.markdown(
            f"**이전 매물 참고값:** {price} · 관리비 {previous['management_fee_manwon'] or '미입력'}만원 · "
            f"상태 {previous['listing_status']} · 마지막 등록 {previous['received_date']}"
        )
        st.caption("이 호실에는 현재 매물 기록이 없습니다. 아래에서 현재 매물 정보를 등록합니다.")

    st.divider()
    st.markdown("#### 현재 매물 조건")
    left, middle, right = st.columns(3)
    with left:
        st.selectbox("매물 상태 *", LISTING_STATUSES, key="relisting_listing_status")
        price_mode = st.radio("가격 입력 방식", ["새 가격 입력", "가격 확인 필요"], key="relisting_price_mode")
    with middle:
        if price_mode == "새 가격 입력":
            st.number_input("보증금 (만원, 선택)", min_value=0, step=10, value=None, key="relisting_deposit_manwon")
            st.number_input("월세 (만원, 선택)", min_value=0, step=1, value=None, key="relisting_monthly_rent_manwon")
            st.caption("전세 매물은 월세를 비워 두세요. 가격 자체가 미확정이면 `가격 확인 필요`를 선택하세요.")
        else:
            st.info("가격은 저장하지 않고 ‘가격 확인 필요’로 기록합니다.")
        st.number_input("관리비 (만원)", min_value=0, step=1, value=None, key="relisting_management_fee_manwon")
    with right:
        st.selectbox("입주 가능 유형 *", AVAILABILITY_TYPES, key="relisting_availability_type")
        st.date_input("매물 접수일", value=date.today(), key="relisting_received_date")
    if st.session_state.get("relisting_availability_type") == "날짜 지정":
        st.date_input("입주 가능일 *", value=None, key="relisting_available_from_date")
    st.date_input("퇴실 예정일", value=None, key="relisting_move_out_due_date")
    _render_listing_holder_fields("relisting")
    _render_management_fields("relisting")
    st.text_area("이번 매물 메모", key="relisting_listing_note")
    with st.expander("임대인·세입자 연락처 (내부정보)"):
        contact_left, contact_right = st.columns(2)
        with contact_left:
            st.text_input("임대인 연락처", key="relisting_landlord_contact", placeholder="예: 010-1234-5678", on_change=_format_phone_input, args=("relisting_landlord_contact",))
        with contact_right:
            st.text_input("세입자 연락처", key="relisting_tenant_contact", placeholder="예: 010-1234-5678", on_change=_format_phone_input, args=("relisting_tenant_contact",))
        st.caption("기본 매물 목록과 엑셀 파일에는 포함하지 않습니다.")

    if st.button("현재 매물 등록", type="primary"):
        raw = {
            "listing_status": st.session_state.get("relisting_listing_status"),
            "price_mode": st.session_state.get("relisting_price_mode"),
            "deposit_manwon": st.session_state.get("relisting_deposit_manwon"),
            "monthly_rent_manwon": st.session_state.get("relisting_monthly_rent_manwon"),
            "management_fee_manwon": st.session_state.get("relisting_management_fee_manwon"),
            "availability_type": st.session_state.get("relisting_availability_type"),
            "available_from_date": st.session_state.get("relisting_available_from_date"),
            "received_date": st.session_state.get("relisting_received_date"),
            "move_out_due_date": st.session_state.get("relisting_move_out_due_date"),
            "has_listing_photos": st.session_state.get("relisting_has_listing_photos"),
            "listing_holder_choice": st.session_state.get("relisting_listing_holder_choice"),
            "listing_holder_custom": st.session_state.get("relisting_listing_holder_custom"),
            "next_check_date": st.session_state.get("relisting_next_check_date"),
            "listing_note": st.session_state.get("relisting_listing_note"),
            "landlord_contact": st.session_state.get("relisting_landlord_contact"),
            "tenant_contact": st.session_state.get("relisting_tenant_contact"),
        }
        listing, errors = validate_relisting(raw)
        if errors:
            for error in errors:
                st.error(error)
            return
        try:
            listing_id = save_current_listing_for_existing_unit(unit_id, listing)
        except Exception as error:
            st.error(f"저장하지 못했습니다. 입력 내용은 유지됩니다. ({error})")
            return
        st.success(f"{context['building_name']} {unit_label}의 현재 매물 정보가 등록되었습니다. 매물번호는 {listing_number(listing_id)}입니다.")
        _clear_relisting_inputs()
        st.session_state.pop("selected_registration_unit_id", None)
        st.rerun()

    with st.expander("이 호실을 더 이상 사용하지 않음"):
        st.caption("호실을 삭제하지 않고 목록에서 숨깁니다. 과거 매물 기록은 남습니다.")
        confirmed = st.checkbox("이 호실을 비활성화하는 것을 확인했습니다.", key=f"deactivate_unit_confirm_{unit_id}")
        if st.button("호실 비활성화", disabled=not confirmed, key=f"deactivate_unit_{unit_id}"):
            try:
                deactivate_unit(unit_id)
            except Exception as error:
                st.error(f"호실을 비활성화하지 못했습니다. ({error})")
                return
            _clear_relisting_inputs()
            st.session_state.pop("selected_registration_unit_id", None)
            st.success("호실을 삭제하지 않고 비활성화했습니다. 과거 기록은 보존됩니다.")
            st.rerun()

    _render_unit_complete_delete(unit_id, context)


def render_listing_form() -> None:
    st.subheader("매물 등록·수정")
    st.markdown("기존 건물을 먼저 찾은 뒤 새 호실과 첫 매물을 등록합니다. 기존 호실을 선택하면 최신 매물 정보를 바로 수정할 수 있습니다.")

    if success_message := st.session_state.pop("registration_success", None):
        st.success(success_message)

    if pending := st.session_state.get("pending_registration"):
        _show_confirmation(pending)
        return

    building = _render_building_search()
    selected_unit_id = st.session_state.get("selected_registration_unit_id")
    if building and selected_unit_id:
        _render_current_listing_edit(selected_unit_id)
        return
    if building:
        _render_existing_building_summary(building)
    else:
        _render_new_building_fields()
    duplicate_unit = _render_unit_and_listing_fields(building)

    st.divider()
    button_label = "새 호실·첫 매물 등록 전 확인" if building else "입력 내용 확인"
    if st.button(button_label, type="primary", disabled=duplicate_unit):
        payload, errors = validate_new_building_listing(_collect_input()) if not building else (None, [])
        if building:
            # 기존 건물의 이름·지번은 선택값으로 넣어 같은 입력 검사를 적용한다.
            from services.listing_service import validate_first_listing
            payload, errors = validate_first_listing(_collect_input())
        if errors:
            for error in errors:
                st.error(error)
            return
        st.session_state["pending_registration"] = {"payload": payload, "building_id": building["id"] if building else None}
        st.rerun()
