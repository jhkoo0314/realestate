"""SQLite 데이터 저장소 모듈.

화면 코드와 저장 규칙을 분리해, 화면을 고쳐도 매물 이력이 손상되지 않게 한다.
실제 데이터 파일은 사용자가 요청한 대로 프로젝트 최상위 폴더에 둔다.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any


# 데이터 파일은 저장 기능 코드와 함께 storage 폴더에서 관리한다.
DATABASE_PATH = Path(__file__).resolve().with_name("real_estate.db")


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


def search_buildings(query: str, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    """건물명 또는 지번으로 기존 건물을 찾는다. 내부정보는 돌려주지 않는다."""
    require_database(path)
    keyword = query.strip()
    if not keyword:
        return []

    connection = get_connection(path)
    try:
        rows = connection.execute(
            """
            SELECT b.id, b.building_name, b.lot_address, b.admin_address, b.road_address,
                   b.has_elevator, b.parking_status, COUNT(u.id) AS unit_count
            FROM buildings b
            LEFT JOIN units u ON u.building_id = b.id AND u.is_active = 1
            WHERE b.is_active = 1
              AND (b.building_name LIKE ? OR b.lot_address LIKE ?)
            GROUP BY b.id
            ORDER BY b.building_name, b.lot_address
            """,
            (f"%{keyword}%", f"%{keyword}%"),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def find_building_by_identity(
    building_name: str, lot_address: str, path: Path = DATABASE_PATH
) -> dict[str, Any] | None:
    """건물명과 지번이 모두 같은 기존 건물을 찾는다."""
    require_database(path)
    connection = get_connection(path)
    try:
        row = connection.execute(
            """
            SELECT id, building_name, lot_address
            FROM buildings
            WHERE building_name = ? AND lot_address = ? AND is_active = 1
            """,
            (building_name.strip(), lot_address.strip()),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_building_units(building_id: int, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    """선택한 건물의 등록 호실을 보여 준다. 비밀번호·내부 메모는 제외한다."""
    require_database(path)
    connection = get_connection(path)
    try:
        rows = connection.execute(
            """
            SELECT u.id, u.unit_number, u.room_type, u.floor_number, u.direction,
                   l.deposit_manwon, l.monthly_rent_manwon, l.listing_status, l.received_date
            FROM units u
            LEFT JOIN listings l ON l.id = (
                SELECT id FROM listings WHERE unit_id = u.id ORDER BY received_date DESC, id DESC LIMIT 1
            )
            WHERE u.building_id = ? AND u.is_active = 1
            ORDER BY unit_number_normalized
            """,
            (building_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_unit_relisting_context(unit_id: int, path: Path = DATABASE_PATH) -> dict[str, Any] | None:
    """재등록 화면에 필요한 고정정보를 읽는다. 비밀번호와 내부 메모는 제외한다."""
    require_database(path)
    connection = get_connection(path)
    try:
        row = connection.execute(
            """
            SELECT u.id AS unit_id, u.unit_number, u.floor_number, u.room_type, u.direction,
                   u.unit_options, u.access_method, u.unit_highlights,
                   b.id AS building_id, b.building_name, b.lot_address, b.admin_address,
                   b.road_address, b.has_elevator, b.parking_status
            FROM units u JOIN buildings b ON b.id = u.building_id
            WHERE u.id = ? AND u.is_active = 1 AND b.is_active = 1
            """,
            (unit_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_unit_listing_history(unit_id: int, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    """한 호실의 이전 매물 기록을 최신순으로 읽는다."""
    require_database(path)
    connection = get_connection(path)
    try:
        rows = connection.execute(
            """
            SELECT id, received_date, listing_status, deposit_manwon, monthly_rent_manwon,
                   management_fee_manwon, availability_type, available_from_date, closed_date
            FROM listings WHERE unit_id = ?
            ORDER BY received_date DESC, id DESC
            """,
            (unit_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def has_active_listing(unit_id: int, path: Path = DATABASE_PATH) -> bool:
    """종료되지 않은 최근 매물이 있는지 확인한다."""
    require_database(path)
    connection = get_connection(path)
    try:
        return connection.execute(
            """
            SELECT 1 FROM listings
            WHERE unit_id = ? AND closed_date IS NULL
              AND listing_status NOT IN ('계약 완료', '종료')
            LIMIT 1
            """,
            (unit_id,),
        ).fetchone() is not None
    finally:
        connection.close()


def get_current_listing(unit_id: int, path: Path = DATABASE_PATH) -> dict[str, Any] | None:
    """수정할 현재 매물 회차를 최신 활성 기록으로 찾는다."""
    require_database(path)
    connection = get_connection(path)
    try:
        row = connection.execute(
            """
            SELECT id, unit_id, received_date, listing_status, deposit_manwon, monthly_rent_manwon,
                   management_fee_manwon, availability_type, available_from_date, move_out_due_date,
                   photo_status, listing_note, next_check_date
            FROM listings
            WHERE unit_id = ? AND closed_date IS NULL
              AND listing_status NOT IN ('계약 완료', '종료')
            ORDER BY received_date DESC, id DESC LIMIT 1
            """,
            (unit_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def update_current_listing(
    listing_id: int, listing: dict[str, Any], path: Path = DATABASE_PATH
) -> None:
    """현재 매물 한 회차의 조건만 한 번에 수정한다."""
    require_database(path)
    connection = get_connection(path)
    try:
        with connection:
            row = connection.execute(
                "SELECT unit_id FROM listings WHERE id = ? AND closed_date IS NULL", (listing_id,)
            ).fetchone()
            if row is None:
                raise ValueError("수정할 현재 매물을 찾을 수 없습니다.")
            connection.execute(
                """
                UPDATE listings SET
                    listing_status = ?, deposit_manwon = ?, monthly_rent_manwon = ?, management_fee_manwon = ?,
                    availability_type = ?, available_from_date = ?, move_out_due_date = ?, photo_status = ?,
                    listing_note = ?, next_check_date = ?
                WHERE id = ?
                """,
                (
                    listing["listing_status"], listing["deposit_manwon"], listing["monthly_rent_manwon"],
                    listing.get("management_fee_manwon"), listing["availability_type"],
                    listing.get("available_from_date"), listing.get("move_out_due_date"), listing.get("photo_status"),
                    listing.get("listing_note"), listing.get("next_check_date"), listing_id,
                ),
            )
            if listing.get("photo_status") == "촬영 완료" and listing.get("last_photo_date"):
                connection.execute(
                    "UPDATE units SET last_photo_date = ? WHERE id = ?",
                    (listing["last_photo_date"], row["unit_id"]),
                )
    finally:
        connection.close()


def close_current_listing(
    listing_id: int, close_date: str, close_reason: str, path: Path = DATABASE_PATH
) -> None:
    """매물 기록을 지우지 않고 종료일과 종료 사유를 남긴다."""
    if not close_reason:
        raise ValueError("종료 사유를 선택해 주세요.")
    require_database(path)
    connection = get_connection(path)
    try:
        with connection:
            row = connection.execute(
                "SELECT id FROM listings WHERE id = ? AND closed_date IS NULL", (listing_id,)
            ).fetchone()
            if row is None:
                raise ValueError("종료할 현재 매물을 찾을 수 없습니다.")
            final_status = "계약 완료" if close_reason == "계약 완료" else "종료"
            connection.execute(
                """
                UPDATE listings SET listing_status = ?, closed_date = ?, close_reason = ? WHERE id = ?
                """,
                (final_status, close_date, close_reason, listing_id),
            )
    finally:
        connection.close()


def deactivate_unit(unit_id: int, path: Path = DATABASE_PATH) -> None:
    """호실을 삭제하지 않고 비활성화한다."""
    require_database(path)
    connection = get_connection(path)
    try:
        with connection:
            if connection.execute("UPDATE units SET is_active = 0 WHERE id = ?", (unit_id,)).rowcount != 1:
                raise ValueError("비활성화할 호실을 찾을 수 없습니다.")
    finally:
        connection.close()


def building_has_unit(building_id: int, unit_number: str, path: Path = DATABASE_PATH) -> bool:
    """302와 302호를 같은 호실로 비교한다."""
    normalized = normalize_unit_number(unit_number)
    if not normalized:
        return False
    require_database(path)
    connection = get_connection(path)
    try:
        return connection.execute(
            """
            SELECT 1 FROM units
            WHERE building_id = ? AND unit_number_normalized = ? AND is_active = 1
            """,
            (building_id, normalized),
        ).fetchone() is not None
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
                    unit_highlights, access_method, unit_access_password
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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


def save_first_listing_for_existing_building(
    building_id: int, unit: dict[str, Any], listing: dict[str, Any], path: Path = DATABASE_PATH
) -> tuple[int, int]:
    """기존 건물에는 새 호실과 첫 매물만 함께 저장한다.

    저장 직전에 다시 중복을 확인해, 화면을 오래 열어 둔 경우에도 같은 호실이
    두 번 만들어지는 일을 막는다.
    """
    required_values = {
        "호수": unit.get("unit_number"),
        "매물 상태": listing.get("listing_status"),
        "입주 가능 유형": listing.get("availability_type"),
    }
    missing = [label for label, value in required_values.items() if not value]
    if missing:
        raise ValueError(f"필수 항목이 비어 있습니다: {', '.join(missing)}")
    for label, value in {"보증금": listing.get("deposit_manwon"), "월세": listing.get("monthly_rent_manwon")}.items():
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
            building = connection.execute(
                "SELECT id FROM buildings WHERE id = ? AND is_active = 1", (building_id,)
            ).fetchone()
            if building is None:
                raise ValueError("선택한 건물을 찾을 수 없습니다. 다시 검색해 주세요.")
            if connection.execute(
                "SELECT 1 FROM units WHERE building_id = ? AND unit_number_normalized = ?",
                (building_id, normalized_unit),
            ).fetchone():
                unit_label = str(unit["unit_number"]).strip()
                if not unit_label.endswith("호"):
                    unit_label = f"{unit_label}호"
                raise ValueError(f"{unit_label}는 이미 등록된 호실입니다. 기존 호실을 선택해 주세요.")

            cursor = connection.execute(
                """
                INSERT INTO units (
                    building_id, unit_number, unit_number_normalized, floor_number, room_type, direction,
                    unit_highlights, access_method, unit_access_password
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    building_id, str(unit["unit_number"]).strip(), normalized_unit, unit.get("floor_number"),
                    unit.get("room_type"), unit.get("direction"), unit.get("unit_highlights"),
                    unit.get("access_method"), unit.get("unit_access_password"),
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
                    unit_id, listing.get("received_date", date.today().isoformat()), listing["listing_status"],
                    listing["deposit_manwon"], listing["monthly_rent_manwon"], listing.get("management_fee_manwon"),
                    listing["availability_type"], listing.get("available_from_date"), listing.get("move_out_due_date"),
                    listing.get("photo_status"), listing.get("listing_note"), listing.get("next_check_date"),
                ),
            )
            return unit_id, cursor.lastrowid
    finally:
        connection.close()


def save_new_listing_round(
    unit_id: int, listing: dict[str, Any], path: Path = DATABASE_PATH
) -> int:
    """기존 호실의 과거 기록을 건드리지 않고 새 매물 회차만 추가한다."""
    required = {"매물 상태": listing.get("listing_status"), "입주 가능 유형": listing.get("availability_type")}
    missing = [label for label, value in required.items() if not value]
    if missing:
        raise ValueError(f"필수 항목이 비어 있습니다: {', '.join(missing)}")
    if listing["availability_type"] == "날짜 지정" and not listing.get("available_from_date"):
        raise ValueError("입주 가능 유형이 날짜 지정이면 입주 가능일이 필요합니다.")

    require_database(path)
    connection = get_connection(path)
    try:
        with connection:
            if connection.execute("SELECT 1 FROM units WHERE id = ? AND is_active = 1", (unit_id,)).fetchone() is None:
                raise ValueError("선택한 호실을 찾을 수 없습니다. 다시 선택해 주세요.")
            cursor = connection.execute(
                """
                INSERT INTO listings (
                    unit_id, received_date, listing_status, deposit_manwon, monthly_rent_manwon,
                    management_fee_manwon, availability_type, available_from_date, move_out_due_date,
                    photo_status, listing_note, next_check_date, verification_note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    unit_id, listing.get("received_date", date.today().isoformat()), listing["listing_status"],
                    listing.get("deposit_manwon"), listing.get("monthly_rent_manwon"), listing.get("management_fee_manwon"),
                    listing["availability_type"], listing.get("available_from_date"), listing.get("move_out_due_date"),
                    listing.get("photo_status"), listing.get("listing_note"), listing.get("next_check_date"),
                    listing.get("verification_note"),
                ),
            )
            return cursor.lastrowid
    finally:
        connection.close()
