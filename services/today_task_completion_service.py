"""오늘 할 일 완료 체크 저장 규칙."""

from services.backup_service import create_daily_backup
from storage.today_task_completion_repository import set_task_completed


def change_today_task_completion(task_key: str, completed: bool) -> None:
    set_task_completed(task_key, completed)
    create_daily_backup()
