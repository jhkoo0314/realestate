"""OneDrive에 보관할 SQLite 일일 순환 백업."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

from storage.database import DATABASE_PATH


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGING_DIRECTORY = PROJECT_ROOT / "backups" / ".staging"
LOG_DIRECTORY = PROJECT_ROOT / "logs"
STATUS_PATH = LOG_DIRECTORY / "backup_status.json"
LOG_PATH = LOG_DIRECTORY / "backup.log"
BACKUP_PREFIX = "real_estate_"
BACKUP_SUFFIX = ".db"
RETENTION_DAYS = 10
_backup_lock = Lock()


def get_backup_directory() -> Path:
    configured = os.environ.get("REALESTATE_BACKUP_DIR")
    if configured:
        return Path(configured)
    one_drive = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer")
    if not one_drive:
        raise FileNotFoundError("OneDrive 동기화 폴더를 찾을 수 없습니다. OneDrive 로그인 상태를 확인해 주세요.")
    return Path(one_drive) / "Documents" / "매물관리백업" / "daily"


def _write_status(status: dict[str, Any]) -> None:
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{status['recorded_at']} | {'성공' if status['success'] else '실패'} | {status['message']}\n")


def get_backup_status() -> dict[str, Any] | None:
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _backup_file_name(now: datetime) -> str:
    return f"{BACKUP_PREFIX}{now.date().isoformat()}{BACKUP_SUFFIX}"


def _verify_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        result = connection.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        connection.close()
    if result != "ok":
        raise ValueError(f"SQLite 무결성 검사 실패: {result}")


def _prune_old_backups(directory: Path) -> int:
    backups = sorted(
        (path for path in directory.glob(f"{BACKUP_PREFIX}????-??-??{BACKUP_SUFFIX}") if path.is_file()),
        key=lambda path: path.name,
        reverse=True,
    )
    removed = 0
    for path in backups[RETENTION_DAYS:]:
        path.unlink()
        removed += 1
    return removed


def create_daily_backup(
    *,
    database_path: Path = DATABASE_PATH,
    backup_directory: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """일관된 SQLite 사본을 만든 뒤 OneDrive 날짜별 백업 파일을 갱신한다.

    백업 실패는 이미 완료된 업무 저장을 되돌리지 않는다. 결과는 상태 파일과 로그에 남긴다.
    """
    created_at = now or datetime.now()
    status: dict[str, Any] = {"recorded_at": created_at.isoformat(timespec="seconds"), "success": False}
    with _backup_lock:
        staging_path: Path | None = None
        partial_path: Path | None = None
        try:
            target_directory = backup_directory or get_backup_directory()
            if not database_path.exists():
                raise FileNotFoundError(f"원본 데이터 파일을 찾을 수 없습니다: {database_path}")
            target_directory.mkdir(parents=True, exist_ok=True)
            STAGING_DIRECTORY.mkdir(parents=True, exist_ok=True)
            final_path = target_directory / _backup_file_name(created_at)
            staging_path = STAGING_DIRECTORY / f"{final_path.name}.{os.getpid()}.partial"
            partial_path = target_directory / f".{final_path.name}.{os.getpid()}.partial"
            for path in (staging_path, partial_path):
                if path.exists():
                    path.unlink()

            source = sqlite3.connect(database_path)
            destination = sqlite3.connect(staging_path)
            try:
                source.backup(destination)
            finally:
                destination.close()
                source.close()
            _verify_database(staging_path)
            shutil.copy2(staging_path, partial_path)
            _verify_database(partial_path)
            os.replace(partial_path, final_path)
            removed = _prune_old_backups(target_directory)
            status.update({
                "success": True,
                "message": f"백업 완료: {final_path.name}" + (f" · 오래된 백업 {removed}개 정리" if removed else ""),
                "backup_path": str(final_path),
                "backup_size": final_path.stat().st_size,
                "completed_at": datetime.now().isoformat(timespec="seconds"),
            })
        except Exception as error:
            status.update({"message": f"백업 실패: {error}", "completed_at": datetime.now().isoformat(timespec="seconds")})
        finally:
            for path in (staging_path, partial_path):
                if path and path.exists():
                    path.unlink(missing_ok=True)
            _write_status(status)
    return status
