"""계약 단계 이력은 실제 처리 결과만 새 입력으로 기록하는지 확인."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.contract_service import CONTRACT_ACTIVITY_STAGES, validate_contract, validate_contract_activity
from storage.contract_repository import add_contract_activity
from storage.database import get_connection, initialize_database


def run() -> None:
    assert "잔금 완료" in CONTRACT_ACTIVITY_STAGES
    assert "잔금 예정" not in CONTRACT_ACTIVITY_STAGES
    activity, errors = validate_contract_activity({"activity_date": "2026-08-28", "activity_stage": "잔금 완료", "activity_note": "잔금 수령 확인"})
    assert not errors and activity is not None
    assert activity["contract_status_after"] == "계약 진행"
    early_balance, errors = validate_contract({
        "contract_type": "일반 계약", "brokerage_method": "단독중개", "contract_status": "계약 진행",
        "contract_progress_date": "2026-08-20", "formal_contract_date": "2026-08-25", "balance_due_date": "2026-08-22",
    })
    assert not errors and early_balance is not None
    _, errors = validate_contract({
        "contract_type": "일반 계약", "brokerage_method": "단독중개", "contract_status": "계약 진행",
        "contract_progress_date": "2026-08-20", "balance_due_date": "2026-08-19",
    })
    assert "잔금 예정일은 계약 진행 시작일보다 빠를 수 없습니다." in errors

    with tempfile.TemporaryDirectory() as directory:
        database_path = Path(directory) / "contract_activity.db"
        initialize_database(database_path)
        connection = get_connection(database_path)
        try:
            building_id = connection.execute("INSERT INTO buildings (building_name, lot_address) VALUES (?, ?)", ("단계 확인빌", "북수리 2000")).lastrowid
            unit_id = connection.execute("INSERT INTO units (building_id, unit_number, unit_number_normalized) VALUES (?, ?, ?)", (building_id, "101", "101")).lastrowid
            listing_id = connection.execute("INSERT INTO listings (unit_id, received_date, listing_status, availability_type) VALUES (?, ?, ?, ?)", (unit_id, "2026-08-20", "계약 진행 중", "즉시입주")).lastrowid
            consultation_id = connection.execute(
                """INSERT INTO consultations
                   (listing_id, customer_name, customer_phone, consulted_date, consultation_type, consultation_note, consultation_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (listing_id, "확인 고객", "010-0000-0000", "2026-08-20", "전화", "계약 진행 확인", "종료"),
            ).lastrowid
            contract_id = connection.execute(
                "INSERT INTO contracts (listing_id, source_consultation_id, contract_type, contract_status) VALUES (?, ?, ?, ?)",
                (listing_id, consultation_id, "일반 계약", "계약 진행"),
            ).lastrowid
            connection.commit()
        finally:
            connection.close()

        add_contract_activity(contract_id, activity, database_path)
        connection = get_connection(database_path)
        try:
            saved_activity = connection.execute("SELECT activity_stage, contract_status_after FROM contract_activities WHERE contract_id=?", (contract_id,)).fetchone()
            contract = connection.execute("SELECT contract_status FROM contracts WHERE id=?", (contract_id,)).fetchone()
            listing = connection.execute("SELECT listing_status, close_reason FROM listings WHERE id=?", (listing_id,)).fetchone()
            consultation = connection.execute("SELECT consultation_status, progress_stage FROM consultations WHERE id=?", (consultation_id,)).fetchone()
            assert tuple(saved_activity) == ("잔금 완료", "계약 진행")
            assert contract["contract_status"] == "계약 진행"
            assert tuple(listing) == ("계약 진행 중", None)
            assert tuple(consultation) == ("진행 중", "계약 진행")
        finally:
            connection.close()


if __name__ == "__main__":
    run()
    print("contract activity stage: PASS")
