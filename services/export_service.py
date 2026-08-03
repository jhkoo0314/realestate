"""현재 매물 목록을 사무실 내부용 엑셀 파일로 만드는 기능."""

from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter


EXPORT_COLUMNS = [
    ("접수일", "received_date", "date"),
    ("매물 상태", "listing_status", "text"),
    ("건물명", "building_name", "text"),
    ("지번주소", "lot_address", "text"),
    ("행정주소", "admin_address", "text"),
    ("도로명주소", "road_address", "text"),
    ("호실", "unit_number", "text"),
    ("층", "floor_number", "number"),
    ("룸 형태", "room_type", "text"),
    ("방향", "direction", "text"),
    ("보증금(만원)", "deposit_manwon", "number"),
    ("월세(만원)", "monthly_rent_manwon", "number"),
    ("관리비(만원)", "management_fee_manwon", "number"),
    ("관리비 메모", "management_fee_note", "text"),
    ("입주 가능", "availability_type", "text"),
    ("입주 가능일", "available_from_date", "date"),
    ("퇴실 예정일", "move_out_due_date", "date"),
    ("사진 상태", "photo_status", "text"),
    ("사진 보유 여부", "has_listing_photos", "text"),
    ("재확인 예정일", "next_check_date", "date"),
    ("공동현관 비밀번호", "common_entrance_password", "text"),
    ("방문 방법", "access_method", "text"),
    ("방문 비밀번호", "unit_access_password", "text"),
    ("엘리베이터", "has_elevator", "text"),
    ("주차", "parking_status", "text"),
    ("호실 옵션", "unit_options", "text"),
    ("건물 내부 메모", "building_internal_note", "text"),
    ("호실 내부 메모", "unit_internal_note", "text"),
    ("매물 메모", "listing_note", "text"),
    ("이번 매물 옵션 변경 메모", "option_change_note", "text"),
]


def _excel_value(value: Any, value_type: str) -> Any:
    if value in (None, ""):
        return None
    if value_type == "date" and isinstance(value, str):
        return date.fromisoformat(value)
    return value


def create_current_listing_excel(rows: list[dict[str, Any]]) -> bytes:
    """명시한 열만 사용해 엑셀 내용을 만든다. 연락처 관련 열은 포함하지 않는다."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "현재 매물"
    sheet.append([label for label, _, _ in EXPORT_COLUMNS])
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")

    for row in rows:
        sheet.append([_excel_value(row.get(key), value_type) for _, key, value_type in EXPORT_COLUMNS])

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for index, (_, _, value_type) in enumerate(EXPORT_COLUMNS, start=1):
        column = get_column_letter(index)
        sheet.column_dimensions[column].width = 14 if value_type != "text" else 20
        if value_type == "date":
            for cell in sheet[column][1:]:
                cell.number_format = "yyyy-mm-dd"
        elif value_type == "number":
            for cell in sheet[column][1:]:
                cell.number_format = '#,##0'

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def make_export_filename(received_start: str | None, received_end: str | None) -> str:
    """접수일 범위와 생성 시각을 알 수 있는 다운로드 파일 이름을 만든다."""
    start = received_start or "처음"
    end = received_end or "전체"
    created = datetime.now().strftime("%Y%m%d_%H%M")
    return f"매물목록_접수일_{start}_{end}_{created}.xlsx"
