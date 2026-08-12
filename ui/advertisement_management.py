"""현재 매물 회차의 광고 채널과 상태를 빠르게 관리하는 화면."""

from __future__ import annotations

from datetime import date

import streamlit as st

from services.advertisement_copy_service import FEATURE_SENTENCES, OUTPUT_LENGTHS, REGION_SENTENCES, ROOM_TITLE_TEMPLATES, ROOM_TYPES, generate_ad_copy, parse_amount, templates_for_room_type
from services.advertisement_service import ADVERTISING_CHANNELS, ADVERTISING_STATUSES, change_advertisement, remove_advertisement, save_advertisement, validate_advertisement
from services.record_number import listing_number
from storage.advertisement_repository import get_advertisements
from storage.listing_repository import search_listing_rounds


def _listing_label(item: dict) -> str:
    unit = item["unit_number"] if item["unit_number"].endswith("호") else f"{item['unit_number']}호"
    return f"{listing_number(item['listing_id'])} · {item['building_name']} · {item['lot_address']} · {unit} · 접수일 {item['received_date']} · {item['listing_status']}"


def _advertisement_rows(items: list[dict]) -> list[dict]:
    return [{
        "매물번호": listing_number(item["listing_id"]), "건물명": item["building_name"], "지번": item["lot_address"], "호실": item["unit_number"],
        "매물 상태": item["listing_status"], "광고 채널": item["advertising_channel"],
        "현재 광고 상태": item["advertising_status"], "마지막 광고 확인일": item["last_checked_date"] or "-",
    } for item in items]


def _clear_listing_channel_search() -> None:
    """광고 채널 연결 대상 매물 검색을 새로 시작한다."""
    st.session_state.pop("advertisement_listing_query", None)
    st.session_state.pop("advertisement_selected_listing", None)


def _render_listing_advertisements(selected: dict) -> None:
    st.markdown("#### 선택한 매물의 광고 현황")
    st.success(f"선택한 매물: {_listing_label(selected)}")
    if st.button("다른 매물 검색", key="clear_advertisement_listing", on_click=_clear_listing_channel_search):
        st.rerun()

    existing = get_advertisements(listing_id=selected["listing_id"])
    if existing:
        st.dataframe(_advertisement_rows(existing), width="stretch", hide_index=True)
        st.markdown("##### 연결된 채널 상태 변경")
        for item in existing:
            left, middle, right, remove_column = st.columns([2, 2, 2, 1])
            with left:
                st.text_input("광고 채널", value=item["advertising_channel"], disabled=True, key=f"advertisement_channel_{item['advertisement_id']}")
            with middle:
                status_index = ADVERTISING_STATUSES.index(item["advertising_status"]) if item["advertising_status"] in ADVERTISING_STATUSES else 0
                status = st.selectbox("현재 광고 상태", ADVERTISING_STATUSES, index=status_index, key=f"advertisement_status_{item['advertisement_id']}")
            with right:
                checked_date = st.date_input("마지막 광고 확인일", value=date.fromisoformat(item["last_checked_date"]) if item["last_checked_date"] else None, key=f"advertisement_checked_{item['advertisement_id']}")
            with remove_column:
                st.caption(" ")
                if st.button("저장", key=f"advertisement_save_{item['advertisement_id']}"):
                    try:
                        change_advertisement(item["advertisement_id"], status, checked_date)
                    except ValueError as error:
                        st.error(str(error))
                    else:
                        st.success(f"{item['advertising_channel']} 광고 상태를 수정했습니다.")
                        st.rerun()
                if st.button("제거", key=f"advertisement_remove_{item['advertisement_id']}"):
                    try:
                        remove_advertisement(item["advertisement_id"])
                    except ValueError as error:
                        st.error(str(error))
                    else:
                        st.success(f"{item['advertising_channel']} 광고 현황을 제거했습니다.")
                        st.rerun()
    else:
        st.info("연결된 광고 채널이 없습니다. 아래에서 현재 광고 채널을 추가해 주세요.")

    st.markdown("##### 광고 채널 추가")
    with st.form(f"advertisement_create_{selected['listing_id']}"):
        left, middle, right = st.columns(3)
        with left:
            choice = st.selectbox("광고 채널", ADVERTISING_CHANNELS)
            custom_channel = st.text_input("직접 입력 채널", disabled=choice != "직접입력", placeholder="예: 지역 커뮤니티")
        with middle:
            status = st.selectbox("현재 광고 상태", ADVERTISING_STATUSES, index=0)
        with right:
            checked_date = st.date_input("마지막 광고 확인일", value=date.today())
        submitted = st.form_submit_button("광고 채널 추가", type="primary")
    if submitted:
        advertisement, errors = validate_advertisement({"channel_choice": choice, "custom_channel": custom_channel, "advertising_status": status, "last_checked_date": checked_date})
        if errors:
            for error in errors:
                st.error(error)
        else:
            try:
                save_advertisement(selected["listing_id"], advertisement or {})
            except ValueError as error:
                st.error(str(error))
            else:
                st.success("광고 채널을 연결했습니다.")
                st.rerun()


def _render_current_advertisements() -> None:
    st.markdown("#### 현재 광고 현황")
    with st.form("advertisement_search_form"):
        left, middle, right, fourth = st.columns([2, 1, 1, 1])
        with left:
            query = st.text_input("건물명·지번·호수 검색", key="advertisement_query")
        with middle:
            channels = st.multiselect("광고 채널", ["당근", "직방", "네이버"], key="advertisement_channel_filter")
        with right:
            channel_query = st.text_input("직접 입력 채널 검색", key="advertisement_channel_query")
        with fourth:
            statuses = st.multiselect("현재 광고 상태", ADVERTISING_STATUSES, key="advertisement_status_filter")
        searched = st.form_submit_button("광고 현황 조회", type="primary")
    if searched:
        st.session_state["advertisement_has_searched"] = True
    if not st.session_state.get("advertisement_has_searched", False):
        st.info("조건을 입력한 뒤 `광고 현황 조회`를 누르면 현재 광고 현황이 표시됩니다.")
        return
    items = get_advertisements(query=query, channels=channels, channel_query=channel_query, statuses=statuses)
    st.caption(f"현재 광고 현황 {len(items)}건")
    if items:
        st.dataframe(_advertisement_rows(items), width="stretch", hide_index=True)
        st.markdown("##### 조회 결과 빠른 수정·삭제")
        labels = [f"{item['building_name']} · {item['lot_address']} · {item['unit_number']}호 · {item['advertising_channel']} · {item['advertising_status']}" for item in items]
        selected_label = st.selectbox("수정하거나 삭제할 광고 현황", labels, key="advertisement_quick_target")
        selected = items[labels.index(selected_label)]
        left, middle, _ = st.columns(3)
        with left:
            status_index = ADVERTISING_STATUSES.index(selected["advertising_status"]) if selected["advertising_status"] in ADVERTISING_STATUSES else 0
            status = st.selectbox("현재 광고 상태", ADVERTISING_STATUSES, index=status_index, key=f"advertisement_quick_status_{selected['advertisement_id']}")
        with middle:
            checked_date = st.date_input("마지막 광고 확인일", value=date.fromisoformat(selected["last_checked_date"]) if selected["last_checked_date"] else None, key=f"advertisement_quick_checked_{selected['advertisement_id']}")
        save_column, delete_column, _ = st.columns(3)
        with save_column:
            if st.button("광고 현황 저장", type="primary", key=f"advertisement_quick_save_{selected['advertisement_id']}"):
                try:
                    change_advertisement(selected["advertisement_id"], status, checked_date)
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.success(f"{selected['advertising_channel']} 광고 현황을 수정했습니다.")
                    st.rerun()
        with delete_column:
            confirmed = st.checkbox("이 광고 현황만 삭제", key=f"advertisement_quick_delete_confirm_{selected['advertisement_id']}")
            if st.button("광고 현황 삭제", type="secondary", disabled=not confirmed, key=f"advertisement_quick_delete_{selected['advertisement_id']}"):
                try:
                    remove_advertisement(selected["advertisement_id"])
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.success(f"{selected['advertising_channel']} 광고 현황을 삭제했습니다. 매물 기록은 유지됩니다.")
                    st.rerun()
    else:
        st.info("조건에 맞는 현재 광고 현황이 없습니다.")


def _render_advertisement_registration() -> None:
    st.markdown("#### 매물에 광고 채널 연결")
    st.caption("현재 운영 중인 매물 회차를 선택한 뒤, 광고 채널·현재 상태·마지막 확인일만 관리합니다. 매물 조건은 이 화면에서 바꾸지 않습니다.")
    query_column, reset_column = st.columns([4, 1])
    with query_column:
        query = st.text_input("연결할 현재 매물 찾기", key="advertisement_listing_query", placeholder="M-000150 또는 건물명·지번·호수 2글자 이상")
    with reset_column:
        st.caption(" ")
        if st.button("검색 초기화", key="advertisement_listing_search_reset", on_click=_clear_listing_channel_search):
            st.rerun()
    selected = st.session_state.get("advertisement_selected_listing")
    if selected is None:
        if len(query.strip()) < 2:
            st.info("현재 매물을 찾기 위해 2글자 이상 입력해 주세요.")
            return
        results = [item for item in search_listing_rounds(query) if item["closed_date"] is None and item["listing_status"] not in ("계약 완료", "종료")]
        if not results:
            st.info("조건에 맞는 현재 매물이 없습니다.")
            return
        for item in results:
            if st.button(_listing_label(item), key=f"advertisement_listing_{item['listing_id']}", width="stretch"):
                st.session_state["advertisement_selected_listing"] = item
                st.rerun()
    else:
        _render_listing_advertisements(selected)


def _render_ad_copy_generator() -> None:
    """매물 DB 저장 없이 조건을 직접 입력해 광고 문구를 만든다."""
    st.markdown("#### 광고 문구 만들기")
    st.caption("매물 등록이나 광고 채널 연결 없이 조건만 직접 입력해 문구를 만듭니다. 생성 문구는 저장되지 않습니다.")

    left, middle, right = st.columns(3)
    with left:
        region = st.selectbox("핵심 지역 선택", ["직접 입력", *REGION_SENTENCES], key="ad_copy_region")
        location = st.text_input("지역 또는 지번 (선택)", placeholder="예: 북수리 1234", key="ad_copy_location")
    with middle:
        room_type = st.selectbox("방 형태", ROOM_TYPES, key="ad_copy_room_type")
        available_date = st.text_input("입주 가능일 (선택)", placeholder="예: 즉시 가능", key="ad_copy_available_date")
    with right:
        deposit_text = st.text_input("보증금 (만원)", placeholder="예: 300", key="ad_copy_deposit")
        rent_text = st.text_input("월세 (만원)", placeholder="예: 55", key="ad_copy_rent")

    title_family = "원룸" if room_type == "원룸" else "쓰리룸" if room_type == "쓰리룸" else "투룸"
    title_template = st.selectbox(
        "광고 제목 한 줄 템플릿 (선택)",
        ["직접 입력", *ROOM_TITLE_TEMPLATES[title_family]],
        key=f"ad_copy_title_template_{title_family}",
    )
    if title_template != "직접 입력":
        st.caption("선택한 문구가 제목으로 그대로 사용됩니다. 실매물·즉시 입주·채광·도보권 등 사실 확인이 필요한 표현은 확인된 매물에만 선택해 주세요.")

    template_choices = templates_for_room_type(room_type)
    selected_template = st.selectbox("광고 템플릿", template_choices, key="ad_copy_template")
    output_length = st.radio("문구 길이", OUTPUT_LENGTHS, horizontal=True, key="ad_copy_output_length", help="짧은형은 핵심 조건만, 기본형은 일반 광고 본문, 상세형은 추천 대상을 더 자세히 표시합니다.")
    st.markdown("##### 광고 강조 포인트 (2~5개 권장)")
    feature_columns = st.columns(4)
    selected_features: list[str] = []
    for index, feature in enumerate(FEATURE_SENTENCES):
        with feature_columns[index % len(feature_columns)]:
            if st.checkbox(feature, key=f"ad_copy_feature_{feature}"):
                selected_features.append(feature)

    selected_region_sentences: list[str] = []
    if region != "직접 입력":
        st.markdown("##### 지역 생활권 강조 (선택 · 실제 매물 위치 확인 후 여러 개 선택 가능)")
        region_columns = st.columns(2)
        for index, sentence in enumerate(REGION_SENTENCES[region]):
            with region_columns[index % len(region_columns)]:
                if st.checkbox(sentence, key=f"ad_copy_region_sentence_{region}_{index}"):
                    selected_region_sentences.append(sentence)
        st.caption("선택한 문구는 모두 본문의 `교통 & 생활`에 들어갑니다. 거리·도보시간은 매물마다 다르므로 실제 위치를 확인한 경우에만 선택해 주세요.")

    transit_living_text = st.text_area(
        "교통·생활 장점 (선택 · 확인된 내용만 줄마다 입력)",
        placeholder="예: 1호선 배방역 도보 약 10분대\n가까운 거리의 버스정류장\n편의점 도보 1분권",
        key="ad_copy_transit_living_text",
        height=80,
    )
    additional_text = st.text_area(
        "추가 핵심 포인트 (선택 · 확인된 내용만 줄마다 입력)",
        placeholder="예: 안방이 넓음\n작은방에도 창 있음",
        key="ad_copy_additional_text",
        height=80,
    )
    notice_left, notice_right = st.columns(2)
    with notice_left:
        actual_listing_checked = st.checkbox("실매물 확인됨 — ‘본 매물은 실매물입니다’ 포함", key="ad_copy_actual_listing")
    with notice_right:
        actual_photo_checked = st.checkbox("실제 호실 사진 확인됨 — 사진 안내 포함", key="ad_copy_actual_photo")
    if st.button("광고 문구 생성", type="primary", key="ad_copy_generate"):
        try:
            result = generate_ad_copy(
                room_type=room_type,
                deposit=parse_amount(deposit_text, "보증금"),
                rent=parse_amount(rent_text, "월세"),
                template_name=selected_template,
                location=location or ("" if region == "직접 입력" else region),
                title_template="" if title_template == "직접 입력" else title_template,
                available_date=available_date,
                selected_features=selected_features,
                region_sentences=selected_region_sentences,
                transit_living_text=transit_living_text,
                additional_text=additional_text,
                output_length=output_length,
                include_actual_listing_notice=actual_listing_checked,
                include_actual_photo_notice=actual_photo_checked,
            )
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["ad_copy_result"] = result
            st.session_state.pop("ad_copy_title_editor", None)
            st.session_state.pop("ad_copy_body_editor", None)

    result = st.session_state.get("ad_copy_result")
    if not result:
        return
    st.divider()
    st.markdown("##### 생성 결과")
    title = st.text_area("광고 제목 수정", value=result["title"], key="ad_copy_title_editor", height=68)
    body = st.text_area("광고 상세문구 수정", value=result["body"], key="ad_copy_body_editor", height=360)
    st.caption("각 문구 오른쪽 위 복사 아이콘을 누르면 바로 복사할 수 있습니다.")
    title_column, body_column = st.columns(2)
    with title_column:
        st.markdown("###### 제목 복사")
        st.code(title, language=None)
    with body_column:
        st.markdown("###### 본문 복사")
        st.code(body, language=None)


def render_advertisement_management() -> None:
    st.subheader("광고관리")
    st.markdown("<p class='section-note'>현재 매물 회차에 당근·직방·네이버 등 광고 채널을 복수로 연결하고, 현재 광고 상태만 빠르게 관리합니다.</p>", unsafe_allow_html=True)
    mode = st.radio("광고관리 메뉴", ["현재 광고 현황", "매물에 광고 채널 연결", "광고 문구 만들기"], horizontal=True, key="advertisement_management_mode")
    if mode == "현재 광고 현황":
        _render_current_advertisements()
    elif mode == "매물에 광고 채널 연결":
        _render_advertisement_registration()
    else:
        _render_ad_copy_generator()
