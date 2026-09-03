"""매물 회차에 연결한 계약 기간과 상태 관리 화면."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from services.contract_service import BROKERAGE_METHODS, CONTRACT_ACTIVITY_DEFAULT_STATUSES, CONTRACT_ACTIVITY_STAGES, CONTRACT_STATUSES, CONTRACT_TYPES, change_contract_details, delete_contract, delete_contract_activity, save_contract, save_contract_activity, save_contract_activity_changes, validate_contract, validate_contract_activity
from services.export_service import create_contract_excel, make_management_export_filename
from services.contract_schedule_service import expiry_summary, get_contract_schedule
from services.record_number import consultation_number, contract_number, listing_number
from storage.contract_repository import get_contract_activities, get_contracts
from storage.consultation_repository import get_consultations
from storage.listing_repository import search_listing_rounds


def _date_text(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _listing_label(item: dict) -> str:
    unit = item["unit_number"] if item["unit_number"].endswith("호") else f"{item['unit_number']}호"
    return f"{listing_number(item['listing_id'])} · {item['building_name']} · {item['lot_address']} · {unit} · 접수일 {item['received_date']} · {item['listing_status']}"


def _consultation_label(item: dict) -> str:
    listing = _listing_label(item) if item.get("listing_id") else "일반 상담 · 연결 매물 없음"
    return f"{consultation_number(item['consultation_id'])} · {item['customer_name']} · {item['customer_phone']} · 상담일 {item['consulted_date']} · {item['consultation_source'] or '유입 미입력'} · {listing}"


def _consultation_for_id(consultation_id: int | None) -> dict | None:
    if consultation_id is None:
        return None
    matches = get_consultations(query=consultation_number(consultation_id))
    return next((item for item in matches if item["consultation_id"] == consultation_id), None)


def _render_source_consultation_summary(source: dict) -> None:
    """계약 전에 원본 상담의 업무 판단 정보를 다시 찾지 않도록 짧게 보여 준다."""
    st.markdown("###### 연결 상담 요약")
    st.dataframe([{
        "상담번호": consultation_number(source["consultation_id"]),
        "고객 연락처": source["customer_phone"] or "-",
        "유입 경로": source["consultation_source"] or "-",
        "희망 지역": source["desired_area"] or "-",
        "희망 방 유형": source["desired_room_types"] or "-",
        "예산(보증금/월세)": f"{source['desired_deposit_manwon'] if source['desired_deposit_manwon'] is not None else '-'} / {source['desired_monthly_rent_manwon'] if source['desired_monthly_rent_manwon'] is not None else '-'}",
        "입주 가능일": source["desired_available_from_date"] or "-",
        "최근 방문 결과": source["latest_visit_result"] or "-",
        "최근 상담일": source["last_contacted_date"] or source["consulted_date"],
    }], width="stretch", hide_index=True)
    if source.get("consultation_note"):
        st.caption(f"상담 메모: {source['consultation_note']}")


def _activity_stage_options(current: str | None = None) -> list[str]:
    """새 입력은 단순하게 보이고 과거에 저장한 단계는 수정 화면에서 보존한다."""
    return [current, *CONTRACT_ACTIVITY_STAGES] if current and current not in CONTRACT_ACTIVITY_STAGES else CONTRACT_ACTIVITY_STAGES


def _render_consultation_picker(key: str, selected_id: int | None = None) -> int | None:
    """계약 화면에서 상담 목록을 바로 보고 고르게 한다. 검색은 목록 축소용 보조 기능이다."""
    filter_query = st.text_input("상담 목록 빠른 필터 (선택)", key=f"{key}_filter", placeholder="고객명·연락처·상담번호·매물번호로 목록 좁히기")
    consultations = get_consultations(query=filter_query) if filter_query.strip() else get_consultations()
    if not consultations:
        st.info("조건에 맞는 상담 기록이 없습니다.")
        return None
    st.caption(f"상담 목록 {len(consultations)}건 · 목록에서 상담을 고르면 고객 정보가 계약자 정보에 자동 입력됩니다.")
    st.dataframe(
        [{
            "상담번호": consultation_number(item["consultation_id"]), "고객 연락처": item["customer_phone"],
            "상담일": item["consulted_date"], "유입 경로": item["consultation_source"] or "-",
            "상담 매물": listing_number(item["listing_id"]), "진행 단계": item["progress_stage"] or "기존 기록",
            "상담 상태": item["consultation_status"],
        } for item in consultations],
        width="stretch", hide_index=True,
    )
    options: list[int | None] = [None, *[item["consultation_id"] for item in consultations]]
    labels = {None: "상담 없이 계약 등록"}
    labels.update({item["consultation_id"]: f"{consultation_number(item['consultation_id'])} · {item['customer_phone']} · {item['consulted_date']} · {item['consultation_source'] or '유입 미입력'}" for item in consultations})
    if key in st.session_state:
        if st.session_state[key] not in options:
            st.session_state[key] = None
        return st.selectbox("연결할 상담 선택", options, format_func=labels.get, key=key)
    index = options.index(selected_id) if selected_id in options else 0
    return st.selectbox("연결할 상담 선택", options, index=index, format_func=labels.get, key=key)


def _contract_rows(contracts: list[dict]) -> list[dict]:
    today = date.today()
    rows = []
    for item in contracts:
        remaining = "-"
        if item["contract_end_date"] and item["contract_status"] not in ("해지", "만료"):
            days = (date.fromisoformat(item["contract_end_date"]) - today).days
            if 0 <= days <= 30:
                remaining = "D-day" if days == 0 else f"{days}일 남음"
        rows.append({
            "계약번호": contract_number(item["contract_id"]), "매물번호": listing_number(item["listing_id"]), "건물명": item["building_name"], "지번주소": item["lot_address"], "호실": item["unit_number"], "매물 접수일": item["received_date"],
            "계약 유형": item["contract_type"], "중개 방식": item["brokerage_method"] or "-", "진행 시작일": item["contract_progress_date"] or "-", "정식 계약일": item["formal_contract_date"] or "-",
            "임대차 시작일": item["contract_start_date"] or "-", "임대차 종료일": item["contract_end_date"] or "-", "만료 임박": remaining,
            "기간(개월)": item["term_months"] or "-", "계약금": item["contract_deposit_manwon"] or "-",
            "가계약금": item["provisional_deposit_manwon"] or "-",
            "계약금 미수령": (item["contract_deposit_manwon"] - (item["provisional_deposit_manwon"] or 0)) if item["contract_deposit_manwon"] is not None else "-",
            "추가 수령 예정일": item["remaining_deposit_due_date"] or "-", "잔금": item["balance_manwon"] or "-", "잔금 예정일": item["balance_due_date"] or "-", "계약 상태": item["contract_status"],
            "메모": item["contract_note"] or "-",
        })
    return rows


def _render_contract_activities(selected: dict) -> None:
    """현재 계약 단계를 이력으로 누적하고 계약 상태에 자동 반영한다."""
    contract_id = selected["contract_id"]
    st.markdown("##### 계약 단계 이력")
    st.caption("가계약·정식계약·잔금 완료·계약 완료·해지 중 실제 처리된 현재 계약 단계를 기록합니다. 미래 잔금 일정은 위 계약 정보의 잔금 예정일에 입력하세요. 선택한 단계는 이력으로 남고 계약 상태에 자동 반영됩니다.")
    activities = get_contract_activities(contract_id)
    if activities:
        st.dataframe(
            [{"상태 변경일": item["activity_date"], "현재 계약 단계": item["activity_stage"], "계약 상태": item["contract_status_after"], "내용": item["activity_note"] or "-"} for item in activities],
            width="stretch",
            hide_index=True,
        )
        with st.expander("계약 단계 이력 수정·삭제", expanded=False):
            activity_options = {item["activity_id"]: f"{item['activity_date']} · {item['activity_stage']} · {item['contract_status_after']} · {item['activity_note'] or '내용 미입력'}" for item in activities}
            selected_activity_id = st.selectbox("수정할 계약 단계 이력 선택", list(activity_options), format_func=activity_options.get, key=f"contract_activity_select_{contract_id}")
            edit_target_key = f"contract_activity_edit_target_{contract_id}"
            if st.button("수정 메뉴 열기", key=f"contract_activity_edit_open_{contract_id}"):
                st.session_state[edit_target_key] = selected_activity_id
                st.rerun()
            edit_activity_id = st.session_state.get(edit_target_key)
            if edit_activity_id in activity_options:
                activity = next(item for item in activities if item["activity_id"] == edit_activity_id)
                if st.button("수정 메뉴 닫기", key=f"contract_activity_edit_close_{contract_id}"):
                    st.session_state.pop(edit_target_key, None)
                    st.rerun()
                with st.form(f"contract_activity_edit_{edit_activity_id}"):
                    left, middle = st.columns(2)
                    with left:
                        edit_date = st.date_input("상태 변경일", value=date.fromisoformat(activity["activity_date"]))
                        edit_stage_options = _activity_stage_options(activity["activity_stage"])
                        edit_stage = st.selectbox("현재 계약 단계", edit_stage_options, index=edit_stage_options.index(activity["activity_stage"]))
                    with middle:
                        edit_status = CONTRACT_ACTIVITY_DEFAULT_STATUSES[edit_stage]
                        st.caption(f"자동 반영될 계약 상태: {edit_status}")
                    edit_note = st.text_area("이번 단계 내용", value=activity["activity_note"] or "")
                    activity_changed = st.form_submit_button("선택한 계약 단계 이력 수정 저장", type="primary")
                if activity_changed:
                    values, errors = validate_contract_activity({"activity_date": edit_date, "activity_stage": edit_stage, "activity_note": edit_note})
                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        try:
                            save_contract_activity_changes(edit_activity_id, contract_id, values)
                        except ValueError as error:
                            st.error(str(error))
                        else:
                            st.success("선택한 계약 단계 이력을 수정했습니다.")
                            st.rerun()
                with st.expander("선택한 계약 단계 이력 삭제"):
                    confirmed = st.checkbox("선택한 계약 단계 이력만 삭제하는 것을 확인했습니다.", key=f"delete_contract_activity_confirm_{edit_activity_id}")
                    if st.button("선택한 계약 단계 이력 삭제", type="secondary", disabled=not confirmed, key=f"delete_contract_activity_{edit_activity_id}"):
                        try:
                            delete_contract_activity(edit_activity_id, contract_id)
                        except ValueError as error:
                            st.error(str(error))
                        else:
                            st.session_state.pop(edit_target_key, None)
                            st.success("선택한 계약 단계 이력 1건을 삭제했습니다.")
                            st.rerun()
    else:
        st.caption("아직 계약 단계 이력이 없습니다.")

    with st.form(f"contract_activity_add_{contract_id}"):
        left, middle = st.columns(2)
        with left:
            activity_date = st.date_input("상태 변경일", value=date.today(), help="이 단계가 실제로 확정·처리된 날입니다. 정식 계약일·잔금 예정일 같은 미래 일정은 위 계약 정보에 기록하세요.")
            activity_stage = st.selectbox("현재 계약 단계", CONTRACT_ACTIVITY_STAGES)
        with middle:
            default_status = CONTRACT_ACTIVITY_DEFAULT_STATUSES[activity_stage]
            st.caption(f"자동 반영될 계약 상태: {default_status}")
        activity_note = st.text_area("이번 단계 내용", placeholder="예: 가계약금 수령 후 정식 계약일 협의")
        activity_submitted = st.form_submit_button("계약 단계 이력 저장", type="primary")
    if activity_submitted:
        values, errors = validate_contract_activity({"activity_date": activity_date, "activity_stage": activity_stage, "activity_note": activity_note})
        if errors:
            for error in errors:
                st.error(error)
        else:
            try:
                save_contract_activity(contract_id, values)
            except ValueError as error:
                st.error(str(error))
            else:
                st.success("기존 계약 정보는 유지하고 계약 단계 이력을 추가했습니다.")
                st.rerun()


def _render_status_change(selected: dict) -> None:
    st.markdown("#### 저장된 계약 정보 수정")
    st.caption(f"수정 대상: {contract_number(selected['contract_id'])} · {_listing_label(selected)}")
    if st.button("수정 닫기", key=f"contract_edit_close_{selected['contract_id']}"):
        st.session_state.pop("contract_edit_target_id", None)
        st.session_state.pop(f"contract_edit_source_{selected['contract_id']}", None)
        st.rerun()
    index = CONTRACT_STATUSES.index(selected["contract_status"]) if selected["contract_status"] in CONTRACT_STATUSES else 0
    left, middle, right = st.columns(3)
    with left:
        type_index = CONTRACT_TYPES.index(selected["contract_type"]) if selected["contract_type"] in CONTRACT_TYPES else 0
        contract_type = st.selectbox("계약 유형", CONTRACT_TYPES, index=type_index, key=f"contract_type_{selected['contract_id']}")
        brokerage_index = BROKERAGE_METHODS.index(selected["brokerage_method"]) if selected.get("brokerage_method") in BROKERAGE_METHODS else 2
        brokerage_method = st.selectbox("중개 방식", BROKERAGE_METHODS, index=brokerage_index, key=f"brokerage_method_{selected['contract_id']}")
        status = st.selectbox("계약 상태", CONTRACT_STATUSES, index=index, key=f"contract_status_{selected['contract_id']}")
    with middle:
        progress_date = st.date_input("계약 진행 시작일", value=date.fromisoformat(selected["contract_progress_date"]) if selected["contract_progress_date"] else None, key=f"contract_progress_{selected['contract_id']}")
        formal_date = st.date_input("정식 계약일", value=date.fromisoformat(selected["formal_contract_date"]) if selected["formal_contract_date"] else None, key=f"contract_formal_{selected['contract_id']}")
    with right:
        start_date = st.date_input("임대차 시작일", value=date.fromisoformat(selected["contract_start_date"]) if selected["contract_start_date"] else None, key=f"contract_start_{selected['contract_id']}")
        end_date = st.date_input("임대차 종료일", value=date.fromisoformat(selected["contract_end_date"]) if selected["contract_end_date"] else None, key=f"contract_end_{selected['contract_id']}")
    source_key = f"contract_edit_source_{selected['contract_id']}"
    if source_key not in st.session_state:
        st.session_state[source_key] = selected.get("source_consultation_id")
    selected_source_id = _render_consultation_picker(source_key, st.session_state[source_key])
    source_consultation = _consultation_for_id(selected_source_id)
    st.markdown("##### 연결 상담")
    if source_consultation:
        st.info(f"연결 상담: {_consultation_label(source_consultation)}")
    else:
        st.caption("상담 연결을 하지 않으려면 목록에서 `상담 없이 계약 등록`을 선택하세요.")

    detail_left, detail_middle, _ = st.columns(3)
    with detail_left:
        contractor_name = st.text_input("계약자 이름 (내부정보)", value=selected.get("contractor_name") or (source_consultation["customer_name"] if source_consultation else ""), key=f"contract_name_{selected['contract_id']}")
        contact = st.text_input("계약자 연락처 (내부정보)", value=selected["contractor_contact"] or (source_consultation["customer_phone"] if source_consultation else ""), key=f"contract_contact_{selected['contract_id']}")
    with detail_middle:
        term_months = st.number_input("임대차 기간 (개월)", min_value=1, step=1, value=selected["term_months"], key=f"contract_term_{selected['contract_id']}")
    payment_left, payment_middle, payment_right = st.columns(3)
    with payment_left:
        deposit = st.number_input("계약금 전체 (만원)", min_value=0, step=10, value=selected["contract_deposit_manwon"], key=f"contract_deposit_{selected['contract_id']}")
    with payment_middle:
        provisional_deposit = st.number_input("가계약금 수령액 (만원)", min_value=0, step=10, value=selected["provisional_deposit_manwon"], key=f"contract_provisional_deposit_{selected['contract_id']}")
    with payment_right:
        remaining_deposit_due = st.date_input("계약금 추가 수령 예정일", value=date.fromisoformat(selected["remaining_deposit_due_date"]) if selected["remaining_deposit_due_date"] else None, key=f"contract_remaining_deposit_due_{selected['contract_id']}")
    if deposit is not None:
        st.caption(f"계약금 미수령: {max(deposit - (provisional_deposit or 0), 0):,}만원")
    balance_left, balance_middle, _ = st.columns(3)
    with balance_left:
        balance = st.number_input("잔금 (만원)", min_value=0, step=10, value=selected["balance_manwon"], key=f"contract_balance_{selected['contract_id']}")
    with balance_middle:
        balance_due = st.date_input("잔금 예정일", value=date.fromisoformat(selected["balance_due_date"]) if selected["balance_due_date"] else None, key=f"contract_balance_due_{selected['contract_id']}")
    note = st.text_area("계약 메모", value=selected["contract_note"] or "", key=f"contract_note_{selected['contract_id']}")
    st.caption("연결 상담은 계약 진행·잔금 예정·계약 완료 상태로 저장하면 자동으로 계약 성사 처리됩니다.")
    if st.button("계약 정보 저장", key=f"contract_status_save_{selected['contract_id']}"):
        try:
            change_contract_details(selected["contract_id"], {
                "contract_type": contract_type, "brokerage_method": brokerage_method, "contract_status": status,
                "contract_progress_date": progress_date, "formal_contract_date": formal_date,
                "contract_start_date": start_date, "contract_end_date": end_date, "term_months": term_months,
                "contract_note": note, "contractor_name": contractor_name, "contractor_contact": contact,
                "source_consultation_id": st.session_state[source_key],
                "contract_deposit_manwon": deposit, "provisional_deposit_manwon": provisional_deposit,
                "remaining_deposit_due_date": remaining_deposit_due, "balance_manwon": balance,
                "balance_due_date": balance_due,
            })
        except ValueError as error:
            st.error(str(error))
        else:
            st.success("계약 기록은 유지한 채 계약 정보를 수정했습니다.")
            st.rerun()

    _render_contract_activities(selected)

    with st.expander("이 계약 기록 완전 삭제"):
        st.error("선택한 계약 기록만 삭제됩니다. 매물과 상담 기록은 남습니다.")
        confirmed = st.checkbox("이 계약 기록을 완전히 삭제하는 것을 확인했습니다.", key=f"delete_contract_confirm_{selected['contract_id']}")
        if st.button("계약 기록 삭제", type="secondary", disabled=not confirmed, key=f"delete_contract_{selected['contract_id']}"):
            try:
                delete_contract(selected["contract_id"])
            except ValueError as error:
                st.error(str(error))
                return
            st.success("계약 기록을 삭제했습니다.")
            st.rerun()


def _render_contract_lookup() -> None:
    st.markdown("#### 계약 조회·수정")
    st.caption("저장된 계약을 찾고, 계약 상태·계약자 연락처·계약금·잔금만 수정합니다. 이 화면에서는 새 계약을 만들지 않습니다.")
    with st.form("contract_search_form"):
        query_column, status_column, start_column, end_column = st.columns([2, 1, 1, 1])
        with query_column:
            query = st.text_input("계약번호·매물번호·건물명·지번·호수 검색", key="contract_query", placeholder="예: C-000042 또는 M-000150")
        with status_column:
            statuses = st.multiselect("계약 상태", CONTRACT_STATUSES, key="contract_status_filter")
        with start_column:
            end_start = st.date_input("임대차 종료일 시작", value=None, key="contract_end_start")
        with end_column:
            end_end = st.date_input("임대차 종료일 종료", value=None, key="contract_end_end")
        expiring_soon = st.checkbox("계약 만료 30일 전만 보기", key="contract_expiring_soon")
        searched = st.form_submit_button("계약 조회", type="primary")
    if searched:
        st.session_state["contract_has_searched"] = True
        st.session_state.pop("contract_edit_target_id", None)
    if end_start and end_end and end_end < end_start:
        st.error("임대차 종료일 종료는 시작일보다 빠를 수 없습니다.")
        return
    contracts = get_contracts(
        query=query, statuses=statuses, end_start=_date_text(end_start), end_end=_date_text(end_end),
        expiring_within_days=30 if expiring_soon else None,
    )
    if st.session_state.get("contract_has_searched"):
        if expiring_soon:
            deadline = date.today() + timedelta(days=30)
            st.caption(f"계약 만료 30일 전 필터 적용: {date.today().isoformat()} ~ {deadline.isoformat()} · 해지·만료 계약 제외")
        st.caption(f"조회된 계약 {len(contracts)}건")
        if contracts:
            st.dataframe(_contract_rows(contracts), width="stretch", hide_index=True)
            st.markdown("##### 엑셀 내보내기")
            st.caption(f"현재 조회 결과 {len(contracts)}건을 내보냅니다.")
            st.warning("내부 업무용 파일입니다. 계약자 연락처는 포함하지 않으며, 외부에 공유하지 마세요.")
            try:
                export_data = create_contract_excel(contracts)
            except Exception as error:
                st.error(f"엑셀 파일을 만들지 못했습니다. ({error})")
            else:
                st.download_button(
                    "계약 조회 결과 엑셀 내려받기",
                    data=export_data,
                    file_name=make_management_export_filename("계약목록"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    key="contract_excel_download",
                )
            st.markdown("##### 계약 상세·수정")
            labels = [f"{contract_number(item['contract_id'])} · {_listing_label(item)} · 진행 {item['contract_progress_date'] or '-'} · {item['contract_type']}" for item in contracts]
            selected_label = st.selectbox("수정할 계약 선택", labels, key="contract_edit_select")
            selected = contracts[labels.index(selected_label)]
            if st.button("선택한 계약 수정 열기", key="contract_edit_open", type="secondary"):
                st.session_state["contract_edit_target_id"] = selected["contract_id"]
                st.rerun()
        else:
            st.info("조건에 맞는 계약 기록이 없습니다.")
    target_id = st.session_state.get("contract_edit_target_id")
    if target_id is not None:
        selected = next((item for item in contracts if item["contract_id"] == target_id), None)
        if selected is None:
            st.session_state.pop("contract_edit_target_id", None)
            st.warning("바로 열려던 계약 기록을 현재 조회 결과에서 찾을 수 없습니다.")
        else:
            _render_status_change(selected)


def _render_contract_schedule() -> None:
    st.markdown("#### 계약 일정")
    st.caption("정식 계약·추가 계약금 수령·잔금·임대차 종료의 기준일 이전 미처리 일정과 앞으로 30일 이내 일정을 표시합니다. 계약 진행 시작일은 이력으로만 관리합니다. 연락처·금액·메모는 이 표에 표시하지 않습니다.")
    reference_date = st.date_input("일정 기준일", value=date.today(), key="contract_schedule_reference_date")
    try:
        summary = expiry_summary(reference_date)
        schedules = get_contract_schedule(reference_date, days=30)
    except ValueError as error:
        st.error(str(error))
        return
    metrics = st.columns(3)
    for column, (label, value) in zip(metrics, summary.items()):
        column.metric(f"임대차 만료 {label}", value)
    st.caption("만료 요약은 해지·만료 계약과 종료일이 없는 계약을 제외한 누적 수치입니다.")
    if not schedules:
        st.info("기준일 이전 미처리 일정 또는 앞으로 30일 이내 일정이 없습니다.")
        return
    st.dataframe([
        {key: value for key, value in item.items() if key not in {"due_date", "remaining_days", "event_type", "is_expiry", "contract_id", "listing_id"}}
        for item in schedules
    ], width="stretch", hide_index=True)


def _render_contract_registration() -> None:
    st.markdown("#### 계약 등록")
    st.caption("계약할 당시의 매물 기록을 먼저 선택한 뒤, 정식 계약일·잔금 예정일·임대차 기간처럼 앞으로의 일정을 먼저 기록합니다. 실제 상태 변경은 저장 뒤 계약 단계 이력에서 남깁니다.")
    listing_query = st.text_input("연결할 매물 회차 찾기", key="contract_listing_query", placeholder="M-000150 또는 건물명·지번·호수 2글자 이상")
    selected = st.session_state.get("contract_selected_listing")
    if selected is None:
        if len(listing_query.strip()) < 2:
            st.info("계약할 당시의 매물 기록을 찾기 위해 2글자 이상 입력해 주세요.")
        else:
            listing_results = search_listing_rounds(listing_query)
            if not listing_results:
                st.info("조건에 맞는 매물 기록이 없습니다.")
            else:
                st.caption("계약을 연결할 매물 기록을 선택해 주세요. 같은 호실도 접수일이 다르면 다른 기록입니다.")
                for item in listing_results:
                    if st.button(_listing_label(item), key=f"contract_listing_{item['listing_id']}", width="stretch"):
                        st.session_state["contract_selected_listing"] = item
                        st.rerun()
    else:
        st.success(f"선택한 매물 기록: {_listing_label(selected)}")
        if st.button("다른 매물 기록 선택", key="clear_contract_listing"):
            st.session_state.pop("contract_selected_listing", None)
            st.rerun()
        pending_source_id = st.session_state.pop("contract_selected_consultation_id", None)
        source_key = "contract_selected_consultation_id_for_create"
        if pending_source_id is not None:
            st.session_state[source_key] = pending_source_id
        st.markdown("##### 계약으로 이어진 상담 (선택)")
        source_id = _render_consultation_picker(source_key, st.session_state.get(source_key))
        source = _consultation_for_id(source_id)
        if source:
            st.info(f"선택한 상담: {_consultation_label(source)}")
            _render_source_consultation_summary(source)
        else:
            st.caption("상담 없이 바로 계약한 경우에는 상담을 선택하지 않고 계속 입력하세요.")
        with st.form(f"contract_create_{selected['listing_id']}_{source['consultation_id'] if source else 'none'}"):
            left, middle, right = st.columns(3)
            with left:
                contract_type = st.selectbox("계약 유형 *", CONTRACT_TYPES)
                brokerage_method = st.selectbox("중개 방식 *", BROKERAGE_METHODS)
                contract_status = st.selectbox("계약 상태 *", CONTRACT_STATUSES)
            with middle:
                contract_progress = st.date_input("계약 진행 시작일", value=date.today())
                formal_contract = st.date_input("정식 계약일", value=None)
            with right:
                contract_start = st.date_input("임대차 시작일", value=None)
                contract_end = st.date_input("임대차 종료일", value=None)
            contract_note = st.text_area("계약 메모", placeholder="예: 단기 연장 여부 확인 필요")
            detail_left, detail_middle, _ = st.columns(3)
            with detail_left:
                contractor_name = st.text_input("계약자 이름 (내부정보)", value=source["customer_name"] if source else "")
                contractor_contact = st.text_input("계약자 연락처 (내부정보)", value=source["customer_phone"] if source else "", placeholder="예: 010-1234-5678")
            with detail_middle:
                term_months = st.number_input("임대차 기간 (개월)", min_value=1, step=1, value=None)
            payment_left, payment_middle, payment_right = st.columns(3)
            with payment_left:
                contract_deposit = st.number_input("계약금 전체 (만원)", min_value=0, step=10, value=None)
            with payment_middle:
                provisional_deposit = st.number_input("가계약금 수령액 (만원)", min_value=0, step=10, value=None)
            with payment_right:
                remaining_deposit_due = st.date_input("계약금 추가 수령 예정일", value=None)
            if contract_deposit is not None:
                st.caption(f"계약금 미수령: {max(contract_deposit - (provisional_deposit or 0), 0):,}만원")
            balance_left, balance_middle, _ = st.columns(3)
            with balance_left:
                balance = st.number_input("잔금 (만원)", min_value=0, step=10, value=None)
            with balance_middle:
                balance_due = st.date_input("잔금 예정일", value=None)
            submitted = st.form_submit_button("새 계약 등록", type="primary")
        if submitted:
            contract, errors = validate_contract({
                "contract_type": contract_type, "brokerage_method": brokerage_method, "contract_status": contract_status, "contract_progress_date": contract_progress,
                "formal_contract_date": formal_contract,
                "contract_start_date": contract_start, "contract_end_date": contract_end,
                "term_months": term_months, "contract_note": contract_note,
                "source_consultation_id": source["consultation_id"] if source else None,
                "contractor_name": contractor_name,
                "contractor_contact": contractor_contact, "contract_deposit_manwon": contract_deposit,
                "provisional_deposit_manwon": provisional_deposit, "remaining_deposit_due_date": remaining_deposit_due,
                "balance_manwon": balance,
                "balance_due_date": balance_due,
            })
            if errors:
                for error in errors:
                    st.error(error)
            else:
                try:
                    contract_id = save_contract(selected["listing_id"], contract)
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.success(f"새 계약 기록을 추가했습니다. 계약번호는 {contract_number(contract_id)}, 연결 매물번호는 {listing_number(selected['listing_id'])}입니다. 기존 계약과 매물 기록은 변경되지 않았습니다.")
                    st.session_state.pop("contract_selected_listing", None)
                    st.session_state.pop(source_key, None)
                    st.rerun()


def render_contract_management() -> None:
    st.subheader("계약관리")
    st.markdown("<p class='section-note'>계약은 실제 계약한 매물 기록에 연결하고, 계약으로 이어진 상담은 별도로 연결합니다. 계약자 정보와 계약금·잔금은 내부정보로 관리하며, 결제·계약서 파일은 관리하지 않습니다.</p>", unsafe_allow_html=True)
    mode = st.radio(
        "계약관리 메뉴",
        ["계약 등록", "계약 조회·수정", "계약 일정"],
        horizontal=True,
        key="contract_management_mode",
    )
    if mode == "계약 등록":
        _render_contract_registration()
    elif mode == "계약 조회·수정":
        _render_contract_lookup()
    else:
        _render_contract_schedule()
