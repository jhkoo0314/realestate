"""오늘의 현재 매물 목록, 검색·필터와 확인 업무 화면."""

from __future__ import annotations

from datetime import date

import streamlit as st

from services.listing_service import LISTING_STATUSES, ROOM_TYPES, delete_listing
from services.export_service import create_current_listing_excel, make_export_filename
from storage.export_repository import get_current_listing_export_rows
from storage.listing_repository import get_current_listings, update_listing_quick_fields
from storage.database import (
    DATABASE_PATH,
)


PHOTO_STATUSES = ["확인 필요", "촬영 필요", "촬영 완료", "기존 사진 사용"]
PHOTO_AVAILABILITY = ["있음", "없음", "확인 필요"]
SITE_PREPARATION_STATUSES = ["확인 필요", "문제 없음", "완료", "필요", "진행 중"]
TASK_FILTERS = ["재확인 필요", "사진 촬영 필요", "현장 상태 확인 필요", "입주 가능일 확인 필요", "매물 상태 확인 필요"]


def _clear_filters() -> None:
    for key in (
        "dashboard_query", "dashboard_received_start", "dashboard_received_end", "dashboard_statuses",
        "dashboard_listing_scope", "dashboard_room_types", "dashboard_photo_statuses", "dashboard_photo_availability", "dashboard_task",
    ):
        st.session_state.pop(key, None)
    st.session_state["dashboard_has_searched"] = False


def _date_text(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _summary(listings: list[dict]) -> dict[str, int]:
    today = date.today().isoformat()
    return {
        "오늘 새 접수": sum(item["received_date"] == today for item in listings),
        "퇴실 예정": sum(item["listing_status"] == "퇴실 예정" for item in listings),
        "재확인 필요": sum("재확인 필요" in item["tasks"] for item in listings),
        "사진 촬영 필요": sum("사진 촬영 필요" in item["tasks"] for item in listings),
        "공실": sum(item["listing_status"] == "공실" for item in listings),
    }


def _site_preparation_text(item: dict) -> str:
    labels = (("청소", "cleaning_status"), ("도배", "wallpaper_status"), ("수리", "repair_status"))
    return " · ".join(f"{label} {item.get(field) or '확인 필요'}" for label, field in labels)


def _display_rows(listings: list[dict]) -> list[dict]:
    rows = []
    for item in listings:
        availability = item["availability_type"]
        if availability == "날짜 지정" and item["available_from_date"]:
            availability = f"{item['available_from_date']} 입주"
        rows.append({
            "상태": item["listing_status"], "건물명": item["building_name"], "호수": item["unit_number"],
            "형태": item["room_type"] or "미입력", "보증금": item["deposit_manwon"] or "확인 필요",
            "월세": item["monthly_rent_manwon"] or "확인 필요", "관리비": item["management_fee_manwon"] or "-",
            "입주 가능": availability, "사진 상태": item["photo_status"] or "확인 필요",
            "사진 보유": item["has_listing_photos"], "현장 준비": _site_preparation_text(item),
            "해야 할 일": ", ".join(item["tasks"]) or "-",
            "재확인일": item["next_check_date"] or "-", "종료일": item["closed_date"] or "-",
            "종료 사유": item["close_reason"] or "-", "메모": item["listing_note"] or "-",
        })
    return rows


def _render_quick_edit(selected: dict) -> None:
    st.markdown("#### 선택한 매물 빠른 수정")
    st.caption(
        f"{selected['building_name']} · {selected['lot_address']} · {selected['unit_number']}호 · "
        f"접수일 {selected['received_date']} · 현재 조건 {selected['deposit_manwon'] or '확인 필요'}/{selected['monthly_rent_manwon'] or '확인 필요'}"
    )
    st.caption("확인·관리 상태만 바로 바꿉니다. 가격·입주일·메모를 바꾸려면 ‘최신 정보 수정’ 화면을 사용하세요.")
    left, middle, right, date_column = st.columns(4)
    with left:
        status_index = LISTING_STATUSES.index(selected["listing_status"]) if selected["listing_status"] in LISTING_STATUSES else 0
        status = st.selectbox("상태", LISTING_STATUSES, index=status_index, key=f"quick_status_{selected['listing_id']}")
    with middle:
        photo_index = PHOTO_STATUSES.index(selected["photo_status"]) if selected["photo_status"] in PHOTO_STATUSES else 0
        photo_status = st.selectbox("사진 상태", PHOTO_STATUSES, index=photo_index, key=f"quick_photo_status_{selected['listing_id']}")
    with right:
        if photo_status == "촬영 완료":
            has_photo = "있음"
            st.text_input("사진 보유 여부", value=has_photo, disabled=True, key=f"quick_has_photo_completed_{selected['listing_id']}", help="사진 촬영 완료를 선택하면 자동으로 ‘있음’으로 저장됩니다.")
        else:
            has_photo_index = PHOTO_AVAILABILITY.index(selected["has_listing_photos"]) if selected["has_listing_photos"] in PHOTO_AVAILABILITY else 2
            has_photo = st.selectbox("사진 보유 여부", PHOTO_AVAILABILITY, index=has_photo_index, key=f"quick_has_photo_{selected['listing_id']}")
    with date_column:
        current_date = date.fromisoformat(selected["next_check_date"]) if selected["next_check_date"] else None
        next_check = st.date_input("재확인 예정일", value=current_date, key=f"quick_next_check_{selected['listing_id']}")
    st.markdown("##### 현장 준비 상태")
    cleaning_column, wallpaper_column, repair_column = st.columns(3)
    with cleaning_column:
        cleaning_index = SITE_PREPARATION_STATUSES.index(selected["cleaning_status"]) if selected["cleaning_status"] in SITE_PREPARATION_STATUSES else 0
        cleaning_status = st.selectbox("청소 상태", SITE_PREPARATION_STATUSES, index=cleaning_index, key=f"quick_cleaning_{selected['listing_id']}")
    with wallpaper_column:
        wallpaper_index = SITE_PREPARATION_STATUSES.index(selected["wallpaper_status"]) if selected["wallpaper_status"] in SITE_PREPARATION_STATUSES else 0
        wallpaper_status = st.selectbox("도배 상태", SITE_PREPARATION_STATUSES, index=wallpaper_index, key=f"quick_wallpaper_{selected['listing_id']}")
    with repair_column:
        repair_index = SITE_PREPARATION_STATUSES.index(selected["repair_status"]) if selected["repair_status"] in SITE_PREPARATION_STATUSES else 0
        repair_status = st.selectbox("수리 상태", SITE_PREPARATION_STATUSES, index=repair_index, key=f"quick_repair_{selected['listing_id']}")
    if st.button("빠른 수정 저장", type="primary", key=f"quick_save_{selected['listing_id']}"):
        try:
            saved_has_photo = "있음" if photo_status == "촬영 완료" else has_photo
            update_listing_quick_fields(selected["listing_id"], status, photo_status, saved_has_photo, _date_text(next_check), cleaning_status, wallpaper_status, repair_status)
        except Exception as error:
            st.error(f"수정하지 못했습니다. ({error})")
            return
        st.session_state["dashboard_quick_save_result"] = (
            f"빠른 수정 저장 완료: 상태 {status} · 사진 {photo_status} · 사진 보유 {saved_has_photo} · "
            f"청소 {cleaning_status} · 도배 {wallpaper_status} · 수리 {repair_status} · "
            f"재확인일 {_date_text(next_check) or '미지정'}"
        )
        st.rerun()

    with st.expander("이 매물 완전 삭제"):
        st.error("이 매물은 복구할 수 없게 삭제됩니다. 연결된 계약·상담 기록도 함께 삭제됩니다.")
        confirmed = st.checkbox("이 매물과 연결 기록을 완전히 삭제하는 것을 확인했습니다.", key=f"dashboard_delete_listing_confirm_{selected['listing_id']}")
        if st.button("매물 완전 삭제", type="secondary", disabled=not confirmed, key=f"dashboard_delete_listing_{selected['listing_id']}"):
            try:
                deleted = delete_listing(selected["listing_id"])
            except Exception as error:
                st.error(f"매물을 삭제하지 못했습니다. ({error})")
                return
            st.success(f"매물을 삭제했습니다. 연결된 계약 {deleted['contracts']}건, 상담 {deleted['consultations']}건도 함께 삭제했습니다.")
            st.rerun()


def _render_closed_listing_detail(selected: dict) -> None:
    st.markdown("#### 선택한 종료 매물")
    st.info("종료된 매물은 매물 현황 리스트에서 조회만 할 수 있습니다. 종료 처리는 매물 등록·수정 탭에서 합니다.")
    st.caption(
        f"{selected['building_name']} · {selected['lot_address']} · {selected['unit_number']}호 · "
        f"접수일 {selected['received_date']} · 종료일 {selected['closed_date'] or '-'} · 종료 사유 {selected['close_reason'] or '-'}"
    )


def _render_excel_export(
    all_listings: list[dict],
    query_listings: list[dict],
    received_start: date | None,
    received_end: date | None,
) -> None:
    """전체 또는 현재 조회 결과를 사용자가 확인한 뒤 내려받게 한다."""
    st.markdown("#### 엑셀 내보내기")
    scope = st.radio(
        "내보낼 범위",
        ["현재 조회 결과", "현재 매물 전체"],
        horizontal=True,
        key="dashboard_export_scope",
    )
    selected = query_listings if scope == "현재 조회 결과" else all_listings
    if scope == "현재 조회 결과":
        start_label = received_start.isoformat() if received_start else "처음"
        end_label = received_end.isoformat() if received_end else "전체"
        period_note = f"접수일: {start_label} ~ {end_label}"
    else:
        period_note = "접수일: 전체"
    st.caption(f"{scope} · {period_note} · 총 {len(selected)}건")
    st.warning("내부 업무용 파일입니다. 임대인·세입자 개인 연락처와 상담관리 고객 이름·연락처는 포함하지 않습니다.")
    if not selected:
        st.info("내보낼 현재 매물이 없습니다.")
        return
    try:
        rows = get_current_listing_export_rows([item["listing_id"] for item in selected])
        file_data = create_current_listing_excel(rows)
    except Exception as error:
        st.error(f"엑셀 파일을 만들지 못했습니다. ({error})")
        return
    filename = make_export_filename(
        _date_text(received_start) if scope == "현재 조회 결과" else None,
        _date_text(received_end) if scope == "현재 조회 결과" else None,
    )
    st.download_button(
        "엑셀 파일 내려받기",
        data=file_data,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        key="dashboard_excel_download",
    )


def render_dashboard(go_to_listing) -> None:
    st.subheader("매물 현황 리스트")
    st.markdown("<p class='section-note'>현재 매물을 조회·필터하고, 확인이 필요한 매물을 찾거나 엑셀로 내보내는 화면입니다.</p>", unsafe_allow_html=True)
    if message := st.session_state.pop("dashboard_quick_save_result", None):
        st.success(message)
    try:
        all_listings = get_current_listings()
    except FileNotFoundError as error:
        st.error(str(error))
        return

    metrics = _summary(all_listings)
    metric_columns = st.columns(5)
    for column, (label, value) in zip(metric_columns, metrics.items()):
        column.metric(label, value)

    st.caption(f"데이터 파일: {DATABASE_PATH} · 현재 매물 {len(all_listings)}건")
    if not all_listings:
        st.markdown("<div class='empty-panel'><h2>현재 운영 중인 매물이 없습니다</h2><p>새 매물을 등록하거나, 아래 필터에서 종료된 매물을 조회해 주세요.</p></div>", unsafe_allow_html=True)
        _, button_column, _ = st.columns([3, 2, 3])
        with button_column:
            st.button("현재 운영할 첫 매물 등록", type="primary", use_container_width=True, on_click=go_to_listing)

    st.markdown("#### 검색·필터")
    with st.form("dashboard_search_form"):
        query_column, date_start_column, date_end_column = st.columns([2, 1, 1])
        with query_column:
            query = st.text_input("건물명·지번·호수 검색", key="dashboard_query", placeholder="예: 대성빌, 북수리 1026, 302")
        with date_start_column:
            received_start = st.date_input("접수일 시작", value=None, key="dashboard_received_start")
        with date_end_column:
            received_end = st.date_input("접수일 종료", value=None, key="dashboard_received_end")
        filter_columns = st.columns(5)
        with filter_columns[0]:
            listing_scope = st.selectbox("표시할 매물", ["현재 매물만", "종료된 매물만", "전체"], key="dashboard_listing_scope")
        with filter_columns[1]:
            statuses = st.multiselect("매물 상태", LISTING_STATUSES, key="dashboard_statuses")
        with filter_columns[2]:
            room_types = st.multiselect("룸 형태", ROOM_TYPES, key="dashboard_room_types")
        with filter_columns[3]:
            photo_statuses = st.multiselect("사진 상태", PHOTO_STATUSES, key="dashboard_photo_statuses")
        with filter_columns[4]:
            photo_availability = st.multiselect("사진 보유 여부", PHOTO_AVAILABILITY, key="dashboard_photo_availability")
        task_filter = st.selectbox("확인 업무", ["전체"] + TASK_FILTERS, key="dashboard_task")
        searched = st.form_submit_button("조회", type="primary")
    if st.button("조회·필터 초기화", on_click=_clear_filters):
        st.rerun()

    if searched:
        st.session_state["dashboard_has_searched"] = True
    if not st.session_state.get("dashboard_has_searched", False):
        st.info("검색 조건을 입력한 뒤 `조회`를 누르면 현재 매물 목록이 표시됩니다.")
        return

    if received_start and received_end and received_end < received_start:
        st.error("접수일 종료는 시작일보다 빠를 수 없습니다.")
        return
    if received_start or received_end:
        start_label = received_start.isoformat() if received_start else "처음"
        end_label = received_end.isoformat() if received_end else "오늘까지"
        st.caption(f"적용 중인 접수일 기간: {start_label} ~ {end_label}")
    listings = get_current_listings(
        query=query,
        received_start=_date_text(received_start),
        received_end=_date_text(received_end),
        statuses=statuses,
        room_types=room_types,
        photo_statuses=photo_statuses,
        photo_availability=photo_availability,
        task_filter=None if task_filter == "전체" else task_filter,
        listing_scope=listing_scope,
    )
    st.markdown(f"#### {listing_scope} 조회 결과 · {len(listings)}건")
    if not listings:
        st.info("조건에 맞는 매물이 없습니다. 검색어나 필터를 조정해 주세요.")
        if listing_scope == "현재 매물만":
            _render_excel_export(all_listings, listings, received_start, received_end)
        return
    st.dataframe(_display_rows(listings), use_container_width=True, hide_index=True)
    if listing_scope == "현재 매물만":
        _render_excel_export(all_listings, listings, received_start, received_end)

    labels = [f"{item['building_name']} · {item['unit_number']}호 · {item['listing_status']} · {item['deposit_manwon'] or '확인 필요'}/{item['monthly_rent_manwon'] or '확인 필요'}" for item in listings]
    selected_label = st.selectbox("상세 확인 또는 빠른 수정할 매물", labels)
    selected = listings[labels.index(selected_label)]
    if selected["closed_date"] or selected["listing_status"] in ("계약 완료", "종료"):
        _render_closed_listing_detail(selected)
    else:
        _render_quick_edit(selected)
