"""지번 지역·번지 번호의 입력, 저장용 결합, 안전한 표시 분리 기능."""

from __future__ import annotations

import re


_LOT_ADDRESS_PATTERN = re.compile(r"^(?P<area>.+?)\s+(?P<number>(?:산\s*)?\d+(?:-\d+)?)$")


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split())


def combine_lot_address(area: object, number: object) -> str:
    """지번 지역과 번지 번호를 기존 저장·검색용 지번 문자열로 합친다."""
    return " ".join(part for part in (_clean_text(area), _clean_text(number)) if part)


def split_lot_address(value: object) -> tuple[str, str]:
    """기존 지번을 표시용 지역·번호로 나눈다.

    형식이 분명하지 않은 오래된 값은 번호를 비워 원문을 지역 칸에 남긴다.
    """
    lot_address = _clean_text(value)
    match = _LOT_ADDRESS_PATTERN.match(lot_address)
    if not match:
        return lot_address, ""
    return match.group("area"), _clean_text(match.group("number"))
