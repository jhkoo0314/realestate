"""선택한 매물 빠른 수정 - 광고 플랫폼 등록 저장 및 스키마 검증."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from storage.database import get_connection, initialize_database
from storage.listing_repository import get_current_listings, update_listing_quick_fields
from ui.dashboard import _display_rows


def run() -> None:
    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory) / "test_quick_edit.db"
        initialize_database(db_path)

        conn = get_connection(db_path)
        try:
            b_id = conn.execute(
                "INSERT INTO buildings (building_name, lot_address) VALUES (?, ?)",
                ("테스트빌딩", "북수리 100"),
            ).lastrowid
            u_id = conn.execute(
                "INSERT INTO units (building_id, unit_number, unit_number_normalized) VALUES (?, ?, ?)",
                (b_id, "301", "301"),
            ).lastrowid
            l_id = conn.execute(
                "INSERT INTO listings (unit_id, received_date, listing_status, availability_type) VALUES (?, ?, ?, ?)",
                (u_id, "2026-09-08", "공실", "즉시입주"),
            ).lastrowid
            conn.commit()
        finally:
            conn.close()

        # 1. 초기 상태 조회 (advertised_platforms is None -> 미등록)
        listings = get_current_listings(path=db_path)
        assert len(listings) == 1
        assert listings[0]["advertised_platforms"] is None

        displayed = _display_rows(listings)
        assert displayed[0]["광고 플랫폼"] == "미등록"

        # 2. 빠른 수정으로 광고 플랫폼 "직방, 당근" 설정
        update_listing_quick_fields(l_id, "직방, 당근", path=db_path)

        listings_updated = get_current_listings(path=db_path)
        assert listings_updated[0]["advertised_platforms"] == "직방, 당근"

        displayed_updated = _display_rows(listings_updated)
        assert displayed_updated[0]["광고 플랫폼"] == "직방, 당근"

        # 3. 다시 초기화 (None으로 수정)
        update_listing_quick_fields(l_id, None, path=db_path)
        listings_cleared = get_current_listings(path=db_path)
        assert listings_cleared[0]["advertised_platforms"] is None
        assert _display_rows(listings_cleared)[0]["광고 플랫폼"] == "미등록"

    print("test_quick_edit_advertised_platforms: PASS")


if __name__ == "__main__":
    run()
