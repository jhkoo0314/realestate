"""상담 기록의 저장·조회 기능."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from storage.database import DATABASE_PATH, ensure_database_schema, get_connection
from services.record_number import record_id_from_query


def get_consultations(*, query: str = "", categories: list[str] | None = None, statuses: list[str] | None = None, progress_stages: list[str] | None = None, closed_reasons: list[str] | None = None, consulted_start: str | None = None, consulted_end: str | None = None, due_only: bool = False, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    ensure_database_schema(path)
    conditions, parameters = ["(c.listing_id IS NULL OR (b.is_active = 1 AND u.is_active = 1))"], []
    if keyword := query.strip():
        conditions.append("(b.building_name LIKE ? OR b.lot_address LIKE ? OR u.unit_number LIKE ? OR c.desired_area LIKE ? OR c.customer_name LIKE ? OR c.customer_phone LIKE ? OR c.id = ? OR c.listing_id = ?)")
        parameters.extend([f"%{keyword}%"] * 6 + [record_id_from_query(keyword, "S") or -1, record_id_from_query(keyword, "M") or -1])
    if categories:
        conditions.append(f"c.consultation_category IN ({', '.join('?' for _ in categories)})")
        parameters.extend(categories)
    if statuses:
        conditions.append(f"c.consultation_status IN ({', '.join('?' for _ in statuses)})")
        parameters.extend(statuses)
    if progress_stages:
        conditions.append(f"c.progress_stage IN ({', '.join('?' for _ in progress_stages)})")
        parameters.extend(progress_stages)
    if closed_reasons:
        conditions.append(f"c.closed_reason IN ({', '.join('?' for _ in closed_reasons)})")
        parameters.extend(closed_reasons)
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
            SELECT c.id AS consultation_id, c.listing_id, c.consultation_category, c.customer_name, c.customer_phone, c.consulted_date, c.consultation_type, c.consultation_source, c.consultation_note, c.desired_area, c.desired_room_type, c.desired_deposit_manwon, c.desired_monthly_rent_manwon, c.desired_available_from_date, c.next_contact_date, c.consultation_status, c.progress_stage, c.last_contacted_date, c.latest_visit_result, c.closed_reason, c.desired_room_types, c.required_features_note, c.created_at, c.updated_at, b.building_name, b.lot_address, u.unit_number, l.received_date, l.listing_status
            FROM consultations c LEFT JOIN listings l ON l.id = c.listing_id LEFT JOIN units u ON u.id = l.unit_id LEFT JOIN buildings b ON b.id = u.building_id
            WHERE {' AND '.join(conditions)} ORDER BY c.consulted_date DESC, c.id DESC
        """, parameters).fetchall()
        return [dict(row) for row in rows]
    finally: connection.close()


def get_consultation_detail(consultation_id: int, path: Path = DATABASE_PATH) -> dict[str, Any] | None:
    ensure_database_schema(path); connection = get_connection(path)
    try:
        row = connection.execute("""
            SELECT c.id AS consultation_id, c.listing_id, c.consultation_category, c.customer_name, c.customer_phone, c.consulted_date, c.consultation_type, c.consultation_source, c.consultation_note, c.desired_area, c.desired_room_type, c.desired_deposit_manwon, c.desired_monthly_rent_manwon, c.desired_available_from_date, c.next_contact_date, c.consultation_status, c.progress_stage, c.last_contacted_date, c.latest_visit_result, c.closed_reason, c.desired_room_types, c.required_features_note, EXISTS(SELECT 1 FROM contracts WHERE source_consultation_id = c.id) AS linked_contract_exists, b.building_name, b.lot_address, u.unit_number, l.received_date
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
            cursor = connection.execute("""INSERT INTO consultations (listing_id, consultation_category, customer_name, customer_phone, consulted_date, consultation_type, consultation_source, consultation_note, desired_area, desired_room_type, desired_deposit_manwon, desired_monthly_rent_manwon, desired_available_from_date, next_contact_date, consultation_status, progress_stage, last_contacted_date, closed_reason, desired_room_types, required_features_note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (listing_id, consultation["consultation_category"], consultation["customer_name"], consultation["customer_phone"], consultation["consulted_date"], consultation["consultation_type"], consultation.get("consultation_source"), consultation["consultation_note"], consultation.get("desired_area"), consultation.get("desired_room_type"), consultation.get("desired_deposit_manwon"), consultation.get("desired_monthly_rent_manwon"), consultation.get("desired_available_from_date"), consultation.get("next_contact_date"), consultation["consultation_status"], consultation.get("progress_stage"), consultation.get("last_contacted_date"), consultation.get("closed_reason"), consultation.get("desired_room_types"), consultation.get("required_features_note")))
            return cursor.lastrowid
    finally: connection.close()


def update_consultation(consultation_id: int, values: dict[str, Any], path: Path = DATABASE_PATH) -> None:
    ensure_database_schema(path); connection = get_connection(path)
    try:
        with connection:
            if connection.execute("UPDATE consultations SET customer_name = ?, customer_phone = ?, consultation_source = ?, consultation_note = ?, desired_area = ?, desired_room_type = ?, desired_room_types = ?, desired_deposit_manwon = ?, desired_monthly_rent_manwon = ?, desired_available_from_date = ?, next_contact_date = ?, consultation_status = ? WHERE id = ?", (values["customer_name"], values["customer_phone"], values.get("consultation_source"), values["consultation_note"], values.get("desired_area"), values.get("desired_room_type"), values.get("desired_room_types"), values.get("desired_deposit_manwon"), values.get("desired_monthly_rent_manwon"), values.get("desired_available_from_date"), values.get("next_contact_date"), values["consultation_status"], consultation_id)).rowcount != 1: raise ValueError("수정할 상담 기록을 찾을 수 없습니다.")
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


def close_legacy_consultation(consultation_id: int, closed_reason: str, path: Path = DATABASE_PATH) -> None:
    """기존 상담의 메모·상담일은 보존하고 종료 정보만 갱신한다."""
    ensure_database_schema(path); connection = get_connection(path)
    try:
        with connection:
            if connection.execute("UPDATE consultations SET consultation_status = '종료', next_contact_date = NULL, closed_reason = ? WHERE id = ?", (closed_reason, consultation_id)).rowcount != 1:
                raise ValueError("종료할 상담 기록을 찾을 수 없습니다.")
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


def get_consultation_activities(consultation_id: int, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    ensure_database_schema(path); connection = get_connection(path)
    try:
        rows = connection.execute("SELECT id AS activity_id, consultation_id, activity_date, activity_type, activity_note, stage_after_activity, visit_result, closed_reason, next_contact_date, created_at FROM consultation_activities WHERE consultation_id = ? ORDER BY activity_date DESC, id DESC", (consultation_id,)).fetchall()
        return [dict(row) for row in rows]
    finally: connection.close()


def add_consultation_activity(consultation_id: int, activity: dict[str, Any], path: Path = DATABASE_PATH) -> int:
    """후속 이력 추가와 상담 요약 갱신을 하나의 거래로 처리한다."""
    ensure_database_schema(path); connection = get_connection(path)
    try:
        with connection:
            if connection.execute("SELECT 1 FROM consultations WHERE id = ?", (consultation_id,)).fetchone() is None:
                raise ValueError("상담 기록을 찾을 수 없습니다.")
            cursor = connection.execute("INSERT INTO consultation_activities (consultation_id, activity_date, activity_type, activity_note, stage_after_activity, visit_result, closed_reason, next_contact_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (consultation_id, activity["activity_date"], activity["activity_type"], activity.get("activity_note"), activity["stage_after_activity"], activity.get("visit_result"), activity.get("closed_reason"), activity.get("next_contact_date")))
            _refresh_consultation_activity_summary(connection, consultation_id)
            return cursor.lastrowid
    finally: connection.close()


def _refresh_consultation_activity_summary(connection: Any, consultation_id: int) -> None:
    """남아 있는 가장 최근 후속 이력으로 상담 요약값을 맞춘다."""
    latest = connection.execute(
        """SELECT activity_date, stage_after_activity, visit_result, closed_reason, next_contact_date
           FROM consultation_activities
           WHERE consultation_id = ?
           ORDER BY activity_date DESC, id DESC LIMIT 1""",
        (consultation_id,),
    ).fetchone()
    if latest is None:
        return
    status = "종료" if latest["stage_after_activity"] in ("계약 완료", "종료") else "진행 중"
    connection.execute(
        """UPDATE consultations
           SET progress_stage = ?, last_contacted_date = ?, latest_visit_result = ?,
               closed_reason = ?, next_contact_date = ?, consultation_status = ?
           WHERE id = ?""",
        (latest["stage_after_activity"], latest["activity_date"], latest["visit_result"], latest["closed_reason"], latest["next_contact_date"], status, consultation_id),
    )


def update_consultation_activity(activity_id: int, consultation_id: int, activity: dict[str, Any], path: Path = DATABASE_PATH) -> None:
    """선택한 후속 이력만 수정하고 상담 요약값을 다시 계산한다."""
    ensure_database_schema(path); connection = get_connection(path)
    try:
        with connection:
            if connection.execute(
                """UPDATE consultation_activities
                   SET activity_date = ?, activity_type = ?, activity_note = ?, stage_after_activity = ?,
                       visit_result = ?, closed_reason = ?, next_contact_date = ?
                   WHERE id = ? AND consultation_id = ?""",
                (activity["activity_date"], activity["activity_type"], activity.get("activity_note"), activity["stage_after_activity"], activity.get("visit_result"), activity.get("closed_reason"), activity.get("next_contact_date"), activity_id, consultation_id),
            ).rowcount != 1:
                raise ValueError("수정할 후속 상담 이력을 찾을 수 없습니다.")
            _refresh_consultation_activity_summary(connection, consultation_id)
    finally: connection.close()


def delete_consultation_activity(activity_id: int, consultation_id: int, path: Path = DATABASE_PATH) -> None:
    """선택한 후속 이력만 삭제하고 남은 이력의 최신 상태를 상담 요약에 반영한다."""
    ensure_database_schema(path); connection = get_connection(path)
    try:
        with connection:
            if connection.execute("DELETE FROM consultation_activities WHERE id = ? AND consultation_id = ?", (activity_id, consultation_id)).rowcount != 1:
                raise ValueError("삭제할 후속 상담 이력을 찾을 수 없습니다.")
            _refresh_consultation_activity_summary(connection, consultation_id)
    finally: connection.close()


def get_consultation_delete_counts(consultation_id: int, path: Path = DATABASE_PATH) -> dict[str, int]:
    ensure_database_schema(path); connection = get_connection(path)
    try:
        return {"activities": connection.execute("SELECT COUNT(*) FROM consultation_activities WHERE consultation_id = ?", (consultation_id,)).fetchone()[0]}
    finally: connection.close()
