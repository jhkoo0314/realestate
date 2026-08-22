"""상담 입력 검사와 저장 규칙."""

from __future__ import annotations

from datetime import date
from typing import Any

from storage.consultation_repository import add_consultation_activity, close_legacy_consultation as close_legacy_consultation_record, create_consultation, delete_consultation as delete_consultation_record, delete_consultation_activity as delete_consultation_activity_record, link_consultation_to_listing as link_consultation_record, update_consultation, update_consultation_activity as update_consultation_activity_record, update_consultation_follow_up, update_consultation_status
from services.backup_service import create_daily_backup


CONSULTATION_TYPES = ["전화", "문자", "방문", "기타"]
CONSULTATION_STATUSES = ["진행 중", "보류", "종료", "확인 필요"]
CONSULTATION_CATEGORIES = ["매물 상담", "일반 상담"]
CONSULTATION_SOURCES = ["미입력", "직방", "다방", "당근", "네이버", "워크인", "타부동산 연계"]
DESIRED_AREA_OPTIONS = ["북수리", "장재리", "공수리", "월천지구", "탕정역권", "기타 배방", "탕정", "기타"]
DESIRED_ROOM_TYPE_OPTIONS = ["원룸", "투베이", "투룸", "쓰리룸", "주인세대", "기타"]
# 계약 진행·완료는 계약관리에서만 자동 반영한다. 과거 저장값은 화면에서 계속 표시한다.
PROGRESS_STAGES = ["신규 문의", "조건 확인", "방문 예정", "방문 완료", "검토 중", "종료"]
LEGACY_PROGRESS_STAGES = ["계약 진행", "계약 완료"]
VISIT_RESULTS = ["만족", "추가 매물 요청", "가격 부담", "조건 불일치", "방문 취소", "기타"]
CLOSED_REASONS = ["가격", "위치", "입주일", "옵션·구조", "계약완료", "타 매물 계약", "연락 두절", "단순 변심", "기타"]


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _date_text(value: Any) -> str | None:
    return value.isoformat() if isinstance(value, date) else _text(value)


def validate_consultation(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    name = _text(raw.get("customer_name")) or "미입력"
    phone = _text(raw.get("customer_phone")) or "미입력"
    note = _text(raw.get("consultation_note")) or "미입력"
    consulted_date, next_contact = _date_text(raw.get("consulted_date")) or date.today().isoformat(), _date_text(raw.get("next_contact_date"))
    category = raw.get("consultation_category", "매물 상담")
    deposit, monthly_rent = raw.get("desired_deposit_manwon"), raw.get("desired_monthly_rent_manwon")
    desired_available_from_date = _date_text(raw.get("desired_available_from_date"))
    consultation_type = raw.get("consultation_type") if raw.get("consultation_type") in CONSULTATION_TYPES else "기타"
    consultation_status = raw.get("consultation_status") if raw.get("consultation_status") in CONSULTATION_STATUSES else "확인 필요"
    consultation_source = raw.get("consultation_source") if raw.get("consultation_source") in CONSULTATION_SOURCES else "미입력"
    progress_stage = raw.get("progress_stage") if raw.get("progress_stage") in [*PROGRESS_STAGES, *LEGACY_PROGRESS_STAGES] else "신규 문의"
    closed_reason = raw.get("closed_reason") if raw.get("closed_reason") in CLOSED_REASONS else None
    if progress_stage == "종료":
        consultation_status = "종료"
        next_contact = None
    if category not in CONSULTATION_CATEGORIES: category = "매물 상담"
    if deposit is not None and deposit < 0: errors.append("희망 보증금은 0 이상의 숫자로 입력해 주세요.")
    if monthly_rent is not None and monthly_rent < 0: errors.append("희망 월세는 0 이상의 숫자로 입력해 주세요.")
    if errors:
        return None, errors
    return {
        "consultation_category": category, "customer_name": name, "customer_phone": phone, "consulted_date": consulted_date,
        "consultation_type": consultation_type, "consultation_source": consultation_source, "consultation_note": note,
        "desired_area": _text(raw.get("desired_area")), "desired_room_type": _text(raw.get("desired_room_type")),
        "desired_deposit_manwon": int(deposit) if deposit is not None else None,
        "desired_monthly_rent_manwon": int(monthly_rent) if monthly_rent is not None else None,
        "desired_available_from_date": desired_available_from_date,
        "next_contact_date": next_contact, "consultation_status": consultation_status,
        "progress_stage": progress_stage, "last_contacted_date": consulted_date, "closed_reason": closed_reason if progress_stage == "종료" else None,
        "desired_room_types": _text(raw.get("desired_room_types")), "required_features_note": _text(raw.get("required_features_note")),
    }, []


def save_consultation(listing_id: int | None, consultation: dict[str, Any]) -> int:
    result = create_consultation(listing_id, consultation)
    create_daily_backup()
    return result


def save_consultation_changes(consultation_id: int, values: dict[str, Any]) -> None:
    consultation, errors = validate_consultation({**values, "consulted_date": date.today(), "consultation_type": "기타", "consultation_category": values.get("consultation_category", "매물 상담")})
    if errors:
        raise ValueError(" ".join(errors))
    update_consultation(consultation_id, consultation)
    create_daily_backup()


def change_consultation_status(consultation_id: int, consultation_status: str) -> None:
    if consultation_status not in CONSULTATION_STATUSES:
        raise ValueError("상담 상태를 선택해 주세요.")
    update_consultation_status(consultation_id, consultation_status)
    create_daily_backup()


def change_consultation_follow_up(consultation_id: int, consultation_status: str, next_contact_date: str | None) -> None:
    if consultation_status not in CONSULTATION_STATUSES:
        raise ValueError("상담 상태를 선택해 주세요.")
    if next_contact_date:
        try:
            date.fromisoformat(next_contact_date)
        except ValueError as error:
            raise ValueError("다음 연락일 형식이 올바르지 않습니다.") from error
    update_consultation_follow_up(consultation_id, consultation_status, next_contact_date)
    create_daily_backup()


def delete_consultation(consultation_id: int) -> None:
    """선택한 상담 기록을 완전히 삭제한다."""
    delete_consultation_record(consultation_id)
    create_daily_backup()


def link_consultation_to_listing(consultation_id: int, listing_id: int) -> None:
    """일반 상담에 나중에 선택한 매물 기록을 연결한다."""
    link_consultation_record(consultation_id, listing_id)
    create_daily_backup()


def validate_consultation_activity(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    activity_date = _date_text(raw.get("activity_date")) or date.today().isoformat()
    activity_type = raw.get("activity_type") if raw.get("activity_type") in CONSULTATION_TYPES else None
    stage = raw.get("stage_after_activity") if raw.get("stage_after_activity") in [*PROGRESS_STAGES, *LEGACY_PROGRESS_STAGES] else None
    visit_result = raw.get("visit_result") if raw.get("visit_result") in VISIT_RESULTS else None
    closed_reason = raw.get("closed_reason") if raw.get("closed_reason") in CLOSED_REASONS else None
    next_contact_date = _date_text(raw.get("next_contact_date"))
    if not activity_type: errors.append("상담 방식을 선택해 주세요.")
    if not stage: errors.append("결과 단계를 선택해 주세요.")
    if stage == "종료":
        next_contact_date = None
    if errors:
        return None, errors
    return {"activity_date": activity_date, "activity_type": activity_type, "activity_note": _text(raw.get("activity_note")), "stage_after_activity": stage, "visit_result": visit_result, "closed_reason": closed_reason, "next_contact_date": next_contact_date, "consultation_status": "종료" if stage == "종료" else "진행 중"}, []


def save_consultation_activity(consultation_id: int, activity: dict[str, Any]) -> int:
    result = add_consultation_activity(consultation_id, activity)
    create_daily_backup()
    return result


def save_consultation_activity_changes(activity_id: int, consultation_id: int, activity: dict[str, Any]) -> None:
    update_consultation_activity_record(activity_id, consultation_id, activity)
    create_daily_backup()


def delete_consultation_activity(activity_id: int, consultation_id: int) -> None:
    delete_consultation_activity_record(activity_id, consultation_id)
    create_daily_backup()


def close_legacy_consultation(consultation_id: int, closed_reason: str | None) -> None:
    if closed_reason is not None and closed_reason not in CLOSED_REASONS:
        raise ValueError("종료 사유 값을 확인해 주세요.")
    close_legacy_consultation_record(consultation_id, closed_reason)
    create_daily_backup()
