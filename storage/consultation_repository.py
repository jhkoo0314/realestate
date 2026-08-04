"""상담 기록의 저장·조회 기능."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from storage.database import DATABASE_PATH, ensure_database_schema, get_connection


def get_consultations(*, query: str = "", statuses: list[str] | None = None, due_only: bool = False, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    ensure_database_schema(path)
    conditions, parameters = ["b.is_active = 1", "u.is_active = 1"], []
    if keyword := query.strip():
        conditions.append("(b.building_name LIKE ? OR b.lot_address LIKE ? OR u.unit_number LIKE ? OR c.customer_name LIKE ?)")
        parameters.extend([f"%{keyword}%"] * 4)
    if statuses:
        conditions.append(f"c.consultation_status IN ({', '.join('?' for _ in statuses)})")
        parameters.extend(statuses)
    if due_only:
        conditions.extend(["c.next_contact_date IS NOT NULL", "c.next_contact_date <= ?", "c.consultation_status != '종료'"])
        parameters.append(date.today().isoformat())
    connection = get_connection(path)
    try:
        rows = connection.execute(f"""
            SELECT c.id AS consultation_id, c.listing_id, c.customer_name, c.consulted_date, c.consultation_type, c.consultation_note, c.next_contact_date, c.consultation_status, c.created_at, c.updated_at, b.building_name, b.lot_address, u.unit_number, l.received_date, l.listing_status
            FROM consultations c JOIN listings l ON l.id = c.listing_id JOIN units u ON u.id = l.unit_id JOIN buildings b ON b.id = u.building_id
            WHERE {' AND '.join(conditions)} ORDER BY c.consulted_date DESC, c.id DESC
        """, parameters).fetchall()
        return [dict(row) for row in rows]
    finally: connection.close()


def get_consultation_detail(consultation_id: int, path: Path = DATABASE_PATH) -> dict[str, Any] | None:
    ensure_database_schema(path); connection = get_connection(path)
    try:
        row = connection.execute("""
            SELECT c.id AS consultation_id, c.listing_id, c.customer_name, c.customer_phone, c.consulted_date, c.consultation_type, c.consultation_note, c.next_contact_date, c.consultation_status, b.building_name, b.lot_address, u.unit_number, l.received_date
            FROM consultations c JOIN listings l ON l.id = c.listing_id JOIN units u ON u.id = l.unit_id JOIN buildings b ON b.id = u.building_id
            WHERE c.id = ? AND b.is_active = 1 AND u.is_active = 1
        """, (consultation_id,)).fetchone()
        return dict(row) if row else None
    finally: connection.close()


def create_consultation(listing_id: int, consultation: dict[str, Any], path: Path = DATABASE_PATH) -> int:
    ensure_database_schema(path); connection = get_connection(path)
    try:
        with connection:
            if connection.execute("SELECT 1 FROM listings WHERE id = ?", (listing_id,)).fetchone() is None: raise ValueError("연결할 매물 기록을 찾을 수 없습니다. 다시 선택해 주세요.")
            cursor = connection.execute("""INSERT INTO consultations (listing_id, customer_name, customer_phone, consulted_date, consultation_type, consultation_note, next_contact_date, consultation_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (listing_id, consultation["customer_name"], consultation["customer_phone"], consultation["consulted_date"], consultation["consultation_type"], consultation["consultation_note"], consultation.get("next_contact_date"), consultation["consultation_status"]))
            return cursor.lastrowid
    finally: connection.close()


def update_consultation(consultation_id: int, values: dict[str, Any], path: Path = DATABASE_PATH) -> None:
    ensure_database_schema(path); connection = get_connection(path)
    try:
        with connection:
            if connection.execute("UPDATE consultations SET customer_name = ?, customer_phone = ?, consultation_note = ?, next_contact_date = ?, consultation_status = ? WHERE id = ?", (values["customer_name"], values["customer_phone"], values["consultation_note"], values.get("next_contact_date"), values["consultation_status"], consultation_id)).rowcount != 1: raise ValueError("수정할 상담 기록을 찾을 수 없습니다.")
    finally: connection.close()


def delete_consultation(consultation_id: int, path: Path = DATABASE_PATH) -> None:
    """선택한 상담 기록 1건만 완전히 삭제한다."""
    ensure_database_schema(path); connection = get_connection(path)
    try:
        with connection:
            if connection.execute("DELETE FROM consultations WHERE id = ?", (consultation_id,)).rowcount != 1:
                raise ValueError("삭제할 상담 기록을 찾을 수 없습니다.")
    finally: connection.close()
