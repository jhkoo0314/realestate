"""날짜별로 계산한 통합 오늘 할 일 화면."""

from __future__ import annotations

from datetime import date

import streamlit as st

from services.today_task_service import get_today_tasks
from services.export_service import create_today_tasks_excel, make_today_tasks_export_filename


def _render_group(title: str, rows: list[dict[str, str]], empty_message: str) -> None:
    st.markdown(f"#### {title} · {len(rows)}건")
    if rows:
        hidden_columns = {"kind"}
        if title == "상시 확인 필요":
            hidden_columns.add("기한")
        st.dataframe([{key: value for key, value in row.items() if key not in hidden_columns} for row in rows], width="stretch", hide_index=True)
    else:
        st.info(empty_message)


def render_today_tasks() -> None:
    st.subheader("오늘 할 일")
    st.markdown("<p class='section-note'>매물·계약·상담 기록에서 기준일 업무를 다시 계산합니다. 이 화면에서 완료 처리나 별도 업무 기록을 만들지는 않습니다.</p>", unsafe_allow_html=True)
    reference_date = st.date_input("기준일", value=date.today(), key="today_tasks_reference_date")
    try:
        tasks = get_today_tasks(reference_date)
    except (FileNotFoundError, ValueError) as error:
        st.error(str(error))
        return
    metrics = st.columns(3)
    for column, key in zip(metrics, ("오늘", "지연", "상시 확인 필요")):
        column.metric(key, len(tasks[key]))
    st.caption("오늘·지연은 날짜가 있는 업무이며, 조건 확인은 사진·현장 상태처럼 날짜 없이 확인이 필요한 업무입니다. 연락처·비밀번호·내부 메모는 표시하지 않습니다.")
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
    _render_group("오늘 해야 할 일", tasks["오늘"], "선택한 날짜에 해야 할 일이 없습니다.")
    _render_group("지연된 일", tasks["지연"], "선택한 날짜보다 지연된 일이 없습니다.")
    _render_group("상시 확인 필요", tasks["상시 확인 필요"], "날짜와 무관하게 확인할 매물 조건이 없습니다.")
