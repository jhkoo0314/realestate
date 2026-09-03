"""월별 광고비 기록의 저장·조회 기능."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from storage.database import DATABASE_PATH, ensure_database_schema, get_connection


def get_monthly_advertising_costs(*, year_month: str | None = None, path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    ensure_database_schema(path)
    connection = get_connection(path)
    try:
        if year_month:
            rows = connection.execute("SELECT id AS cost_id, year_month, advertising_channel, monthly_cost_manwon, memo, created_at, updated_at FROM monthly_advertising_costs WHERE year_month=? ORDER BY advertising_channel", (year_month,)).fetchall()
        else:
            rows = connection.execute("SELECT id AS cost_id, year_month, advertising_channel, monthly_cost_manwon, memo, created_at, updated_at FROM monthly_advertising_costs ORDER BY year_month DESC, advertising_channel").fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def save_monthly_advertising_cost(values: dict[str, Any], path: Path = DATABASE_PATH) -> int:
    ensure_database_schema(path)
    connection = get_connection(path)
    try:
        with connection:
            current = connection.execute("SELECT id FROM monthly_advertising_costs WHERE year_month=? AND advertising_channel=?", (values["year_month"], values["advertising_channel"])).fetchone()
            if current:
                connection.execute("UPDATE monthly_advertising_costs SET monthly_cost_manwon=?, memo=? WHERE id=?", (values["monthly_cost_manwon"], values.get("memo"), current["id"]))
                return current["id"]
            cursor = connection.execute("INSERT INTO monthly_advertising_costs (year_month, advertising_channel, monthly_cost_manwon, memo, created_at, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)", (values["year_month"], values["advertising_channel"], values["monthly_cost_manwon"], values.get("memo")))
            return cursor.lastrowid
    finally:
        connection.close()


def delete_monthly_advertising_cost(cost_id: int, path: Path = DATABASE_PATH) -> None:
    ensure_database_schema(path)
    connection = get_connection(path)
    try:
        with connection:
            if connection.execute("DELETE FROM monthly_advertising_costs WHERE id=?", (cost_id,)).rowcount != 1:
                raise ValueError("삭제할 월별 광고비 기록을 찾을 수 없습니다.")
    finally:
        connection.close()
