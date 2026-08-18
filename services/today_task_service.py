"""여러 업무 기록에서 기준일의 할 일을 계산한다. 별도 완료 기록은 만들지 않는다."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from services.contract_schedule_service import get_contract_schedule
from storage.consultation_repository import get_consultations
from storage.listing_repository import get_current_listings
from storage.database import DATABASE_PATH
from services.record_number import consultation_number, contract_number, listing_number
from storage.today_task_completion_repository import get_completed_task_keys


def _row(source: str, task: str, due_date: str | None, item: dict[str, Any], status: str, kind: str) -> dict[str, str]:
    listing_id = item.get("listing_id")
    record_number = {
        "매물": listing_number(listing_id),
        "계약": contract_number(item.get("contract_id")),
        "상담": consultation_number(item.get("consultation_id")),
    }.get(source, "-")
    record_id = {"매물": listing_id, "계약": item.get("contract_id"), "상담": item.get("consultation_id")}.get(source)
    task_key = f"{source}:{record_id}:{task}:{due_date or '조건확인'}"
    return {
        "업무 구분": source,
        "업무번호": record_number,
        "연결 매물번호": listing_number(listing_id),
        "해야 할 일": task,
        "기한": due_date or "조건 확인",
        "건물명": item.get("building_name") or item.get("건물명") or "-",
        "지번": item.get("lot_address") or item.get("지번") or "-",
        "호실": item.get("unit_number") or item.get("호실") or "-",
        "퇴실 예정일": item.get("move_out_due_date"),
        "상태": status,
        "task_key": task_key,
        "source_record_id": record_id,
        "kind": kind,
    }


def get_today_tasks(reference_date: date, path=DATABASE_PATH) -> dict[str, list[dict[str, str]]]:
    """당일, 지연, 날짜와 무관한 조건 확인 업무를 분리한다."""
    today_text = reference_date.isoformat()
    result: dict[str, list[dict[str, str]]] = {"오늘": [], "지연": [], "상시 확인 필요": []}

    for listing in get_current_listings(path=path):
        if listing["next_check_date"] and listing["next_check_date"] <= today_text:
            bucket = "오늘" if listing["next_check_date"] == today_text else "지연"
            result[bucket].append(_row("매물", "매물 재확인", listing["next_check_date"], listing, listing["listing_status"], bucket))
        move_out_due_date = listing["move_out_due_date"]
        if move_out_due_date:
            move_out_date = date.fromisoformat(move_out_due_date)
            remaining_days = (move_out_date - reference_date).days
            if 1 <= remaining_days <= 7:
                result["오늘"].append(_row(
                    "매물",
                    f"퇴실 예정 확인 (D-{remaining_days} 알림)",
                    move_out_due_date,
                    listing,
                    listing["listing_status"],
                    "오늘",
                ))
            elif remaining_days == 0:
                result["오늘"].append(_row("매물", "퇴실 예정", move_out_due_date, listing, listing["listing_status"], "오늘"))
        for task in listing["tasks"]:
            if task != "재확인 필요":
                result["상시 확인 필요"].append(_row("매물", task, None, listing, listing["listing_status"], "상시 확인 필요"))

    for consultation in get_consultations(path=path):
        due_date = consultation.get("next_contact_date")
        if due_date and due_date <= today_text and consultation["consultation_status"] != "종료":
            bucket = "오늘" if due_date == today_text else "지연"
            result[bucket].append(_row("상담", "다음 연락", due_date, consultation, consultation["consultation_status"], bucket))

    for event in get_contract_schedule(reference_date, days=1, path=path):
        if event["remaining_days"] == 1:
            if event["일정 종류"] == "잔금 예정":
                result["오늘"].append(_row("계약", "잔금 예정 (D-1 알림)", event["예정일"], event, event["계약 상태"], "오늘"))
            continue
        bucket = "오늘" if event["remaining_days"] == 0 else "지연"
        result[bucket].append(_row("계약", event["일정 종류"], event["예정일"], event, event["계약 상태"], bucket))

    for key in result:
        result[key].sort(key=lambda item: (item["기한"], item["업무 구분"], item["건물명"], item["호실"]))
    completed_keys = get_completed_task_keys([item["task_key"] for rows in result.values() for item in rows], path=path)
    for rows in result.values():
        for item in rows:
            item["is_completed"] = item["task_key"] in completed_keys
            item["완료"] = "완료" if item["is_completed"] else "미완료"
    return result
