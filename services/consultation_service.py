"""상담 입력 검사와 저장 규칙."""

from __future__ import annotations

from datetime import date
from typing import Any

from storage.consultation_repository import create_consultation, delete_consultation as delete_consultation_record, link_consultation_to_listing as link_consultation_record, update_consultation, update_consultation_follow_up, update_consultation_status
from services.backup_service import create_daily_backup


CONSULTATION_TYPES = ["전화", "문자", "방문", "기타"]
CONSULTATION_STATUSES = ["진행 중", "보류", "종료", "확인 필요"]
CONSULTATION_CATEGORIES = ["매물 상담", "일반 상담"]
CONSULTATION_SOURCES = ["미입력", "직방", "다방", "당근", "네이버"]


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _date_text(value: Any) -> str | None:
    return value.isoformat() if isinstance(value, date) else _text(value)


def validate_consultation(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    name = _text(raw.get("customer_name")) or "미입력"
    phone = _text(raw.get("customer_phone")) or "미입력"
    note = _text(raw.get("consultation_note")) or "미입력"
    consulted_date, next_contact = _date_text(raw.get("consulted_date")) or date.today().isoformat(), _date_text(raw.get("next_contact_date"))
    category = raw.get("consultation_category", "매물 상담")
    deposit, monthly_rent = raw.get("desired_deposit_manwon"), raw.get("desired_monthly_rent_manwon")
    desired_available_from_date = _date_text(raw.get("desired_available_from_date"))
    consultation_type = raw.get("consultation_type") if raw.get("consultation_type") in CONSULTATION_TYPES else "기타"
    consultation_status = raw.get("consultation_status") if raw.get("consultation_status") in CONSULTATION_STATUSES else "확인 필요"
    consultation_source = raw.get("consultation_source") if raw.get("consultation_source") in CONSULTATION_SOURCES else "미입력"
    if category not in CONSULTATION_CATEGORIES: category = "매물 상담"
    if deposit is not None and deposit < 0: errors.append("희망 보증금은 0 이상의 숫자로 입력해 주세요.")
    if monthly_rent is not None and monthly_rent < 0: errors.append("희망 월세는 0 이상의 숫자로 입력해 주세요.")
    if errors:
        return None, errors
    return {
        "consultation_category": category, "customer_name": name, "customer_phone": phone, "consulted_date": consulted_date,
        "consultation_type": consultation_type, "consultation_source": consultation_source, "consultation_note": note,
        "desired_area": _text(raw.get("desired_area")), "desired_room_type": _text(raw.get("desired_room_type")),
        "desired_deposit_manwon": int(deposit) if deposit is not None else None,
        "desired_monthly_rent_manwon": int(monthly_rent) if monthly_rent is not None else None,
        "desired_available_from_date": desired_available_from_date,
        "next_contact_date": next_contact, "consultation_status": consultation_status,
    }, []


def save_consultation(listing_id: int | None, consultation: dict[str, Any]) -> int:
    result = create_consultation(listing_id, consultation)
    create_daily_backup()
    return result


def save_consultation_changes(consultation_id: int, values: dict[str, Any]) -> None:
    consultation, errors = validate_consultation({**values, "consulted_date": date.today(), "consultation_type": "기타", "consultation_category": values.get("consultation_category", "매물 상담")})
    if errors:
        raise ValueError(" ".join(errors))
    update_consultation(consultation_id, consultation)
    create_daily_backup()


def change_consultation_status(consultation_id: int, consultation_status: str) -> None:
    if consultation_status not in CONSULTATION_STATUSES:
        raise ValueError("상담 상태를 선택해 주세요.")
    update_consultation_status(consultation_id, consultation_status)
    create_daily_backup()


def change_consultation_follow_up(consultation_id: int, consultation_status: str, next_contact_date: str | None) -> None:
    if consultation_status not in CONSULTATION_STATUSES:
        raise ValueError("상담 상태를 선택해 주세요.")
    if next_contact_date:
        try:
            date.fromisoformat(next_contact_date)
        except ValueError as error:
            raise ValueError("다음 연락일 형식이 올바르지 않습니다.") from error
    update_consultation_follow_up(consultation_id, consultation_status, next_contact_date)
    create_daily_backup()


def delete_consultation(consultation_id: int) -> None:
    """선택한 상담 기록을 완전히 삭제한다."""
    delete_consultation_record(consultation_id)
    create_daily_backup()


def link_consultation_to_listing(consultation_id: int, listing_id: int) -> None:
    """일반 상담에 나중에 선택한 매물 기록을 연결한다."""
    link_consultation_record(consultation_id, listing_id)
    create_daily_backup()
