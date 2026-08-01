"""매물 등록에 필요한 입력 검사와 저장 순서."""

from __future__ import annotations

from datetime import date
from typing import Any

from storage.database import save_first_listing


LISTING_STATUSES = ["확인 필요", "퇴실 예정", "공실", "광고 가능", "계약 진행 중", "보류"]
ROOM_TYPES = ["원룸", "분리형 원룸", "투룸", "쓰리룸", "주인세대", "기타", "확인 필요"]
AVAILABILITY_TYPES = ["즉시입주", "날짜 지정", "퇴실 후 협의", "확인 필요"]


def _clean_text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _date_text(value: Any) -> str | None:
    if isinstance(value, date):
        return value.isoformat()
    return _clean_text(value)


def validate_first_listing(raw: dict[str, Any]) -> tuple[dict[str, dict[str, Any]] | None, list[str]]:
    """화면의 입력값을 저장용 묶음으로 바꾸고, 오류를 쉬운 말로 돌려준다."""
    errors: list[str] = []

    building_name = _clean_text(raw.get("building_name"))
    lot_address = _clean_text(raw.get("lot_address"))
    unit_number = _clean_text(raw.get("unit_number"))
    deposit = raw.get("deposit_manwon")
    rent = raw.get("monthly_rent_manwon")
    availability_type = raw.get("availability_type")
    available_from_date = raw.get("available_from_date")

    if not building_name:
        errors.append("건물명을 입력해 주세요.")
    if not lot_address:
        errors.append("지번을 입력해 주세요.")
    if not unit_number:
        errors.append("호수를 입력해 주세요.")
    if deposit is None or deposit <= 0:
        errors.append("보증금은 0보다 큰 숫자로 입력해 주세요. 가격을 모르면 확인 필요로 남겨 주세요.")
    if rent is None or rent <= 0:
        errors.append("월세는 0보다 큰 숫자로 입력해 주세요. 가격을 모르면 확인 필요로 남겨 주세요.")
    if availability_type == "날짜 지정" and not available_from_date:
        errors.append("입주 가능 유형이 날짜 지정이면 입주 가능일을 입력해 주세요.")

    if errors:
        return None, errors

    payload = {
        "building": {
            "building_name": building_name,
            "lot_address": lot_address,
            "admin_address": _clean_text(raw.get("admin_address")),
            "road_address": _clean_text(raw.get("road_address")),
            "common_entrance_password": _clean_text(raw.get("common_entrance_password")),
            "has_elevator": raw.get("has_elevator"),
            "parking_status": raw.get("parking_status"),
            "internal_note": _clean_text(raw.get("building_internal_note")),
        },
        "unit": {
            "unit_number": unit_number,
            "floor_number": raw.get("floor_number"),
            "room_type": raw.get("room_type"),
            "direction": raw.get("direction"),
            "access_method": raw.get("access_method"),
            "unit_access_password": _clean_text(raw.get("unit_access_password")),
            "photo_folder_url": _clean_text(raw.get("photo_folder_url")),
            "unit_highlights": _clean_text(raw.get("unit_highlights")),
        },
        "listing": {
            "listing_status": raw.get("listing_status"),
            "deposit_manwon": int(deposit),
            "monthly_rent_manwon": int(rent),
            "management_fee_manwon": raw.get("management_fee_manwon"),
            "availability_type": availability_type,
            "available_from_date": _date_text(available_from_date),
            "move_out_due_date": _date_text(raw.get("move_out_due_date")),
            "photo_status": raw.get("photo_status"),
            "listing_note": _clean_text(raw.get("listing_note")),
            "next_check_date": _date_text(raw.get("next_check_date")),
        },
    }
    return payload, []


def save_confirmed_first_listing(payload: dict[str, dict[str, Any]]) -> tuple[int, int, int]:
    """확인된 입력만 데이터 저장소에 전달한다."""
    return save_first_listing(payload["building"], payload["unit"], payload["listing"])


def listing_summary(payload: dict[str, dict[str, Any]]) -> str:
    """저장 직전에 보여 줄 짧은 요약문."""
    building = payload["building"]
    unit = payload["unit"]
    listing = payload["listing"]
    unit_label = f"{unit['unit_number']}호" if not unit["unit_number"].endswith("호") else unit["unit_number"]
    availability = listing["availability_type"]
    if availability == "날짜 지정":
        availability = f"{listing['available_from_date']} 입주 가능"
    return (
        f"{building['building_name']} · {building['lot_address']} · {unit_label} · "
        f"{unit.get('room_type') or '형태 미입력'} · "
        f"{listing['deposit_manwon']}/{listing['monthly_rent_manwon']} · {availability}"
    )
