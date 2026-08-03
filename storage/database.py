"""SQLite 데이터 저장소 모듈.

화면 코드와 저장 규칙을 분리해, 화면을 고쳐도 매물 이력이 손상되지 않게 한다.
실제 데이터 파일은 사용자가 요청한 대로 프로젝트 최상위 폴더에 둔다.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
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
    has_listing_photos TEXT NOT NULL DEFAULT '확인 필요',
    ad_status TEXT,
    ad_channel_note TEXT,
    listing_note TEXT,
    option_change_note TEXT,
    last_checked_date TEXT,
    next_check_date TEXT,
    verification_note TEXT,
    landlord_contact TEXT,
    tenant_contact TEXT,
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

CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    contract_type TEXT NOT NULL,
    contract_start_date TEXT NOT NULL,
    contract_end_date TEXT,
    term_months INTEGER,
    contract_status TEXT NOT NULL,
    contract_note TEXT,
    contractor_contact TEXT,
    contract_deposit_manwon INTEGER,
    balance_manwon INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER IF NOT EXISTS contracts_set_updated_at
AFTER UPDATE ON contracts
FOR EACH ROW
BEGIN
    UPDATE contracts SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;

CREATE TABLE IF NOT EXISTS consultations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    consulted_date TEXT NOT NULL,
    consultation_type TEXT NOT NULL,
    consultation_note TEXT NOT NULL,
    next_contact_date TEXT,
    consultation_status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER IF NOT EXISTS consultations_set_updated_at
AFTER UPDATE ON consultations
FOR EACH ROW
BEGIN
    UPDATE consultations SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
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
            _ensure_listing_photo_column(connection)
            _ensure_listing_contact_columns(connection)
            _ensure_consultation_table(connection)
    finally:
        connection.close()


def _ensure_listing_photo_column(connection: sqlite3.Connection) -> None:
    """기존 데이터 파일에도 사진 보유 여부 칸을 안전하게 추가한다."""
    columns = {row[1] for row in connection.execute("PRAGMA table_info(listings)").fetchall()}
    if "has_listing_photos" not in columns:
        connection.execute(
            "ALTER TABLE listings ADD COLUMN has_listing_photos TEXT NOT NULL DEFAULT '확인 필요'"
        )


def _ensure_listing_contact_columns(connection: sqlite3.Connection) -> None:
    """기존 데이터 파일에도 매물 회차별 임대인·세입자 연락처 칸을 추가한다."""
    columns = {row[1] for row in connection.execute("PRAGMA table_info(listings)").fetchall()}
    for column in ("landlord_contact", "tenant_contact"):
        if column not in columns:
            connection.execute(f"ALTER TABLE listings ADD COLUMN {column} TEXT")


def ensure_database_schema(path: Path = DATABASE_PATH) -> None:
    """이미 존재하는 데이터 파일에 필요한 추가 칸만 만든다. 기존 기록은 바꾸지 않는다."""
    require_database(path)
    connection = get_connection(path)
    try:
        with connection:
            _ensure_listing_photo_column(connection)
            _ensure_listing_contact_columns(connection)
            _ensure_contract_table(connection)
            _ensure_consultation_table(connection)
    finally:
        connection.close()


def _ensure_contract_table(connection: sqlite3.Connection) -> None:
    """기존 데이터 파일에도 계약 기록 표와 수정일 기록 규칙을 안전하게 추가한다."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER NOT NULL REFERENCES listings(id),
            contract_type TEXT NOT NULL,
            contract_start_date TEXT NOT NULL,
            contract_end_date TEXT,
            term_months INTEGER,
            contract_status TEXT NOT NULL,
            contract_note TEXT,
            contractor_contact TEXT,
            contract_deposit_manwon INTEGER,
            balance_manwon INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TRIGGER IF NOT EXISTS contracts_set_updated_at
        AFTER UPDATE ON contracts
        FOR EACH ROW
        BEGIN
            UPDATE contracts SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
        """
    )
    columns = {row[1] for row in connection.execute("PRAGMA table_info(contracts)").fetchall()}
    for column, column_type in (
        ("contractor_contact", "TEXT"),
        ("contract_deposit_manwon", "INTEGER"),
        ("balance_manwon", "INTEGER"),
    ):
        if column not in columns:
            connection.execute(f"ALTER TABLE contracts ADD COLUMN {column} {column_type}")


def _ensure_consultation_table(connection: sqlite3.Connection) -> None:
    """기존 데이터 파일에도 상담 기록 표를 추가한다."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS consultations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER NOT NULL REFERENCES listings(id),
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            consulted_date TEXT NOT NULL,
            consultation_type TEXT NOT NULL,
            consultation_note TEXT NOT NULL,
            next_contact_date TEXT,
            consultation_status TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TRIGGER IF NOT EXISTS consultations_set_updated_at
        AFTER UPDATE ON consultations
        FOR EACH ROW
        BEGIN
            UPDATE consultations SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
        """
    )


def require_database(path: Path = DATABASE_PATH) -> None:
    """잘못된 경로에서 새 빈 파일을 조용히 만들지 않도록 확인한다."""
    if not path.exists():
        raise FileNotFoundError(
            f"데이터 파일을 찾을 수 없습니다: {path}. "
            "경로를 확인하거나 관리자에게 문의하세요."
        )


def get_database_summary(path: Path = DATABASE_PATH) -> dict[str, int]:
    """첫 화면에서 사용할 안전한 건수만 돌려준다."""
    ensure_database_schema(path)
    connection = get_connection(path)
    try:
        return {
            "buildings": connection.execute("SELECT COUNT(*) FROM buildings").fetchone()[0],
            "units": connection.execute("SELECT COUNT(*) FROM units").fetchone()[0],
            "listings": connection.execute("SELECT COUNT(*) FROM listings").fetchone()[0],
        }
    finally:
        connection.close()


def get_current_listings(
    *,
    query: str = "",
    received_start: str | None = None,
    received_end: str | None = None,
    statuses: list[str] | None = None,
    room_types: list[str] | None = None,
    photo_statuses: list[str] | None = None,
    photo_availability: list[str] | None = None,
    task_filter: str | None = None,
    path: Path = DATABASE_PATH,
) -> list[dict[str, Any]]:
    """오늘의 현황에 표시할 현재 매물을 조건에 맞게 찾는다. 내부정보는 제외한다."""
    ensure_database_schema(path)
    conditions = ["l.closed_date IS NULL", "l.listing_status NOT IN ('계약 완료', '종료')", "u.is_active = 1", "b.is_active = 1"]
    parameters: list[Any] = []
    if keyword := query.strip():
        conditions.append("(b.building_name LIKE ? OR b.lot_address LIKE ? OR u.unit_number LIKE ? OR u.unit_number_normalized LIKE ?)")
        parameters.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
    if received_start:
        conditions.append("l.received_date >= ?")
        parameters.append(received_start)
    if received_end:
        conditions.append("l.received_date <= ?")
        parameters.append(received_end)
    for column, values in (("l.listing_status", statuses), ("u.room_type", room_types), ("l.photo_status", photo_statuses), ("l.has_listing_photos", photo_availability)):
        if values:
            placeholders = ", ".join("?" for _ in values)
            conditions.append(f"{column} IN ({placeholders})")
            parameters.extend(values)

    connection = get_connection(path)
    try:
        rows = connection.execute(
            f"""
            SELECT l.id AS listing_id, u.id AS unit_id, b.building_name, b.lot_address, u.unit_number,
                   u.room_type, l.received_date, l.listing_status, l.deposit_manwon, l.monthly_rent_manwon,
                   l.management_fee_manwon, l.availability_type, l.available_from_date, l.photo_status,
                   l.has_listing_photos, l.cleaning_status, l.wallpaper_status, l.repair_status,
                   l.next_check_date, l.listing_note, l.updated_at
            FROM listings l
            JOIN units u ON u.id = l.unit_id
            JOIN buildings b ON b.id = u.building_id
            WHERE {' AND '.join(conditions)}
            ORDER BY l.received_date DESC, l.updated_at DESC, l.id DESC
            """,
            parameters,
        ).fetchall()
        listings = [dict(row) for row in rows]
    finally:
        connection.close()

    today = date.today().isoformat()
    for listing in listings:
        tasks: list[str] = []
        if listing["next_check_date"] and listing["next_check_date"] <= today:
            tasks.append("재확인 필요")
        if listing["photo_status"] == "촬영 필요" or listing["has_listing_photos"] == "없음":
            tasks.append("사진 촬영 필요")
        if any(listing[field] in ("필요", "진행 중") for field in ("cleaning_status", "wallpaper_status", "repair_status")):
            tasks.append("현장 상태 확인 필요")
        if listing["availability_type"] == "확인 필요":
            tasks.append("입주 가능일 확인 필요")
        if listing["listing_status"] == "확인 필요":
            tasks.append("매물 상태 확인 필요")
        listing["tasks"] = tasks
    if task_filter:
        listings = [listing for listing in listings if task_filter in listing["tasks"]]
    return listings


def get_current_listing_export_rows(
    listing_ids: list[int], path: Path = DATABASE_PATH
) -> list[dict[str, Any]]:
    """선택된 현재 매물의 내부 업무용 엑셀 항목을 읽는다.

    개인 연락처는 어떤 표에도 넣지 않는다. 현재 데이터 구조에는 연락처 칸이 없으며,
    이후 상담관리 표가 추가돼도 이 함수와 엑셀 내보내기에는 연결하지 않는다.
    """
    if not listing_ids:
        return []
    ensure_database_schema(path)
    placeholders = ", ".join("?" for _ in listing_ids)
    connection = get_connection(path)
    try:
        rows = connection.execute(
            f"""
            SELECT l.id AS listing_id, l.received_date, l.listing_status, l.deposit_manwon,
                   l.monthly_rent_manwon, l.management_fee_manwon, l.management_fee_note,
                   l.availability_type, l.available_from_date, l.move_out_due_date,
                   l.lease_term_note, l.short_term_note, l.cleaning_status, l.wallpaper_status,
                   l.repair_status, l.photo_status, l.has_listing_photos, l.ad_status,
                   l.ad_channel_note, l.listing_note, l.option_change_note, l.last_checked_date,
                   l.next_check_date, l.verification_note,
                   b.building_name, b.lot_address, b.admin_address, b.road_address,
                   b.common_entrance_password, b.has_elevator, b.parking_status, b.has_cctv,
                   b.pet_policy, b.move_in_registration_policy, b.short_term_policy,
                   b.common_fee_note, b.building_highlights, b.internal_note AS building_internal_note,
                   u.unit_number, u.floor_number, u.room_type, u.is_separated, u.direction,
                   u.area_status, u.exclusive_area_m2, u.has_balcony, u.has_built_in_closet,
                   u.has_double_window, u.storage_status, u.system_aircon_count, u.unit_options,
                   u.unit_highlights, u.unit_cautions, u.internal_note AS unit_internal_note,
                   u.access_method, u.unit_access_password, u.last_photo_date
            FROM listings l
            JOIN units u ON u.id = l.unit_id
            JOIN buildings b ON b.id = u.building_id
            WHERE l.id IN ({placeholders})
              AND l.closed_date IS NULL
              AND l.listing_status NOT IN ('계약 완료', '종료')
              AND u.is_active = 1 AND b.is_active = 1
            ORDER BY l.received_date DESC, l.updated_at DESC, l.id DESC
            """,
            listing_ids,
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def search_listing_rounds(query: str, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    """계약을 연결할 과거·현재 매물 회차를 건물명·지번·호수로 찾는다."""
    ensure_database_schema(path)
    keyword = query.strip()
    if not keyword:
        return []
    connection = get_connection(path)
    try:
        rows = connection.execute(
            """
            SELECT l.id AS listing_id, l.received_date, l.listing_status, l.closed_date,
                   b.building_name, b.lot_address, u.unit_number, u.room_type
            FROM listings l
            JOIN units u ON u.id = l.unit_id
            JOIN buildings b ON b.id = u.building_id
            WHERE b.is_active = 1 AND u.is_active = 1
              AND (b.building_name LIKE ? OR b.lot_address LIKE ?
                   OR u.unit_number LIKE ? OR u.unit_number_normalized LIKE ?)
            ORDER BY l.received_date DESC, l.id DESC
            LIMIT 50
            """,
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_contracts(
    *,
    query: str = "",
    statuses: list[str] | None = None,
    end_start: str | None = None,
    end_end: str | None = None,
    expiring_within_days: int | None = None,
    unit_id: int | None = None,
    path: Path = DATABASE_PATH,
) -> list[dict[str, Any]]:
    """계약 목록을 매물 회차 정보와 함께 읽는다. 계약자 개인정보는 읽지 않는다."""
    ensure_database_schema(path)
    conditions = ["b.is_active = 1", "u.is_active = 1"]
    parameters: list[Any] = []
    if keyword := query.strip():
        conditions.append("(b.building_name LIKE ? OR b.lot_address LIKE ? OR u.unit_number LIKE ?)")
        parameters.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
    if statuses:
        placeholders = ", ".join("?" for _ in statuses)
        conditions.append(f"c.contract_status IN ({placeholders})")
        parameters.extend(statuses)
    if end_start:
        conditions.append("c.contract_end_date >= ?")
        parameters.append(end_start)
    if end_end:
        conditions.append("c.contract_end_date <= ?")
        parameters.append(end_end)
    if expiring_within_days is not None:
        if expiring_within_days < 0:
            raise ValueError("계약 만료 예정 기간은 0일 이상이어야 합니다.")
        today = date.today()
        deadline = (today + timedelta(days=expiring_within_days)).isoformat()
        conditions.extend([
            "c.contract_end_date IS NOT NULL",
            "c.contract_end_date >= ?",
            "c.contract_end_date <= ?",
            "c.contract_status NOT IN ('해지', '만료')",
        ])
        parameters.extend([today.isoformat(), deadline])
    if unit_id is not None:
        conditions.append("u.id = ?")
        parameters.append(unit_id)
    connection = get_connection(path)
    try:
        rows = connection.execute(
            f"""
            SELECT c.id AS contract_id, c.listing_id, c.contract_type, c.contract_start_date,
                   c.contract_end_date, c.term_months, c.contract_status, c.contract_note,
                   c.contractor_contact, c.contract_deposit_manwon, c.balance_manwon,
                   c.created_at, c.updated_at, b.building_name, b.lot_address, u.unit_number,
                   l.received_date, l.listing_status
            FROM contracts c
            JOIN listings l ON l.id = c.listing_id
            JOIN units u ON u.id = l.unit_id
            JOIN buildings b ON b.id = u.building_id
            WHERE {' AND '.join(conditions)}
            ORDER BY c.contract_start_date DESC, c.id DESC
            """,
            parameters,
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_unit_contracts(unit_id: int, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    """건물·호실 관리 화면에서 보여 줄 호실별 계약 이력이다. 수정은 하지 않는다."""
    return get_contracts(unit_id=unit_id, path=path)


def create_contract(listing_id: int, contract: dict[str, Any], path: Path = DATABASE_PATH) -> int:
    """선택한 매물 회차에 새 계약 기록을 추가한다. 기존 계약은 바꾸지 않는다."""
    ensure_database_schema(path)
    connection = get_connection(path)
    try:
        with connection:
            if connection.execute("SELECT 1 FROM listings WHERE id = ?", (listing_id,)).fetchone() is None:
                raise ValueError("연결할 매물 기록을 찾을 수 없습니다. 다시 선택해 주세요.")
            cursor = connection.execute(
                """
                INSERT INTO contracts (
                    listing_id, contract_type, contract_start_date, contract_end_date,
                    term_months, contract_status, contract_note, contractor_contact,
                    contract_deposit_manwon, balance_manwon
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    listing_id, contract["contract_type"], contract["contract_start_date"],
                    contract.get("contract_end_date"), contract.get("term_months"),
                    contract["contract_status"], contract.get("contract_note"), contract.get("contractor_contact"),
                    contract.get("contract_deposit_manwon"), contract.get("balance_manwon"),
                ),
            )
            return cursor.lastrowid
    finally:
        connection.close()


def update_contract_status(contract_id: int, contract_status: str, path: Path = DATABASE_PATH) -> None:
    """계약을 지우지 않고 상태만 바꿔 해지·만료 이력을 보존한다."""
    if not contract_status:
        raise ValueError("계약 상태를 선택해 주세요.")
    ensure_database_schema(path)
    connection = get_connection(path)
    try:
        with connection:
            if connection.execute("UPDATE contracts SET contract_status = ? WHERE id = ?", (contract_status, contract_id)).rowcount != 1:
                raise ValueError("수정할 계약 기록을 찾을 수 없습니다.")
    finally:
        connection.close()


def update_contract_details(contract_id: int, values: dict[str, Any], path: Path = DATABASE_PATH) -> None:
    """계약 기록을 지우지 않고 상태·연락처·계약금·잔금만 수정한다."""
    ensure_database_schema(path)
    connection = get_connection(path)
    try:
        with connection:
            if connection.execute(
                """
                UPDATE contracts
                SET contract_status = ?, contractor_contact = ?, contract_deposit_manwon = ?, balance_manwon = ?
                WHERE id = ?
                """,
                (
                    values["contract_status"], values.get("contractor_contact"),
                    values.get("contract_deposit_manwon"), values.get("balance_manwon"), contract_id,
                ),
            ).rowcount != 1:
                raise ValueError("수정할 계약 기록을 찾을 수 없습니다.")
    finally:
        connection.close()


def get_consultations(*, query: str = "", statuses: list[str] | None = None, due_only: bool = False, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    """상담 목록을 읽는다. 고객 연락처는 목록 조회에 포함하지 않는다."""
    ensure_database_schema(path)
    conditions = ["b.is_active = 1", "u.is_active = 1"]
    parameters: list[Any] = []
    if keyword := query.strip():
        conditions.append("(b.building_name LIKE ? OR b.lot_address LIKE ? OR u.unit_number LIKE ? OR c.customer_name LIKE ?)")
        parameters.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
    if statuses:
        placeholders = ", ".join("?" for _ in statuses)
        conditions.append(f"c.consultation_status IN ({placeholders})")
        parameters.extend(statuses)
    if due_only:
        conditions.extend(["c.next_contact_date IS NOT NULL", "c.next_contact_date <= ?", "c.consultation_status != '종료'"])
        parameters.append(date.today().isoformat())
    connection = get_connection(path)
    try:
        rows = connection.execute(
            f"""
            SELECT c.id AS consultation_id, c.listing_id, c.customer_name, c.consulted_date,
                   c.consultation_type, c.consultation_note, c.next_contact_date, c.consultation_status,
                   c.created_at, c.updated_at, b.building_name, b.lot_address, u.unit_number,
                   l.received_date, l.listing_status
            FROM consultations c
            JOIN listings l ON l.id = c.listing_id
            JOIN units u ON u.id = l.unit_id
            JOIN buildings b ON b.id = u.building_id
            WHERE {' AND '.join(conditions)}
            ORDER BY c.consulted_date DESC, c.id DESC
            """, parameters,
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_consultation_detail(consultation_id: int, path: Path = DATABASE_PATH) -> dict[str, Any] | None:
    """상담 상세에서만 고객 연락처를 포함해 읽는다."""
    ensure_database_schema(path)
    connection = get_connection(path)
    try:
        row = connection.execute(
            """
            SELECT c.id AS consultation_id, c.listing_id, c.customer_name, c.customer_phone,
                   c.consulted_date, c.consultation_type, c.consultation_note, c.next_contact_date,
                   c.consultation_status, b.building_name, b.lot_address, u.unit_number, l.received_date
            FROM consultations c
            JOIN listings l ON l.id = c.listing_id
            JOIN units u ON u.id = l.unit_id
            JOIN buildings b ON b.id = u.building_id
            WHERE c.id = ? AND b.is_active = 1 AND u.is_active = 1
            """, (consultation_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def create_consultation(listing_id: int, consultation: dict[str, Any], path: Path = DATABASE_PATH) -> int:
    """선택한 매물 회차에 새 상담 기록을 추가한다."""
    ensure_database_schema(path)
    connection = get_connection(path)
    try:
        with connection:
            if connection.execute("SELECT 1 FROM listings WHERE id = ?", (listing_id,)).fetchone() is None:
                raise ValueError("연결할 매물 기록을 찾을 수 없습니다. 다시 선택해 주세요.")
            cursor = connection.execute(
                """
                INSERT INTO consultations (listing_id, customer_name, customer_phone, consulted_date, consultation_type, consultation_note, next_contact_date, consultation_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (listing_id, consultation["customer_name"], consultation["customer_phone"], consultation["consulted_date"], consultation["consultation_type"], consultation["consultation_note"], consultation.get("next_contact_date"), consultation["consultation_status"]),
            )
            return cursor.lastrowid
    finally:
        connection.close()


def update_consultation(consultation_id: int, values: dict[str, Any], path: Path = DATABASE_PATH) -> None:
    """상담 기록을 지우지 않고 상세값을 수정한다."""
    ensure_database_schema(path)
    connection = get_connection(path)
    try:
        with connection:
            if connection.execute(
                """
                UPDATE consultations
                SET customer_name = ?, customer_phone = ?, consultation_note = ?, next_contact_date = ?, consultation_status = ?
                WHERE id = ?
                """,
                (values["customer_name"], values["customer_phone"], values["consultation_note"], values.get("next_contact_date"), values["consultation_status"], consultation_id),
            ).rowcount != 1:
                raise ValueError("수정할 상담 기록을 찾을 수 없습니다.")
    finally:
        connection.close()


def update_listing_quick_fields(
    listing_id: int,
    listing_status: str,
    photo_status: str,
    has_listing_photos: str,
    next_check_date: str | None,
    path: Path = DATABASE_PATH,
) -> None:
    """오늘의 현황에서 자주 바꾸는 값만 현재 매물 회차에 저장한다."""
    ensure_database_schema(path)
    connection = get_connection(path)
    try:
        with connection:
            if connection.execute(
                "SELECT 1 FROM listings WHERE id = ? AND closed_date IS NULL", (listing_id,)
            ).fetchone() is None:
                raise ValueError("수정할 현재 매물을 찾을 수 없습니다.")
            connection.execute(
                """
                UPDATE listings
                SET listing_status = ?, photo_status = ?, has_listing_photos = ?, next_check_date = ?
                WHERE id = ?
                """,
                (listing_status, photo_status, has_listing_photos, next_check_date, listing_id),
            )
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


def get_building_management_detail(building_id: int, path: Path = DATABASE_PATH) -> dict[str, Any] | None:
    """건물 관리 화면용 공통정보를 읽는다. 비밀번호는 제외한다."""
    require_database(path)
    connection = get_connection(path)
    try:
        row = connection.execute(
            """
            SELECT id, building_name, lot_address, admin_address, road_address, has_elevator,
                   parking_status, has_cctv, pet_policy, move_in_registration_policy,
                   short_term_policy, common_fee_note, building_highlights, info_status,
                   last_checked_date, next_check_date
            FROM buildings WHERE id = ? AND is_active = 1
            """,
            (building_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_building_password(building_id: int, path: Path = DATABASE_PATH) -> str | None:
    """명시적으로 요청했을 때만 공동현관 비밀번호를 읽는다."""
    require_database(path)
    connection = get_connection(path)
    try:
        row = connection.execute(
            "SELECT common_entrance_password FROM buildings WHERE id = ? AND is_active = 1", (building_id,)
        ).fetchone()
        return row[0] if row else None
    finally:
        connection.close()


def update_building_management_detail(building_id: int, values: dict[str, Any], path: Path = DATABASE_PATH) -> None:
    """건물 공통정보만 수정한다."""
    require_database(path)
    connection = get_connection(path)
    try:
        with connection:
            if connection.execute("SELECT 1 FROM buildings WHERE id = ? AND is_active = 1", (building_id,)).fetchone() is None:
                raise ValueError("수정할 건물을 찾을 수 없습니다.")
            connection.execute(
                """
                UPDATE buildings SET admin_address = COALESCE(?, admin_address), road_address = COALESCE(?, road_address),
                    has_elevator = COALESCE(?, has_elevator), parking_status = COALESCE(?, parking_status),
                    has_cctv = COALESCE(?, has_cctv), pet_policy = COALESCE(?, pet_policy),
                    move_in_registration_policy = COALESCE(?, move_in_registration_policy), short_term_policy = COALESCE(?, short_term_policy),
                    common_fee_note = COALESCE(?, common_fee_note), building_highlights = COALESCE(?, building_highlights),
                    info_status = COALESCE(?, info_status), next_check_date = COALESCE(?, next_check_date),
                    common_entrance_password = CASE
                        WHEN ? THEN NULL
                        ELSE COALESCE(?, common_entrance_password)
                    END
                WHERE id = ?
                """,
                (
                    values.get("admin_address"), values.get("road_address"), values.get("has_elevator"),
                    values.get("parking_status"), values.get("has_cctv"), values.get("pet_policy"),
                    values.get("move_in_registration_policy"), values.get("short_term_policy"),
                    values.get("common_fee_note"), values.get("building_highlights"), values.get("info_status"),
                    values.get("next_check_date"), values.get("clear_common_entrance_password", False),
                    values.get("common_entrance_password"), building_id,
                ),
            )
    finally:
        connection.close()


def get_unit_management_detail(unit_id: int, path: Path = DATABASE_PATH) -> dict[str, Any] | None:
    """호실 관리 화면용 고정정보를 읽는다. 방문 비밀번호는 제외한다."""
    require_database(path)
    connection = get_connection(path)
    try:
        row = connection.execute(
            """
            SELECT id, building_id, unit_number, floor_number, room_type, direction, unit_options,
                   unit_highlights, unit_cautions, access_method, last_photo_date
            FROM units WHERE id = ? AND is_active = 1
            """,
            (unit_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_unit_password(unit_id: int, path: Path = DATABASE_PATH) -> str | None:
    """명시적으로 요청했을 때만 방문 비밀번호를 읽는다."""
    require_database(path)
    connection = get_connection(path)
    try:
        row = connection.execute(
            "SELECT unit_access_password FROM units WHERE id = ? AND is_active = 1", (unit_id,)
        ).fetchone()
        return row[0] if row else None
    finally:
        connection.close()


def update_unit_management_detail(unit_id: int, values: dict[str, Any], path: Path = DATABASE_PATH) -> None:
    """호실의 고정정보만 수정한다."""
    require_database(path)
    connection = get_connection(path)
    try:
        with connection:
            if connection.execute("SELECT 1 FROM units WHERE id = ? AND is_active = 1", (unit_id,)).fetchone() is None:
                raise ValueError("수정할 호실을 찾을 수 없습니다.")
            connection.execute(
                """
                UPDATE units SET floor_number = COALESCE(?, floor_number), room_type = COALESCE(?, room_type),
                    direction = COALESCE(?, direction), unit_options = COALESCE(?, unit_options),
                    unit_highlights = COALESCE(?, unit_highlights), unit_cautions = COALESCE(?, unit_cautions),
                    access_method = COALESCE(?, access_method),
                    unit_access_password = CASE
                        WHEN ? THEN NULL
                        ELSE COALESCE(?, unit_access_password)
                    END
                WHERE id = ?
                """,
                (
                    values.get("floor_number"), values.get("room_type"), values.get("direction"),
                    values.get("unit_options"), values.get("unit_highlights"), values.get("unit_cautions"),
                    values.get("access_method"), values.get("clear_unit_access_password", False),
                    values.get("unit_access_password"), unit_id,
                ),
            )
    finally:
        connection.close()


def update_current_listing_option_note(unit_id: int, option_change_note: str | None, path: Path = DATABASE_PATH) -> None:
    """이번 매물에만 다른 옵션은 호실 기본정보 대신 현재 매물 회차에 남긴다."""
    require_database(path)
    connection = get_connection(path)
    try:
        with connection:
            row = connection.execute(
                """
                SELECT id FROM listings WHERE unit_id = ? AND closed_date IS NULL
                  AND listing_status NOT IN ('계약 완료', '종료')
                ORDER BY received_date DESC, id DESC LIMIT 1
                """,
                (unit_id,),
            ).fetchone()
            if row is None:
                raise ValueError("현재 운영 중인 매물이 없습니다.")
            connection.execute("UPDATE listings SET option_change_note = ? WHERE id = ?", (option_change_note, row[0]))
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
                   management_fee_manwon, availability_type, available_from_date, closed_date,
                   close_reason, option_change_note
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
    ensure_database_schema(path)
    connection = get_connection(path)
    try:
        row = connection.execute(
            """
            SELECT id, unit_id, received_date, listing_status, deposit_manwon, monthly_rent_manwon,
                   management_fee_manwon, availability_type, available_from_date, move_out_due_date,
                   photo_status, listing_note, next_check_date, landlord_contact, tenant_contact
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
                    listing_note = ?, next_check_date = ?, landlord_contact = ?, tenant_contact = ?
                WHERE id = ?
                """,
                (
                    listing["listing_status"], listing["deposit_manwon"], listing["monthly_rent_manwon"],
                    listing.get("management_fee_manwon"), listing["availability_type"],
                    listing.get("available_from_date"), listing.get("move_out_due_date"), listing.get("photo_status"),
                    listing.get("listing_note"), listing.get("next_check_date"),
                    listing.get("landlord_contact"), listing.get("tenant_contact"), listing_id,
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
                    photo_status, listing_note, next_check_date, landlord_contact, tenant_contact
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    listing.get("next_check_date"), listing.get("landlord_contact"), listing.get("tenant_contact"),
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
                    photo_status, listing_note, next_check_date, landlord_contact, tenant_contact
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    unit_id, listing.get("received_date", date.today().isoformat()), listing["listing_status"],
                    listing["deposit_manwon"], listing["monthly_rent_manwon"], listing.get("management_fee_manwon"),
                    listing["availability_type"], listing.get("available_from_date"), listing.get("move_out_due_date"),
                    listing.get("photo_status"), listing.get("listing_note"), listing.get("next_check_date"),
                    listing.get("landlord_contact"), listing.get("tenant_contact"),
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
                    photo_status, listing_note, next_check_date, verification_note, landlord_contact, tenant_contact
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    unit_id, listing.get("received_date", date.today().isoformat()), listing["listing_status"],
                    listing.get("deposit_manwon"), listing.get("monthly_rent_manwon"), listing.get("management_fee_manwon"),
                    listing["availability_type"], listing.get("available_from_date"), listing.get("move_out_due_date"),
                    listing.get("photo_status"), listing.get("listing_note"), listing.get("next_check_date"),
                    listing.get("verification_note"), listing.get("landlord_contact"), listing.get("tenant_contact"),
                ),
            )
            return cursor.lastrowid
    finally:
        connection.close()
