"""상담 입력 검사와 저장 규칙."""

from __future__ import annotations

from datetime import date
from typing import Any

from storage.database import create_consultation, update_consultation


CONSULTATION_TYPES = ["전화", "문자", "방문", "기타"]
CONSULTATION_STATUSES = ["진행 중", "보류", "종료", "확인 필요"]


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _date_text(value: Any) -> str | None:
    return value.isoformat() if isinstance(value, date) else _text(value)


def validate_consultation(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    name, phone, note = _text(raw.get("customer_name")), _text(raw.get("customer_phone")), _text(raw.get("consultation_note"))
    consulted_date, next_contact = _date_text(raw.get("consulted_date")), _date_text(raw.get("next_contact_date"))
    if not name: errors.append("고객 이름을 입력해 주세요.")
    if not phone: errors.append("고객 연락처를 입력해 주세요.")
    if not consulted_date: errors.append("상담일을 입력해 주세요.")
    if raw.get("consultation_type") not in CONSULTATION_TYPES: errors.append("상담 종류를 선택해 주세요.")
    if not note: errors.append("상담 내용을 입력해 주세요.")
    if raw.get("consultation_status") not in CONSULTATION_STATUSES: errors.append("상담 상태를 선택해 주세요.")
    if errors:
        return None, errors
    return {
        "customer_name": name, "customer_phone": phone, "consulted_date": consulted_date,
        "consultation_type": raw["consultation_type"], "consultation_note": note,
        "next_contact_date": next_contact, "consultation_status": raw["consultation_status"],
    }, []


def save_consultation(listing_id: int, consultation: dict[str, Any]) -> int:
    return create_consultation(listing_id, consultation)


def save_consultation_changes(consultation_id: int, values: dict[str, Any]) -> None:
    consultation, errors = validate_consultation({**values, "consulted_date": date.today(), "consultation_type": "기타"})
    if errors:
        raise ValueError(" ".join(errors))
    update_consultation(consultation_id, consultation)
