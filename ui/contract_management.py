"""매물 회차에 연결한 계약 기간과 상태 관리 화면."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from services.contract_service import CONTRACT_STATUSES, CONTRACT_TYPES, change_contract_details, delete_contract, save_contract, validate_contract
from storage.contract_repository import get_contracts
from storage.listing_repository import search_listing_rounds


def _date_text(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _listing_label(item: dict) -> str:
    unit = item["unit_number"] if item["unit_number"].endswith("호") else f"{item['unit_number']}호"
    return f"{item['building_name']} · {item['lot_address']} · {unit} · 접수일 {item['received_date']} · {item['listing_status']}"


def _contract_rows(contracts: list[dict]) -> list[dict]:
    today = date.today()
    rows = []
    for item in contracts:
        remaining = "-"
        if item["contract_end_date"] and item["contract_status"] not in ("해지", "만료"):
            days = (date.fromisoformat(item["contract_end_date"]) - today).days
            if 0 <= days <= 30:
                remaining = "D-day" if days == 0 else f"{days}일 남음"
        rows.append({
            "건물명": item["building_name"], "호실": item["unit_number"], "매물 접수일": item["received_date"],
            "계약 유형": item["contract_type"], "시작일": item["contract_start_date"],
            "종료일": item["contract_end_date"] or "-", "만료 임박": remaining,
            "기간(개월)": item["term_months"] or "-", "계약 상태": item["contract_status"],
            "메모": item["contract_note"] or "-",
        })
    return rows


def _render_status_change(contracts: list[dict]) -> None:
    if not contracts:
        return
    st.markdown("#### 저장된 계약 정보 수정")
    labels = [f"{_listing_label(item)} · 시작 {item['contract_start_date']} · {item['contract_type']}" for item in contracts]
    selected_label = st.selectbox("상태를 변경할 계약", labels, key="contract_status_target")
    selected = contracts[labels.index(selected_label)]
    index = CONTRACT_STATUSES.index(selected["contract_status"]) if selected["contract_status"] in CONTRACT_STATUSES else 0
    left, middle, right = st.columns(3)
    with left:
        status = st.selectbox("계약 상태", CONTRACT_STATUSES, index=index, key=f"contract_status_{selected['contract_id']}")
    with middle:
        contact = st.text_input("계약자 연락처 (내부정보)", value=selected["contractor_contact"] or "", key=f"contract_contact_{selected['contract_id']}")
    with right:
        deposit = st.number_input("계약금 (만원)", min_value=0, step=10, value=selected["contract_deposit_manwon"], key=f"contract_deposit_{selected['contract_id']}")
        balance = st.number_input("잔금 (만원)", min_value=0, step=10, value=selected["balance_manwon"], key=f"contract_balance_{selected['contract_id']}")
    if st.button("계약 정보 저장", key=f"contract_status_save_{selected['contract_id']}"):
        try:
            change_contract_details(selected["contract_id"], {
                "contract_status": status, "contractor_contact": contact,
                "contract_deposit_manwon": deposit, "balance_manwon": balance,
            })
        except ValueError as error:
            st.error(str(error))
        else:
            st.success("계약 기록은 유지한 채 계약 정보를 수정했습니다.")
            st.rerun()

    with st.expander("이 계약 기록 완전 삭제"):
        st.error("선택한 계약 기록만 삭제됩니다. 매물과 상담 기록은 남습니다.")
        confirmed = st.checkbox("이 계약 기록을 완전히 삭제하는 것을 확인했습니다.", key=f"delete_contract_confirm_{selected['contract_id']}")
        if st.button("계약 기록 삭제", type="secondary", disabled=not confirmed, key=f"delete_contract_{selected['contract_id']}"):
            try:
                delete_contract(selected["contract_id"])
            except ValueError as error:
                st.error(str(error))
                return
            st.success("계약 기록을 삭제했습니다.")
            st.rerun()


def _render_contract_lookup() -> None:
    st.markdown("#### 계약 조회·수정")
    st.caption("저장된 계약을 찾고, 계약 상태·계약자 연락처·계약금·잔금만 수정합니다. 이 화면에서는 새 계약을 만들지 않습니다.")
    with st.form("contract_search_form"):
        query_column, status_column, start_column, end_column = st.columns([2, 1, 1, 1])
        with query_column:
            query = st.text_input("건물명·지번·호수 검색", key="contract_query")
        with status_column:
            statuses = st.multiselect("계약 상태", CONTRACT_STATUSES, key="contract_status_filter")
        with start_column:
            end_start = st.date_input("종료일 시작", value=None, key="contract_end_start")
        with end_column:
            end_end = st.date_input("종료일 종료", value=None, key="contract_end_end")
        expiring_soon = st.checkbox("계약 만료 30일 전만 보기", key="contract_expiring_soon")
        searched = st.form_submit_button("계약 조회", type="primary")
    if searched:
        st.session_state["contract_has_searched"] = True
    if end_start and end_end and end_end < end_start:
        st.error("종료일 종료는 시작일보다 빠를 수 없습니다.")
        return
    contracts = get_contracts(
        query=query, statuses=statuses, end_start=_date_text(end_start), end_end=_date_text(end_end),
        expiring_within_days=30 if expiring_soon else None,
    )
    if st.session_state.get("contract_has_searched"):
        if expiring_soon:
            deadline = date.today() + timedelta(days=30)
            st.caption(f"계약 만료 30일 전 필터 적용: {date.today().isoformat()} ~ {deadline.isoformat()} · 해지·만료 계약 제외")
        st.caption(f"조회된 계약 {len(contracts)}건")
        if contracts:
            st.dataframe(_contract_rows(contracts), width="stretch", hide_index=True)
        else:
            st.info("조건에 맞는 계약 기록이 없습니다.")
    _render_status_change(contracts)


def _render_contract_registration() -> None:
    st.markdown("#### 계약 등록")
    st.caption("계약할 당시의 매물 기록을 먼저 선택한 뒤, 새 계약을 한 건 추가합니다. 기존 계약은 수정하지 않습니다.")
    listing_query = st.text_input("연결할 매물 회차 찾기", key="contract_listing_query", placeholder="건물명·지번·호수 중 2글자 이상")
    selected = st.session_state.get("contract_selected_listing")
    if selected is None:
        if len(listing_query.strip()) < 2:
            st.info("계약할 당시의 매물 기록을 찾기 위해 2글자 이상 입력해 주세요.")
        else:
            listing_results = search_listing_rounds(listing_query)
            if not listing_results:
                st.info("조건에 맞는 매물 기록이 없습니다.")
            else:
                st.caption("계약을 연결할 매물 기록을 선택해 주세요. 같은 호실도 접수일이 다르면 다른 기록입니다.")
                for item in listing_results:
                    if st.button(_listing_label(item), key=f"contract_listing_{item['listing_id']}", width="stretch"):
                        st.session_state["contract_selected_listing"] = item
                        st.rerun()
    else:
        st.success(f"선택한 매물 기록: {_listing_label(selected)}")
        if st.button("다른 매물 기록 선택", key="clear_contract_listing"):
            st.session_state.pop("contract_selected_listing", None)
            st.rerun()
        with st.form(f"contract_create_{selected['listing_id']}"):
            left, middle, right = st.columns(3)
            with left:
                contract_type = st.selectbox("계약 유형 *", CONTRACT_TYPES)
                contract_status = st.selectbox("계약 상태 *", CONTRACT_STATUSES)
            with middle:
                contract_start = st.date_input("계약 시작일 *", value=date.today())
                contract_end = st.date_input("계약 종료일", value=None)
            with right:
                term_months = st.number_input("계약 기간 (개월)", min_value=1, step=1, value=None)
            contract_note = st.text_area("계약 메모", placeholder="예: 단기 연장 여부 확인 필요")
            detail_left, detail_right, _ = st.columns(3)
            with detail_left:
                contractor_contact = st.text_input("계약자 연락처 (내부정보)", placeholder="예: 010-1234-5678")
            with detail_right:
                contract_deposit = st.number_input("계약금 (만원)", min_value=0, step=10, value=None)
                balance = st.number_input("잔금 (만원)", min_value=0, step=10, value=None)
            confirmed = st.checkbox("선택한 매물 기록에 새 계약을 추가하는 것을 확인했습니다.")
            submitted = st.form_submit_button("새 계약 등록", type="primary", disabled=not confirmed)
        if submitted:
            contract, errors = validate_contract({
                "contract_type": contract_type, "contract_status": contract_status,
                "contract_start_date": contract_start, "contract_end_date": contract_end,
                "term_months": term_months, "contract_note": contract_note,
                "contractor_contact": contractor_contact, "contract_deposit_manwon": contract_deposit,
                "balance_manwon": balance,
            })
            if errors:
                for error in errors:
                    st.error(error)
            else:
                try:
                    save_contract(selected["listing_id"], contract)
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.success("새 계약 기록을 추가했습니다. 기존 계약과 매물 기록은 변경되지 않았습니다.")
                    st.session_state.pop("contract_selected_listing", None)
                    st.rerun()


def render_contract_management() -> None:
    st.subheader("계약관리")
    st.markdown("<p class='section-note'>계약은 건물·호실이 아니라 계약 당시의 매물 기록에 연결합니다. 계약자 연락처와 계약금·잔금은 내부정보로 관리하며, 결제·계약서 파일은 관리하지 않습니다.</p>", unsafe_allow_html=True)
    mode = st.radio(
        "계약관리 메뉴",
        ["계약 등록", "계약 조회·수정"],
        horizontal=True,
        key="contract_management_mode",
    )
    if mode == "계약 등록":
        _render_contract_registration()
    else:
        _render_contract_lookup()
