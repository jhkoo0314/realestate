"""신규 건물 또는 기존 건물의 새 호실·첫 매물 등록 화면."""

from __future__ import annotations

from datetime import date

import streamlit as st

from services.listing_service import (
    AVAILABILITY_TYPES,
    LISTING_STATUSES,
    ROOM_TYPES,
    listing_summary,
    save_confirmed_existing_building_listing,
    save_confirmed_first_listing,
    save_confirmed_relisting,
    save_current_listing_changes,
    close_listing,
    validate_new_building_listing,
    validate_relisting,
    validate_current_listing,
)
from storage.building_repository import get_building_units, get_unit_listing_history, search_buildings
from storage.listing_create_repository import building_has_unit
from storage.listing_write_repository import deactivate_unit, get_current_listing, get_unit_relisting_context, has_active_listing


INPUT_KEYS = [
    "building_name", "lot_address", "admin_address", "road_address", "common_entrance_password",
    "has_elevator", "parking_status", "building_internal_note", "unit_number", "floor_number",
    "room_type", "direction", "access_method", "unit_access_password",
    "unit_highlights", "listing_status", "deposit_manwon", "monthly_rent_manwon",
    "management_fee_manwon", "received_date", "availability_type", "available_from_date", "move_out_due_date",
    "photo_status", "listing_note", "landlord_contact", "tenant_contact", "next_check_date",
]


def _clear_registration_inputs() -> None:
    for key in INPUT_KEYS:
        st.session_state.pop(f"registration_{key}", None)
    st.session_state.pop("pending_registration", None)


def _field_value(name: str):
    return st.session_state.get(f"registration_{name}")


def _selected_building() -> dict | None:
    return st.session_state.get("selected_registration_building")


def _collect_input() -> dict:
    values = {key: _field_value(key) for key in INPUT_KEYS}
    if building := _selected_building():
        values["building_name"] = building["building_name"]
        values["lot_address"] = building["lot_address"]
    return values


def _clear_selected_building() -> None:
    st.session_state.pop("selected_registration_building", None)
    st.session_state.pop("selected_registration_unit_id", None)
    st.session_state.pop("relisting_confirmed_unit_id", None)
    st.session_state.pop("editing_listing_unit_id", None)
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
    st.session_state["selected_registration_unit_id"] = unit_id
    st.session_state.pop("relisting_confirmed_unit_id", None)
    st.session_state.pop("editing_listing_unit_id", None)
    st.session_state.pop("pending_registration", None)


def _render_building_search() -> dict | None:
    st.markdown("#### 1. 먼저 기존 건물을 찾아보세요")
    st.caption("건물명 또는 지번을 2글자 이상 입력하면, 이미 등록된 건물을 먼저 보여 드립니다.")
    search_column, reset_column = st.columns([4, 1])
    with search_column:
        query = st.text_input("건물명·지번 검색", key="registration_building_search", placeholder="예: 대성빌 또는 북수리 1026")
    with reset_column:
        st.markdown("<div style='height: 1.75rem'></div>", unsafe_allow_html=True)
        if st.button("검색 초기화", use_container_width=True):
            reset_for_new_listing()
            st.rerun()
    selected = _selected_building()

    if selected:
        st.success(f"선택한 기존 건물: {selected['building_name']} · {selected['lot_address']}")
        if st.button("다른 건물 찾기 또는 새 건물 등록", use_container_width=True):
            _clear_selected_building()
            st.rerun()
        return selected

    if len(query.strip()) >= 2:
        results = search_buildings(query)
        if results:
            st.info("같은 건물을 새로 만들지 않도록, 아래 결과에서 먼저 선택해 주세요.")
            for building in results:
                label = f"{building['building_name']} · {building['lot_address']} · 등록 호실 {building['unit_count']}개"
                if st.button(label, key=f"select_building_{building['id']}", use_container_width=True):
                    _select_building(building)
                    st.rerun()
        else:
            st.caption("등록된 건물이 없습니다. 아래에서 새 건물 정보를 입력해 주세요.")
    return None


def _render_new_building_fields() -> None:
    st.markdown("#### 2. 새 건물 정보")
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
            use_container_width=True,
            hide_index=True,
        )
        st.caption("같은 호실이 다시 매물로 나왔다면 아래에서 선택해 새 매물 회차를 만드세요.")
        unit_columns = st.columns(min(len(units), 4))
        for index, unit in enumerate(units):
            with unit_columns[index % len(unit_columns)]:
                if st.button(f"{unit['unit_number']} 재등록", key=f"relist_unit_{unit['id']}", use_container_width=True):
                    _select_unit_for_relisting(unit["id"])
                    st.rerun()
    st.info("새 호실을 등록합니다. 주소·공동현관·엘리베이터·주차 정보는 다시 입력하지 않습니다.")


def _render_unit_and_listing_fields(building: dict | None) -> bool:
    st.divider()
    st.markdown("#### 3. 새 호실 정보")
    unit_left, unit_middle, unit_right = st.columns(3)
    with unit_left:
        st.text_input("호수 *", key="registration_unit_number", placeholder="예: 302")
    with unit_middle:
        st.selectbox("룸 형태", ROOM_TYPES, key="registration_room_type")
    with unit_right:
        st.number_input("층", min_value=0, step=1, value=None, key="registration_floor_number")

    duplicate_unit = False
    if building and (unit_number := _field_value("unit_number")):
        duplicate_unit = building_has_unit(building["id"], str(unit_number))
        if duplicate_unit:
            st.error(f"{unit_number}는 이미 등록된 호실입니다. 이 단계에서는 새 호실을 저장할 수 없습니다. 기존 호실 재등록은 다음 단계에서 연결됩니다.")

    with st.expander("호실 상세정보"):
        detail_left, detail_right = st.columns(2)
        with detail_left:
            st.selectbox("방향", ["확인 필요", "동", "서", "남", "북", "남동", "남서", "북동", "북서"], key="registration_direction")
            st.selectbox("방문 방법", ["확인 필요", "비밀번호", "열쇠", "세입자 협의", "관리인 문의"], key="registration_access_method")
            st.text_input("방문 비밀번호 (내부정보)", key="registration_unit_access_password", type="password")
        with detail_right:
            st.text_area("구조상 장점", key="registration_unit_highlights", placeholder="예: 안방 양창, 수납 넉넉함")

    st.divider()
    st.markdown("#### 4. 이번 매물 조건")
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
    with st.expander("임대인·세입자 연락처 (내부정보)"):
        contact_left, contact_right = st.columns(2)
        with contact_left:
            st.text_input("임대인 연락처", key="registration_landlord_contact", placeholder="예: 010-1234-5678")
        with contact_right:
            st.text_input("세입자 연락처", key="registration_tenant_contact", placeholder="예: 010-1234-5678")
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
        if st.button(button_label, type="primary", use_container_width=True):
            try:
                if building_id:
                    save_confirmed_existing_building_listing(building_id, payload)
                else:
                    save_confirmed_first_listing(payload)
            except Exception as error:
                st.error(f"저장하지 못했습니다. 입력 내용을 확인해 주세요. ({error})")
                return
            unit_number = payload["unit"]["unit_number"]
            building_name = payload["building"]["building_name"]
            _clear_registration_inputs()
            _clear_selected_building()
            st.session_state["registration_success"] = f"{building_name} {unit_number}호가 등록되었습니다."
            st.rerun()
    with edit_column:
        if st.button("입력 계속하기", use_container_width=True):
            st.session_state.pop("pending_registration", None)
            st.rerun()


def _date_value(value: str | None):
    return date.fromisoformat(value) if value else None


def _render_current_listing_edit(unit_id: int) -> None:
    context = get_unit_relisting_context(unit_id)
    listing = get_current_listing(unit_id)
    if context is None or listing is None:
        st.error("수정할 현재 매물을 찾을 수 없습니다. 다른 호실을 선택해 주세요.")
        return

    unit_label = context["unit_number"] if context["unit_number"].endswith("호") else f"{context['unit_number']}호"
    st.markdown("#### 현재 매물 수정")
    st.info(f"수정 대상: {context['building_name']} · {unit_label} · 접수일 {listing['received_date']}")
    st.caption("이 화면에서 저장해도 새 매물 기록은 생기지 않습니다. 현재 기록의 조건만 바뀝니다.")
    if st.button("재등록 선택으로 돌아가기", key="back_to_relisting"):
        st.session_state.pop("editing_listing_unit_id", None)
        st.rerun()

    left, middle, right = st.columns(3)
    with left:
        status_index = LISTING_STATUSES.index(listing["listing_status"]) if listing["listing_status"] in LISTING_STATUSES else 0
        st.selectbox("매물 상태 *", LISTING_STATUSES, index=status_index, key="edit_listing_status")
        st.number_input("보증금 (만원) *", min_value=0, step=10, value=listing["deposit_manwon"], key="edit_deposit_manwon")
        st.number_input("월세 (만원) *", min_value=0, step=1, value=listing["monthly_rent_manwon"], key="edit_monthly_rent_manwon")
    with middle:
        availability_index = AVAILABILITY_TYPES.index(listing["availability_type"]) if listing["availability_type"] in AVAILABILITY_TYPES else 0
        st.selectbox("입주 가능 유형 *", AVAILABILITY_TYPES, index=availability_index, key="edit_availability_type")
        st.number_input("관리비 (만원)", min_value=0, step=1, value=listing["management_fee_manwon"], key="edit_management_fee_manwon")
        photo_options = ["확인 필요", "촬영 필요", "촬영 완료", "기존 사진 사용"]
        photo_index = photo_options.index(listing["photo_status"]) if listing["photo_status"] in photo_options else 0
        st.selectbox("사진 상태", photo_options, index=photo_index, key="edit_photo_status")
    with right:
        if st.session_state.get("edit_availability_type", listing["availability_type"]) == "날짜 지정":
            st.date_input("입주 가능일 *", value=_date_value(listing["available_from_date"]), key="edit_available_from_date")
        st.date_input("퇴실 예정일", value=_date_value(listing["move_out_due_date"]), key="edit_move_out_due_date")
        st.date_input("재확인 예정일", value=_date_value(listing["next_check_date"]), key="edit_next_check_date")
        if st.session_state.get("edit_photo_status", listing["photo_status"]) == "촬영 완료":
            st.date_input("사진 촬영일", value=date.today(), key="edit_last_photo_date")
    st.text_area("이번 매물 메모", value=listing["listing_note"] or "", key="edit_listing_note")
    with st.expander("임대인·세입자 연락처 (내부정보)"):
        contact_left, contact_right = st.columns(2)
        with contact_left:
            st.text_input("임대인 연락처", value=listing["landlord_contact"] or "", key="edit_landlord_contact")
        with contact_right:
            st.text_input("세입자 연락처", value=listing["tenant_contact"] or "", key="edit_tenant_contact")
        st.caption("기본 매물 목록과 엑셀 파일에는 포함하지 않습니다.")

    if st.button("현재 매물 수정", type="primary"):
        raw = {
            "listing_status": st.session_state.get("edit_listing_status"),
            "deposit_manwon": st.session_state.get("edit_deposit_manwon"),
            "monthly_rent_manwon": st.session_state.get("edit_monthly_rent_manwon"),
            "management_fee_manwon": st.session_state.get("edit_management_fee_manwon"),
            "availability_type": st.session_state.get("edit_availability_type"),
            "available_from_date": st.session_state.get("edit_available_from_date"),
            "move_out_due_date": st.session_state.get("edit_move_out_due_date"),
            "photo_status": st.session_state.get("edit_photo_status"),
            "last_photo_date": st.session_state.get("edit_last_photo_date"),
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
        st.success("현재 매물 조건을 수정했습니다. 새 매물 기록은 만들지 않았습니다.")
        st.rerun()

    with st.expander("이 매물 종료 처리"):
        st.warning("종료해도 기록은 삭제되지 않고 과거 이력에 남습니다.")
        close_reason = st.selectbox("종료 사유", ["계약 완료", "임대인 보류", "광고 중단", "정보 오류", "기타"], key="close_reason")
        close_date = st.date_input("종료일", value=date.today(), key="close_date")
        if st.button("종료 처리", type="secondary"):
            try:
                close_listing(listing["id"], close_date, close_reason)
            except Exception as error:
                st.error(f"종료 처리하지 못했습니다. ({error})")
                return
            st.session_state.pop("editing_listing_unit_id", None)
            st.success("매물을 종료 처리했습니다. 기록은 과거 이력에 남아 있습니다.")
            st.rerun()


def _render_relisting_form(unit_id: int) -> None:
    context = get_unit_relisting_context(unit_id)
    if context is None:
        st.error("선택한 호실을 찾을 수 없습니다. 다시 선택해 주세요.")
        return
    history = get_unit_listing_history(unit_id)
    previous = history[0] if history else None

    st.markdown("#### 기존 호실 재등록")
    if st.button("다른 호실 선택", key="change_relisting_unit"):
        st.session_state.pop("selected_registration_unit_id", None)
        st.session_state.pop("relisting_confirmed_unit_id", None)
        st.rerun()

    unit_label = context["unit_number"] if context["unit_number"].endswith("호") else f"{context['unit_number']}호"
    st.info(f"선택한 호실: {context['building_name']} · {context['lot_address']} · {unit_label}")
    st.caption(
        f"고정정보: {context['room_type'] or '룸 형태 미입력'} · {context['floor_number'] or '층 미입력'}층 · "
        f"{context['direction'] or '방향 미입력'} · 방문 방법 {context['access_method'] or '미입력'}"
    )
    if context["unit_options"] or context["unit_highlights"]:
        st.caption(f"옵션·특징: {context['unit_options'] or '옵션 미입력'} · {context['unit_highlights'] or '특징 미입력'}")
    st.caption("공동현관·방문 비밀번호와 내부 메모는 안전을 위해 이 화면에 자동 표시하지 않습니다.")

    if previous:
        price = f"{previous['deposit_manwon'] or '확인 필요'}/{previous['monthly_rent_manwon'] or '확인 필요'}"
        st.markdown(
            f"**이전 매물 참고값:** {price} · 관리비 {previous['management_fee_manwon'] or '미입력'}만원 · "
            f"상태 {previous['listing_status']} · 마지막 등록 {previous['received_date']}"
        )
        st.caption("이전 가격과 상태는 참고용입니다. 아래 입력칸에 자동으로 넣지 않습니다.")

    if has_active_listing(unit_id) and st.session_state.get("relisting_confirmed_unit_id") != unit_id:
        st.warning("현재 운영 중인 매물 기록이 있습니다. 단순한 조건 변경은 다음 단계의 ‘현재 매물 수정’ 기능으로 처리합니다.")
        left, right = st.columns(2)
        with left:
            if st.button("현재 매물 수정", use_container_width=True):
                st.session_state["editing_listing_unit_id"] = unit_id
                st.rerun()
        with right:
            if st.button("그래도 새 매물 회차 생성", type="primary", use_container_width=True):
                st.session_state["relisting_confirmed_unit_id"] = unit_id
                st.rerun()
        return

    if not has_active_listing(unit_id) and st.session_state.get("relisting_confirmed_unit_id") != unit_id:
        if st.button("새 매물 회차 생성", type="primary"):
            st.session_state["relisting_confirmed_unit_id"] = unit_id
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
                st.session_state.pop("selected_registration_unit_id", None)
                st.success("호실을 삭제하지 않고 비활성화했습니다. 과거 기록은 보존됩니다.")
                st.rerun()
        return

    st.divider()
    st.markdown("#### 이번 매물 조건")
    left, middle, right = st.columns(3)
    with left:
        st.selectbox("매물 상태 *", LISTING_STATUSES, key="relisting_listing_status")
        price_mode = st.radio("가격 입력 방식", ["새 가격 입력", "가격 확인 필요"], key="relisting_price_mode")
    with middle:
        if price_mode == "새 가격 입력":
            st.number_input("보증금 (만원) *", min_value=0, step=10, value=None, key="relisting_deposit_manwon")
            st.number_input("월세 (만원) *", min_value=0, step=1, value=None, key="relisting_monthly_rent_manwon")
        else:
            st.info("가격은 저장하지 않고 ‘가격 확인 필요’로 기록합니다.")
        st.number_input("관리비 (만원)", min_value=0, step=1, value=None, key="relisting_management_fee_manwon")
    with right:
        st.selectbox("입주 가능 유형 *", AVAILABILITY_TYPES, key="relisting_availability_type")
        st.date_input("매물 접수일", value=date.today(), key="relisting_received_date")
        st.selectbox("사진 상태", ["확인 필요", "촬영 필요", "촬영 완료", "기존 사진 사용"], key="relisting_photo_status")
    if st.session_state.get("relisting_availability_type") == "날짜 지정":
        st.date_input("입주 가능일 *", value=None, key="relisting_available_from_date")
    st.date_input("퇴실 예정일", value=None, key="relisting_move_out_due_date")
    st.date_input("재확인 예정일", value=None, key="relisting_next_check_date")
    st.text_area("이번 매물 메모", key="relisting_listing_note")
    with st.expander("임대인·세입자 연락처 (내부정보)"):
        contact_left, contact_right = st.columns(2)
        with contact_left:
            st.text_input("임대인 연락처", key="relisting_landlord_contact", placeholder="예: 010-1234-5678")
        with contact_right:
            st.text_input("세입자 연락처", key="relisting_tenant_contact", placeholder="예: 010-1234-5678")
        st.caption("기본 매물 목록과 엑셀 파일에는 포함하지 않습니다.")

    if st.button("새 매물 회차로 등록", type="primary"):
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
            "photo_status": st.session_state.get("relisting_photo_status"),
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
            save_confirmed_relisting(unit_id, listing)
        except Exception as error:
            st.error(f"저장하지 못했습니다. 입력 내용은 유지됩니다. ({error})")
            return
        st.success(f"{context['building_name']} {unit_label}의 새 매물 회차가 등록되었습니다.")
        st.session_state.pop("relisting_confirmed_unit_id", None)
        st.rerun()


def render_listing_form() -> None:
    st.subheader("매물 등록·수정")
    st.markdown("기존 건물을 먼저 찾은 뒤 새 호실과 첫 매물을 등록합니다. 기존 호실 재등록은 다음 단계에서 연결합니다.")

    if success_message := st.session_state.pop("registration_success", None):
        st.success(success_message)

    if pending := st.session_state.get("pending_registration"):
        _show_confirmation(pending)
        return

    building = _render_building_search()
    selected_unit_id = st.session_state.get("selected_registration_unit_id")
    if building and selected_unit_id:
        if st.session_state.get("editing_listing_unit_id") == selected_unit_id:
            _render_current_listing_edit(selected_unit_id)
            return
        _render_relisting_form(selected_unit_id)
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
