"""종료 매물을 다시 공실 등으로 등록 시 매물접수일 업데이트 검증."""

from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from storage.database import get_connection, initialize_database
from storage.listing_write_repository import update_current_listing


def run() -> None:
    with tempfile.TemporaryDirectory() as directory:
        database_path = Path(directory) / "relisting_test.db"
        initialize_database(database_path)
        connection = get_connection(database_path)
        try:
            building_id = connection.execute(
                "INSERT INTO buildings (building_name, lot_address) VALUES (?, ?)",
                ("테스트빌", "북수리 100"),
            ).lastrowid
            unit_id = connection.execute(
                "INSERT INTO units (building_id, unit_number, unit_number_normalized) VALUES (?, ?, ?)",
                (building_id, "301", "301"),
            ).lastrowid
            listing_id = connection.execute(
                """INSERT INTO listings
                   (unit_id, received_date, listing_status, closed_date, close_reason, deposit_manwon, monthly_rent_manwon, availability_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (unit_id, "2025-01-01", "계약 완료", "2025-05-01", "계약 완료", 500, 45, "즉시입주"),
            ).lastrowid
            connection.commit()
        finally:
            connection.close()

        # Update closed listing to vacant with new received date (today's date)
        new_received_date = "2026-09-14"
        update_data = {
            "received_date": new_received_date,
            "listing_status": "공실",
            "deposit_manwon": 500,
            "monthly_rent_manwon": 50,
            "management_fee_manwon": 5,
            "availability_type": "즉시입주",
        }
        update_current_listing(listing_id, update_data, database_path)

        connection = get_connection(database_path)
        try:
            row = connection.execute(
                "SELECT received_date, listing_status, closed_date, close_reason, monthly_rent_manwon FROM listings WHERE id=?",
                (listing_id,),
            ).fetchone()
            assert row["received_date"] == new_received_date, f"Expected {new_received_date}, got {row['received_date']}"
            assert row["listing_status"] == "공실"
            assert row["closed_date"] is None
            assert row["close_reason"] is None
            assert row["monthly_rent_manwon"] == 50
        finally:
            connection.close()


if __name__ == "__main__":
    run()
    print("relisting received date update: PASS")
