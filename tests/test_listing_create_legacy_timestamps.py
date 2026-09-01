"""생성일 기본값이 없는 기존 표에서도 신규 등록이 되는지 확인한다."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from storage.database import get_connection, initialize_database
from storage.listing_create_repository import save_first_listing, save_first_listing_for_existing_building


def _remove_timestamp_defaults(path: Path) -> None:
    connection = get_connection(path)
    try:
        with connection:
            for table in ("listings", "units", "buildings"):
                connection.execute(f"ALTER TABLE {table} RENAME TO {table}_legacy")
            connection.executescript("""
                CREATE TABLE buildings (id INTEGER PRIMARY KEY AUTOINCREMENT, building_name TEXT NOT NULL, lot_address TEXT NOT NULL, common_entrance_password TEXT, has_elevator TEXT, parking_status TEXT, internal_note TEXT, is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)), created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(building_name, lot_address));
                CREATE TABLE units (id INTEGER PRIMARY KEY AUTOINCREMENT, building_id INTEGER NOT NULL REFERENCES buildings(id), unit_number TEXT NOT NULL, unit_number_normalized TEXT NOT NULL, floor_number INTEGER, room_type TEXT, unit_options TEXT, access_method TEXT, unit_access_password TEXT, is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)), created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(building_id, unit_number_normalized));
                CREATE TABLE listings (id INTEGER PRIMARY KEY AUTOINCREMENT, unit_id INTEGER NOT NULL REFERENCES units(id), received_date TEXT NOT NULL, listing_status TEXT NOT NULL, closed_date TEXT, close_reason TEXT, deposit_manwon INTEGER, monthly_rent_manwon INTEGER, management_fee_manwon INTEGER, availability_type TEXT NOT NULL, move_out_due_date TEXT, listing_holder TEXT, listing_note TEXT, last_checked_date TEXT, next_check_date TEXT, landlord_contact TEXT, tenant_contact TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                DROP TABLE listings_legacy;
                DROP TABLE units_legacy;
                DROP TABLE buildings_legacy;
            """)
    finally:
        connection.close()


def _payload(unit_number: str) -> tuple[dict, dict, dict]:
    return (
        {"building_name": "생성일 확인빌", "lot_address": "북수리 9000"},
        {"unit_number": unit_number, "room_type": "원룸"},
        {"listing_status": "공실", "availability_type": "즉시입주", "listing_holder": "개인매물"},
    )


def run() -> None:
    with tempfile.TemporaryDirectory() as directory:
        database_path = Path(directory) / "legacy_timestamps.db"
        initialize_database(database_path)
        _remove_timestamp_defaults(database_path)

        building, unit, listing = _payload("101")
        building_id, unit_id, listing_id = save_first_listing(building, unit, listing, database_path)
        _, second_unit, second_listing = _payload("102")
        second_unit_id, second_listing_id = save_first_listing_for_existing_building(building_id, second_unit, second_listing, database_path)

        connection = get_connection(database_path)
        try:
            assert all(connection.execute(f"SELECT created_at, updated_at FROM {table} WHERE id=?", (record_id,)).fetchone()[0] for table, record_id in (("buildings", building_id), ("units", unit_id), ("units", second_unit_id), ("listings", listing_id), ("listings", second_listing_id)))
        finally:
            connection.close()


if __name__ == "__main__":
    run()
    print("listing create legacy timestamps: PASS")
