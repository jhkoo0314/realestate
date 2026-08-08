"""오늘 할 일 완료 체크의 저장·조회 기능."""

from __future__ import annotations

from pathlib import Path

from storage.database import DATABASE_PATH, ensure_database_schema, get_connection


def get_completed_task_keys(task_keys: list[str], path: Path = DATABASE_PATH) -> set[str]:
    if not task_keys:
        return set()
    ensure_database_schema(path)
    connection = get_connection(path)
    try:
        placeholders = ", ".join("?" for _ in task_keys)
        rows = connection.execute(f"SELECT task_key FROM today_task_completions WHERE task_key IN ({placeholders})", task_keys).fetchall()
        return {row["task_key"] for row in rows}
    finally:
        connection.close()


def set_task_completed(task_key: str, completed: bool, path: Path = DATABASE_PATH) -> None:
    ensure_database_schema(path)
    connection = get_connection(path)
    try:
        with connection:
            if completed:
                connection.execute("INSERT OR IGNORE INTO today_task_completions (task_key) VALUES (?)", (task_key,))
            else:
                connection.execute("DELETE FROM today_task_completions WHERE task_key = ?", (task_key,))
    finally:
        connection.close()
