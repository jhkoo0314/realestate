"""매물 회차별 현재 광고 현황의 저장·조회 기능."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from storage.database import DATABASE_PATH, ensure_database_schema, get_connection


def get_advertisements(*, query: str = "", channels: list[str] | None = None, channel_query: str = "", statuses: list[str] | None = None, listing_id: int | None = None, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    ensure_database_schema(path)
    conditions, parameters = ["b.is_active=1", "u.is_active=1", "l.closed_date IS NULL", "l.listing_status NOT IN ('계약 완료', '종료')"], []
    if keyword := query.strip():
        conditions.append("(b.building_name LIKE ? OR b.lot_address LIKE ? OR u.unit_number LIKE ? OR u.unit_number_normalized LIKE ?)")
        parameters.extend([f"%{keyword}%"] * 4)
    if channels:
        conditions.append(f"a.advertising_channel IN ({', '.join('?' for _ in channels)})")
        parameters.extend(channels)
    if custom_channel := channel_query.strip():
        conditions.append("a.advertising_channel LIKE ?")
        parameters.append(f"%{custom_channel}%")
    if statuses:
        conditions.append(f"a.advertising_status IN ({', '.join('?' for _ in statuses)})")
        parameters.extend(statuses)
    if listing_id is not None:
        conditions.append("a.listing_id=?")
        parameters.append(listing_id)
    connection = get_connection(path)
    try:
        rows = connection.execute(f"""
            SELECT a.id AS advertisement_id, a.listing_id, a.advertising_channel, a.advertising_status, a.last_checked_date,
                   b.building_name, b.lot_address, u.unit_number, l.received_date, l.listing_status
            FROM listing_advertisements a
            JOIN listings l ON l.id=a.listing_id JOIN units u ON u.id=l.unit_id JOIN buildings b ON b.id=u.building_id
            WHERE {' AND '.join(conditions)}
            ORDER BY b.building_name, b.lot_address, u.unit_number_normalized, a.advertising_channel
        """, parameters).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def create_advertisement(listing_id: int, advertising_channel: str, advertising_status: str, last_checked_date: str | None, path: Path = DATABASE_PATH) -> int:
    ensure_database_schema(path)
    connection = get_connection(path)
    try:
        with connection:
            listing = connection.execute("SELECT 1 FROM listings WHERE id=? AND closed_date IS NULL AND listing_status NOT IN ('계약 완료', '종료')", (listing_id,)).fetchone()
            if listing is None:
                raise ValueError("현재 운영 중인 매물 기록에만 광고 현황을 연결할 수 있습니다.")
            if connection.execute("SELECT 1 FROM listing_advertisements WHERE listing_id=? AND advertising_channel=?", (listing_id, advertising_channel)).fetchone():
                raise ValueError("같은 매물에 해당 광고 채널이 이미 있습니다. 아래 목록에서 상태를 수정해 주세요.")
            cursor = connection.execute("INSERT INTO listing_advertisements (listing_id, advertising_channel, advertising_status, last_checked_date) VALUES (?, ?, ?, ?)", (listing_id, advertising_channel, advertising_status, last_checked_date))
            return cursor.lastrowid
    finally:
        connection.close()


def update_advertisement(advertisement_id: int, advertising_status: str, last_checked_date: str | None, path: Path = DATABASE_PATH) -> None:
    ensure_database_schema(path)
    connection = get_connection(path)
    try:
        with connection:
            if connection.execute("UPDATE listing_advertisements SET advertising_status=?, last_checked_date=? WHERE id=?", (advertising_status, last_checked_date, advertisement_id)).rowcount != 1:
                raise ValueError("수정할 광고 현황을 찾을 수 없습니다.")
    finally:
        connection.close()


def delete_advertisement(advertisement_id: int, path: Path = DATABASE_PATH) -> None:
    ensure_database_schema(path)
    connection = get_connection(path)
    try:
        with connection:
            if connection.execute("DELETE FROM listing_advertisements WHERE id=?", (advertisement_id,)).rowcount != 1:
                raise ValueError("삭제할 광고 현황을 찾을 수 없습니다.")
    finally:
        connection.close()
