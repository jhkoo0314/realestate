"""기존 호실의 최신 매물 정보 수정·종료·현재 매물 등록 기능."""

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


def get_current_listing(unit_id: int, path: Path = DATABASE_PATH) -> dict[str, Any] | None:
    ensure_database_schema(path); connection=get_connection(path)
    try:
        row=connection.execute("""SELECT id,unit_id,received_date,listing_status,closed_date,close_reason,deposit_manwon,monthly_rent_manwon,management_fee_manwon,availability_type,available_from_date,move_out_due_date,has_listing_photos,cleaning_status,wallpaper_status,repair_status,listing_note,next_check_date,landlord_contact,tenant_contact FROM listings WHERE unit_id=? ORDER BY CASE WHEN closed_date IS NULL AND listing_status NOT IN ('계약 완료','종료') THEN 0 ELSE 1 END, received_date DESC,id DESC LIMIT 1""",(unit_id,)).fetchone(); return dict(row) if row else None
    finally: connection.close()


def update_current_listing(listing_id: int, listing: dict[str, Any], path: Path = DATABASE_PATH) -> None:
    ensure_database_schema(path); connection=get_connection(path)
    try:
        with connection:
            row=connection.execute("SELECT unit_id FROM listings WHERE id=?",(listing_id,)).fetchone()
            if row is None: raise ValueError("수정할 매물 정보를 찾을 수 없습니다.")
            connection.execute("""UPDATE listings SET listing_status=?,closed_date=NULL,close_reason=NULL,deposit_manwon=?,monthly_rent_manwon=?,management_fee_manwon=?,availability_type=?,available_from_date=?,move_out_due_date=?,has_listing_photos=?,cleaning_status=?,wallpaper_status=?,repair_status=?,listing_note=?,next_check_date=?,landlord_contact=?,tenant_contact=? WHERE id=?""",(listing["listing_status"],listing["deposit_manwon"],listing["monthly_rent_manwon"],listing.get("management_fee_manwon"),listing["availability_type"],listing.get("available_from_date"),listing.get("move_out_due_date"),listing.get("has_listing_photos","확인 필요"),listing.get("cleaning_status"),listing.get("wallpaper_status"),listing.get("repair_status"),listing.get("listing_note"),listing.get("next_check_date"),listing.get("landlord_contact"),listing.get("tenant_contact"),listing_id))
            if "unit_options" in listing:
                connection.execute("UPDATE units SET unit_options=? WHERE id=?", (listing["unit_options"], row["unit_id"]))
    finally: connection.close()


def close_current_listing(listing_id: int, close_date: str, close_reason: str, path: Path = DATABASE_PATH) -> None:
    if not close_reason: raise ValueError("종료 사유를 선택해 주세요.")
    require_database(path); connection=get_connection(path)
    try:
        with connection:
            if connection.execute("UPDATE listings SET listing_status=?,closed_date=?,close_reason=? WHERE id=? AND closed_date IS NULL",("계약 완료" if close_reason=="계약 완료" else "종료",close_date,close_reason,listing_id)).rowcount != 1: raise ValueError("종료할 현재 매물을 찾을 수 없습니다.")
    finally: connection.close()


def delete_listing(listing_id: int, path: Path = DATABASE_PATH) -> dict[str, int]:
    """매물 1건과 연결된 계약·상담 기록을 함께 완전히 삭제한다."""
    require_database(path); connection=get_connection(path)
    try:
        with connection:
            if connection.execute("SELECT 1 FROM listings WHERE id=?", (listing_id,)).fetchone() is None:
                raise ValueError("삭제할 매물을 찾을 수 없습니다.")
            consultation_count = connection.execute("SELECT COUNT(*) FROM consultations WHERE listing_id=?", (listing_id,)).fetchone()[0]
            contract_count = connection.execute("SELECT COUNT(*) FROM contracts WHERE listing_id=?", (listing_id,)).fetchone()[0]
            connection.execute("DELETE FROM consultations WHERE listing_id=?", (listing_id,))
            connection.execute("DELETE FROM contracts WHERE listing_id=?", (listing_id,))
            connection.execute("DELETE FROM listings WHERE id=?", (listing_id,))
            return {"contracts": contract_count, "consultations": consultation_count}
    finally: connection.close()


def get_unit_deletion_summary(unit_id: int, path: Path = DATABASE_PATH) -> dict[str, int]:
    """호실 완전 삭제 전에 함께 지워질 기록 수를 확인한다."""
    require_database(path); connection=get_connection(path)
    try:
        unit = connection.execute("SELECT 1 FROM units WHERE id=? AND is_active=1", (unit_id,)).fetchone()
        if unit is None: raise ValueError("삭제할 호실을 찾을 수 없습니다.")
        listings = connection.execute("SELECT COUNT(*) FROM listings WHERE unit_id=?", (unit_id,)).fetchone()[0]
        contracts = connection.execute("SELECT COUNT(*) FROM contracts WHERE listing_id IN (SELECT id FROM listings WHERE unit_id=?)", (unit_id,)).fetchone()[0]
        consultations = connection.execute("SELECT COUNT(*) FROM consultations WHERE listing_id IN (SELECT id FROM listings WHERE unit_id=?)", (unit_id,)).fetchone()[0]
        return {"listings": listings, "contracts": contracts, "consultations": consultations}
    finally: connection.close()


def delete_unit(unit_id: int, path: Path = DATABASE_PATH) -> dict[str, int]:
    """잘못 만든 호실과 연결된 매물·계약·상담 기록을 함께 완전 삭제한다."""
    summary = get_unit_deletion_summary(unit_id, path)
    connection=get_connection(path)
    try:
        with connection:
            connection.execute("DELETE FROM consultations WHERE listing_id IN (SELECT id FROM listings WHERE unit_id=?)", (unit_id,))
            connection.execute("DELETE FROM contracts WHERE listing_id IN (SELECT id FROM listings WHERE unit_id=?)", (unit_id,))
            connection.execute("DELETE FROM listings WHERE unit_id=?", (unit_id,))
            if connection.execute("DELETE FROM units WHERE id=?", (unit_id,)).rowcount != 1:
                raise ValueError("호실을 삭제하지 못했습니다.")
        return summary
    finally: connection.close()


def save_new_listing_round(unit_id: int, listing: dict[str, Any], path: Path = DATABASE_PATH) -> int:
    require_database(path); connection=get_connection(path)
    try:
        with connection:
            if connection.execute("SELECT 1 FROM units WHERE id=? AND is_active=1",(unit_id,)).fetchone() is None: raise ValueError("선택한 호실을 찾을 수 없습니다. 다시 선택해 주세요.")
            cursor=connection.execute("""INSERT INTO listings (unit_id,received_date,listing_status,deposit_manwon,monthly_rent_manwon,management_fee_manwon,availability_type,available_from_date,move_out_due_date,has_listing_photos,cleaning_status,wallpaper_status,repair_status,listing_note,next_check_date,verification_note,landlord_contact,tenant_contact) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(unit_id,listing.get("received_date",date.today().isoformat()),listing["listing_status"],listing.get("deposit_manwon"),listing.get("monthly_rent_manwon"),listing.get("management_fee_manwon"),listing["availability_type"],listing.get("available_from_date"),listing.get("move_out_due_date"),listing.get("has_listing_photos","확인 필요"),listing.get("cleaning_status"),listing.get("wallpaper_status"),listing.get("repair_status"),listing.get("listing_note"),listing.get("next_check_date"),listing.get("verification_note"),listing.get("landlord_contact"),listing.get("tenant_contact")))
            return cursor.lastrowid
    finally: connection.close()


def deactivate_unit(unit_id: int, path: Path = DATABASE_PATH) -> None:
    require_database(path); connection=get_connection(path)
    try:
        with connection:
            if connection.execute("UPDATE units SET is_active=0 WHERE id=?",(unit_id,)).rowcount != 1: raise ValueError("비활성화할 호실을 찾을 수 없습니다.")
    finally: connection.close()
