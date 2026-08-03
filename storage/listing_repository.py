"""매물 현황 조회와 빠른 수정 기능."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from storage.database import DATABASE_PATH, ensure_database_schema, get_connection


def search_listing_rounds(query: str, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    """계약·상담에 연결할 현재·과거 매물 회차를 찾는다."""
    ensure_database_schema(path)
    keyword = query.strip()
    if not keyword:
        return []
    connection = get_connection(path)
    try:
        rows = connection.execute(
            """SELECT l.id AS listing_id, l.received_date, l.listing_status, l.closed_date,
                      b.building_name, b.lot_address, u.unit_number, u.room_type
               FROM listings l
               JOIN units u ON u.id = l.unit_id
               JOIN buildings b ON b.id = u.building_id
               WHERE b.is_active = 1 AND u.is_active = 1
                 AND (b.building_name LIKE ? OR b.lot_address LIKE ?
                      OR u.unit_number LIKE ? OR u.unit_number_normalized LIKE ?)
               ORDER BY l.received_date DESC, l.id DESC LIMIT 50""",
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_current_listings(*, query: str = "", received_start: str | None = None, received_end: str | None = None, statuses: list[str] | None = None, room_types: list[str] | None = None, photo_statuses: list[str] | None = None, photo_availability: list[str] | None = None, task_filter: str | None = None, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    ensure_database_schema(path); conditions, parameters = ["l.closed_date IS NULL", "l.listing_status NOT IN ('계약 완료', '종료')", "u.is_active = 1", "b.is_active = 1"], []
    if keyword := query.strip():
        conditions.append("(b.building_name LIKE ? OR b.lot_address LIKE ? OR u.unit_number LIKE ? OR u.unit_number_normalized LIKE ?)"); parameters.extend([f"%{keyword}%"] * 4)
    if received_start: conditions.append("l.received_date >= ?"); parameters.append(received_start)
    if received_end: conditions.append("l.received_date <= ?"); parameters.append(received_end)
    for column, values in (("l.listing_status", statuses), ("u.room_type", room_types), ("l.photo_status", photo_statuses), ("l.has_listing_photos", photo_availability)):
        if values: conditions.append(f"{column} IN ({', '.join('?' for _ in values)})"); parameters.extend(values)
    connection = get_connection(path)
    try:
        rows = connection.execute(f"""SELECT l.id AS listing_id,u.id AS unit_id,b.building_name,b.lot_address,u.unit_number,u.room_type,l.received_date,l.listing_status,l.deposit_manwon,l.monthly_rent_manwon,l.management_fee_manwon,l.availability_type,l.available_from_date,l.photo_status,l.has_listing_photos,l.cleaning_status,l.wallpaper_status,l.repair_status,l.next_check_date,l.listing_note,l.updated_at FROM listings l JOIN units u ON u.id=l.unit_id JOIN buildings b ON b.id=u.building_id WHERE {' AND '.join(conditions)} ORDER BY l.received_date DESC,l.updated_at DESC,l.id DESC""", parameters).fetchall()
        listings=[dict(row) for row in rows]
    finally: connection.close()
    today=date.today().isoformat()
    for item in listings:
        tasks=[]
        if item["next_check_date"] and item["next_check_date"] <= today: tasks.append("재확인 필요")
        if item["photo_status"] == "촬영 필요" or item["has_listing_photos"] == "없음": tasks.append("사진 촬영 필요")
        if any(item[field] in ("필요", "진행 중") for field in ("cleaning_status","wallpaper_status","repair_status")): tasks.append("현장 상태 확인 필요")
        if item["availability_type"] == "확인 필요": tasks.append("입주 가능일 확인 필요")
        if item["listing_status"] == "확인 필요": tasks.append("매물 상태 확인 필요")
        item["tasks"]=tasks
    return [item for item in listings if not task_filter or task_filter in item["tasks"]]


def update_listing_quick_fields(listing_id: int, listing_status: str, photo_status: str, has_listing_photos: str, next_check_date: str | None, path: Path = DATABASE_PATH) -> None:
    ensure_database_schema(path); connection=get_connection(path)
    try:
        with connection:
            if connection.execute("SELECT 1 FROM listings WHERE id=? AND closed_date IS NULL",(listing_id,)).fetchone() is None: raise ValueError("수정할 현재 매물을 찾을 수 없습니다.")
            connection.execute("UPDATE listings SET listing_status=?, photo_status=?, has_listing_photos=?, next_check_date=? WHERE id=?",(listing_status,photo_status,has_listing_photos,next_check_date,listing_id))
    finally: connection.close()
