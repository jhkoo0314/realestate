"""건물·호실 관리 화면의 검색·상세·수정·이력 조회 기능."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from storage.database import DATABASE_PATH, get_connection, normalize_unit_number, require_database


def search_buildings(query: str, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    require_database(path); keyword = query.strip()
    if not keyword: return []
    connection = get_connection(path)
    try:
        rows = connection.execute("""SELECT b.id, b.building_name, b.lot_address, b.has_elevator, b.parking_status, COUNT(u.id) AS unit_count FROM buildings b LEFT JOIN units u ON u.building_id = b.id AND u.is_active = 1 WHERE b.is_active = 1 AND (b.building_name LIKE ? OR b.lot_address LIKE ?) GROUP BY b.id ORDER BY b.building_name, b.lot_address""", (f"%{keyword}%", f"%{keyword}%")).fetchall()
        return [dict(row) for row in rows]
    finally: connection.close()


def get_building_management_detail(building_id: int, path: Path = DATABASE_PATH) -> dict[str, Any] | None:
    require_database(path); connection = get_connection(path)
    try:
        row = connection.execute("""SELECT id, building_name, lot_address, has_elevator, parking_status, has_cctv, pet_policy, move_in_registration_policy, short_term_policy, common_fee_note, building_highlights, info_status, last_checked_date, next_check_date FROM buildings WHERE id = ? AND is_active = 1""", (building_id,)).fetchone()
        return dict(row) if row else None
    finally: connection.close()


def get_building_password(building_id: int, path: Path = DATABASE_PATH) -> str | None:
    require_database(path); connection = get_connection(path)
    try:
        row = connection.execute("SELECT common_entrance_password FROM buildings WHERE id = ? AND is_active = 1", (building_id,)).fetchone()
        return row[0] if row else None
    finally: connection.close()


def update_building_management_detail(building_id: int, values: dict[str, Any], path: Path = DATABASE_PATH) -> None:
    require_database(path); connection = get_connection(path)
    try:
        with connection:
            building = connection.execute("SELECT building_name, lot_address FROM buildings WHERE id = ? AND is_active = 1", (building_id,)).fetchone()
            if building is None: raise ValueError("수정할 건물을 찾을 수 없습니다.")
            building_name = str(values.get("building_name") or "").strip() or "건물명 미입력"
            lot_address = values.get("lot_address") or building["lot_address"]
            duplicate = connection.execute("SELECT 1 FROM buildings WHERE building_name = ? AND lot_address = ? AND id <> ?", (building_name, lot_address, building_id)).fetchone()
            if duplicate is not None: raise ValueError("같은 건물명과 지번의 건물이 이미 등록되어 있습니다. 기존 건물을 확인해 주세요.")
            connection.execute("""UPDATE buildings SET building_name=?, lot_address=?, has_elevator=COALESCE(?,has_elevator), parking_status=COALESCE(?,parking_status), has_cctv=COALESCE(?,has_cctv), pet_policy=COALESCE(?,pet_policy), move_in_registration_policy=COALESCE(?,move_in_registration_policy), short_term_policy=COALESCE(?,short_term_policy), common_fee_note=COALESCE(?,common_fee_note), building_highlights=COALESCE(?,building_highlights), info_status=COALESCE(?,info_status), next_check_date=COALESCE(?,next_check_date), common_entrance_password=CASE WHEN ? THEN NULL ELSE COALESCE(?,common_entrance_password) END WHERE id=?""", (building_name,lot_address,values.get("has_elevator"),values.get("parking_status"),values.get("has_cctv"),values.get("pet_policy"),values.get("move_in_registration_policy"),values.get("short_term_policy"),values.get("common_fee_note"),values.get("building_highlights"),values.get("info_status"),values.get("next_check_date"),values.get("clear_common_entrance_password",False),values.get("common_entrance_password"),building_id))
    finally: connection.close()


def get_building_units(building_id: int, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    require_database(path); connection = get_connection(path)
    try:
        rows = connection.execute("""SELECT u.id, u.unit_number, u.room_type, u.floor_number, u.direction, l.id AS listing_id, l.deposit_manwon, l.monthly_rent_manwon, l.listing_status, l.received_date FROM units u LEFT JOIN listings l ON l.id=(SELECT id FROM listings WHERE unit_id=u.id ORDER BY received_date DESC,id DESC LIMIT 1) WHERE u.building_id=? AND u.is_active=1 ORDER BY unit_number_normalized""", (building_id,)).fetchall()
        return [dict(row) for row in rows]
    finally: connection.close()


def get_unit_management_detail(unit_id: int, path: Path = DATABASE_PATH) -> dict[str, Any] | None:
    require_database(path); connection = get_connection(path)
    try:
        row = connection.execute("SELECT id, building_id, unit_number, floor_number, room_type, direction, unit_options, unit_highlights, unit_cautions, access_method, last_photo_date FROM units WHERE id=? AND is_active=1", (unit_id,)).fetchone()
        return dict(row) if row else None
    finally: connection.close()


def get_unit_password(unit_id: int, path: Path = DATABASE_PATH) -> str | None:
    require_database(path); connection = get_connection(path)
    try:
        row = connection.execute("SELECT unit_access_password FROM units WHERE id=? AND is_active=1", (unit_id,)).fetchone(); return row[0] if row else None
    finally: connection.close()


def update_unit_management_detail(unit_id: int, values: dict[str, Any], path: Path = DATABASE_PATH) -> None:
    require_database(path); connection = get_connection(path)
    try:
        with connection:
            if connection.execute("SELECT 1 FROM units WHERE id=? AND is_active=1", (unit_id,)).fetchone() is None: raise ValueError("수정할 호실을 찾을 수 없습니다.")
            connection.execute("""UPDATE units SET floor_number=COALESCE(?,floor_number), room_type=COALESCE(?,room_type), direction=COALESCE(?,direction), unit_options=COALESCE(?,unit_options), unit_highlights=COALESCE(?,unit_highlights), unit_cautions=COALESCE(?,unit_cautions), access_method=COALESCE(?,access_method), unit_access_password=CASE WHEN ? THEN NULL ELSE COALESCE(?,unit_access_password) END WHERE id=?""", (values.get("floor_number"),values.get("room_type"),values.get("direction"),values.get("unit_options"),values.get("unit_highlights"),values.get("unit_cautions"),values.get("access_method"),values.get("clear_unit_access_password",False),values.get("unit_access_password"),unit_id))
    finally: connection.close()


def rename_unit(unit_id: int, new_unit_number: str, path: Path = DATABASE_PATH) -> str:
    """연결된 매물·계약·상담 이력은 유지한 채 호실 번호만 정정한다."""
    display_number = str(new_unit_number or "").strip()
    normalized = normalize_unit_number(display_number)
    if not normalized:
        raise ValueError("새 호실 번호를 입력해 주세요.")
    connection = get_connection(path)
    try:
        with connection:
            unit = connection.execute("SELECT building_id, unit_number, unit_number_normalized FROM units WHERE id=? AND is_active=1", (unit_id,)).fetchone()
            if unit is None:
                raise ValueError("정정할 호실을 찾을 수 없습니다.")
            if unit["unit_number_normalized"] == normalized:
                raise ValueError("현재 호실 번호와 같습니다.")
            duplicate = connection.execute("SELECT 1 FROM units WHERE building_id=? AND unit_number_normalized=? AND id<>?", (unit["building_id"], normalized, unit_id)).fetchone()
            if duplicate is not None:
                raise ValueError("같은 건물에 이미 해당 호실 번호가 등록되어 있습니다.")
            connection.execute("UPDATE units SET unit_number=?, unit_number_normalized=? WHERE id=?", (normalized, normalized, unit_id))
            return unit["unit_number"]
    finally: connection.close()


def update_current_listing_option_note(unit_id: int, option_change_note: str | None, path: Path = DATABASE_PATH) -> None:
    require_database(path); connection = get_connection(path)
    try:
        with connection:
            row=connection.execute("SELECT id FROM listings WHERE unit_id=? AND closed_date IS NULL AND listing_status NOT IN ('계약 완료','종료') ORDER BY received_date DESC,id DESC LIMIT 1",(unit_id,)).fetchone()
            if row is None: raise ValueError("현재 운영 중인 매물이 없습니다.")
            connection.execute("UPDATE listings SET option_change_note=? WHERE id=?",(option_change_note,row[0]))
    finally: connection.close()


def get_unit_listing_history(unit_id: int, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    require_database(path); connection = get_connection(path)
    try:
        rows=connection.execute("SELECT id,received_date,listing_status,deposit_manwon,monthly_rent_manwon,management_fee_manwon,availability_type,available_from_date,closed_date,close_reason,option_change_note FROM listings WHERE unit_id=? ORDER BY received_date DESC,id DESC",(unit_id,)).fetchall(); return [dict(row) for row in rows]
    finally: connection.close()
