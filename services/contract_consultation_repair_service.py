"""성사 계약에 연결된 기존 상담을 안전하게 한 번 보정한다."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from storage.contract_repository import repair_successful_contract_consultations
from storage.database import DATABASE_PATH


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def repair_existing_successful_contract_consultations(path: Path = DATABASE_PATH) -> dict[str, int | str]:
    """운영 DB 보호 사본과 무결성 검사를 마친 뒤 성사 계약 상담을 보정한다."""
    if not path.exists():
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {path}")
    backup_directory = PROJECT_ROOT / "backups"
    backup_directory.mkdir(parents=True, exist_ok=True)
    backup_path = backup_directory / f"real_estate_before_contract_consultation_success_{datetime.now():%Y%m%d_%H%M%S}.db"
    source = sqlite3.connect(path)
    destination = sqlite3.connect(backup_path)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    verification = sqlite3.connect(backup_path)
    try:
        if verification.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("보호 사본의 SQLite 무결성 검사를 통과하지 못했습니다.")
    finally:
        verification.close()
    result = repair_successful_contract_consultations(path)
    return {**result, "backup_path": str(backup_path)}
