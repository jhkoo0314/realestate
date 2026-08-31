# DB·입력항목 정리 기준

목적: 원룸 빠른 회전에 맞춰 건물·호실·매물 등록 업무를 단순화한다. 화면만 숨기지 않고 DB 컬럼·기존 값·CRUD·엑셀·테스트·문서를 함께 정리한다. 실제 사진 파일과 외부 사진 저장소는 절대 건드리지 않는다.

## 삭제 대상

- `buildings`: `admin_address`, `road_address`, `building_alias_note`, `has_cctv`, `pet_policy`, `move_in_registration_policy`, `short_term_policy`, `common_fee_note`, `building_highlights`, `info_status`, `last_checked_date`, `next_check_date`
- `units`: `is_separated`, `direction`, `area_status`, `exclusive_area_m2`, `has_balcony`, `has_built_in_closet`, `has_double_window`, `storage_status`, `system_aircon_count`, `unit_highlights`, `unit_cautions`, `internal_note`, `photo_folder_url`, `last_photo_date`
- `listings`: `management_fee_note`, `available_from_date`, `lease_term_note`, `short_term_note`, `cleaning_status`, `wallpaper_status`, `repair_status`, `photo_status`, `ad_status`, `ad_channel_note`, `option_change_note`, `verification_note`, `has_listing_photos`
- `consultations`: `consultation_category`, `consultation_type`, `desired_room_type`

삭제 값은 운영 DB에서 컬럼과 함께 제거하며, 보존은 타임스탬프 보호 사본에서만 한다.

## 유지·화면 기준

- 건물: 이름·지번·공동현관 비밀번호·엘리베이터·주차·`internal_note`(화면명 `건물 메모`)
- 호실: 호수·층·방 유형·`unit_options`(화면명 `옵션호실 메모`)·출입방법·호실 비밀번호
- 매물: 가격·관리비·상태·입주 가능 상태·퇴실 예정일·보유처·재확인일·연락처·매물 메모
- 입주 가능 상태: `즉시입주`, `퇴실 후 협의`, `확인 필요`만 사용한다. `날짜 지정`은 제거한다.
- 상담: 희망 방 유형은 `desired_room_types` 다중선택만 사용한다. 기존 `desired_room_type` 값은 비어 있는 `desired_room_types`로 먼저 이전하고 중복 없이 삭제한다.
- 계약·계약 활동·상담 활동·계약 출처 상담 연결은 보존한다.

## 매물 ID 67 보정

- `availability_type`: `날짜 지정` → `퇴실 후 협의`
- `move_out_due_date`: `2026-09-29` 유지
- `available_from_date`의 `2026-10-05`는 매물 메모 끝에 `입주 가능일 2026-10-05`를 한 번만 추가한 뒤 컬럼을 삭제한다.

## 안전 기준

1. 마이그레이션 전 보호 사본을 만든다.
2. 임시 테이블에 유지 컬럼을 명시적으로 복사하고, 행 수·최대 ID·외래키·무결성을 확인한다.
3. 상담·계약 부모와 `consultation_activities`, `contract_activities`를 모두 보존한다. `SELECT *`는 사용하지 않는다.
4. 한 SQLite 거래로 성공 시 커밋, 오류 시 전체 롤백한다.
5. 운영 DB와 신규 초기 스키마는 동일해야 하며, 앱 재시작 때 재실행·중복 백업·중복 메모가 생기면 안 된다.
6. 최종 검증: `PRAGMA integrity_check = ok`, `PRAGMA foreign_key_check` 0건, 기존 행 수와 관계 보존, 삭제 컬럼의 일반 실행경로 참조 제거.
