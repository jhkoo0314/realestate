"""퇴실 예정일 경과 시 현재 매물 자동 정리 규칙 확인."""

from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from storage.database import get_connection, initialize_database
from storage.listing_repository import mark_past_due_move_out_listings_vacant


def _add_listing(connection, *, status: str, availability: str, move_out_due: str | None) -> int:
    building_id = connection.execute(
        "INSERT INTO buildings (building_name, lot_address) VALUES (?, ?)",
        ("자동전환 확인", f"북수리 {1000 + connection.total_changes}"),
    ).lastrowid
    unit_id = connection.execute(
        "INSERT INTO units (building_id, unit_number, unit_number_normalized) VALUES (?, ?, ?)",
        (building_id, "101", "101"),
    ).lastrowid
    return connection.execute(
        """INSERT INTO listings
           (unit_id, received_date, listing_status, availability_type, move_out_due_date)
           VALUES (?, ?, ?, ?, ?)""",
        (unit_id, "2026-08-20", status, availability, move_out_due),
    ).lastrowid


def run() -> None:
    with tempfile.TemporaryDirectory() as directory:
        database_path = Path(directory) / "listing_status.db"
        initialize_database(database_path)
        connection = get_connection(database_path)
        try:
            due_listing_id = _add_listing(
                connection,
                status="퇴실 예정",
                availability="퇴실 후 협의",
                move_out_due="2026-08-23",
            )
            legacy_listing_id = _add_listing(
                connection,
                status="공실",
                availability="퇴실 후 협의",
                move_out_due="2026-08-23",
            )
            today_listing_id = _add_listing(
                connection,
                status="퇴실 예정",
                availability="퇴실 후 협의",
                move_out_due="2026-08-24",
            )
            connection.commit()
        finally:
            connection.close()

        assert mark_past_due_move_out_listings_vacant(date(2026, 8, 24), database_path) == 2
        connection = get_connection(database_path)
        try:
            for listing_id in (due_listing_id, legacy_listing_id):
                row = connection.execute(
                    "SELECT listing_status, availability_type, move_out_due_date FROM listings WHERE id=?",
                    (listing_id,),
                ).fetchone()
                assert tuple(row) == ("공실", "즉시입주", None)
            today_row = connection.execute(
                "SELECT listing_status, availability_type, move_out_due_date FROM listings WHERE id=?",
                (today_listing_id,),
            ).fetchone()
            assert tuple(today_row) == ("퇴실 예정", "퇴실 후 협의", "2026-08-24")
        finally:
            connection.close()


if __name__ == "__main__":
    run()
    print("listing status transition: PASS")
