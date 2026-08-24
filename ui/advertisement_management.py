"""월별 광고비 기록과 광고 문구 만들기 화면."""

from __future__ import annotations

from datetime import date

import streamlit as st

from services.advertisement_copy_service import PROPERTY_POSITIONING_COPY, ROOM_TYPES, generate_lead_ad_copy, parse_optional_amount, room_title_templates_for_room_type
from services.advertisement_cost_service import ADVERTISING_COST_CHANNELS, remove_monthly_cost, save_monthly_cost, validate_monthly_advertising_cost
from storage.advertisement_cost_repository import get_monthly_advertising_costs


def _set_ad_copy_result(result: dict[str, str], *, reset_editor: bool = False) -> None:
    """새 생성본 또는 수정본을 결과와 편집칸에 함께 반영한다."""
    st.session_state["ad_copy_result"] = result
    if reset_editor:
        st.session_state["ad_copy_title_editor"] = result["title"]
        st.session_state["ad_copy_body_editor"] = result["body"]


def _render_monthly_advertising_costs() -> None:
    st.markdown("#### 월별 광고비 기록")
    st.caption("매물별 광고 연결 없이 월별 채널 광고비만 기록합니다. 같은 기준연월·채널을 다시 저장하면 기존 금액을 수정합니다.")
    with st.form("monthly_advertising_cost_create"):
        left, middle, right, last = st.columns(4)
        with left:
            year_month = st.text_input("기준연월", value=date.today().strftime("%Y-%m"), placeholder="예: 2026-08")
        with middle:
            choice = st.selectbox("광고 채널", ADVERTISING_COST_CHANNELS)
            custom = st.text_input("기타 채널", disabled=choice != "기타")
        with right:
            amount = st.number_input("월 광고비 (만원)", min_value=0, step=10, value=None)
        with last:
            memo = st.text_input("메모 (선택)")
        submitted = st.form_submit_button("월별 광고비 저장", type="primary")
    if submitted:
        values, errors = validate_monthly_advertising_cost({"year_month": year_month, "channel_choice": choice, "custom_channel": custom, "monthly_cost_manwon": amount, "memo": memo})
        if errors:
            for error in errors:
                st.error(error)
        else:
            save_monthly_cost(values or {})
            st.success("월별 광고비를 저장했습니다.")
            st.rerun()
    records = get_monthly_advertising_costs()
    st.caption(f"저장된 월별 광고비 {len(records)}건")
    if not records:
        st.info("아직 저장된 월별 광고비가 없습니다.")
        return
    st.dataframe([{"기준연월": item["year_month"], "광고 채널": item["advertising_channel"], "월 광고비 (만원)": item["monthly_cost_manwon"], "메모": item["memo"] or "-", "수정일시": item["updated_at"]} for item in records], width="stretch", hide_index=True)
    labels = {item["cost_id"]: f"{item['year_month']} · {item['advertising_channel']} · {item['monthly_cost_manwon']:,}만원" for item in records}
    selected_id = st.selectbox("삭제할 월별 광고비 선택", list(labels), format_func=labels.get)
    confirmed = st.checkbox("선택한 월별 광고비 기록만 삭제하는 것을 확인했습니다.")
    if st.button("선택한 월별 광고비 삭제", disabled=not confirmed, type="secondary"):
        remove_monthly_cost(selected_id)
        st.success("선택한 월별 광고비 기록을 삭제했습니다.")
        st.rerun()


def _render_ad_copy_generator() -> None:
    st.markdown("#### 광고 문구 만들기")
    st.caption("매물 DB와 연결하지 않습니다. 직접 입력한 사실만으로 광고문을 만들며, 입력값과 생성 결과는 저장되지 않습니다.")
    st.warning("비밀번호·연락처·내부 메모는 입력하거나 광고문에 넣지 마세요.")
    location_column, room_type_column, transaction_type_column = st.columns([2, 1, 1])
    with location_column: location = st.text_input("지역 또는 지번", placeholder="예: 장재리 1684", key="ad_copy_location")
    with room_type_column: room_type = st.selectbox("방 형태", ROOM_TYPES, key="ad_copy_room_type")
    with transaction_type_column: transaction_type = st.selectbox("거래 방식", ["월세", "전세", "보증부월세", "가격 문의"], key="ad_copy_transaction_type")
    title_template = st.selectbox("룸 제목 템플릿", ["기본 제목", *room_title_templates_for_room_type(room_type)], key=f"ad_copy_room_title_template_{room_type}")
    deposit_column, rent_column, fee_column, available_column = st.columns(4)
    with deposit_column: deposit_text = st.text_input("보증금 (만원 · 선택)", placeholder="예: 500", key="ad_copy_deposit")
    with rent_column: rent_text = st.text_input("월세 (만원 · 선택)", placeholder="예: 40", key="ad_copy_rent")
    with fee_column: management_fee_text = st.text_input("관리비 (만원 · 선택)", placeholder="예: 8", key="ad_copy_management_fee")
    with available_column: available_date = st.text_input("입주 가능일 (선택)", placeholder="예: 즉시 가능", key="ad_copy_available_date")
    st.markdown("##### 매물 성격")
    property_condition = st.radio("매물 컨디션", ["신축급", "구축"], horizontal=True, key="ad_copy_property_condition")
    positioning_type = st.radio("이 매물에서 가장 강조할 점", list(PROPERTY_POSITIONING_COPY[property_condition]), horizontal=True, key=f"ad_copy_positioning_type_{property_condition}")
    special_point = st.text_input("이 매물의 특별한 점 *" if positioning_type == "특별매물" else "특별 포인트 추가 (선택)", key="ad_copy_special_point")
    option_text = st.text_input("옵션 문구 수정 (선택)", key="ad_copy_option_text")
    actual_listing_checked = st.checkbox("실매물 확인됨 — ‘본 매물은 실매물입니다’ 포함", key="ad_copy_actual_listing")
    actual_photo_checked = st.checkbox("실제 호실 사진 확인됨 — 사진 안내 포함", key="ad_copy_actual_photo")
    if st.button("광고 문구 생성", type="primary", key="ad_copy_generate"):
        try:
            _set_ad_copy_result(generate_lead_ad_copy(location=location, room_type=room_type, title_template="" if title_template == "기본 제목" else title_template, transaction_type=transaction_type, deposit=parse_optional_amount(deposit_text, "보증금"), rent=parse_optional_amount(rent_text, "월세"), management_fee=parse_optional_amount(management_fee_text, "관리비"), available_date=available_date, property_condition=property_condition, positioning_type=positioning_type, special_point=special_point, option_text=option_text, include_actual_listing_notice=actual_listing_checked, include_actual_photo_notice=actual_photo_checked), reset_editor=True)
        except ValueError as error:
            st.error(str(error))
    result = st.session_state.get("ad_copy_result")
    if result:
        st.divider()
        title = st.text_area("광고 제목 수정", key="ad_copy_title_editor", height=68)
        body = st.text_area("광고 상세문구 수정", key="ad_copy_body_editor", height=360)
        applied = st.button("수정 내용 적용", key="ad_copy_apply")
        if applied:
            _set_ad_copy_result({"title": title, "body": body})
            st.success("수정한 광고 문구를 적용했습니다.")
        preview = st.session_state["ad_copy_result"]
        left, right = st.columns(2)
        with left: st.code(preview["title"], language=None)
        with right: st.code(preview["body"], language=None)


def render_advertisement_management() -> None:
    st.subheader("광고관리")
    st.markdown("<p class='section-note'>월별 광고비 기록과 광고 문구 만들기만 관리합니다. 매물별 광고 조회·연결 기능은 사용하지 않습니다.</p>", unsafe_allow_html=True)
    mode = st.radio("광고관리 메뉴", ["월별 광고비 기록", "광고 문구 만들기"], horizontal=True, key="advertisement_management_mode")
    if mode == "월별 광고비 기록":
        _render_monthly_advertising_costs()
    else:
        _render_ad_copy_generator()
