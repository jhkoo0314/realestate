"""생성일 기본값이 없는 임시/기존 표에서 상담 후속 이력 및 계약 이력이 정상 추가되는지 확인한다."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from storage.database import get_connection, initialize_database
from storage.consultation_repository import create_consultation, add_consultation_activity, get_consultation_activities
from storage.contract_repository import create_contract, add_contract_activity
from storage.listing_create_repository import save_first_listing


def _remove_activity_timestamp_defaults(path: Path) -> None:
    connection = get_connection(path)
    try:
        with connection:
            connection.execute("ALTER TABLE consultation_activities RENAME TO consultation_activities_legacy")
            connection.execute("ALTER TABLE contract_activities RENAME TO contract_activities_legacy")
            connection.executescript("""
                CREATE TABLE consultation_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consultation_id INTEGER NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
                    activity_date TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    activity_note TEXT,
                    stage_after_activity TEXT NOT NULL,
                    visit_result TEXT,
                    closed_reason TEXT,
                    next_contact_date TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE contract_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
                    activity_date TEXT NOT NULL,
                    activity_stage TEXT NOT NULL,
                    activity_note TEXT,
                    contract_status_after TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                DROP TABLE consultation_activities_legacy;
                DROP TABLE contract_activities_legacy;
            """)
    finally:
        connection.close()


def run() -> None:
    with tempfile.TemporaryDirectory() as directory:
        database_path = Path(directory) / "activity_legacy_timestamps.db"
        initialize_database(database_path)

        building_id, unit_id, listing_id = save_first_listing(
            {"building_name": "이력확인빌", "lot_address": "북수리 999"},
            {"unit_number": "201", "room_type": "원룸"},
            {"listing_status": "공실", "availability_type": "즉시입주", "listing_holder": "개인매물"},
            database_path
        )

        consultation_id = create_consultation(
            listing_id,
            {
                "customer_name": "홍길동",
                "customer_phone": "010-1234-5678",
                "consulted_date": "2026-09-03",
                "consultation_note": "첫 문의",
                "consultation_status": "진행 중",
            },
            database_path
        )

        contract_id = create_contract(
            listing_id,
            {
                "contract_type": "일반 계약",
                "contract_status": "계약 진행",
                "source_consultation_id": consultation_id,
            },
            database_path
        )

        # 테이블에서 created_at/updated_at 기본값 제거
        _remove_activity_timestamp_defaults(database_path)

        # 상담 이력 추가 테스트
        act_id = add_consultation_activity(
            consultation_id,
            {
                "activity_date": "2026-09-03",
                "activity_type": "전화",
                "activity_note": "조건 안내",
                "stage_after_activity": "방문 예약",
            },
            database_path
        )
        assert act_id > 0
        activities = get_consultation_activities(consultation_id, database_path)
        assert len(activities) >= 1

        # 계약 이력 추가 테스트
        c_act_id = add_contract_activity(
            contract_id,
            {
                "activity_date": "2026-09-03",
                "activity_stage": "가계약",
                "activity_note": "가계약금 수령",
                "contract_status_after": "계약 진행",
            },
            database_path
        )
        assert c_act_id > 0


if __name__ == "__main__":
    run()
    print("consultation activity legacy timestamps: PASS")
