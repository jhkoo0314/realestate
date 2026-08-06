"""새 건물·호실·첫 매물 및 기존 건물의 새 호실 등록 저장 기능."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from storage.database import DATABASE_PATH, get_connection, normalize_unit_number, require_database


def find_building_by_identity(building_name: str, lot_address: str, path: Path = DATABASE_PATH) -> dict[str, Any] | None:
    require_database(path); connection=get_connection(path)
    try:
        row=connection.execute("SELECT id,building_name,lot_address FROM buildings WHERE building_name=? AND lot_address=? AND is_active=1",(building_name.strip(),lot_address.strip())).fetchone(); return dict(row) if row else None
    finally: connection.close()


def building_has_unit(building_id: int, unit_number: str, path: Path = DATABASE_PATH) -> bool:
    normalized=normalize_unit_number(unit_number)
    if not normalized: return False
    require_database(path); connection=get_connection(path)
    try: return connection.execute("SELECT 1 FROM units WHERE building_id=? AND unit_number_normalized=? AND is_active=1",(building_id,normalized)).fetchone() is not None
    finally: connection.close()


def _validate(unit: dict[str, Any], listing: dict[str, Any]) -> str:
    missing=[label for label,value in {"호수":unit.get("unit_number"),"매물 상태":listing.get("listing_status"),"입주 가능 유형":listing.get("availability_type")}.items() if not value]
    if missing: raise ValueError(f"필수 항목이 비어 있습니다: {', '.join(missing)}")
    if listing["availability_type"]=="날짜 지정" and not listing.get("available_from_date"): raise ValueError("입주 가능 유형이 날짜 지정이면 입주 가능일이 필요합니다.")
    normalized=normalize_unit_number(str(unit["unit_number"]))
    if not normalized: raise ValueError("호수를 확인해 주세요.")
    return normalized


def _insert_listing(connection, unit_id: int, listing: dict[str, Any]) -> int:
    cursor=connection.execute("""INSERT INTO listings (unit_id,received_date,listing_status,deposit_manwon,monthly_rent_manwon,management_fee_manwon,availability_type,available_from_date,move_out_due_date,has_listing_photos,cleaning_status,wallpaper_status,repair_status,listing_note,next_check_date,landlord_contact,tenant_contact) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(unit_id,listing.get("received_date",date.today().isoformat()),listing["listing_status"],listing.get("deposit_manwon"),listing.get("monthly_rent_manwon"),listing.get("management_fee_manwon"),listing["availability_type"],listing.get("available_from_date"),listing.get("move_out_due_date"),listing.get("has_listing_photos","확인 필요"),listing.get("cleaning_status"),listing.get("wallpaper_status"),listing.get("repair_status"),listing.get("listing_note"),listing.get("next_check_date"),listing.get("landlord_contact"),listing.get("tenant_contact")))
    return cursor.lastrowid


def _insert_unit(connection, building_id: int, unit: dict[str, Any], normalized: str) -> int:
    cursor=connection.execute("""INSERT INTO units (building_id,unit_number,unit_number_normalized,floor_number,room_type,direction,unit_options,unit_highlights,access_method,unit_access_password) VALUES (?,?,?,?,?,?,?,?,?,?)""",(building_id,str(unit["unit_number"]).strip(),normalized,unit.get("floor_number"),unit.get("room_type"),unit.get("direction"),unit.get("unit_options"),unit.get("unit_highlights"),unit.get("access_method"),unit.get("unit_access_password")))
    return cursor.lastrowid


def save_first_listing(building: dict[str, Any], unit: dict[str, Any], listing: dict[str, Any], path: Path = DATABASE_PATH) -> tuple[int,int,int]:
    if not building.get("building_name") or not building.get("lot_address"): raise ValueError("건물명과 지번을 입력해 주세요.")
    normalized=_validate(unit,listing); require_database(path); connection=get_connection(path)
    try:
        with connection:
            cursor=connection.execute("""INSERT INTO buildings (building_name,lot_address,admin_address,road_address,common_entrance_password,has_elevator,parking_status,internal_note) VALUES (?,?,?,?,?,?,?,?)""",(building["building_name"].strip(),building["lot_address"].strip(),building.get("admin_address"),building.get("road_address"),building.get("common_entrance_password"),building.get("has_elevator"),building.get("parking_status"),building.get("internal_note")))
            building_id=cursor.lastrowid; unit_id=_insert_unit(connection,building_id,unit,normalized); return building_id,unit_id,_insert_listing(connection,unit_id,listing)
    finally: connection.close()


def save_first_listing_for_existing_building(building_id: int, unit: dict[str, Any], listing: dict[str, Any], path: Path = DATABASE_PATH) -> tuple[int,int]:
    normalized=_validate(unit,listing); require_database(path); connection=get_connection(path)
    try:
        with connection:
            if connection.execute("SELECT 1 FROM buildings WHERE id=? AND is_active=1",(building_id,)).fetchone() is None: raise ValueError("선택한 건물을 찾을 수 없습니다. 다시 검색해 주세요.")
            if connection.execute("SELECT 1 FROM units WHERE building_id=? AND unit_number_normalized=?",(building_id,normalized)).fetchone(): raise ValueError("같은 호실이 이미 등록되어 있습니다. 기존 호실을 선택해 주세요.")
            unit_id=_insert_unit(connection,building_id,unit,normalized); return unit_id,_insert_listing(connection,unit_id,listing)
    finally: connection.close()
