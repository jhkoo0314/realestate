"""내부 자동 ID를 업무 화면에서 일관된 번호로 표시한다."""

from __future__ import annotations


def format_record_number(prefix: str, record_id: int | None) -> str:
    """DB 기본키를 사람이 읽기 쉬운 업무번호로 바꾼다."""
    return f"{prefix}-{record_id:06d}" if record_id is not None else "-"


def listing_number(listing_id: int | None) -> str:
    return format_record_number("M", listing_id)


def contract_number(contract_id: int | None) -> str:
    return format_record_number("C", contract_id)


def consultation_number(consultation_id: int | None) -> str:
    return format_record_number("S", consultation_id)


def record_id_from_query(value: str, prefix: str) -> int | None:
    """`M-000123`처럼 완전 입력한 업무번호에서 DB ID를 읽는다."""
    normalized = value.strip().upper().replace(" ", "")
    expected_prefix = f"{prefix.upper()}-"
    if not normalized.startswith(expected_prefix):
        return None
    digits = normalized.removeprefix(expected_prefix)
    return int(digits) if digits.isdigit() and int(digits) > 0 else None
