"""SQLite 공통 연결과 표 구조 관리만 담당한다.

업무별 저장·조회 코드는 각 repository 파일에 둔다.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().with_name("real_estate.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS buildings (id INTEGER PRIMARY KEY AUTOINCREMENT, building_name TEXT NOT NULL, lot_address TEXT NOT NULL, common_entrance_password TEXT, has_elevator TEXT, parking_status TEXT, internal_note TEXT, is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(building_name, lot_address));
CREATE TABLE IF NOT EXISTS units (id INTEGER PRIMARY KEY AUTOINCREMENT, building_id INTEGER NOT NULL REFERENCES buildings(id), unit_number TEXT NOT NULL, unit_number_normalized TEXT NOT NULL, floor_number INTEGER, room_type TEXT, unit_options TEXT, access_method TEXT, unit_access_password TEXT, is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(building_id, unit_number_normalized));
CREATE TABLE IF NOT EXISTS listings (id INTEGER PRIMARY KEY AUTOINCREMENT, unit_id INTEGER NOT NULL REFERENCES units(id), received_date TEXT NOT NULL, listing_status TEXT NOT NULL, closed_date TEXT, close_reason TEXT, deposit_manwon INTEGER, monthly_rent_manwon INTEGER, management_fee_manwon INTEGER, availability_type TEXT NOT NULL, move_out_due_date TEXT, listing_holder TEXT, listing_note TEXT, last_checked_date TEXT, next_check_date TEXT, landlord_contact TEXT, tenant_contact TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS contracts (id INTEGER PRIMARY KEY AUTOINCREMENT, listing_id INTEGER NOT NULL REFERENCES listings(id), source_consultation_id INTEGER REFERENCES consultations(id) ON DELETE SET NULL, contract_type TEXT NOT NULL, brokerage_method TEXT, contract_progress_date TEXT, formal_contract_date TEXT, contract_start_date TEXT, contract_end_date TEXT, term_months INTEGER, contract_status TEXT NOT NULL, contract_note TEXT, contractor_name TEXT, contractor_contact TEXT, contract_deposit_manwon INTEGER, provisional_deposit_manwon INTEGER, remaining_deposit_due_date TEXT, balance_manwon INTEGER, balance_due_date TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS contract_activities (id INTEGER PRIMARY KEY AUTOINCREMENT, contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE, activity_date TEXT NOT NULL, activity_stage TEXT NOT NULL, activity_note TEXT, contract_status_after TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS consultations (id INTEGER PRIMARY KEY AUTOINCREMENT, listing_id INTEGER REFERENCES listings(id), customer_name TEXT NOT NULL, customer_phone TEXT NOT NULL, consulted_date TEXT NOT NULL, consultation_source TEXT, consultation_note TEXT NOT NULL, desired_area TEXT, desired_room_types TEXT, desired_deposit_manwon INTEGER, desired_monthly_rent_manwon INTEGER, desired_available_from_date TEXT, next_contact_date TEXT, consultation_status TEXT NOT NULL, progress_stage TEXT, last_contacted_date TEXT, latest_visit_result TEXT, closed_reason TEXT, required_features_note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS consultation_activities (id INTEGER PRIMARY KEY AUTOINCREMENT, consultation_id INTEGER NOT NULL REFERENCES consultations(id) ON DELETE CASCADE, activity_date TEXT NOT NULL, activity_type TEXT NOT NULL, activity_note TEXT, stage_after_activity TEXT NOT NULL, visit_result TEXT, closed_reason TEXT, next_contact_date TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS monthly_advertising_costs (id INTEGER PRIMARY KEY AUTOINCREMENT, year_month TEXT NOT NULL, advertising_channel TEXT NOT NULL COLLATE NOCASE, monthly_cost_manwon INTEGER NOT NULL, memo TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(year_month, advertising_channel));
CREATE TABLE IF NOT EXISTS today_task_completions (task_key TEXT PRIMARY KEY, completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TRIGGER IF NOT EXISTS buildings_set_updated_at AFTER UPDATE ON buildings FOR EACH ROW BEGIN UPDATE buildings SET updated_at=CURRENT_TIMESTAMP WHERE id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS units_set_updated_at AFTER UPDATE ON units FOR EACH ROW BEGIN UPDATE units SET updated_at=CURRENT_TIMESTAMP WHERE id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS listings_set_updated_at AFTER UPDATE ON listings FOR EACH ROW BEGIN UPDATE listings SET updated_at=CURRENT_TIMESTAMP WHERE id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS contracts_set_updated_at AFTER UPDATE ON contracts FOR EACH ROW BEGIN UPDATE contracts SET updated_at=CURRENT_TIMESTAMP WHERE id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS contract_activities_set_updated_at AFTER UPDATE ON contract_activities FOR EACH ROW BEGIN UPDATE contract_activities SET updated_at=CURRENT_TIMESTAMP WHERE id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS consultations_set_updated_at AFTER UPDATE ON consultations FOR EACH ROW BEGIN UPDATE consultations SET updated_at=CURRENT_TIMESTAMP WHERE id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS consultation_activities_set_updated_at AFTER UPDATE ON consultation_activities FOR EACH ROW BEGIN UPDATE consultation_activities SET updated_at=CURRENT_TIMESTAMP WHERE id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS monthly_advertising_costs_set_updated_at AFTER UPDATE ON monthly_advertising_costs FOR EACH ROW BEGIN UPDATE monthly_advertising_costs SET updated_at=CURRENT_TIMESTAMP WHERE id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS today_task_completions_set_updated_at AFTER UPDATE ON today_task_completions FOR EACH ROW BEGIN UPDATE today_task_completions SET updated_at=CURRENT_TIMESTAMP WHERE task_key=OLD.task_key; END;
"""


def normalize_unit_number(value: str) -> str:
    return value.strip().replace(" ", "").removesuffix("호")


def get_connection(path: Path = DATABASE_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(path: Path = DATABASE_PATH) -> None:
    if not path.parent.exists():
        raise FileNotFoundError(f"데이터 폴더를 찾을 수 없습니다: {path.parent}")
    connection = get_connection(path)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        with connection:
            _cleanup_unused_fields(connection)
            _backup_before_today_task_completion_migration(connection)
            _backup_before_consultation_progress_migration(connection)
            _backup_before_contract_activity_migration(connection)
            _backup_before_contract_consultation_link_migration(connection)
            _replace_listing_advertisements(connection)
            connection.executescript(SCHEMA)
            _ensure_compatibility_columns(connection)
    finally:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.close()


def _ensure_compatibility_columns(connection: sqlite3.Connection) -> None:
    """필드 정리 뒤의 초기 스키마를 보장한다."""
    connection.executescript(SCHEMA)
    return
    contract_info = {row[1]: row for row in connection.execute("PRAGMA table_info(contracts)")}
    if contract_info["contract_start_date"][3] or "contract_progress_date" not in contract_info or "formal_contract_date" not in contract_info:
        connection.execute("DROP TRIGGER IF EXISTS contracts_set_updated_at")
        connection.execute("ALTER TABLE contracts RENAME TO contracts_legacy")
        connection.execute("""CREATE TABLE contracts (id INTEGER PRIMARY KEY AUTOINCREMENT, listing_id INTEGER NOT NULL REFERENCES listings(id), contract_type TEXT NOT NULL, contract_progress_date TEXT, formal_contract_date TEXT, contract_start_date TEXT, contract_end_date TEXT, term_months INTEGER, contract_status TEXT NOT NULL, contract_note TEXT, contractor_contact TEXT, contract_deposit_manwon INTEGER, provisional_deposit_manwon INTEGER, remaining_deposit_due_date TEXT, balance_manwon INTEGER, balance_due_date TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        connection.execute("""INSERT INTO contracts (id, listing_id, contract_type, contract_start_date, contract_end_date, term_months, contract_status, contract_note, contractor_contact, contract_deposit_manwon, balance_manwon, created_at, updated_at) SELECT id, listing_id, contract_type, contract_start_date, contract_end_date, term_months, contract_status, contract_note, contractor_contact, contract_deposit_manwon, balance_manwon, created_at, updated_at FROM contracts_legacy""")
        connection.execute("DROP TABLE contracts_legacy")
    consultation_info = {row[1]: row for row in connection.execute("PRAGMA table_info(consultations)")}
    if consultation_info["listing_id"][3]:
        connection.execute("ALTER TABLE consultations RENAME TO consultations_legacy")
        connection.execute("""CREATE TABLE consultations (id INTEGER PRIMARY KEY AUTOINCREMENT, listing_id INTEGER REFERENCES listings(id), consultation_category TEXT NOT NULL DEFAULT '매물 상담', customer_name TEXT NOT NULL, customer_phone TEXT NOT NULL, consulted_date TEXT NOT NULL, consultation_type TEXT NOT NULL, consultation_note TEXT NOT NULL, desired_area TEXT, desired_room_type TEXT, desired_deposit_manwon INTEGER, desired_monthly_rent_manwon INTEGER, next_contact_date TEXT, consultation_status TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        connection.execute("""INSERT INTO consultations (id, listing_id, consultation_category, customer_name, customer_phone, consulted_date, consultation_type, consultation_note, next_contact_date, consultation_status, created_at, updated_at) SELECT id, listing_id, '매물 상담', customer_name, customer_phone, consulted_date, consultation_type, consultation_note, next_contact_date, consultation_status, created_at, updated_at FROM consultations_legacy""")
        connection.execute("DROP TABLE consultations_legacy")
    additions = {
        "listings": (("has_listing_photos", "TEXT NOT NULL DEFAULT '확인 필요'"), ("landlord_contact", "TEXT"), ("tenant_contact", "TEXT"), ("listing_holder", "TEXT")),
        "contracts": (("contract_progress_date", "TEXT"), ("formal_contract_date", "TEXT"), ("contractor_contact", "TEXT"), ("contract_deposit_manwon", "INTEGER"), ("provisional_deposit_manwon", "INTEGER"), ("remaining_deposit_due_date", "TEXT"), ("balance_manwon", "INTEGER"), ("balance_due_date", "TEXT"), ("brokerage_method", "TEXT"), ("source_consultation_id", "INTEGER REFERENCES consultations(id) ON DELETE SET NULL"), ("contractor_name", "TEXT")),
        "consultations": (("consultation_category", "TEXT NOT NULL DEFAULT '매물 상담'"), ("consultation_source", "TEXT"), ("desired_area", "TEXT"), ("desired_room_type", "TEXT"), ("desired_deposit_manwon", "INTEGER"), ("desired_monthly_rent_manwon", "INTEGER"), ("desired_available_from_date", "TEXT"), ("progress_stage", "TEXT"), ("last_contacted_date", "TEXT"), ("latest_visit_result", "TEXT"), ("closed_reason", "TEXT"), ("desired_room_types", "TEXT"), ("required_features_note", "TEXT")),
    }
    for table, columns in additions.items():
        existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        for name, column_type in columns:
            if name not in existing:
                if table == "contracts" and name == "balance_due_date":
                    _backup_before_balance_due_date_migration(connection)
                if table == "contracts" and name == "brokerage_method":
                    _backup_before_brokerage_method_migration(connection)
                if table == "contracts" and name in {"source_consultation_id", "contractor_name"}:
                    _backup_before_contract_consultation_link_migration(connection)
                if table == "listings" and name == "listing_holder":
                    _backup_before_listing_holder_migration(connection)
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}")
    # 공동중개가 계약 유형으로 잠시 저장된 기록은 의미를 보존해 별도 중개 방식으로 옮긴다.
    connection.execute("UPDATE contracts SET contract_type = '확인 필요', brokerage_method = '공동중개' WHERE contract_type = '공동중개' AND (brokerage_method IS NULL OR TRIM(brokerage_method) = '')")
    connection.executescript(SCHEMA)


def _cleanup_unused_fields(connection: sqlite3.Connection) -> None:
    """불필요한 입력 열을 보존 열만 가진 표로 한 번 안전하게 재생성한다."""
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='listings'").fetchone():
        return
    if "available_from_date" not in {row[1] for row in connection.execute("PRAGMA table_info(listings)")}:
        return
    counts = {name: connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in ("buildings", "units", "listings", "consultations", "contracts", "consultation_activities", "contract_activities")}
    connection.execute("PRAGMA foreign_keys = OFF")
    try:
        connection.executescript("""
        CREATE TABLE buildings_new (id INTEGER PRIMARY KEY AUTOINCREMENT, building_name TEXT NOT NULL, lot_address TEXT NOT NULL, common_entrance_password TEXT, has_elevator TEXT, parking_status TEXT, internal_note TEXT, is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN(0,1)), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(building_name,lot_address));
        CREATE TABLE units_new (id INTEGER PRIMARY KEY AUTOINCREMENT, building_id INTEGER NOT NULL REFERENCES buildings(id), unit_number TEXT NOT NULL, unit_number_normalized TEXT NOT NULL, floor_number INTEGER, room_type TEXT, unit_options TEXT, access_method TEXT, unit_access_password TEXT, is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN(0,1)), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(building_id,unit_number_normalized));
        CREATE TABLE listings_new (id INTEGER PRIMARY KEY AUTOINCREMENT, unit_id INTEGER NOT NULL REFERENCES units(id), received_date TEXT NOT NULL, listing_status TEXT NOT NULL, closed_date TEXT, close_reason TEXT, deposit_manwon INTEGER, monthly_rent_manwon INTEGER, management_fee_manwon INTEGER, availability_type TEXT NOT NULL, move_out_due_date TEXT, listing_holder TEXT, listing_note TEXT, last_checked_date TEXT, next_check_date TEXT, landlord_contact TEXT, tenant_contact TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE consultations_new (id INTEGER PRIMARY KEY AUTOINCREMENT, listing_id INTEGER REFERENCES listings(id), customer_name TEXT NOT NULL, customer_phone TEXT NOT NULL, consulted_date TEXT NOT NULL, consultation_source TEXT, consultation_note TEXT NOT NULL, desired_area TEXT, desired_room_types TEXT, desired_deposit_manwon INTEGER, desired_monthly_rent_manwon INTEGER, desired_available_from_date TEXT, next_contact_date TEXT, consultation_status TEXT NOT NULL, progress_stage TEXT, last_contacted_date TEXT, latest_visit_result TEXT, closed_reason TEXT, required_features_note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE contracts_new (id INTEGER PRIMARY KEY AUTOINCREMENT, listing_id INTEGER NOT NULL REFERENCES listings(id), source_consultation_id INTEGER REFERENCES consultations(id) ON DELETE SET NULL, contract_type TEXT NOT NULL, brokerage_method TEXT, contract_progress_date TEXT, formal_contract_date TEXT, contract_start_date TEXT, contract_end_date TEXT, term_months INTEGER, contract_status TEXT NOT NULL, contract_note TEXT, contractor_name TEXT, contractor_contact TEXT, contract_deposit_manwon INTEGER, provisional_deposit_manwon INTEGER, remaining_deposit_due_date TEXT, balance_manwon INTEGER, balance_due_date TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE consultation_activities_new (id INTEGER PRIMARY KEY AUTOINCREMENT, consultation_id INTEGER NOT NULL REFERENCES consultations(id) ON DELETE CASCADE, activity_date TEXT NOT NULL, activity_type TEXT NOT NULL, activity_note TEXT, stage_after_activity TEXT NOT NULL, visit_result TEXT, closed_reason TEXT, next_contact_date TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE contract_activities_new (id INTEGER PRIMARY KEY AUTOINCREMENT, contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE, activity_date TEXT NOT NULL, activity_stage TEXT NOT NULL, activity_note TEXT, contract_status_after TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        """)
        connection.execute("INSERT INTO buildings_new SELECT id,building_name,lot_address,common_entrance_password,has_elevator,parking_status,internal_note,is_active,created_at,updated_at FROM buildings")
        connection.execute("INSERT INTO units_new SELECT id,building_id,unit_number,unit_number_normalized,floor_number,room_type,unit_options,access_method,unit_access_password,is_active,created_at,updated_at FROM units")
        connection.execute("""INSERT INTO listings_new SELECT id,unit_id,received_date,listing_status,closed_date,close_reason,deposit_manwon,monthly_rent_manwon,management_fee_manwon,CASE WHEN id=67 AND availability_type='날짜 지정' THEN '퇴실 후 협의' WHEN availability_type='날짜 지정' THEN '확인 필요' ELSE availability_type END,move_out_due_date,listing_holder,CASE WHEN id=67 AND available_from_date IS NOT NULL AND INSTR(COALESCE(listing_note,''), '입주 가능일 ' || available_from_date)=0 THEN TRIM(COALESCE(listing_note,'') || CASE WHEN COALESCE(listing_note,'')='' THEN '' ELSE '\n' END || '입주 가능일 ' || available_from_date) ELSE listing_note END,last_checked_date,next_check_date,landlord_contact,tenant_contact,created_at,updated_at FROM listings""")
        connection.execute("""INSERT INTO consultations_new SELECT id,listing_id,customer_name,customer_phone,consulted_date,consultation_source,consultation_note,desired_area,CASE WHEN COALESCE(desired_room_types,'')='' THEN desired_room_type WHEN COALESCE(desired_room_type,'')='' OR INSTR(desired_room_types,desired_room_type)>0 THEN desired_room_types ELSE desired_room_types || ' | ' || desired_room_type END,desired_deposit_manwon,desired_monthly_rent_manwon,desired_available_from_date,next_contact_date,consultation_status,progress_stage,last_contacted_date,latest_visit_result,closed_reason,required_features_note,created_at,updated_at FROM consultations""")
        connection.execute("INSERT INTO contracts_new (id,listing_id,source_consultation_id,contract_type,brokerage_method,contract_progress_date,formal_contract_date,contract_start_date,contract_end_date,term_months,contract_status,contract_note,contractor_name,contractor_contact,contract_deposit_manwon,provisional_deposit_manwon,remaining_deposit_due_date,balance_manwon,balance_due_date,created_at,updated_at) SELECT id,listing_id,source_consultation_id,contract_type,brokerage_method,contract_progress_date,formal_contract_date,contract_start_date,contract_end_date,term_months,contract_status,contract_note,contractor_name,contractor_contact,contract_deposit_manwon,provisional_deposit_manwon,remaining_deposit_due_date,balance_manwon,balance_due_date,created_at,updated_at FROM contracts")
        connection.execute("INSERT INTO consultation_activities_new (id,consultation_id,activity_date,activity_type,activity_note,stage_after_activity,visit_result,closed_reason,next_contact_date,created_at,updated_at) SELECT id,consultation_id,activity_date,activity_type,activity_note,stage_after_activity,visit_result,closed_reason,next_contact_date,created_at,updated_at FROM consultation_activities")
        connection.execute("INSERT INTO contract_activities_new (id,contract_id,activity_date,activity_stage,activity_note,contract_status_after,created_at,updated_at) SELECT id,contract_id,activity_date,activity_stage,activity_note,contract_status_after,created_at,updated_at FROM contract_activities")
        connection.executescript("DROP TABLE contract_activities; DROP TABLE consultation_activities; DROP TABLE contracts; DROP TABLE consultations; DROP TABLE listings; DROP TABLE units; DROP TABLE buildings; ALTER TABLE buildings_new RENAME TO buildings; ALTER TABLE units_new RENAME TO units; ALTER TABLE listings_new RENAME TO listings; ALTER TABLE consultations_new RENAME TO consultations; ALTER TABLE contracts_new RENAME TO contracts; ALTER TABLE consultation_activities_new RENAME TO consultation_activities; ALTER TABLE contract_activities_new RENAME TO contract_activities;")
        connection.executescript(SCHEMA)
        if any(connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] != count for name, count in counts.items()):
            raise RuntimeError("필드 정리 뒤 행 수가 달라져 마이그레이션을 취소했습니다.")
    finally:
        connection.execute("PRAGMA foreign_keys = ON")


def _replace_listing_advertisements(connection: sqlite3.Connection) -> None:
    """승인된 광고관리 전환: 보호 사본을 확인한 뒤 매물별 광고 표를 제거한다."""
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='listing_advertisements'").fetchone():
        return
    source_name = next((row[2] for row in connection.execute("PRAGMA database_list") if row[1] == "main"), "")
    if source_name and source_name != ":memory:" and Path(source_name).resolve() == DATABASE_PATH.resolve():
        backup_directory = Path(__file__).resolve().parents[1] / "backups"
        backup_directory.mkdir(parents=True, exist_ok=True)
        backup_path = backup_directory / f"real_estate_before_advertisement_cleanup_{datetime.now():%Y%m%d_%H%M%S}.db"
        destination = sqlite3.connect(backup_path)
        try:
            connection.backup(destination)
        finally:
            destination.close()
        if not backup_path.exists() or backup_path.stat().st_size == 0:
            raise RuntimeError("매물별 광고 삭제 전 보호 사본을 확인하지 못했습니다.")
    connection.execute("DROP TRIGGER IF EXISTS listing_advertisements_set_updated_at")
    connection.execute("DROP TABLE listing_advertisements")


def _backup_before_today_task_completion_migration(connection: sqlite3.Connection) -> None:
    """운영 DB에 완료 체크 표를 더리기 전 보호 사본을 남긴다."""
    source_name = next((row[2] for row in connection.execute("PRAGMA database_list") if row[1] == "main"), "")
    if not source_name or source_name == ":memory:" or Path(source_name).resolve() != DATABASE_PATH.resolve():
        return
    if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='today_task_completions'").fetchone():
        return
    backup_directory = Path(__file__).resolve().parents[1] / "backups"
    backup_directory.mkdir(parents=True, exist_ok=True)
    backup_path = backup_directory / f"real_estate_before_today_task_completion_{datetime.now():%Y%m%d_%H%M%S}.db"
    destination = sqlite3.connect(backup_path)
    try:
        connection.backup(destination)
    finally:
        destination.close()


def _backup_before_consultation_progress_migration(connection: sqlite3.Connection) -> None:
    """상담 진행관리 열과 후속 이력 표를 더리기 전 운영 DB 보호 사본을 남긴다."""
    source_name = next((row[2] for row in connection.execute("PRAGMA database_list") if row[1] == "main"), "")
    if not source_name or source_name == ":memory:" or Path(source_name).resolve() != DATABASE_PATH.resolve():
        return
    has_activities = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='consultation_activities'").fetchone()
    consultation_columns = {row[1] for row in connection.execute("PRAGMA table_info(consultations)")}
    if has_activities and "progress_stage" in consultation_columns:
        return
    backup_directory = Path(__file__).resolve().parents[1] / "backups"
    backup_directory.mkdir(parents=True, exist_ok=True)
    backup_path = backup_directory / f"real_estate_before_consultation_progress_{datetime.now():%Y%m%d_%H%M%S}.db"
    destination = sqlite3.connect(backup_path)
    try:
        connection.backup(destination)
    finally:
        destination.close()


def _backup_before_contract_activity_migration(connection: sqlite3.Connection) -> None:
    """계약 단계 이력 표를 추가하기 전 운영 DB 보호 사본을 남긴다."""
    source_name = next((row[2] for row in connection.execute("PRAGMA database_list") if row[1] == "main"), "")
    if not source_name or source_name == ":memory:" or Path(source_name).resolve() != DATABASE_PATH.resolve():
        return
    if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='contract_activities'").fetchone():
        return
    backup_directory = Path(__file__).resolve().parents[1] / "backups"
    backup_directory.mkdir(parents=True, exist_ok=True)
    backup_path = backup_directory / f"real_estate_before_contract_activities_{datetime.now():%Y%m%d_%H%M%S}.db"
    destination = sqlite3.connect(backup_path)
    try:
        connection.backup(destination)
    finally:
        destination.close()


def _backup_before_contract_consultation_link_migration(connection: sqlite3.Connection) -> None:
    """계약의 상담 출처 연결 열을 더리기 전 운영 DB 보호 사본을 남긴다."""
    source_name = next((row[2] for row in connection.execute("PRAGMA database_list") if row[1] == "main"), "")
    if not source_name or source_name == ":memory:" or Path(source_name).resolve() != DATABASE_PATH.resolve():
        return
    columns = {row[1] for row in connection.execute("PRAGMA table_info(contracts)")}
    if {"source_consultation_id", "contractor_name"}.issubset(columns):
        return
    backup_directory = Path(__file__).resolve().parents[1] / "backups"
    backup_directory.mkdir(parents=True, exist_ok=True)
    backup_path = backup_directory / f"real_estate_before_contract_consultation_link_{datetime.now():%Y%m%d_%H%M%S}.db"
    destination = sqlite3.connect(backup_path)
    try:
        connection.backup(destination)
    finally:
        destination.close()


def _backup_before_balance_due_date_migration(connection: sqlite3.Connection) -> None:
    """새 계약 일정 열을 더하기 전, 운영 DB의 읽기 전용 사본을 남긴다."""
    source_name = next((row[2] for row in connection.execute("PRAGMA database_list") if row[1] == "main"), "")
    if not source_name or source_name == ":memory:":
        return
    source_path = Path(source_name)
    if not source_path.exists():
        return
    backup_directory = Path(__file__).resolve().parents[1] / "backups"
    backup_directory.mkdir(parents=True, exist_ok=True)
    backup_path = backup_directory / f"real_estate_before_balance_due_date_{datetime.now():%Y%m%d_%H%M%S}.db"
    destination = sqlite3.connect(backup_path)
    try:
        connection.backup(destination)
    finally:
        destination.close()


def _backup_before_listing_holder_migration(connection: sqlite3.Connection) -> None:
    """매물 보유처 열을 더하기 전 운영 DB의 보호 사본을 남긴다."""
    source_name = next((row[2] for row in connection.execute("PRAGMA database_list") if row[1] == "main"), "")
    if not source_name or source_name == ":memory:":
        return
    source_path = Path(source_name)
    if not source_path.exists():
        return
    backup_directory = Path(__file__).resolve().parents[1] / "backups"
    backup_directory.mkdir(parents=True, exist_ok=True)
    backup_path = backup_directory / f"real_estate_before_listing_holder_{datetime.now():%Y%m%d_%H%M%S}.db"
    destination = sqlite3.connect(backup_path)
    try:
        connection.backup(destination)
    finally:
        destination.close()


def _backup_before_brokerage_method_migration(connection: sqlite3.Connection) -> None:
    """계약 중개 방식 열을 더리기 전 운영 DB 보호 사본을 남긴다."""
    source_name = next((row[2] for row in connection.execute("PRAGMA database_list") if row[1] == "main"), "")
    if not source_name or source_name == ":memory:" or Path(source_name).resolve() != DATABASE_PATH.resolve():
        return
    backup_directory = Path(__file__).resolve().parents[1] / "backups"
    backup_directory.mkdir(parents=True, exist_ok=True)
    backup_path = backup_directory / f"real_estate_before_brokerage_method_{datetime.now():%Y%m%d_%H%M%S}.db"
    destination = sqlite3.connect(backup_path)
    try:
        connection.backup(destination)
    finally:
        destination.close()


def ensure_database_schema(path: Path = DATABASE_PATH) -> None:
    require_database(path)
    connection = get_connection(path)
    try:
        with connection:
            _backup_before_consultation_progress_migration(connection)
            _backup_before_contract_activity_migration(connection)
            _backup_before_contract_consultation_link_migration(connection)
            connection.executescript(SCHEMA)
            _ensure_compatibility_columns(connection)
    finally:
        connection.close()


def require_database(path: Path = DATABASE_PATH) -> None:
    if not path.exists():
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {path}. 경로를 확인하거나 관리자에게 문의하세요.")
