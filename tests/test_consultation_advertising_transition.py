"""상담 표준 입력과 광고관리 전환의 핵심 저장 규칙 확인."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.advertisement_cost_service import validate_monthly_advertising_cost
from services.advertisement_copy_service import generate_lead_ad_copy
from services.consultation_service import validate_consultation, validate_consultation_activity
from storage.advertisement_cost_repository import get_monthly_advertising_costs, save_monthly_advertising_cost
from storage.consultation_repository import create_consultation, get_consultation_detail
from storage.database import DATABASE_PATH, get_connection, initialize_database


def run() -> None:
    with tempfile.TemporaryDirectory() as directory:
        database_path = Path(directory) / "transition.db"
        shutil.copy2(DATABASE_PATH, database_path)
        initialize_database(database_path)
        connection = get_connection(database_path)
        try:
            assert connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='listing_advertisements'").fetchone() is None
            assert connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='monthly_advertising_costs'").fetchone() is not None
        finally:
            connection.close()

        consultation, errors = validate_consultation({
            "consultation_category": "일반 상담", "consulted_date": "2026-08-22", "consultation_type": "전화",
            "consultation_source": "당근", "consultation_note": "미입력", "progress_stage": "종료",
            "closed_reason": None, "desired_area": "북수리 | 기타: 배방역", "desired_room_type": "원룸",
            "desired_room_types": "원룸 | 투룸",
        })
        assert not errors and consultation is not None
        consultation_id = create_consultation(None, consultation, database_path)
        detail = get_consultation_detail(consultation_id, database_path)
        assert detail and detail["desired_room_types"] == "원룸 | 투룸" and detail["closed_reason"] is None

        _, errors = validate_consultation_activity({"activity_date": "2026-08-22", "activity_type": "전화", "stage_after_activity": "종료", "closed_reason": None})
        assert "상담 종료 사유를 선택해 주세요." in errors
        activity, errors = validate_consultation_activity({"activity_date": "2026-08-22", "activity_type": "전화", "stage_after_activity": "종료", "closed_reason": "기타"})
        assert not errors and activity is not None

        cost, errors = validate_monthly_advertising_cost({"year_month": "2026-08-01", "channel_choice": "당근", "monthly_cost_manwon": 100, "memo": "검증"})
        assert not errors and cost is not None
        save_monthly_advertising_cost(cost, database_path)
        saved_cost = next(item for item in get_monthly_advertising_costs(path=database_path) if item["year_month"] == "2026-08" and item["advertising_channel"] == "당근")
        assert saved_cost["monthly_cost_manwon"] == 100

    copy = generate_lead_ad_copy(
        location="장재리 1684", room_type="원룸", title_template="", transaction_type="월세",
        deposit=500, rent=40, management_fee=8, available_date="즉시 가능",
        property_condition="신축급", positioning_type="컨디션", special_point="", option_text="",
        include_actual_listing_notice=False, include_actual_photo_notice=False,
    )
    assert "💡 이 매물의 포인트" in copy["body"]
    assert "① 이 매물의 포인트" not in copy["body"]


if __name__ == "__main__":
    run()
    print("consultation and advertising transition: PASS")
