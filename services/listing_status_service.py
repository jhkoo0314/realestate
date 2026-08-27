"""날짜 경과에 따른 현재 매물 상태 자동 갱신 규칙."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from services.backup_service import create_daily_backup
from storage.database import DATABASE_PATH
from storage.listing_repository import mark_past_due_move_out_listings_vacant


def apply_past_due_move_out_statuses(
    *,
    reference_date: date | None = None,
    path: Path = DATABASE_PATH,
    create_backup: bool = True,
) -> int:
    """지난 퇴실 예정 매물을 공실·즉시입주로 정리하고 변경 시 백업한다."""
    changed = mark_past_due_move_out_listings_vacant(reference_date=reference_date, path=path)
    if changed and create_backup:
        create_daily_backup(database_path=path)
    return changed
