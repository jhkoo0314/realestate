"""광고 현황 입력 검사와 저장 규칙."""

from __future__ import annotations

from datetime import date
from typing import Any

from services.backup_service import create_daily_backup
from storage.advertisement_repository import create_advertisement, delete_advertisement as delete_record, update_advertisement


ADVERTISING_CHANNELS = ["당근", "직방", "네이버", "직접입력"]
ADVERTISING_STATUSES = ["광고 중", "광고 중지", "확인 필요"]


def _date_text(value: Any) -> str | None:
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip() if value else None


def validate_advertisement(raw: dict[str, Any]) -> tuple[dict[str, str | None] | None, list[str]]:
    choice = raw.get("channel_choice")
    channel = str(raw.get("custom_channel") if choice == "직접입력" else choice or "").strip()
    status = raw.get("advertising_status")
    errors = []
    if choice not in ADVERTISING_CHANNELS:
        errors.append("광고 채널을 선택해 주세요.")
    if not channel:
        errors.append("직접 입력할 광고 채널 이름을 입력해 주세요.")
    if status not in ADVERTISING_STATUSES:
        errors.append("현재 광고 상태를 선택해 주세요.")
    if errors:
        return None, errors
    return {"advertising_channel": channel, "advertising_status": status, "last_checked_date": _date_text(raw.get("last_checked_date"))}, []


def save_advertisement(listing_id: int, advertisement: dict[str, str | None]) -> int:
    result = create_advertisement(listing_id, advertisement["advertising_channel"] or "", advertisement["advertising_status"] or "", advertisement["last_checked_date"])
    create_daily_backup()
    return result


def change_advertisement(advertisement_id: int, advertising_status: str, last_checked_date: date | None) -> None:
    if advertising_status not in ADVERTISING_STATUSES:
        raise ValueError("현재 광고 상태를 선택해 주세요.")
    update_advertisement(advertisement_id, advertising_status, _date_text(last_checked_date))
    create_daily_backup()


def remove_advertisement(advertisement_id: int) -> None:
    delete_record(advertisement_id)
    create_daily_backup()
