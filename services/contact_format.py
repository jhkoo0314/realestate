"""내부 연락처 입력을 읽기 쉬운 전화번호 형식으로 정리하는 공통 함수."""

from __future__ import annotations

import re


def format_phone_number(value: str) -> str:
    """숫자로 된 국내 전화번호에 하이픈을 넣고, 다른 형식의 값은 그대로 둔다."""
    if not value or not re.fullmatch(r"[\d\s()-]+", value):
        return value
    digits = re.sub(r"\D", "", value)
    if digits.startswith("02"):
        if len(digits) <= 2:
            return digits
        if len(digits) <= 6:
            return f"02-{digits[2:]}"
        return f"02-{digits[2:-4]}-{digits[-4:]}"
    if len(digits) <= 3:
        return digits
    if len(digits) <= 7:
        return f"{digits[:3]}-{digits[3:]}"
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
