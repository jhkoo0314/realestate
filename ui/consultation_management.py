"""매물 회차별 상담 CRM 화면."""

from __future__ import annotations

from datetime import date

import streamlit as st

from services.contact_format import format_phone_number
from services.consultation_service import CLOSED_REASONS, CONSULTATION_CATEGORIES, CONSULTATION_SOURCES, CONSULTATION_STATUSES, CONSULTATION_TYPES, PROGRESS_STAGES, VISIT_RESULTS, close_legacy_consultation, delete_consultation, delete_consultation_activity, link_consultation_to_listing, save_consultation, save_consultation_activity, save_consultation_activity_changes, save_consultation_changes, validate_consultation, validate_consultation_activity
from services.export_service import create_consultation_excel, make_management_export_filename
from services.record_number import consultation_number, listing_number
from storage.consultation_repository import get_consultation_activities, get_consultation_delete_counts, get_consultation_detail, get_consultations
from storage.listing_repository import search_listing_rounds


def _listing_label(item: dict) -> str:
    if not item.get("listing_id"):
        return "일반 상담 · 연결 매물 없음"
    unit = item["unit_number"] if item["unit_number"].endswith("호") else f"{item['unit_number']}호"
    return f"{listing_number(item['listing_id'])} · {item['building_name']} · {item['lot_address']} · {unit} · 접수일 {item['received_date']} · {item['listing_status']}"


def _date_text(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _stage_options(current: str | None = None) -> list[str]:
    """새 입력에서는 계약 단계를 숨기되 과거 기록은 수정 화면에서 보존한다."""
    return [current, *PROGRESS_STAGES] if current and current not in PROGRESS_STAGES else PROGRESS_STAGES


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
        "상담번호": consultation_number(item["consultation_id"]), "연결 매물번호": listing_number(item["listing_id"]), "고객 연락처": item["customer_phone"] or "-", "상담 구분": item["consultation_category"], "건물명": item["building_name"] or "-", "지번주소": item["lot_address"] or "-", "호실": item["unit_number"] or "-",
        "매물 접수일": item["received_date"], "상담일": item["consulted_date"], "상담 종류": item["consultation_type"], "유입 경로": item["consultation_source"] or "-",
        "진행 단계": item["progress_stage"] or "기존 기록", "최근 상담일": item["last_contacted_date"] or item["consulted_date"], "종료 사유": item["closed_reason"] or "-", "상담 상태": item["consultation_status"], "다음 연락일": item["next_contact_date"] or "-",
        "해야 할 일": _task_text(item, today),
        "희망 조건": " · ".join(filter(None, [item["desired_area"], item["desired_room_type"], f"{item['desired_deposit_manwon']}/{item['desired_monthly_rent_manwon']}" if item["desired_deposit_manwon"] is not None or item["desired_monthly_rent_manwon"] is not None else None, f"입주 가능일 {item['desired_available_from_date']}" if item.get("desired_available_from_date") else None])) or "-", "상담 내용": item["consultation_note"],
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
                progress_stage = st.selectbox("진행 단계", PROGRESS_STAGES)
                closed_reason = st.selectbox("종료 사유", ["선택 안 함", *CLOSED_REASONS]) if progress_stage == "종료" else "선택 안 함"
                consultation_status = "종료" if progress_stage == "종료" else "진행 중"
                next_contact = st.date_input("다음 연락일", value=None, disabled=progress_stage == "종료")
                consultation_source = st.selectbox("유입 경로", CONSULTATION_SOURCES)
            st.markdown("##### 희망 조건 (선택)")
            desired_left, desired_middle, desired_right, desired_last, desired_date_column = st.columns(5)
            with desired_left: desired_area = st.text_input("희망 지역", placeholder="예: 배방읍")
            with desired_middle: desired_room_type = st.text_input("희망 방 형태", placeholder="예: 투룸")
            with desired_right: desired_deposit = st.number_input("희망 보증금 (만원)", min_value=0, step=100, value=None)
            with desired_last: desired_monthly_rent = st.number_input("희망 월세 (만원)", min_value=0, step=5, value=None)
            with desired_date_column: desired_available_from_date = st.date_input("희망 입주 가능일", value=None)
            required_features_note = st.text_input("필수 조건", placeholder="예: 엘리베이터, 주차, 반려동물")
            note = st.text_area("상담 내용", placeholder="예: 원하는 지역·입주 시기·특이사항")
            submitted = st.form_submit_button("일반 상담 등록", type="primary")
        if submitted:
            customer_phone = format_phone_number(customer_phone)
            consultation, errors = validate_consultation({
                "consultation_category": category, "customer_phone": customer_phone,
                "consulted_date": consulted_date, "consultation_type": consultation_type, "consultation_source": consultation_source, "consultation_note": note,
                "desired_area": desired_area, "desired_room_type": desired_room_type,
                "desired_deposit_manwon": desired_deposit, "desired_monthly_rent_manwon": desired_monthly_rent,
                "desired_available_from_date": desired_available_from_date,
                "next_contact_date": next_contact, "consultation_status": consultation_status,
                "progress_stage": progress_stage, "closed_reason": None if closed_reason == "선택 안 함" else closed_reason, "desired_room_types": desired_room_type, "required_features_note": required_features_note,
            })
            if errors:
                for error in errors: st.error(error)
                return
            try:
                consultation_id = save_consultation(None, consultation)
            except ValueError as error:
                st.error(str(error))
            else:
                st.session_state["consultation_registration_notice"] = f"일반 상담 등록을 완료했습니다. 상담번호는 {consultation_number(consultation_id)}입니다. 상담 조회·수정에서 등록 내용과 해야 할 일을 확인할 수 있습니다."
                st.rerun()
        return

    st.caption("상담할 당시의 매물 기록을 선택한 뒤 새 상담을 추가합니다.")
    query = st.text_input("연결할 매물 회차 찾기", key="consultation_listing_query", placeholder="M-000150 또는 건물명·지번·호수 2글자 이상")
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
            progress_stage = st.selectbox("진행 단계", PROGRESS_STAGES)
            closed_reason = st.selectbox("종료 사유", ["선택 안 함", *CLOSED_REASONS]) if progress_stage == "종료" else "선택 안 함"
            consultation_status = "종료" if progress_stage == "종료" else "진행 중"
            next_contact = st.date_input("다음 연락일", value=None, disabled=progress_stage == "종료")
            consultation_source = st.selectbox("유입 경로", CONSULTATION_SOURCES)
        st.markdown("##### 희망 조건 (선택)")
        desired_left, desired_middle, desired_right, desired_last, desired_date_column = st.columns(5)
        with desired_left: desired_area = st.text_input("희망 지역", placeholder="예: 배방읍")
        with desired_middle: desired_room_type = st.text_input("희망 방 형태", placeholder="예: 투룸")
        with desired_right: desired_deposit = st.number_input("희망 보증금 (만원)", min_value=0, step=100, value=None)
        with desired_last: desired_monthly_rent = st.number_input("희망 월세 (만원)", min_value=0, step=5, value=None)
        with desired_date_column: desired_available_from_date = st.date_input("희망 입주 가능일", value=None)
        required_features_note = st.text_input("필수 조건", placeholder="예: 엘리베이터, 주차, 반려동물")
        note = st.text_area("상담 내용", placeholder="예: 방문 일정 협의, 가격 안내")
        submitted = st.form_submit_button("새 상담 등록", type="primary")
    if submitted:
        customer_phone = format_phone_number(customer_phone)
        consultation, errors = validate_consultation({
            "consultation_category": category, "customer_phone": customer_phone, "consulted_date": consulted_date,
            "consultation_type": consultation_type, "consultation_source": consultation_source, "consultation_note": note,
            "desired_area": desired_area, "desired_room_type": desired_room_type,
            "desired_deposit_manwon": desired_deposit, "desired_monthly_rent_manwon": desired_monthly_rent,
            "desired_available_from_date": desired_available_from_date,
            "next_contact_date": next_contact, "consultation_status": consultation_status,
            "progress_stage": progress_stage, "closed_reason": None if closed_reason == "선택 안 함" else closed_reason, "desired_room_types": desired_room_type, "required_features_note": required_features_note,
        })
        if errors:
            for error in errors: st.error(error)
            return
        try:
            consultation_id = save_consultation(selected["listing_id"], consultation)
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["consultation_registration_notice"] = f"매물 상담 등록을 완료했습니다. 상담번호는 {consultation_number(consultation_id)}, 연결 매물번호는 {listing_number(selected['listing_id'])}입니다. 기존 상담과 매물 기록은 변경되지 않았습니다."
            st.session_state.pop("consultation_selected_listing", None)
            st.rerun()


def _render_lookup() -> None:
    st.markdown("#### 상담 조회·수정")
    with st.form("consultation_search_form"):
        query_column, category_column, status_column, stage_column = st.columns([2, 1, 1, 1])
        with query_column:
            query = st.text_input("상담번호·매물번호·건물명·지번·호수·희망 지역 검색", key="consultation_query", placeholder="예: S-000078 또는 M-000150")
        with category_column:
            categories = st.multiselect("상담 구분", CONSULTATION_CATEGORIES, key="consultation_category_filter")
        with status_column:
            statuses = st.multiselect("상담 상태", CONSULTATION_STATUSES, key="consultation_status_filter")
        with stage_column:
            progress_stages = st.multiselect("진행 단계", PROGRESS_STAGES, key="consultation_stage_filter")
        start_column, end_column, due_column, reason_column = st.columns([1, 1, 2, 1])
        with start_column:
            consulted_start = st.date_input("상담일 시작", value=None, key="consultation_start")
        with end_column:
            consulted_end = st.date_input("상담일 종료", value=None, key="consultation_end")
        with due_column:
            due_only = st.checkbox("다음 연락 필요만 보기", key="consultation_due_only")
        with reason_column:
            closed_reasons = st.multiselect("종료 사유", CLOSED_REASONS, key="consultation_closed_reason_filter")
        searched = st.form_submit_button("상담 조회", type="primary")
    if searched:
        st.session_state["consultation_has_searched"] = True
        st.session_state.pop("consultation_edit_target_id", None)
    if consulted_start and consulted_end and consulted_end < consulted_start:
        st.error("상담일 종료는 시작일보다 빠를 수 없습니다.")
        return
    items = get_consultations(
        query=query,
        categories=categories,
        statuses=statuses,
        progress_stages=progress_stages,
        closed_reasons=closed_reasons,
        consulted_start=_date_text(consulted_start),
        consulted_end=_date_text(consulted_end),
        due_only=due_only,
    )
    if not st.session_state.get("consultation_has_searched"):
        st.info("조건을 입력한 뒤 `상담 조회`를 누르면 상담 목록이 표시됩니다.")
        return
    if consulted_start or consulted_end:
        start_label = consulted_start.isoformat() if consulted_start else "처음"
        end_label = consulted_end.isoformat() if consulted_end else "오늘까지"
        st.caption(f"적용 중인 상담일 기간: {start_label} ~ {end_label}")
    st.caption(f"조회된 상담 {len(items)}건")
    if not items:
        if st.session_state.pop("consultation_edit_target_id", None) is not None:
            st.warning("바로 열려던 상담 기록을 찾을 수 없습니다.")
            return
        st.info("조건에 맞는 상담 기록이 없습니다.")
        return
    st.dataframe(_rows(items), width="stretch", hide_index=True)
    st.markdown("##### 엑셀 내보내기")
    st.caption(f"현재 조회 결과 {len(items)}건을 내보냅니다.")
    st.warning("고객 연락처가 포함되는 내부 업무용 파일입니다. 고객 이름과 상담 내용은 제외되지만, 외부 공유·개인 기기 보관은 하지 마세요.")
    try:
        export_data = create_consultation_excel(items)
    except Exception as error:
        st.error(f"엑셀 파일을 만들지 못했습니다. ({error})")
    else:
        st.download_button(
            "상담 조회 결과 엑셀 내려받기",
            data=export_data,
            file_name=make_management_export_filename("상담목록"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            key="consultation_excel_download",
        )
    st.markdown("##### 상담 상세·수정")
    labels = [f"{consultation_number(item['consultation_id'])} · {_listing_label(item)} · 상담일 {item['consulted_date']}" for item in items]
    chosen = st.selectbox("수정할 상담 선택", labels, key="consultation_edit_select")
    chosen_item = items[labels.index(chosen)]
    if st.button("선택한 상담 상세·수정 열기", key="consultation_edit_open", type="secondary"):
        st.session_state["consultation_edit_target_id"] = chosen_item["consultation_id"]
        st.rerun()
    target_id = st.session_state.get("consultation_edit_target_id")
    if target_id is None:
        return
    detail = get_consultation_detail(target_id)
    if detail is None:
        st.session_state.pop("consultation_edit_target_id", None)
        st.error("선택한 상담 기록을 찾을 수 없습니다.")
        return
    st.markdown("#### 상담 상세·수정")
    st.caption(f"수정 대상: {consultation_number(detail['consultation_id'])} · 연결 매물번호 {listing_number(detail['listing_id'])}")
    st.caption(f"진행 단계: {detail['progress_stage'] or '기존 기록'} · 최근 상담일: {detail['last_contacted_date'] or detail['consulted_date']} · 종료 사유: {detail['closed_reason'] or '-'}")
    if st.button("상세·수정 닫기", key=f"consultation_edit_close_{detail['consultation_id']}"):
        st.session_state.pop("consultation_edit_target_id", None)
        st.rerun()
    if st.button("이 상담으로 계약 등록", key=f"consultation_to_contract_{detail['consultation_id']}", type="primary"):
        st.session_state["selected_page"] = "계약관리"
        st.session_state["contract_management_mode"] = "계약 등록"
        st.session_state["contract_selected_consultation_id"] = detail["consultation_id"]
        st.rerun()
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
            clear_next_contact = st.checkbox("다음 연락일 지정 취소")
        with right:
            st.caption(f"상담 구분: {detail['consultation_category']}\n\n상담일: {detail['consulted_date']}\n\n상담 종류: {detail['consultation_type']}")
            source_index = CONSULTATION_SOURCES.index(detail["consultation_source"]) if detail["consultation_source"] in CONSULTATION_SOURCES else 0
            consultation_source = st.selectbox("유입 경로", CONSULTATION_SOURCES, index=source_index)
        note = st.text_area("상담 내용", value=detail["consultation_note"])
        st.markdown("##### 희망 조건 (선택)")
        desired_left, desired_middle, desired_right, desired_last, desired_date_column = st.columns(5)
        with desired_left: desired_area = st.text_input("희망 지역", value=detail["desired_area"] or "")
        with desired_middle: desired_room_type = st.text_input("희망 방 형태", value=detail["desired_room_type"] or "")
        with desired_right: desired_deposit = st.number_input("희망 보증금 (만원)", min_value=0, step=100, value=detail["desired_deposit_manwon"])
        with desired_last: desired_monthly_rent = st.number_input("희망 월세 (만원)", min_value=0, step=5, value=detail["desired_monthly_rent_manwon"])
        with desired_date_column: desired_available_from_date = st.date_input("희망 입주 가능일", value=date.fromisoformat(detail["desired_available_from_date"]) if detail["desired_available_from_date"] else None)
        submitted = st.form_submit_button("상담 정보 저장", type="primary")
    if submitted:
        try:
            customer_phone = format_phone_number(customer_phone)
            save_consultation_changes(detail["consultation_id"], {
                "consultation_category": detail["consultation_category"], "customer_name": detail["customer_name"], "customer_phone": customer_phone, "consultation_source": consultation_source, "consultation_note": note,
                "desired_area": desired_area, "desired_room_type": desired_room_type,
                "desired_deposit_manwon": desired_deposit, "desired_monthly_rent_manwon": desired_monthly_rent,
                "desired_available_from_date": desired_available_from_date,
                "next_contact_date": None if clear_next_contact else next_contact, "consultation_status": status,
            })
        except ValueError as error:
            st.error(str(error))
        else:
            st.success("상담 기록은 유지한 채 정보를 수정했습니다.")
            st.rerun()

    if detail.get("linked_contract_exists"):
        st.info("이 상담은 계약에 연결되어 있습니다. 계약 진행·완료와 단계 이력은 계약관리에서 처리합니다.")
    elif detail["progress_stage"]:
        st.markdown("##### 후속 상담 이력")
        activities = get_consultation_activities(detail["consultation_id"])
        if activities:
            st.dataframe([{"상담일": row["activity_date"], "방식": row["activity_type"], "결과 단계": row["stage_after_activity"], "방문 결과": row["visit_result"] or "-", "종료 사유": row["closed_reason"] or "-", "다음 연락일": row["next_contact_date"] or "-", "내용": row["activity_note"] or "-"} for row in activities], width="stretch", hide_index=True)
            with st.expander("후속 상담 이력 수정·삭제", expanded=False):
                st.caption("이력을 선택한 뒤 `수정 메뉴 열기`를 누르면 해당 이력만 수정하거나 삭제할 수 있습니다.")
                activity_options = {row["activity_id"]: f"{row['activity_date']} · {row['activity_type']} · {row['stage_after_activity']} · {row['activity_note'] or '내용 미입력'}" for row in activities}
                selected_activity_id = st.selectbox("수정할 후속 상담 이력 선택", list(activity_options), format_func=activity_options.get, key=f"consultation_activity_select_{detail['consultation_id']}")
                edit_target_key = f"consultation_activity_edit_target_{detail['consultation_id']}"
                if st.button("수정 메뉴 열기", key=f"consultation_activity_edit_open_{detail['consultation_id']}"):
                    st.session_state[edit_target_key] = selected_activity_id
                    st.rerun()
                edit_activity_id = st.session_state.get(edit_target_key)
                if edit_activity_id in activity_options:
                    selected_activity = next(row for row in activities if row["activity_id"] == edit_activity_id)
                    st.markdown("###### 선택한 후속 상담 이력 수정")
                    if st.button("수정 메뉴 닫기", key=f"consultation_activity_edit_close_{detail['consultation_id']}"):
                        st.session_state.pop(edit_target_key, None)
                        st.rerun()
                    with st.form(f"consultation_activity_edit_{edit_activity_id}"):
                        edit_left, edit_middle, edit_right = st.columns(3)
                        with edit_left:
                            edit_activity_date = st.date_input("후속 상담일", value=date.fromisoformat(selected_activity["activity_date"]), key=f"activity_date_{edit_activity_id}")
                            edit_activity_type = st.selectbox("상담 방식", CONSULTATION_TYPES, index=CONSULTATION_TYPES.index(selected_activity["activity_type"]), key=f"activity_type_{edit_activity_id}")
                        with edit_middle:
                            edit_stage_options = _stage_options(selected_activity["stage_after_activity"])
                            edit_stage = st.selectbox("결과 단계", edit_stage_options, index=edit_stage_options.index(selected_activity["stage_after_activity"]), key=f"activity_stage_{edit_activity_id}")
                            visit_index = (["미입력", *VISIT_RESULTS].index(selected_activity["visit_result"]) if selected_activity["visit_result"] in VISIT_RESULTS else 0)
                            edit_visit_result = st.selectbox("방문 결과", ["미입력", *VISIT_RESULTS], index=visit_index, key=f"activity_visit_result_{edit_activity_id}")
                            st.caption("방문 상담이 아니면 `미입력`으로 두세요.")
                        with edit_right:
                            closed_index = (["선택 안 함", *CLOSED_REASONS].index(selected_activity["closed_reason"]) if selected_activity["closed_reason"] in CLOSED_REASONS else 0)
                            edit_closed_reason = st.selectbox("종료 사유", ["선택 안 함", *CLOSED_REASONS], index=closed_index, key=f"activity_closed_reason_{edit_activity_id}", help="결과 단계를 `종료`로 저장할 때는 반드시 선택해 주세요.")
                            edit_next_contact = st.date_input("다음 연락일", value=date.fromisoformat(selected_activity["next_contact_date"]) if selected_activity["next_contact_date"] else None, disabled=edit_stage == "종료", key=f"activity_next_contact_{edit_activity_id}")
                        edit_activity_note = st.text_area("이번 상담 내용", value=selected_activity["activity_note"] or "", key=f"activity_note_{edit_activity_id}")
                        activity_change_submitted = st.form_submit_button("선택한 후속 상담 이력 수정 저장", type="primary")
                    if activity_change_submitted:
                        activity, errors = validate_consultation_activity({"activity_date": edit_activity_date, "activity_type": edit_activity_type, "activity_note": edit_activity_note, "stage_after_activity": edit_stage, "visit_result": None if edit_visit_result == "미입력" else edit_visit_result, "closed_reason": None if edit_closed_reason == "선택 안 함" else edit_closed_reason, "next_contact_date": edit_next_contact})
                        if errors:
                            for error in errors: st.error(error)
                        else:
                            try:
                                save_consultation_activity_changes(edit_activity_id, detail["consultation_id"], activity)
                            except ValueError as error:
                                st.error(str(error))
                            else:
                                st.success("선택한 후속 상담 이력을 수정했습니다. 첫 상담 내용과 다른 후속 이력은 유지됩니다.")
                                st.rerun()
                    with st.expander("선택한 후속 상담 이력 삭제"):
                        st.warning("선택한 후속 상담 이력 1건만 삭제합니다. 첫 상담 내용과 다른 후속 이력은 유지됩니다.")
                        activity_delete_confirmed = st.checkbox("선택한 후속 상담 이력만 삭제하는 것을 확인했습니다.", key=f"delete_activity_confirm_{edit_activity_id}")
                        if st.button("선택한 후속 상담 이력 삭제", type="secondary", disabled=not activity_delete_confirmed, key=f"delete_activity_{edit_activity_id}"):
                            try:
                                delete_consultation_activity(edit_activity_id, detail["consultation_id"])
                            except ValueError as error:
                                st.error(str(error))
                            else:
                                st.session_state.pop(edit_target_key, None)
                                st.success("선택한 후속 상담 이력 1건을 삭제했습니다.")
                                st.rerun()
        else:
            st.caption("아직 후속 상담 이력이 없습니다.")
        with st.form(f"consultation_activity_{detail['consultation_id']}"):
            activity_left, activity_middle, activity_right = st.columns(3)
            with activity_left:
                activity_date = st.date_input("후속 상담일", value=date.today())
                activity_type = st.selectbox("상담 방식", CONSULTATION_TYPES)
            with activity_middle:
                stage_options = _stage_options(detail["progress_stage"])
                stage_after_activity = st.selectbox("결과 단계", stage_options, index=stage_options.index(detail["progress_stage"]))
                visit_result = st.selectbox("방문 결과", ["미입력", *VISIT_RESULTS])
                st.caption("방문 상담이 아니면 `미입력`으로 두세요.")
            with activity_right:
                closed_reason = st.selectbox("종료 사유", ["선택 안 함", *CLOSED_REASONS], help="결과 단계를 `종료`로 저장할 때는 반드시 선택해 주세요.")
                next_activity_contact = st.date_input("다음 연락일", value=None, disabled=stage_after_activity == "종료")
            activity_note = st.text_area("이번 상담 내용", placeholder="예: 방문 후 가격을 검토하기로 함")
            activity_submitted = st.form_submit_button("후속 상담 기록 저장", type="primary")
        if activity_submitted:
            activity, errors = validate_consultation_activity({"activity_date": activity_date, "activity_type": activity_type, "activity_note": activity_note, "stage_after_activity": stage_after_activity, "visit_result": None if visit_result == "미입력" else visit_result, "closed_reason": None if closed_reason == "선택 안 함" else closed_reason, "next_contact_date": next_activity_contact})
            if errors:
                for error in errors: st.error(error)
            else:
                try:
                    save_consultation_activity(detail["consultation_id"], activity)
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.success("기존 상담 내용은 유지하고 후속 상담 이력을 추가했습니다.")
                    st.rerun()
    else:
        st.info("기존 상담 기록입니다. 기존 내용은 바꾸지 않고 새 상담부터 진행 단계와 후속 이력을 관리합니다.")
        with st.expander("이 기존 상담 종료 처리"):
            st.caption("기존 상담 내용과 상담일은 바꾸지 않습니다. 종료 사유를 남기고 다음 연락일만 해제합니다.")
            legacy_closed_reason = st.selectbox("종료 사유", CLOSED_REASONS, key=f"legacy_close_reason_{detail['consultation_id']}")
            legacy_close_confirmed = st.checkbox("이 상담을 종료 처리하는 것을 확인했습니다.", key=f"legacy_close_confirm_{detail['consultation_id']}")
            if st.button("기존 상담 종료 처리", type="secondary", disabled=not legacy_close_confirmed, key=f"legacy_close_{detail['consultation_id']}"):
                try:
                    close_legacy_consultation(detail["consultation_id"], legacy_closed_reason)
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.success("기존 상담을 종료 처리했습니다. 다음 연락일은 해제됐고 기존 내용은 유지됩니다.")
                    st.rerun()

    if detail["consultation_category"] == "일반 상담" and detail["listing_id"] is None:
        with st.expander("이 일반 상담에 매물 연결"):
            st.caption("고객에게 맞는 매물이 정해진 뒤에만 연결합니다. 연결 전까지는 일반 상담으로 유지됩니다.")
            link_query = st.text_input("연결할 매물 회차 찾기", key=f"general_consultation_link_query_{detail['consultation_id']}", placeholder="M-000150 또는 건물명·지번·호수 2글자 이상")
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
        delete_counts = get_consultation_delete_counts(detail["consultation_id"])
        st.error(f"선택한 상담 기록과 후속 상담 이력 {delete_counts['activities']}건이 함께 삭제됩니다. 매물과 계약 기록은 남습니다.")
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
    st.markdown("<p class='section-note'>상담 단계는 계약 전까지 관리합니다. 계약 진행·완료와 계약 단계 이력은 계약관리에서 처리하며, 고객 연락처는 상담 상세에서만 확인합니다.</p>", unsafe_allow_html=True)
    mode = st.radio("상담관리 메뉴", ["상담 등록", "상담 조회·수정"], horizontal=True, key="consultation_management_mode")
    if mode == "상담 등록":
        _render_registration()
    else:
        _render_lookup()
