"""계약 입력 검사와 저장 규칙."""

from __future__ import annotations

from datetime import date
from typing import Any

from storage.contract_repository import create_contract, delete_contract as delete_contract_record, update_contract_details, update_contract_status


CONTRACT_TYPES = ["일반 계약", "단기계약", "확인 필요"]
CONTRACT_STATUSES = ["계약 예정", "계약 진행", "계약 완료", "해지", "만료", "확인 필요"]


def _date_text(value: Any) -> str | None:
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip() if value else None


def validate_contract(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """계약 진행·정식 계약·임대차 기간을 검사해 저장 가능한 값으로 만든다."""
    errors: list[str] = []
    contract_type = raw.get("contract_type")
    contract_status = raw.get("contract_status")
    progress = _date_text(raw.get("contract_progress_date"))
    formal = _date_text(raw.get("formal_contract_date"))
    start = _date_text(raw.get("contract_start_date"))
    end = _date_text(raw.get("contract_end_date"))
    term = raw.get("term_months")
    deposit = raw.get("contract_deposit_manwon")
    provisional_deposit = raw.get("provisional_deposit_manwon")
    remaining_deposit_due_date = _date_text(raw.get("remaining_deposit_due_date"))
    balance = raw.get("balance_manwon")
    if contract_type not in CONTRACT_TYPES:
        errors.append("계약 유형을 선택해 주세요.")
    if contract_status not in CONTRACT_STATUSES:
        errors.append("계약 상태를 선택해 주세요.")
    if progress and formal and formal < progress:
        errors.append("정식 계약일은 계약 진행 시작일보다 빠를 수 없습니다.")
    if progress and remaining_deposit_due_date and remaining_deposit_due_date < progress:
        errors.append("계약금 추가 수령 예정일은 계약 진행 시작일보다 빠를 수 없습니다.")
    if start and end and end < start:
        errors.append("계약 종료일은 시작일보다 빠를 수 없습니다.")
    if term is not None and term <= 0:
        errors.append("계약 기간은 1개월 이상의 숫자로 입력해 주세요.")
    if deposit is not None and deposit < 0:
        errors.append("계약금은 0 이상의 숫자로 입력해 주세요.")
    if provisional_deposit is not None and provisional_deposit < 0:
        errors.append("가계약금 수령액은 0 이상의 숫자로 입력해 주세요.")
    if provisional_deposit is not None and deposit is None:
        errors.append("가계약금을 기록하려면 계약금 전체를 먼저 입력해 주세요.")
    if deposit is not None and provisional_deposit is not None and provisional_deposit > deposit:
        errors.append("가계약금 수령액은 계약금 전체보다 클 수 없습니다.")
    if balance is not None and balance < 0:
        errors.append("잔금은 0 이상의 숫자로 입력해 주세요.")
    if errors:
        return None, errors
    note = str(raw.get("contract_note") or "").strip() or None
    return {
        "contract_type": contract_type,
        "contract_progress_date": progress,
        "formal_contract_date": formal,
        "contract_start_date": start,
        "contract_end_date": end,
        "term_months": int(term) if term is not None else None,
        "contract_status": contract_status,
        "contract_note": note,
        "contractor_contact": str(raw.get("contractor_contact") or "").strip() or None,
        "contract_deposit_manwon": int(deposit) if deposit is not None else None,
        "provisional_deposit_manwon": int(provisional_deposit) if provisional_deposit is not None else None,
        "remaining_deposit_due_date": remaining_deposit_due_date,
        "balance_manwon": int(balance) if balance is not None else None,
    }, []


def save_contract(listing_id: int, contract: dict[str, Any]) -> int:
    return create_contract(listing_id, contract)


def change_contract_status(contract_id: int, contract_status: str) -> None:
    if contract_status not in CONTRACT_STATUSES:
        raise ValueError("계약 상태를 선택해 주세요.")
    update_contract_status(contract_id, contract_status)


def change_contract_details(contract_id: int, values: dict[str, Any]) -> None:
    """선택한 계약의 진행 단계, 기간, 내부정보를 수정한다."""
    contract, errors = validate_contract(values)
    if errors:
        raise ValueError(" ".join(errors))
    update_contract_details(contract_id, contract)


def delete_contract(contract_id: int) -> None:
    """선택한 계약 기록을 완전히 삭제한다."""
    delete_contract_record(contract_id)
