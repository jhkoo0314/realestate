"""매물 등록에 필요한 입력 검사와 저장 순서."""

from __future__ import annotations

from datetime import date
from typing import Any

from storage.listing_create_repository import (
    find_building_by_identity,
    save_first_listing,
    save_first_listing_for_existing_building,
)
from storage.listing_write_repository import close_current_listing, delete_listing as delete_listing_record, save_new_listing_round, update_current_listing


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
            "unit_options": _clean_text(raw.get("unit_options")),
            "access_method": raw.get("access_method"),
            "unit_access_password": _clean_text(raw.get("unit_access_password")),
            "unit_highlights": _clean_text(raw.get("unit_highlights")),
        },
        "listing": {
            "received_date": _date_text(raw.get("received_date")) or date.today().isoformat(),
            "listing_status": raw.get("listing_status"),
            "deposit_manwon": int(deposit),
            "monthly_rent_manwon": int(rent),
            "management_fee_manwon": raw.get("management_fee_manwon"),
            "availability_type": availability_type,
            "available_from_date": _date_text(available_from_date),
            "move_out_due_date": _date_text(raw.get("move_out_due_date")),
            "has_listing_photos": raw.get("has_listing_photos") or "확인 필요",
            "cleaning_status": raw.get("cleaning_status"),
            "wallpaper_status": raw.get("wallpaper_status"),
            "repair_status": raw.get("repair_status"),
            "listing_note": _clean_text(raw.get("listing_note")),
            "landlord_contact": _clean_text(raw.get("landlord_contact")),
            "tenant_contact": _clean_text(raw.get("tenant_contact")),
            "next_check_date": _date_text(raw.get("next_check_date")),
        },
    }
    return payload, []


def validate_new_building_listing(raw: dict[str, Any]) -> tuple[dict[str, dict[str, Any]] | None, list[str]]:
    """새 건물 등록 전, 같은 건물은 기존 건물 선택으로 안내한다."""
    payload, errors = validate_first_listing(raw)
    if errors or payload is None:
        return payload, errors

    existing = find_building_by_identity(
        payload["building"]["building_name"], payload["building"]["lot_address"]
    )
    if existing:
        return None, [
            f"{existing['building_name']} · {existing['lot_address']}은(는) 이미 등록되어 있습니다. "
            "위 검색 결과에서 기존 건물을 선택해 새 호실을 등록해 주세요."
        ]
    return payload, []


def save_confirmed_first_listing(payload: dict[str, dict[str, Any]]) -> tuple[int, int, int]:
    """확인된 입력만 데이터 저장소에 전달한다."""
    return save_first_listing(payload["building"], payload["unit"], payload["listing"])


def save_confirmed_existing_building_listing(
    building_id: int, payload: dict[str, dict[str, Any]]
) -> tuple[int, int]:
    """선택한 기존 건물에 새 호실과 첫 매물을 저장한다."""
    return save_first_listing_for_existing_building(building_id, payload["unit"], payload["listing"])


def validate_relisting(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """현재 매물 기록이 없는 기존 호실의 첫 현재 매물 조건을 검사한다."""
    errors: list[str] = []
    listing_status = raw.get("listing_status")
    availability_type = raw.get("availability_type")
    available_from_date = raw.get("available_from_date")
    price_mode = raw.get("price_mode")
    deposit = raw.get("deposit_manwon")
    rent = raw.get("monthly_rent_manwon")

    if not listing_status:
        errors.append("매물 상태를 선택해 주세요.")
    if not availability_type:
        errors.append("입주 가능 유형을 선택해 주세요.")
    if availability_type == "날짜 지정" and not available_from_date:
        errors.append("입주 가능 유형이 날짜 지정이면 입주 가능일을 입력해 주세요.")
    if price_mode == "새 가격 입력":
        if deposit is None or deposit <= 0:
            errors.append("보증금은 0보다 큰 숫자로 입력해 주세요.")
        if rent is None or rent <= 0:
            errors.append("월세는 0보다 큰 숫자로 입력해 주세요.")
    if errors:
        return None, errors

    note = _clean_text(raw.get("listing_note"))
    verification_note = None
    if price_mode == "가격 확인 필요":
        verification_note = "보증금·월세 확인 필요"
        note = f"{note}\n가격 확인 필요" if note else "가격 확인 필요"
        deposit = None
        rent = None

    return {
        "received_date": _date_text(raw.get("received_date")) or date.today().isoformat(),
        "listing_status": listing_status,
        "deposit_manwon": int(deposit) if deposit is not None else None,
        "monthly_rent_manwon": int(rent) if rent is not None else None,
        "management_fee_manwon": raw.get("management_fee_manwon"),
        "availability_type": availability_type,
        "available_from_date": _date_text(available_from_date),
        "move_out_due_date": _date_text(raw.get("move_out_due_date")),
        "has_listing_photos": raw.get("has_listing_photos") or "확인 필요",
        "cleaning_status": raw.get("cleaning_status"),
        "wallpaper_status": raw.get("wallpaper_status"),
        "repair_status": raw.get("repair_status"),
        "listing_note": note,
        "landlord_contact": _clean_text(raw.get("landlord_contact")),
        "tenant_contact": _clean_text(raw.get("tenant_contact")),
        "next_check_date": _date_text(raw.get("next_check_date")),
        "verification_note": verification_note,
    }, []


def save_current_listing_for_existing_unit(unit_id: int, listing: dict[str, Any]) -> int:
    """현재 매물 기록이 없는 기존 호실에 현재 매물 1건을 등록한다."""
    return save_new_listing_round(unit_id, listing)


def validate_current_listing(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """현재 매물의 수정값을 검사한다. 새 회차는 만들지 않는다."""
    raw = {**raw, "price_mode": "새 가격 입력"}
    listing, errors = validate_relisting(raw)
    if errors or listing is None:
        return listing, errors
    listing["last_photo_date"] = _date_text(raw.get("last_photo_date"))
    listing["unit_options"] = _clean_text(raw.get("unit_options"))
    return listing, []


def save_current_listing_changes(listing_id: int, listing: dict[str, Any]) -> None:
    """검사된 수정값을 현재 매물 회차에 한 번에 저장한다."""
    update_current_listing(listing_id, listing)


def close_listing(listing_id: int, close_date: date, close_reason: str) -> None:
    """현재 매물을 종료 처리하고 기록은 남긴다."""
    close_current_listing(listing_id, close_date.isoformat(), close_reason)


def delete_listing(listing_id: int) -> dict[str, int]:
    """매물과 그 매물에 연결된 계약·상담 기록을 완전히 삭제한다."""
    return delete_listing_record(listing_id)


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
