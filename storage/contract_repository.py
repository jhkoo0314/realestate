"""계약 기록의 저장·조회 기능."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from storage.database import DATABASE_PATH, ensure_database_schema, get_connection
from services.record_number import record_id_from_query


def _apply_linked_listing_status(connection, listing_id: int, contract_status: str) -> None:
    """계약 상태가 바뀔 때만 연결 매물의 현재 상태를 안전하게 반영한다."""
    if contract_status == "계약 진행":
        connection.execute("UPDATE listings SET listing_status='계약 진행 중' WHERE id=? AND closed_date IS NULL AND listing_status NOT IN ('계약 완료', '종료')", (listing_id,))
    elif contract_status == "계약 완료":
        connection.execute("UPDATE listings SET listing_status='계약 완료', closed_date=?, close_reason='계약 완료' WHERE id=? AND closed_date IS NULL", (date.today().isoformat(), listing_id))
    elif contract_status in ("해지", "만료"):
        connection.execute("UPDATE listings SET listing_status='공실' WHERE id=? AND closed_date IS NULL AND listing_status='계약 진행 중'", (listing_id,))


def get_contracts(*, query: str = "", statuses: list[str] | None = None, end_start: str | None = None, end_end: str | None = None, expiring_within_days: int | None = None, unit_id: int | None = None, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    ensure_database_schema(path)
    conditions, parameters = ["b.is_active = 1", "u.is_active = 1"], []
    if keyword := query.strip():
        conditions.append("(b.building_name LIKE ? OR b.lot_address LIKE ? OR u.unit_number LIKE ? OR c.id = ? OR c.listing_id = ?)")
        parameters.extend([f"%{keyword}%"] * 3 + [record_id_from_query(keyword, "C") or -1, record_id_from_query(keyword, "M") or -1])
    if statuses:
        conditions.append(f"c.contract_status IN ({', '.join('?' for _ in statuses)})")
        parameters.extend(statuses)
    if end_start: conditions.append("c.contract_end_date >= ?"); parameters.append(end_start)
    if end_end: conditions.append("c.contract_end_date <= ?"); parameters.append(end_end)
    if expiring_within_days is not None:
        if expiring_within_days < 0: raise ValueError("계약 만료 예정 기간은 0일 이상이어야 합니다.")
        conditions.extend(["c.contract_end_date IS NOT NULL", "c.contract_end_date >= ?", "c.contract_end_date <= ?", "c.contract_status NOT IN ('해지', '만료')"])
        parameters.extend([date.today().isoformat(), (date.today() + timedelta(days=expiring_within_days)).isoformat()])
    if unit_id is not None: conditions.append("u.id = ?"); parameters.append(unit_id)
    connection = get_connection(path)
    try:
        rows = connection.execute(f"""
            SELECT c.id AS contract_id, c.listing_id, c.contract_type, c.contract_progress_date, c.formal_contract_date, c.contract_start_date, c.contract_end_date, c.term_months, c.contract_status, c.contract_note, c.contractor_contact, c.contract_deposit_manwon, c.provisional_deposit_manwon, c.remaining_deposit_due_date, c.balance_manwon, c.balance_due_date, c.created_at, c.updated_at, b.building_name, b.lot_address, u.unit_number, l.received_date, l.listing_status
            FROM contracts c JOIN listings l ON l.id = c.listing_id JOIN units u ON u.id = l.unit_id JOIN buildings b ON b.id = u.building_id
            WHERE {' AND '.join(conditions)} ORDER BY COALESCE(c.contract_progress_date, c.formal_contract_date, c.contract_start_date, c.created_at) DESC, c.id DESC
        """, parameters).fetchall()
        return [dict(row) for row in rows]
    finally: connection.close()


def get_unit_contracts(unit_id: int, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    return get_contracts(unit_id=unit_id, path=path)


def create_contract(listing_id: int, contract: dict[str, Any], path: Path = DATABASE_PATH) -> int:
    ensure_database_schema(path); connection = get_connection(path)
    try:
        with connection:
            if connection.execute("SELECT 1 FROM listings WHERE id = ?", (listing_id,)).fetchone() is None: raise ValueError("연결할 매물 기록을 찾을 수 없습니다. 다시 선택해 주세요.")
            cursor = connection.execute("""INSERT INTO contracts (listing_id, contract_type, contract_progress_date, formal_contract_date, contract_start_date, contract_end_date, term_months, contract_status, contract_note, contractor_contact, contract_deposit_manwon, provisional_deposit_manwon, remaining_deposit_due_date, balance_manwon, balance_due_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (listing_id, contract["contract_type"], contract.get("contract_progress_date"), contract.get("formal_contract_date"), contract.get("contract_start_date"), contract.get("contract_end_date"), contract.get("term_months"), contract["contract_status"], contract.get("contract_note"), contract.get("contractor_contact"), contract.get("contract_deposit_manwon"), contract.get("provisional_deposit_manwon"), contract.get("remaining_deposit_due_date"), contract.get("balance_manwon"), contract.get("balance_due_date")))
            _apply_linked_listing_status(connection, listing_id, contract["contract_status"])
            return cursor.lastrowid
    finally: connection.close()


def update_contract_status(contract_id: int, contract_status: str, path: Path = DATABASE_PATH) -> None:
    if not contract_status: raise ValueError("계약 상태를 선택해 주세요.")
    update_contract_details(contract_id, {"contract_status": contract_status}, path)


def update_contract_details(contract_id: int, values: dict[str, Any], path: Path = DATABASE_PATH) -> None:
    ensure_database_schema(path); connection = get_connection(path)
    try:
        with connection:
            current = connection.execute("SELECT listing_id, contract_type, contract_progress_date, formal_contract_date, contract_start_date, contract_end_date, term_months, contract_status, contract_note, contractor_contact, contract_deposit_manwon, provisional_deposit_manwon, remaining_deposit_due_date, balance_manwon, balance_due_date FROM contracts WHERE id = ?", (contract_id,)).fetchone()
            if current is None: raise ValueError("수정할 계약 기록을 찾을 수 없습니다.")
            contract_status = values.get("contract_status", current["contract_status"])
            connection.execute("""UPDATE contracts SET contract_type=?, contract_progress_date=?, formal_contract_date=?, contract_start_date=?, contract_end_date=?, term_months=?, contract_status=?, contract_note=?, contractor_contact=?, contract_deposit_manwon=?, provisional_deposit_manwon=?, remaining_deposit_due_date=?, balance_manwon=?, balance_due_date=? WHERE id=?""", (values.get("contract_type", current["contract_type"]), values.get("contract_progress_date", current["contract_progress_date"]), values.get("formal_contract_date", current["formal_contract_date"]), values.get("contract_start_date", current["contract_start_date"]), values.get("contract_end_date", current["contract_end_date"]), values.get("term_months", current["term_months"]), contract_status, values.get("contract_note", current["contract_note"]), values.get("contractor_contact", current["contractor_contact"]), values.get("contract_deposit_manwon", current["contract_deposit_manwon"]), values.get("provisional_deposit_manwon", current["provisional_deposit_manwon"]), values.get("remaining_deposit_due_date", current["remaining_deposit_due_date"]), values.get("balance_manwon", current["balance_manwon"]), values.get("balance_due_date", current["balance_due_date"]), contract_id))
            _apply_linked_listing_status(connection, current["listing_id"], contract_status)
    finally: connection.close()


def delete_contract(contract_id: int, path: Path = DATABASE_PATH) -> None:
    """선택한 계약 기록 1건만 완전히 삭제한다."""
    ensure_database_schema(path); connection = get_connection(path)
    try:
        with connection:
            if connection.execute("DELETE FROM contracts WHERE id = ?", (contract_id,)).rowcount != 1:
                raise ValueError("삭제할 계약 기록을 찾을 수 없습니다.")
    finally: connection.close()
