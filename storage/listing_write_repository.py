"""기존 호실의 매물 수정·종료·재등록 저장 기능."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from storage.database import DATABASE_PATH, ensure_database_schema, get_connection, require_database


def get_unit_relisting_context(unit_id: int, path: Path = DATABASE_PATH) -> dict[str, Any] | None:
    require_database(path); connection=get_connection(path)
    try:
        row=connection.execute("""SELECT u.id AS unit_id,u.unit_number,u.floor_number,u.room_type,u.direction,u.unit_options,u.access_method,u.unit_highlights,b.id AS building_id,b.building_name,b.lot_address,b.admin_address,b.road_address,b.has_elevator,b.parking_status FROM units u JOIN buildings b ON b.id=u.building_id WHERE u.id=? AND u.is_active=1 AND b.is_active=1""",(unit_id,)).fetchone(); return dict(row) if row else None
    finally: connection.close()


def has_active_listing(unit_id: int, path: Path = DATABASE_PATH) -> bool:
    require_database(path); connection=get_connection(path)
    try: return connection.execute("SELECT 1 FROM listings WHERE unit_id=? AND closed_date IS NULL AND listing_status NOT IN ('계약 완료','종료') LIMIT 1",(unit_id,)).fetchone() is not None
    finally: connection.close()


def get_current_listing(unit_id: int, path: Path = DATABASE_PATH) -> dict[str, Any] | None:
    ensure_database_schema(path); connection=get_connection(path)
    try:
        row=connection.execute("""SELECT id,unit_id,received_date,listing_status,deposit_manwon,monthly_rent_manwon,management_fee_manwon,availability_type,available_from_date,move_out_due_date,photo_status,listing_note,next_check_date,landlord_contact,tenant_contact FROM listings WHERE unit_id=? AND closed_date IS NULL AND listing_status NOT IN ('계약 완료','종료') ORDER BY received_date DESC,id DESC LIMIT 1""",(unit_id,)).fetchone(); return dict(row) if row else None
    finally: connection.close()


def update_current_listing(listing_id: int, listing: dict[str, Any], path: Path = DATABASE_PATH) -> None:
    ensure_database_schema(path); connection=get_connection(path)
    try:
        with connection:
            row=connection.execute("SELECT unit_id FROM listings WHERE id=? AND closed_date IS NULL",(listing_id,)).fetchone()
            if row is None: raise ValueError("수정할 현재 매물을 찾을 수 없습니다.")
            connection.execute("""UPDATE listings SET listing_status=?,deposit_manwon=?,monthly_rent_manwon=?,management_fee_manwon=?,availability_type=?,available_from_date=?,move_out_due_date=?,photo_status=?,listing_note=?,next_check_date=?,landlord_contact=?,tenant_contact=? WHERE id=?""",(listing["listing_status"],listing["deposit_manwon"],listing["monthly_rent_manwon"],listing.get("management_fee_manwon"),listing["availability_type"],listing.get("available_from_date"),listing.get("move_out_due_date"),listing.get("photo_status"),listing.get("listing_note"),listing.get("next_check_date"),listing.get("landlord_contact"),listing.get("tenant_contact"),listing_id))
            if listing.get("photo_status")=="촬영 완료" and listing.get("last_photo_date"): connection.execute("UPDATE units SET last_photo_date=? WHERE id=?",(listing["last_photo_date"],row["unit_id"]))
    finally: connection.close()


def close_current_listing(listing_id: int, close_date: str, close_reason: str, path: Path = DATABASE_PATH) -> None:
    if not close_reason: raise ValueError("종료 사유를 선택해 주세요.")
    require_database(path); connection=get_connection(path)
    try:
        with connection:
            if connection.execute("UPDATE listings SET listing_status=?,closed_date=?,close_reason=? WHERE id=? AND closed_date IS NULL",("계약 완료" if close_reason=="계약 완료" else "종료",close_date,close_reason,listing_id)).rowcount != 1: raise ValueError("종료할 현재 매물을 찾을 수 없습니다.")
    finally: connection.close()


def save_new_listing_round(unit_id: int, listing: dict[str, Any], path: Path = DATABASE_PATH) -> int:
    require_database(path); connection=get_connection(path)
    try:
        with connection:
            if connection.execute("SELECT 1 FROM units WHERE id=? AND is_active=1",(unit_id,)).fetchone() is None: raise ValueError("선택한 호실을 찾을 수 없습니다. 다시 선택해 주세요.")
            cursor=connection.execute("""INSERT INTO listings (unit_id,received_date,listing_status,deposit_manwon,monthly_rent_manwon,management_fee_manwon,availability_type,available_from_date,move_out_due_date,photo_status,listing_note,next_check_date,verification_note,landlord_contact,tenant_contact) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(unit_id,listing.get("received_date",date.today().isoformat()),listing["listing_status"],listing.get("deposit_manwon"),listing.get("monthly_rent_manwon"),listing.get("management_fee_manwon"),listing["availability_type"],listing.get("available_from_date"),listing.get("move_out_due_date"),listing.get("photo_status"),listing.get("listing_note"),listing.get("next_check_date"),listing.get("verification_note"),listing.get("landlord_contact"),listing.get("tenant_contact")))
            return cursor.lastrowid
    finally: connection.close()


def deactivate_unit(unit_id: int, path: Path = DATABASE_PATH) -> None:
    require_database(path); connection=get_connection(path)
    try:
        with connection:
            if connection.execute("UPDATE units SET is_active=0 WHERE id=?",(unit_id,)).rowcount != 1: raise ValueError("비활성화할 호실을 찾을 수 없습니다.")
    finally: connection.close()
