"""상담 기록의 저장·조회 기능."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from storage.database import DATABASE_PATH, ensure_database_schema, get_connection
from services.record_number import record_id_from_query


def get_consultations(*, query: str = "", categories: list[str] | None = None, statuses: list[str] | None = None, consulted_start: str | None = None, consulted_end: str | None = None, due_only: bool = False, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    ensure_database_schema(path)
    conditions, parameters = ["(c.listing_id IS NULL OR (b.is_active = 1 AND u.is_active = 1))"], []
    if keyword := query.strip():
        conditions.append("(b.building_name LIKE ? OR b.lot_address LIKE ? OR u.unit_number LIKE ? OR c.desired_area LIKE ? OR c.id = ? OR c.listing_id = ?)")
        parameters.extend([f"%{keyword}%"] * 4 + [record_id_from_query(keyword, "S") or -1, record_id_from_query(keyword, "M") or -1])
    if categories:
        conditions.append(f"c.consultation_category IN ({', '.join('?' for _ in categories)})")
        parameters.extend(categories)
    if statuses:
        conditions.append(f"c.consultation_status IN ({', '.join('?' for _ in statuses)})")
        parameters.extend(statuses)
    if consulted_start:
        conditions.append("c.consulted_date >= ?")
        parameters.append(consulted_start)
    if consulted_end:
        conditions.append("c.consulted_date <= ?")
        parameters.append(consulted_end)
    if due_only:
        conditions.extend(["c.next_contact_date IS NOT NULL", "c.next_contact_date <= ?", "c.consultation_status != '종료'"])
        parameters.append(date.today().isoformat())
    connection = get_connection(path)
    try:
        rows = connection.execute(f"""
            SELECT c.id AS consultation_id, c.listing_id, c.consultation_category, c.customer_name, c.customer_phone, c.consulted_date, c.consultation_type, c.consultation_source, c.consultation_note, c.desired_area, c.desired_room_type, c.desired_deposit_manwon, c.desired_monthly_rent_manwon, c.desired_available_from_date, c.next_contact_date, c.consultation_status, c.created_at, c.updated_at, b.building_name, b.lot_address, u.unit_number, l.received_date, l.listing_status
            FROM consultations c LEFT JOIN listings l ON l.id = c.listing_id LEFT JOIN units u ON u.id = l.unit_id LEFT JOIN buildings b ON b.id = u.building_id
            WHERE {' AND '.join(conditions)} ORDER BY c.consulted_date DESC, c.id DESC
        """, parameters).fetchall()
        return [dict(row) for row in rows]
    finally: connection.close()


def get_consultation_detail(consultation_id: int, path: Path = DATABASE_PATH) -> dict[str, Any] | None:
    ensure_database_schema(path); connection = get_connection(path)
    try:
        row = connection.execute("""
            SELECT c.id AS consultation_id, c.listing_id, c.consultation_category, c.customer_name, c.customer_phone, c.consulted_date, c.consultation_type, c.consultation_source, c.consultation_note, c.desired_area, c.desired_room_type, c.desired_deposit_manwon, c.desired_monthly_rent_manwon, c.desired_available_from_date, c.next_contact_date, c.consultation_status, b.building_name, b.lot_address, u.unit_number, l.received_date
            FROM consultations c LEFT JOIN listings l ON l.id = c.listing_id LEFT JOIN units u ON u.id = l.unit_id LEFT JOIN buildings b ON b.id = u.building_id
            WHERE c.id = ? AND (c.listing_id IS NULL OR (b.is_active = 1 AND u.is_active = 1))
        """, (consultation_id,)).fetchone()
        return dict(row) if row else None
    finally: connection.close()


def create_consultation(listing_id: int | None, consultation: dict[str, Any], path: Path = DATABASE_PATH) -> int:
    ensure_database_schema(path); connection = get_connection(path)
    try:
        with connection:
            if listing_id is not None and connection.execute("SELECT 1 FROM listings WHERE id = ?", (listing_id,)).fetchone() is None: raise ValueError("연결할 매물 기록을 찾을 수 없습니다. 다시 선택해 주세요.")
            cursor = connection.execute("""INSERT INTO consultations (listing_id, consultation_category, customer_name, customer_phone, consulted_date, consultation_type, consultation_source, consultation_note, desired_area, desired_room_type, desired_deposit_manwon, desired_monthly_rent_manwon, desired_available_from_date, next_contact_date, consultation_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (listing_id, consultation["consultation_category"], consultation["customer_name"], consultation["customer_phone"], consultation["consulted_date"], consultation["consultation_type"], consultation.get("consultation_source"), consultation["consultation_note"], consultation.get("desired_area"), consultation.get("desired_room_type"), consultation.get("desired_deposit_manwon"), consultation.get("desired_monthly_rent_manwon"), consultation.get("desired_available_from_date"), consultation.get("next_contact_date"), consultation["consultation_status"]))
            return cursor.lastrowid
    finally: connection.close()


def update_consultation(consultation_id: int, values: dict[str, Any], path: Path = DATABASE_PATH) -> None:
    ensure_database_schema(path); connection = get_connection(path)
    try:
        with connection:
            if connection.execute("UPDATE consultations SET customer_name = ?, customer_phone = ?, consultation_source = ?, consultation_note = ?, desired_area = ?, desired_room_type = ?, desired_deposit_manwon = ?, desired_monthly_rent_manwon = ?, desired_available_from_date = ?, next_contact_date = ?, consultation_status = ? WHERE id = ?", (values["customer_name"], values["customer_phone"], values.get("consultation_source"), values["consultation_note"], values.get("desired_area"), values.get("desired_room_type"), values.get("desired_deposit_manwon"), values.get("desired_monthly_rent_manwon"), values.get("desired_available_from_date"), values.get("next_contact_date"), values["consultation_status"], consultation_id)).rowcount != 1: raise ValueError("수정할 상담 기록을 찾을 수 없습니다.")
    finally: connection.close()


def update_consultation_status(consultation_id: int, consultation_status: str, path: Path = DATABASE_PATH) -> None:
    ensure_database_schema(path); connection = get_connection(path)
    try:
        with connection:
            if connection.execute("UPDATE consultations SET consultation_status=? WHERE id=?", (consultation_status, consultation_id)).rowcount != 1:
                raise ValueError("수정할 상담 기록을 찾을 수 없습니다.")
    finally: connection.close()


def update_consultation_follow_up(consultation_id: int, consultation_status: str, next_contact_date: str | None, path: Path = DATABASE_PATH) -> None:
    """오늘 할 일에서 상담 상태와 다음 연락일을 함께 갱신한다."""
    ensure_database_schema(path); connection = get_connection(path)
    try:
        with connection:
            if connection.execute("UPDATE consultations SET consultation_status=?, next_contact_date=? WHERE id=?", (consultation_status, next_contact_date, consultation_id)).rowcount != 1:
                raise ValueError("수정할 상담 기록을 찾을 수 없습니다.")
    finally: connection.close()


def link_consultation_to_listing(consultation_id: int, listing_id: int, path: Path = DATABASE_PATH) -> None:
    """일반 상담에 나중에 선택한 매물 기록을 연결한다."""
    ensure_database_schema(path); connection = get_connection(path)
    try:
        with connection:
            if connection.execute("SELECT 1 FROM listings WHERE id = ?", (listing_id,)).fetchone() is None:
                raise ValueError("연결할 매물 기록을 찾을 수 없습니다. 다시 선택해 주세요.")
            if connection.execute("UPDATE consultations SET listing_id = ? WHERE id = ?", (listing_id, consultation_id)).rowcount != 1:
                raise ValueError("연결할 상담 기록을 찾을 수 없습니다.")
    finally: connection.close()


def delete_consultation(consultation_id: int, path: Path = DATABASE_PATH) -> None:
    """선택한 상담 기록 1건만 완전히 삭제한다."""
    ensure_database_schema(path); connection = get_connection(path)
    try:
        with connection:
            if connection.execute("DELETE FROM consultations WHERE id = ?", (consultation_id,)).rowcount != 1:
                raise ValueError("삭제할 상담 기록을 찾을 수 없습니다.")
    finally: connection.close()
