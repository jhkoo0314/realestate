"""월별 광고비 입력 검사와 저장 규칙."""

from __future__ import annotations

from datetime import date
from typing import Any

from services.backup_service import create_daily_backup
from storage.advertisement_cost_repository import delete_monthly_advertising_cost, save_monthly_advertising_cost


ADVERTISING_COST_CHANNELS = ["당근", "네이버", "직방", "기타"]


def validate_monthly_advertising_cost(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    year_month = str(raw.get("year_month") or "")[:7]
    try:
        date.fromisoformat(f"{year_month}-01")
    except ValueError:
        errors.append("기준연월을 선택해 주세요.")
    choice = raw.get("channel_choice")
    custom = str(raw.get("custom_channel") or "").strip()
    channel = custom if choice == "기타" else choice
    if choice not in ADVERTISING_COST_CHANNELS or not channel:
        errors.append("광고 채널을 선택해 주세요.")
    amount = raw.get("monthly_cost_manwon")
    if amount is None or int(amount) < 0:
        errors.append("월 광고비는 0 이상의 숫자로 입력해 주세요.")
    if errors:
        return None, errors
    return {"year_month": year_month, "advertising_channel": channel, "monthly_cost_manwon": int(amount), "memo": str(raw.get("memo") or "").strip() or None}, []


def save_monthly_cost(values: dict[str, Any]) -> int:
    result = save_monthly_advertising_cost(values)
    create_daily_backup()
    return result


def remove_monthly_cost(cost_id: int) -> None:
    delete_monthly_advertising_cost(cost_id)
    create_daily_backup()
