"""매물 현황 조회와 빠른 수정 기능."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from storage.database import DATABASE_PATH, ensure_database_schema, get_connection
from services.record_number import record_id_from_query


def search_listing_rounds(query: str, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    """계약·상담에 연결할 현재·과거 매물 회차를 찾는다."""
    ensure_database_schema(path)
    keyword = query.strip()
    if not keyword:
        return []
    connection = get_connection(path)
    try:
        listing_id = record_id_from_query(keyword, "M") or -1
        rows = connection.execute(
            """SELECT l.id AS listing_id, l.received_date, l.listing_status, l.closed_date,
                      b.building_name, b.lot_address, u.unit_number, u.room_type
               FROM listings l
               JOIN units u ON u.id = l.unit_id
               JOIN buildings b ON b.id = u.building_id
               WHERE b.is_active = 1 AND u.is_active = 1
                 AND (b.building_name LIKE ? OR b.lot_address LIKE ?
                      OR u.unit_number LIKE ? OR u.unit_number_normalized LIKE ? OR l.id = ?)
               ORDER BY l.received_date DESC, l.id DESC LIMIT 50""",
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", listing_id),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_current_listings(*, query: str = "", received_start: str | None = None, received_end: str | None = None, deposit_min: int | None = None, deposit_max: int | None = None, monthly_rent_min: int | None = None, monthly_rent_max: int | None = None, statuses: list[str] | None = None, room_types: list[str] | None = None, photo_availability: list[str] | None = None, listing_holders: list[str] | None = None, listing_holder_query: str = "", task_filter: str | None = None, listing_scope: str = "현재 매물만", path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    ensure_database_schema(path); conditions, parameters = ["u.is_active = 1", "b.is_active = 1"], []
    if listing_scope == "현재 매물만":
        conditions.extend(["l.closed_date IS NULL", "l.listing_status NOT IN ('계약 완료', '종료')"])
    elif listing_scope == "종료된 매물만":
        conditions.append("(l.closed_date IS NOT NULL OR l.listing_status IN ('계약 완료', '종료'))")
    if keyword := query.strip():
        conditions.append("(b.building_name LIKE ? OR b.lot_address LIKE ? OR u.unit_number LIKE ? OR u.unit_number_normalized LIKE ? OR l.id = ?)"); parameters.extend([f"%{keyword}%"] * 4 + [record_id_from_query(keyword, "M") or -1])
    if received_start: conditions.append("l.received_date >= ?"); parameters.append(received_start)
    if received_end: conditions.append("l.received_date <= ?"); parameters.append(received_end)
    if deposit_min is not None: conditions.append("l.deposit_manwon >= ?"); parameters.append(deposit_min)
    if deposit_max is not None: conditions.append("l.deposit_manwon <= ?"); parameters.append(deposit_max)
    if monthly_rent_min is not None: conditions.append("l.monthly_rent_manwon >= ?"); parameters.append(monthly_rent_min)
    if monthly_rent_max is not None: conditions.append("l.monthly_rent_manwon <= ?"); parameters.append(monthly_rent_max)
    for column, values in (("l.listing_status", statuses), ("u.room_type", room_types), ("l.has_listing_photos", photo_availability)):
        if values: conditions.append(f"{column} IN ({', '.join('?' for _ in values)})"); parameters.extend(values)
    if listing_holders:
        holder_conditions = []
        stored_holders = [holder for holder in listing_holders if holder != "미입력"]
        if stored_holders:
            holder_conditions.append(f"l.listing_holder IN ({', '.join('?' for _ in stored_holders)})")
            parameters.extend(stored_holders)
        if "미입력" in listing_holders:
            holder_conditions.append("(l.listing_holder IS NULL OR TRIM(l.listing_holder) = '')")
        conditions.append(f"({' OR '.join(holder_conditions)})")
    if holder_keyword := listing_holder_query.strip():
        conditions.append("l.listing_holder LIKE ?")
        parameters.append(f"%{holder_keyword}%")
    connection = get_connection(path)
    try:
        rows = connection.execute(f"""SELECT l.id AS listing_id,u.id AS unit_id,b.building_name,b.lot_address,u.unit_number,u.room_type,l.received_date,l.listing_status,l.closed_date,l.close_reason,l.deposit_manwon,l.monthly_rent_manwon,l.management_fee_manwon,l.availability_type,l.available_from_date,l.move_out_due_date,l.has_listing_photos,l.cleaning_status,l.wallpaper_status,l.repair_status,l.listing_holder,l.next_check_date,l.listing_note,l.updated_at,
        (SELECT MIN(c.next_contact_date) FROM consultations c WHERE c.listing_id=l.id AND c.consultation_status != '종료' AND c.next_contact_date IS NOT NULL) AS next_contact_date
        FROM listings l JOIN units u ON u.id=l.unit_id JOIN buildings b ON b.id=u.building_id WHERE {' AND '.join(conditions)} ORDER BY CASE WHEN l.closed_date IS NULL THEN 1 ELSE 0 END, l.closed_date DESC, l.received_date DESC,l.updated_at DESC,l.id DESC""", parameters).fetchall()
        listings=[dict(row) for row in rows]
    finally: connection.close()
    today=date.today().isoformat()
    for item in listings:
        tasks=[]
        if item["next_check_date"] and item["next_check_date"] <= today: tasks.append("재확인 필요")
        if item["has_listing_photos"] == "없음": tasks.append("사진 촬영 필요")
        if item["has_listing_photos"] == "확인 필요": tasks.append("사진 확인 필요")
        if any(item[field] in ("필요", "진행 중") for field in ("cleaning_status","wallpaper_status","repair_status")): tasks.append("현장 상태 확인 필요")
        if item["availability_type"] == "확인 필요": tasks.append("입주 가능일 확인 필요")
        if item["listing_status"] == "확인 필요": tasks.append("매물 상태 확인 필요")
        item["tasks"]=tasks
    return [item for item in listings if not task_filter or task_filter in item["tasks"]]


def update_listing_quick_fields(listing_id: int, listing_status: str, has_listing_photos: str, next_check_date: str | None, cleaning_status: str | None, wallpaper_status: str | None, repair_status: str | None, listing_holder: str | None, path: Path = DATABASE_PATH) -> None:
    ensure_database_schema(path); connection=get_connection(path)
    try:
        with connection:
            if connection.execute("SELECT 1 FROM listings WHERE id=? AND closed_date IS NULL",(listing_id,)).fetchone() is None: raise ValueError("수정할 현재 매물을 찾을 수 없습니다.")
            connection.execute("UPDATE listings SET listing_status=?, has_listing_photos=?, next_check_date=?, cleaning_status=?, wallpaper_status=?, repair_status=?, listing_holder=? WHERE id=?",(listing_status,has_listing_photos,next_check_date,cleaning_status,wallpaper_status,repair_status,listing_holder,listing_id))
    finally: connection.close()
