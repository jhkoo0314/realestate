"""SQLite 데이터 저장소 모듈.

화면 코드와 저장 규칙을 분리해, 화면을 고쳐도 매물 이력이 손상되지 않게 한다.
실제 데이터 파일은 사용자가 요청한 대로 프로젝트 최상위 폴더에 둔다.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any


DATABASE_PATH = Path(__file__).resolve().parent / "real_estate.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS buildings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_name TEXT NOT NULL,
    lot_address TEXT NOT NULL,
    admin_address TEXT,
    road_address TEXT,
    building_alias_note TEXT,
    common_entrance_password TEXT,
    has_elevator TEXT,
    parking_status TEXT,
    has_cctv TEXT,
    pet_policy TEXT,
    move_in_registration_policy TEXT,
    short_term_policy TEXT,
    common_fee_note TEXT,
    building_highlights TEXT,
    internal_note TEXT,
    info_status TEXT NOT NULL DEFAULT '기본등록',
    last_checked_date TEXT,
    next_check_date TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (building_name, lot_address)
);

CREATE TABLE IF NOT EXISTS units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_id INTEGER NOT NULL REFERENCES buildings(id),
    unit_number TEXT NOT NULL,
    unit_number_normalized TEXT NOT NULL,
    floor_number INTEGER,
    room_type TEXT,
    is_separated TEXT,
    direction TEXT,
    area_status TEXT,
    exclusive_area_m2 REAL,
    has_balcony TEXT,
    has_built_in_closet TEXT,
    has_double_window TEXT,
    storage_status TEXT,
    system_aircon_count INTEGER,
    unit_options TEXT,
    unit_highlights TEXT,
    unit_cautions TEXT,
    internal_note TEXT,
    access_method TEXT,
    unit_access_password TEXT,
    photo_folder_url TEXT,
    last_photo_date TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (building_id, unit_number_normalized)
);

CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id INTEGER NOT NULL REFERENCES units(id),
    received_date TEXT NOT NULL,
    listing_status TEXT NOT NULL,
    closed_date TEXT,
    close_reason TEXT,
    deposit_manwon INTEGER,
    monthly_rent_manwon INTEGER,
    management_fee_manwon INTEGER,
    management_fee_note TEXT,
    availability_type TEXT NOT NULL,
    available_from_date TEXT,
    move_out_due_date TEXT,
    lease_term_note TEXT,
    short_term_note TEXT,
    cleaning_status TEXT,
    wallpaper_status TEXT,
    repair_status TEXT,
    photo_status TEXT,
    ad_status TEXT,
    ad_channel_note TEXT,
    listing_note TEXT,
    option_change_note TEXT,
    last_checked_date TEXT,
    next_check_date TEXT,
    verification_note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER IF NOT EXISTS buildings_set_updated_at
AFTER UPDATE ON buildings
FOR EACH ROW
BEGIN
    UPDATE buildings SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS units_set_updated_at
AFTER UPDATE ON units
FOR EACH ROW
BEGIN
    UPDATE units SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS listings_set_updated_at
AFTER UPDATE ON listings
FOR EACH ROW
BEGIN
    UPDATE listings SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;
"""


def normalize_unit_number(value: str) -> str:
    """302와 302호를 같은 호실로 비교하기 위한 값."""
    return value.strip().replace(" ", "").removesuffix("호")


def get_connection(path: Path = DATABASE_PATH) -> sqlite3.Connection:
    """외래키 규칙을 켠 SQLite 연결을 연다."""
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(path: Path = DATABASE_PATH) -> None:
    """명시적으로 요청됐을 때만 빈 데이터 파일과 표를 만든다."""
    if not path.parent.exists():
        raise FileNotFoundError(f"데이터 폴더를 찾을 수 없습니다: {path.parent}")

    connection = get_connection(path)
    try:
        with connection:
            connection.executescript(SCHEMA)
    finally:
        connection.close()


def require_database(path: Path = DATABASE_PATH) -> None:
    """잘못된 경로에서 새 빈 파일을 조용히 만들지 않도록 확인한다."""
    if not path.exists():
        raise FileNotFoundError(
            f"데이터 파일을 찾을 수 없습니다: {path}. "
            "경로를 확인하거나 관리자에게 문의하세요."
        )


def get_database_summary(path: Path = DATABASE_PATH) -> dict[str, int]:
    """첫 화면에서 사용할 안전한 건수만 돌려준다."""
    require_database(path)
    connection = get_connection(path)
    try:
        return {
            "buildings": connection.execute("SELECT COUNT(*) FROM buildings").fetchone()[0],
            "units": connection.execute("SELECT COUNT(*) FROM units").fetchone()[0],
            "listings": connection.execute("SELECT COUNT(*) FROM listings").fetchone()[0],
        }
    finally:
        connection.close()


def save_first_listing(
    building: dict[str, Any], unit: dict[str, Any], listing: dict[str, Any], path: Path = DATABASE_PATH
) -> tuple[int, int, int]:
    """건물·호실·첫 매물을 한 묶음으로 저장한다.

    화면 입력 검사는 3단계에서 추가한다. 이 함수는 저장 중 문제가 생기면
    세 기록 모두 취소해 건물만 남는 일을 막는다.
    """
    required_values = {
        "건물명": building.get("building_name"),
        "지번": building.get("lot_address"),
        "호수": unit.get("unit_number"),
        "매물 상태": listing.get("listing_status"),
        "입주 가능 유형": listing.get("availability_type"),
    }
    missing = [label for label, value in required_values.items() if not value]
    if missing:
        raise ValueError(f"필수 항목이 비어 있습니다: {', '.join(missing)}")

    for label, value in {
        "보증금": listing.get("deposit_manwon"),
        "월세": listing.get("monthly_rent_manwon"),
    }.items():
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"{label}은 0 이상의 숫자여야 합니다.")

    if listing["availability_type"] == "날짜 지정" and not listing.get("available_from_date"):
        raise ValueError("입주 가능 유형이 날짜 지정이면 입주 가능일이 필요합니다.")

    require_database(path)
    normalized_unit = normalize_unit_number(str(unit["unit_number"]))
    if not normalized_unit:
        raise ValueError("호수를 확인해 주세요.")

    connection = get_connection(path)
    try:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO buildings (
                    building_name, lot_address, admin_address, road_address,
                    common_entrance_password, has_elevator, parking_status, internal_note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    building["building_name"].strip(),
                    building["lot_address"].strip(),
                    building.get("admin_address"),
                    building.get("road_address"),
                    building.get("common_entrance_password"),
                    building.get("has_elevator"),
                    building.get("parking_status"),
                    building.get("internal_note"),
                ),
            )
            building_id = cursor.lastrowid

            cursor = connection.execute(
                """
                INSERT INTO units (
                    building_id, unit_number, unit_number_normalized, floor_number, room_type, direction,
                    unit_highlights, access_method, unit_access_password, photo_folder_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    building_id,
                    str(unit["unit_number"]).strip(),
                    normalized_unit,
                    unit.get("floor_number"),
                    unit.get("room_type"),
                    unit.get("direction"),
                    unit.get("unit_highlights"),
                    unit.get("access_method"),
                    unit.get("unit_access_password"),
                    unit.get("photo_folder_url"),
                ),
            )
            unit_id = cursor.lastrowid

            cursor = connection.execute(
                """
                INSERT INTO listings (
                    unit_id, received_date, listing_status, deposit_manwon, monthly_rent_manwon,
                    management_fee_manwon, availability_type, available_from_date, move_out_due_date,
                    photo_status, listing_note, next_check_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    unit_id,
                    listing.get("received_date", date.today().isoformat()),
                    listing["listing_status"],
                    listing["deposit_manwon"],
                    listing["monthly_rent_manwon"],
                    listing.get("management_fee_manwon"),
                    listing["availability_type"],
                    listing.get("available_from_date"),
                    listing.get("move_out_due_date"),
                    listing.get("photo_status"),
                    listing.get("listing_note"),
                    listing.get("next_check_date"),
                ),
            )
            return building_id, unit_id, cursor.lastrowid
    finally:
        connection.close()
