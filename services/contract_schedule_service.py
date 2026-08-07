"""계약 기록에서 개인정보 없이 일정 행을 계산한다."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from storage.contract_repository import get_contracts


SCHEDULE_FIELDS = (
    ("formal_contract_date", "정식 계약"),
    ("remaining_deposit_due_date", "계약금 추가 수령 예정"),
    ("balance_due_date", "잔금 예정"),
    ("contract_end_date", "임대차 종료"),
)


def expiry_band(days: int) -> str:
    if days <= 0:
        return "오늘 또는 지남"
    if days <= 7:
        return "7일 이내"
    if days <= 15:
        return "8~15일"
    return "16~30일"


def get_contract_schedule(reference_date: date, days: int = 30, path: Path | None = None) -> list[dict[str, Any]]:
    """실제로 처리할 계약 일정만 기준일 이전 미처리·이후 기간으로 반환한다.

    계약 진행 시작일은 가계약·구두 합의의 이력일 수 있으므로 일정 업무로 만들지 않는다.
    """
    if days < 0:
        raise ValueError("조회 기간은 0일 이상이어야 합니다.")
    rows: list[dict[str, Any]] = []
    for contract in get_contracts(**({"path": path} if path else {})):
        if contract["contract_status"] in ("해지", "만료"):
            continue
        for field, label in SCHEDULE_FIELDS:
            value = contract.get(field)
            if not value:
                continue
            due_date = date.fromisoformat(value)
            remaining_days = (due_date - reference_date).days
            if remaining_days > days:
                continue
            is_expiry = field == "contract_end_date"
            rows.append({
                "일정 종류": label,
                "예정일": value,
                "남은 일수": "지남" if remaining_days < 0 else ("D-day" if remaining_days == 0 else f"{remaining_days}일 남음"),
                "계약 상태": contract["contract_status"],
                "건물명": contract["building_name"],
                "지번": contract["lot_address"],
                "호실": contract["unit_number"],
                "만료 구간": expiry_band(remaining_days) if is_expiry else "-",
                "due_date": value,
                "remaining_days": remaining_days,
                "event_type": label,
                "is_expiry": is_expiry,
            })
    return sorted(rows, key=lambda item: (item["due_date"], item["건물명"], item["호실"], item["일정 종류"]))


def expiry_summary(reference_date: date, path: Path | None = None) -> dict[str, int]:
    events = [item for item in get_contract_schedule(reference_date, days=30, path=path) if item["is_expiry"] and item["remaining_days"] >= 0]
    return {
        "30일 이내": len(events),
        "15일 이내": sum(item["remaining_days"] <= 15 for item in events),
        "7일 이내": sum(item["remaining_days"] <= 7 for item in events),
    }
