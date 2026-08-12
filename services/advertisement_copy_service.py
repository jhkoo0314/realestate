"""광고관리의 수동 입력용 광고 문구 템플릿 생성 규칙."""

from __future__ import annotations


ROOM_TYPES = ["원룸", "투룸", "투베이", "쓰리룸", "쓰리베이", "기타"]
OUTPUT_LENGTHS = ["짧은형", "기본형", "상세형"]

ROOM_TITLE_TEMPLATES = {
    "원룸": [
        "🏠 첫 자취라면 꼭 한 번 보셔야 할 원룸!",
        "🏡 깔끔한 원룸, 몸만 들어오시면 됩니다.",
        "🌞 채광 좋은 원룸, 하루 종일 밝아요.",
        "💰 가격 대비 만족도 높은 원룸!",
        "🛏 풀옵션 원룸, 즉시 입주 가능합니다.",
        "🚶 편의시설 가까운 인기 원룸!",
        "💼 직장인에게 딱 맞는 깔끔한 원룸.",
        "🎓 학생들에게 인기 많은 원룸입니다.",
        "🌿 조용한 주거환경의 아늑한 원룸.",
        "🚗 주차 가능한 실속 원룸!",
        "📷 사진보다 실물이 더 예쁜 원룸.",
        "🏠 관리 잘 된 깨끗한 원룸입니다.",
        "💰 부담 없는 월세, 가성비 최고 원룸!",
        "🌈 밝고 쾌적한 원룸 찾으셨나요?",
        "📍 위치 좋은 원룸, 출퇴근도 편리합니다.",
        "🛋 혼자 살기 딱 좋은 공간.",
        "💎 컨디션 좋은 실매물 원룸입니다.",
        "👀 보시면 바로 계약하고 싶은 원룸!",
        "🔑 오늘 바로 입주 가능한 원룸.",
        "🏡 오래 살고 싶은 원룸입니다.",
    ],
    "투룸": [
        "🏡 신혼부부 추천! 넓고 깔끔한 투룸.",
        "🏠 방 2개, 거실까지 여유로운 투룸!",
        "🌞 채광 좋은 인기 투룸입니다.",
        "💯 가성비 좋은 투룸, 놓치면 아쉬워요.",
        "👨‍👩‍👧 가족이 살기 좋은 투룸.",
        "💼 직장인 2인 거주 추천!",
        "🛋 넓은 거실이 매력적인 투룸.",
        "🚗 주차 가능한 깔끔한 투룸.",
        "🌿 조용한 주거환경의 인기 투룸.",
        "🏡 오래 살기 좋은 투룸입니다.",
        "💎 컨디션 최상! 실매물 투룸.",
        "📷 사진보다 실물이 더 만족스러운 투룸.",
        "📦 수납공간 넉넉한 실속 투룸.",
        "🌈 환기 잘 되는 쾌적한 투룸.",
        "📍 생활권 좋은 인기 투룸!",
        "💰 월세 부담 적은 가성비 투룸.",
        "🏠 첫 신혼집으로 추천드리는 투룸.",
        "👀 보시면 바로 마음에 드실 투룸.",
        "🔑 즉시 입주 가능한 깔끔한 투룸.",
        "🏡 편안한 생활이 가능한 아늑한 투룸.",
    ],
    "쓰리룸": [
        "🏡 가족 거주에 여유로운 쓰리룸입니다.",
        "🏠 방 3개로 생활공간을 넉넉하게 나눠 쓰는 쓰리룸!",
        "👨‍👩‍👧 가족 생활에 잘 맞는 깔끔한 쓰리룸.",
        "🛋 각 방을 다양하게 활용하기 좋은 여유로운 쓰리룸.",
        "📦 수납과 생활공간이 넉넉한 실속 쓰리룸.",
        "🌞 채광과 공간감을 함께 갖춘 쓰리룸입니다.",
        "🚗 주차 가능 여부를 확인한 쓰리룸 매물.",
        "📍 생활권과 넉넉한 공간을 함께 보는 쓰리룸.",
        "💼 재택·자녀방 등 공간 분리가 필요한 분께 추천.",
        "🏡 오래 편하게 거주할 집을 찾는 분께 좋은 쓰리룸.",
    ],
}

AD_TEMPLATES = {
    "원룸 기본형": {
        "room_types": {"원룸"},
        "opening": "생활 동선을 편하게 꾸릴 수 있는 깔끔한 원룸 매물입니다.",
        "layout": "혼자 거주하기 좋은 실용적인 원룸 구조",
        "recommendations": ["첫 독립을 준비하는 분", "간편한 생활공간이 필요한 분"],
    },
    "원룸 신축·옵션형": {
        "room_types": {"원룸"},
        "opening": "깔끔한 내부와 생활 편의를 함께 갖춘 원룸 매물입니다.",
        "layout": "혼자 거주하기 좋은 실용적인 원룸 구조",
        "recommendations": ["깔끔한 컨디션을 중요하게 보는 분", "옵션을 갖춘 원룸을 찾는 분"],
    },
    "투룸 기본형": {
        "room_types": {"투룸", "투베이", "쓰리룸", "쓰리베이", "기타"},
        "opening": "원룸보다 여유 있는 공간을 찾는 분께 잘 맞는 실속 있는 투룸입니다.",
        "layout": "침실과 생활공간을 나눠 쓰기 좋은 투룸 구조",
        "opening_by_room_type": {"쓰리룸": "방마다 용도를 나눠 쓰기 좋은 여유로운 쓰리룸 매물입니다."},
        "layout_by_room_type": {"쓰리룸": "침실·자녀방·서재 등 생활공간을 나눠 쓰기 좋은 쓰리룸 구조"},
        "recommendations": ["원룸보다 여유 있는 공간이 필요한 분", "두 분이 함께 거주할 집을 찾는 분"],
    },
    "투룸 공간·수납형": {
        "room_types": {"투룸", "투베이", "쓰리룸", "쓰리베이", "기타"},
        "opening": "수납과 공간 활용에 장점이 있는 여유로운 투룸 매물입니다.",
        "layout": "침실과 생활공간을 나눠 쓰기 좋은 투룸 구조",
        "opening_by_room_type": {"쓰리룸": "수납과 공간 활용을 넉넉하게 고려할 수 있는 쓰리룸 매물입니다."},
        "layout_by_room_type": {"쓰리룸": "여러 방을 생활·수납 공간으로 나눠 활용하기 좋은 쓰리룸 구조"},
        "recommendations": ["짐이 있거나 수납공간이 필요한 분", "침실과 생활공간을 분리하고 싶은 분"],
    },
    "직장인 출퇴근형": {
        "room_types": {"원룸", "투룸", "투베이", "쓰리룸", "쓰리베이", "기타"},
        "opening": "출퇴근 동선과 일상생활의 편의를 함께 고려하는 분께 잘 맞는 매물입니다.",
        "layout": "출퇴근 후 편하게 쉴 수 있도록 생활 동선을 고려하기 좋은 구조",
        "recommendations": ["출퇴근 편의를 중요하게 보는 분", "생활권을 함께 고려하는 직장인"],
    },
    "신혼·2인 거주형": {
        "room_types": {"투룸", "투베이", "쓰리룸", "쓰리베이", "기타"},
        "opening": "두 분이 함께 거주할 공간과 생활 동선을 고려하는 분께 잘 맞는 매물입니다.",
        "layout": "침실과 생활공간을 나눠 쓰기 좋은 여유 있는 구조",
        "opening_by_room_type": {"쓰리룸": "가족 또는 다인 거주의 생활공간을 넉넉하게 고려하는 분께 잘 맞는 쓰리룸입니다."},
        "layout_by_room_type": {"쓰리룸": "가족 구성원별 생활공간을 나눠 쓰기 좋은 여유 있는 구조"},
        "recommendations": ["신혼 또는 2인 거주를 준비하는 분", "각자의 생활공간이 필요한 분"],
    },
    "즉시 입주형": {
        "room_types": {"원룸", "투룸", "투베이", "쓰리룸", "쓰리베이", "기타"},
        "opening": "입주 시점을 빠르게 맞춰야 하는 분께 확인해 볼 만한 매물입니다.",
        "layout": "입주 준비를 빠르게 진행하기 좋은 실용적인 구조",
        "recommendations": ["빠른 입주를 준비하는 분", "입주 가능 시점을 우선 확인하는 분"],
    },
    "가성비형": {
        "room_types": {"원룸", "투룸", "투베이", "쓰리룸", "쓰리베이", "기타"},
        "opening": "예산과 필요한 생활 조건을 함께 비교하는 분께 잘 맞는 실속형 매물입니다.",
        "layout": "필요한 생활공간을 알맞게 구성하기 좋은 실용적인 구조",
        "recommendations": ["예산을 고려해 매물을 비교하는 분", "필요한 조건을 우선 확인하는 분"],
    },
    "쓰리룸 가족·공간형": {
        "room_types": {"쓰리룸"},
        "opening": "가족 거주와 방별 공간 활용을 함께 고려하는 분께 잘 맞는 쓰리룸 매물입니다.",
        "layout": "침실·자녀방·서재 등 용도에 맞춰 방을 나눠 쓰기 좋은 쓰리룸 구조",
        "recommendations": ["가족 거주를 준비하는 분", "방별 공간 분리가 필요한 분", "넉넉한 생활공간을 찾는 분"],
    },
}

FEATURE_SENTENCES = {
    "붙박이장": "넉넉한 붙박이장으로 수납 활용도 좋음",
    "베란다": "별도 베란다 공간으로 생활공간 활용 편리",
    "양창": "양창 구조로 환기와 개방감 좋음",
    "엘리베이터": "엘리베이터 있어 층간 이동 편리",
    "주차 가능": "주차 가능",
    "신축급": "깔끔하게 관리된 신축급 컨디션",
    "중문": "중문 설치로 공간 분리와 냉난방 관리 용이",
    "풀옵션": "생활에 필요한 주요 가전 갖춘 풀옵션",
}

REGION_SENTENCES = {
    "북수리": [
        "배방·월천 생활권을 함께 누릴 수 있는 위치",
        "삼성전자 온양캠퍼스 출퇴근 편리한 위치",
        "출퇴근과 일상생활의 균형을 갖춘 배방 생활권",
        "배방 생활권 중심에서 편하게 거주하기 좋은 위치",
        "생활 편의와 주거 환경을 함께 고려한 북수리 생활권",
    ],
    "공수리": [
        "삼성전자 온양캠퍼스 출퇴근 편리한 위치",
        "도서관·수영장·체육관 이용 편리한 배방복합커뮤니티센터 생활권",
        "교통과 생활 편의를 함께 누릴 수 있는 배방 생활권",
        "일상생활에 필요한 편의시설 이용이 좋은 공수리 생활권",
        "직장인과 실거주자 모두 선호하는 배방 생활권",
    ],
    "장재리": [
        "천안아산역과 배방 생활권 이용 편리한 위치",
        "광역 교통 이용을 중요하게 보는 분께 좋은 장재리 생활권",
        "천안아산역 중심 생활권을 누릴 수 있는 위치",
        "배방 생활권과 인근 업무지역 이동을 함께 고려한 위치",
        "교통 편의와 생활 인프라를 함께 갖춘 장재리 생활권",
    ],
    "월천지구": [
        "배방·탕정 생활권을 함께 누릴 수 있는 위치",
        "삼성전자 온양캠퍼스 출퇴근 편리한 위치",
        "배방 생활권에서 쾌적한 주거환경을 찾는 분께 좋은 위치",
        "배방과 탕정 방향 생활권을 함께 고려한 월천지구",
        "출퇴근과 생활 편의를 함께 챙길 수 있는 월천지구 생활권",
    ],
}

COMMON_NOTICE = [
    "다가구주택 특성상 호실별 전용면적은 참고용으로 안내드립니다.",
    "계약 가능 여부 및 옵션은 실시간으로 변동될 수 있으므로 방문 전 문의 부탁드립니다.",
    "자세한 상담 및 방문 예약은 언제든 편하게 연락 주세요.",
]


def parse_amount(value: str, label: str) -> int:
    """만원 단위 금액을 숫자로만 안전하게 받는다."""
    compact = value.strip().replace(",", "")
    if not compact:
        raise ValueError(f"{label}을 입력해 주세요.")
    if not compact.isdigit():
        raise ValueError(f"{label}은 숫자만 입력해 주세요. (만원)")
    return int(compact)


def templates_for_room_type(room_type: str) -> list[str]:
    """방 형태에 맞는 기본 템플릿을 앞에 배치한다."""
    preferred = [name for name, template in AD_TEMPLATES.items() if room_type in template["room_types"]]
    return preferred + [name for name in AD_TEMPLATES if name not in preferred]


def generate_ad_copy(
    *,
    room_type: str,
    deposit: int,
    rent: int,
    template_name: str,
    location: str = "",
    building_name: str = "",
    title_headline: str = "",
    title_template: str = "",
    available_date: str = "",
    selected_features: list[str] | None = None,
    region_sentence: str = "",
    region_sentences: list[str] | None = None,
    transit_living_text: str = "",
    additional_text: str = "",
    output_length: str = "기본형",
    include_actual_listing_notice: bool = False,
    include_actual_photo_notice: bool = False,
) -> dict[str, str]:
    """입력된 사실만 조합해 제목과 광고 본문을 만든다."""
    if template_name not in AD_TEMPLATES:
        raise ValueError("광고 템플릿을 다시 선택해 주세요.")
    if room_type not in ROOM_TYPES:
        raise ValueError("방 형태를 다시 선택해 주세요.")
    if deposit < 0 or rent < 0:
        raise ValueError("보증금과 월세는 0 이상으로 입력해 주세요.")
    if output_length not in OUTPUT_LENGTHS:
        raise ValueError("문구 길이를 다시 선택해 주세요.")

    template = AD_TEMPLATES[template_name]
    features = [feature for feature in (selected_features or []) if feature in FEATURE_SENTENCES]
    if title_template.strip():
        title = title_template.strip()
    else:
        title_parts = [part.strip() for part in (title_headline, building_name, room_type) if part.strip()]
        if not title_parts:
            title_parts = [features[0] if features else room_type, room_type]
        title = " ".join(title_parts)

    core_lines = [template["opening"]]
    if room_type in {"투룸", "투베이", "쓰리룸", "쓰리베이"}:
        core_lines.append("침실과 생활공간을 나눠 쓰고 싶은 분께 추천드려요.")
    if location.strip() or building_name.strip():
        address = " ".join(part.strip() for part in (location, building_name) if part.strip())
        core_lines.extend(["", f"📍 {address}"])
    opening = template.get("opening_by_room_type", {}).get(room_type, template["opening"])
    layout = template.get("layout_by_room_type", {}).get(room_type, template["layout"])
    core_lines = [opening, *core_lines[1:]]
    core_lines.extend(["", "✔ 핵심 포인트", f"✔ {layout}"])
    core_lines.extend(f"✔ {FEATURE_SENTENCES[feature]}" for feature in features)
    core_lines.append(f"✔ 보증금 {deposit:,} / 월세 {rent:,}")
    if available_date.strip():
        core_lines.append(f"✔ 입주 가능: {available_date.strip()}")
    if additional_text.strip():
        core_lines.extend(f"✔ {line.strip()}" for line in additional_text.splitlines() if line.strip())
    if output_length == "짧은형":
        core_lines.extend(["", "자세한 조건과 방문 가능 여부는 문의로 확인해 주세요."])
        return {"title": title, "body": "\n".join(core_lines)}

    lines = core_lines
    selected_region_sentences = [sentence.strip() for sentence in (region_sentences or []) if sentence.strip()]
    if region_sentence.strip():
        selected_region_sentences.insert(0, region_sentence.strip())
    if selected_region_sentences or transit_living_text.strip():
        lines.extend(["", "🚉 교통 & 생활"])
        lines.extend(selected_region_sentences)
        lines.extend(line.strip() for line in transit_living_text.splitlines() if line.strip())
    lines.extend(["", "💡 이런 분께 추천드려요"])
    recommendations = [*template["recommendations"], "교통과 생활편의를 중요하게 보는 분"]
    if output_length == "상세형":
        recommendations.append("입주 전 조건을 꼼꼼히 비교하고 싶은 분")
    lines.extend(f"👉 {item}" for item in recommendations)
    notices = list(COMMON_NOTICE)
    if include_actual_listing_notice:
        notices.insert(0, "본 매물은 실매물입니다.")
    if include_actual_photo_notice:
        notices.insert(1 if include_actual_listing_notice else 0, "사진은 실제 호실 촬영본이며 촬영 시점에 따라 일부 차이가 있을 수 있습니다.")
    lines.extend(["", "📌 안내사항"])
    lines.extend(f"✔ {notice}" for notice in notices)
    return {"title": title, "body": "\n".join(lines)}
