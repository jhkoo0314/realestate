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
            SELECT l.id AS listing_id, l.received_date, l.listing_status, l.listing_holder, l.deposit_manwon, l.monthly_rent_manwon, l.management_fee_manwon, l.management_fee_note, l.availability_type, l.available_from_date, l.move_out_due_date, l.lease_term_note, l.short_term_note, l.cleaning_status, l.wallpaper_status, l.repair_status, l.has_listing_photos, l.ad_status, l.ad_channel_note, l.listing_note, l.option_change_note, l.last_checked_date, l.next_check_date, l.verification_note,
                   b.building_name, b.lot_address, b.admin_address, b.road_address, b.common_entrance_password, b.has_elevator, b.parking_status, b.has_cctv, b.pet_policy, b.move_in_registration_policy, b.short_term_policy, b.common_fee_note, b.building_highlights, b.internal_note AS building_internal_note,
                   u.unit_number, u.floor_number, u.room_type, u.is_separated, u.direction, u.area_status, u.exclusive_area_m2, u.has_balcony, u.has_built_in_closet, u.has_double_window, u.storage_status, u.system_aircon_count, u.unit_options, u.unit_highlights, u.unit_cautions, u.internal_note AS unit_internal_note, u.access_method, u.unit_access_password, u.last_photo_date
            FROM listings l JOIN units u ON u.id = l.unit_id JOIN buildings b ON b.id = u.building_id
            WHERE l.id IN ({placeholders}) AND l.closed_date IS NULL AND l.listing_status NOT IN ('계약 완료', '종료') AND u.is_active = 1 AND b.is_active = 1
            ORDER BY l.received_date DESC, l.updated_at DESC, l.id DESC
        """, listing_ids).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()
