"""내부 업무용 엑셀에 보낼 매물 데이터 조회 기능."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from storage.database import DATABASE_PATH, ensure_database_schema, get_connection


def get_current_listing_export_rows(listing_ids: list[int], path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    """선택된 현재 매물의 엑셀 항목을 읽는다. 개인 연락처는 포함하지 않는다."""
    if not listing_ids:
        return []
    ensure_database_schema(path)
    placeholders = ", ".join("?" for _ in listing_ids)
    connection = get_connection(path)
    try:
        rows = connection.execute(f"""
            SELECT l.id AS listing_id, l.received_date, l.listing_status, l.listing_holder, l.deposit_manwon, l.monthly_rent_manwon, l.management_fee_manwon, l.availability_type, l.move_out_due_date, l.listing_note, l.last_checked_date, l.next_check_date,
                   b.building_name, b.lot_address, b.common_entrance_password, b.has_elevator, b.parking_status, b.internal_note AS building_internal_note,
                   u.unit_number, u.floor_number, u.room_type, u.unit_options, u.access_method, u.unit_access_password
            FROM listings l JOIN units u ON u.id = l.unit_id JOIN buildings b ON b.id = u.building_id
            WHERE l.id IN ({placeholders}) AND l.closed_date IS NULL AND l.listing_status NOT IN ('계약 완료', '종료') AND u.is_active = 1 AND b.is_active = 1
            ORDER BY l.received_date DESC, l.updated_at DESC, l.id DESC
        """, listing_ids).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()
