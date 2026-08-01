"""건물·호실 관리 화면. 상세 관리 기능은 다음 단계에서 추가한다."""

import streamlit as st


def render_building_management() -> None:
    st.subheader("건물·호실 관리")
    st.markdown("<p class='section-note'>건물 공통정보, 호실 정보, 과거 매물 이력을 관리하는 화면입니다.</p>", unsafe_allow_html=True)
    st.info("등록된 건물과 호실을 검색·수정하는 기능은 다음 단계에서 연결합니다.")
