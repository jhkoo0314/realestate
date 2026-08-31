"""계약 성사 상담 자동 종료·이력·목록 제외 및 기존 데이터 보정 확인."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.today_task_service import get_today_tasks
from storage.consultation_repository import get_consultation_activities, get_consultation_detail, get_consultations, get_successful_contract_for_consultation
from storage.contract_repository import create_contract, repair_successful_contract_consultations, update_contract_details
from storage.database import get_connection, initialize_database


def _listing(connection, suffix: int) -> int:
    building_id = connection.execute("INSERT INTO buildings (building_name, lot_address) VALUES (?, ?)", (f"계약성사빌{suffix}", f"북수리 {2000 + suffix}")).lastrowid
    unit_id = connection.execute("INSERT INTO units (building_id, unit_number, unit_number_normalized) VALUES (?, ?, ?)", (building_id, "301", "301")).lastrowid
    return connection.execute("INSERT INTO listings (unit_id, received_date, listing_status, availability_type) VALUES (?, ?, ?, ?)", (unit_id, "2026-08-30", "공실", "즉시입주")).lastrowid


def _consultation(connection, listing_id: int, suffix: int) -> int:
    return connection.execute(
        """INSERT INTO consultations
           (listing_id, customer_name, customer_phone, consulted_date, consultation_type, consultation_note,
            next_contact_date, consultation_status, progress_stage, last_contacted_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (listing_id, f"고객{suffix}", f"010-0000-00{suffix:02d}", "2026-08-29", "전화", "계약 전 상담", "2026-08-31", "진행 중", "검토 중", "2026-08-29"),
    ).lastrowid


def run() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "contract_consultation.db"
        initialize_database(path)
        connection = get_connection(path)
        try:
            listing_id = _listing(connection, 1)
            consultation_id = _consultation(connection, listing_id, 1)
            pending_listing_id = _listing(connection, 2)
            pending_consultation_id = _consultation(connection, pending_listing_id, 2)
            connection.commit()
        finally:
            connection.close()

        contract_id = create_contract(listing_id, {
            "contract_type": "일반 계약", "brokerage_method": "단독중개", "contract_status": "계약 진행",
            "contract_progress_date": "2026-08-30", "source_consultation_id": consultation_id,
        }, path)
        detail = get_consultation_detail(consultation_id, path)
        assert detail is not None
        assert (detail["consultation_status"], detail["progress_stage"], detail["closed_reason"], detail["next_contact_date"], detail["last_contacted_date"]) == ("종료", "계약 완료", "계약완료", None, "2026-08-29")
        activities = get_consultation_activities(consultation_id, path)
        assert len(activities) == 1
        assert (activities[0]["activity_type"], activities[0]["stage_after_activity"], activities[0]["closed_reason"], activities[0]["next_contact_date"]) == ("계약", "계약 완료", "계약완료", None)
        linked = get_successful_contract_for_consultation(consultation_id, path)
        assert linked and linked["contract_id"] == contract_id and linked["brokerage_method"] == "단독중개"

        update_contract_details(contract_id, {"contract_status": "잔금 예정"}, path)
        assert len(get_consultation_activities(consultation_id, path)) == 1
        rows = {row["consultation_id"]: row for row in get_consultations(path=path)}
        assert rows[consultation_id]["has_active_linked_contract"] == 1
        assert rows[pending_consultation_id]["has_active_linked_contract"] == 0
        assert consultation_id not in {row["consultation_id"] for row in get_consultations(statuses=["진행 중"], path=path)}
        tasks = get_today_tasks(__import__("datetime").date(2026, 8, 31), path)
        assert all(row["source_record_id"] != consultation_id for values in tasks.values() for row in values)
        assert any(row["source_record_id"] == pending_consultation_id for values in tasks.values() for row in values)

        connection = get_connection(path)
        try:
            connection.execute("UPDATE consultations SET consultation_status='진행 중', progress_stage='검토 중', closed_reason=NULL, next_contact_date='2026-08-31' WHERE id=?", (consultation_id,))
            connection.commit()
        finally:
            connection.close()
        repaired = repair_successful_contract_consultations(path)
        assert repaired["eligible_contracts"] == 1 and repaired["changed_consultations"] == 1
        assert len(get_consultation_activities(consultation_id, path)) == 1


if __name__ == "__main__":
    run()
    print("contract consultation success: PASS")
