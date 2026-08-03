"""계약 입력 검사와 저장 규칙."""

from __future__ import annotations

from datetime import date
from typing import Any

from storage.contract_repository import create_contract, update_contract_details, update_contract_status


CONTRACT_TYPES = ["일반 계약", "단기계약", "확인 필요"]
CONTRACT_STATUSES = ["계약 예정", "계약 진행", "계약 완료", "해지", "만료", "확인 필요"]


def _date_text(value: Any) -> str | None:
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip() if value else None


def validate_contract(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """시작일·종료일·개월 수를 검사해 저장 가능한 계약 값으로 만든다."""
    errors: list[str] = []
    contract_type = raw.get("contract_type")
    contract_status = raw.get("contract_status")
    start = _date_text(raw.get("contract_start_date"))
    end = _date_text(raw.get("contract_end_date"))
    term = raw.get("term_months")
    deposit = raw.get("contract_deposit_manwon")
    balance = raw.get("balance_manwon")
    if contract_type not in CONTRACT_TYPES:
        errors.append("계약 유형을 선택해 주세요.")
    if contract_status not in CONTRACT_STATUSES:
        errors.append("계약 상태를 선택해 주세요.")
    if not start:
        errors.append("계약 시작일을 입력해 주세요.")
    if start and end and end < start:
        errors.append("계약 종료일은 시작일보다 빠를 수 없습니다.")
    if term is not None and term <= 0:
        errors.append("계약 기간은 1개월 이상의 숫자로 입력해 주세요.")
    if deposit is not None and deposit < 0:
        errors.append("계약금은 0 이상의 숫자로 입력해 주세요.")
    if balance is not None and balance < 0:
        errors.append("잔금은 0 이상의 숫자로 입력해 주세요.")
    if errors:
        return None, errors
    note = str(raw.get("contract_note") or "").strip() or None
    return {
        "contract_type": contract_type,
        "contract_start_date": start,
        "contract_end_date": end,
        "term_months": int(term) if term is not None else None,
        "contract_status": contract_status,
        "contract_note": note,
        "contractor_contact": str(raw.get("contractor_contact") or "").strip() or None,
        "contract_deposit_manwon": int(deposit) if deposit is not None else None,
        "balance_manwon": int(balance) if balance is not None else None,
    }, []


def save_contract(listing_id: int, contract: dict[str, Any]) -> int:
    return create_contract(listing_id, contract)


def change_contract_status(contract_id: int, contract_status: str) -> None:
    if contract_status not in CONTRACT_STATUSES:
        raise ValueError("계약 상태를 선택해 주세요.")
    update_contract_status(contract_id, contract_status)


def change_contract_details(contract_id: int, values: dict[str, Any]) -> None:
    """선택한 계약의 내부 연락처와 계약금·잔금, 상태를 수정한다."""
    contract, errors = validate_contract({
        "contract_type": "일반 계약", "contract_start_date": date.today(),
        "contract_status": values.get("contract_status"),
        "contract_deposit_manwon": values.get("contract_deposit_manwon"),
        "balance_manwon": values.get("balance_manwon"),
        "contractor_contact": values.get("contractor_contact"),
    })
    if errors:
        raise ValueError(" ".join(errors))
    update_contract_details(contract_id, contract)
