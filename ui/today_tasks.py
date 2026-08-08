"""날짜별로 계산한 통합 오늘 할 일 화면."""

from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from services.consultation_service import CONSULTATION_STATUSES, change_consultation_status
from services.contract_service import CONTRACT_STATUSES, change_contract_status
from services.export_service import create_today_tasks_excel, make_today_tasks_export_filename
from services.record_number import consultation_number, listing_number
from services.today_task_completion_service import change_today_task_completion
from services.today_task_service import get_today_tasks
from storage.consultation_repository import get_consultation_detail


CHANGE_OPTIONS = ["유지"]


def _render_consultation_summary(consultation_id: int) -> None:
    """선택한 상담만 표 아래에서 빠르게 확인한다."""
    detail = get_consultation_detail(consultation_id)
    if detail is None:
        st.warning("선택한 상담 기록을 찾을 수 없습니다.")
        return
    st.markdown("##### 선택한 상담 내용")
    st.caption(
        f"{consultation_number(detail['consultation_id'])} · {detail['consultation_category']} · "
        f"상담일 {detail['consulted_date']} · 연결 매물번호 {listing_number(detail['listing_id'])}"
    )
    contact_column, due_column = st.columns(2)
    contact_column.write(f"고객 연락처: {detail['customer_phone'] or '-'}")
    due_column.write(f"다음 연락일: {detail['next_contact_date'] or '-'}")
    st.write(detail["consultation_note"] or "등록된 상담 내용이 없습니다.")


def _base_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "업무번호": row["업무번호"],
        "연결 매물번호": row["연결 매물번호"],
        "해야 할 일": row["해야 할 일"],
        "기한": row["기한"],
        "건물명": row["건물명"],
        "지번": row["지번"],
        "호실": row["호실"],
        "현재 상태": row["상태"],
    }


def _render_date_task_table(title: str, source: str, rows: list[dict[str, Any]], empty_message: str) -> None:
    remaining = sum(not row["is_completed"] for row in rows)
    st.markdown(f"##### {title} · 미완료 {remaining}건 / 전체 {len(rows)}건")
    if not rows:
        st.info(empty_message)
        return

    display_rows: list[dict[str, Any]] = []
    for row in rows:
        display = _base_row(row)
        if source == "계약":
            display["계약 열기"] = f"?open_task=contract&record_id={row['source_record_id']}"
            display["상태 변경"] = "유지"
        elif source == "상담":
            display["상담 내용 보기"] = False
            display["상태 변경"] = "유지"
        display["완료"] = row["is_completed"]
        display_rows.append(display)

    editable_columns = {"완료"}
    column_config: dict[str, Any] = {
        "완료": st.column_config.CheckboxColumn("완료", help="처리한 날짜 업무는 체크하고, 다시 확인해야 하면 해제합니다."),
    }
    if source == "계약":
        column_config["계약 열기"] = st.column_config.LinkColumn("계약 열기", display_text="열기", help="해당 계약 상세·수정 화면을 엽니다.")
        column_config["상태 변경"] = st.column_config.SelectboxColumn("상태 변경", options=CHANGE_OPTIONS + CONTRACT_STATUSES, help="계약 상태를 바꾸면 연결 매물에도 자동 반영합니다.")
        editable_columns.add("상태 변경")
    elif source == "상담":
        column_config["상담 내용 보기"] = st.column_config.CheckboxColumn("상담 내용 보기", help="선택한 상담의 내용과 고객 연락처를 표 아래에 표시합니다.")
        column_config["상태 변경"] = st.column_config.SelectboxColumn("상태 변경", options=CHANGE_OPTIONS + CONSULTATION_STATUSES, help="선택한 상담 기록의 상태만 변경합니다.")
        editable_columns.update({"상담 내용 보기", "상태 변경"})

    edited = st.data_editor(
        display_rows,
        width="stretch",
        hide_index=True,
        disabled=[column for column in display_rows[0] if column not in editable_columns],
        column_config=column_config,
        key=f"today_task_grid_{title}_{source}",
    )
    edited_rows = edited if isinstance(edited, list) else edited.to_dict("records")
    selected_consultation_id: int | None = None
    changed = False
    for row, edited_row in zip(rows, edited_rows):
        requested_status = edited_row.get("상태 변경", "유지")
        try:
            if requested_status != "유지" and requested_status != row["상태"]:
                if source == "계약":
                    change_contract_status(row["source_record_id"], requested_status)
                elif source == "상담":
                    change_consultation_status(row["source_record_id"], requested_status)
                changed = True
            if bool(edited_row["완료"]) != row["is_completed"]:
                change_today_task_completion(row["task_key"], bool(edited_row["완료"]))
                changed = True
        except Exception as error:
            st.error(f"상태 또는 완료 표시를 저장하지 못했습니다. ({error})")
            return
        if source == "상담" and bool(edited_row["상담 내용 보기"]):
            selected_consultation_id = row["source_record_id"]
    if changed:
        st.rerun()
    if selected_consultation_id is not None:
        _render_consultation_summary(selected_consultation_id)


def _render_always_listing_table(rows: list[dict[str, Any]]) -> None:
    st.markdown(f"#### 상시 확인 필요 · {len(rows)}건")
    if not rows:
        st.info("날짜와 무관하게 확인할 매물 조건이 없습니다.")
        return
    hidden_columns = {"kind", "task_key", "source_record_id", "is_completed", "완료"}
    hidden_columns.add("기한")
    st.dataframe([{key: value for key, value in row.items() if key not in hidden_columns} for row in rows], width="stretch", hide_index=True)


def _render_date_task_section(title: str, rows: list[dict[str, Any]], empty_message: str) -> None:
    st.markdown(f"#### {title}")
    for source, label in (("매물", "매물 업무"), ("계약", "계약 업무"), ("상담", "상담 업무")):
        source_rows = [row for row in rows if row["업무 구분"] == source]
        _render_date_task_table(label, source, source_rows, empty_message)


def render_today_tasks() -> None:
    st.subheader("오늘 할 일")
    st.markdown("<p class='section-note'>매물·계약·상담 업무를 각각의 표로 구분합니다. 계약 상태 변경은 연결 매물에 자동 반영되고, 상담 상태 변경은 해당 상담 기록에만 반영됩니다.</p>", unsafe_allow_html=True)
    reference_date = st.date_input("기준일", value=date.today(), key="today_tasks_reference_date")
    try:
        tasks = get_today_tasks(reference_date)
    except (FileNotFoundError, ValueError) as error:
        st.error(str(error))
        return
    metrics = st.columns(3)
    for column, key in zip(metrics, ("오늘", "지연", "상시 확인 필요")):
        count = sum(not task["is_completed"] for task in tasks[key]) if key in ("오늘", "지연") else len(tasks[key])
        column.metric(key, count)
    st.caption("완료는 해당 날짜 업무의 처리 표시입니다. 계약 상태는 연결 매물에 연동되며, 상담 상태는 선택한 상담 기록만 바뀝니다. 상담 내용과 고객 연락처는 상담 행을 선택한 경우에만 표시합니다.")
    try:
        export_data = create_today_tasks_excel(tasks)
    except Exception as error:
        st.error(f"오늘 할 일 엑셀 파일을 만들지 못했습니다. ({error})")
    else:
        st.download_button(
            "오늘 할 일 엑셀 내려받기",
            data=export_data,
            file_name=make_today_tasks_export_filename(reference_date.isoformat()),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            key="today_tasks_excel_download",
        )
    _render_date_task_section("오늘 해야 할 일", tasks["오늘"], "해당 업무가 없습니다.")
    _render_date_task_section("지연된 일", tasks["지연"], "해당 업무가 없습니다.")
    _render_always_listing_table(tasks["상시 확인 필요"])
