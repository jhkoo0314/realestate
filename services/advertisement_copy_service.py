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


LEAD_TOP_PRESETS = {
    "다양한 매물 비교": "★ 찾으시는 조건에 맞춰 다양한 매물을 비교해드립니다.",
    "조건 상담": "★ 보증금·월세·입주일을 말씀해주시면 조건에 맞는 매물을 찾아드립니다.",
    "대체 매물 안내": "★ 광고 매물이 조건에 맞지 않아도 다른 매물 안내가 가능합니다.",
}

LEAD_ALTERNATIVE_PRESETS = {
    "기본 상담 유도": "현재 매물이 조건에 맞지 않더라도 괜찮습니다. 예산·입주일·위치·주차 등 원하는 조건을 말씀해주시면 다른 매물도 함께 찾아드립니다.",
    "비교 상담 유도": "원룸·투룸 등 여러 매물을 비교해 보실 수 있습니다. 필요한 조건을 알려주시면 맞는 매물을 안내해드립니다.",
    "입주 조건 상담": "입주 시기와 예산이 정해지지 않았어도 상담 가능합니다. 현재 상황에 맞는 매물을 함께 찾아드립니다.",
}

LEAD_BASE_OPTION_TEXT = "냉장고, 세탁기, 에어컨 등 생활 기본 옵션을 갖춘 실용적인 구성"
BUILDING_HIGHLIGHTS = ["엘리베이터 있음", "주차 편리함"]
BUILDING_HIGHLIGHT_SENTENCES = {
    "엘리베이터 있음": "엘리베이터 있어 층간 이동이 편리함",
    "주차 편리함": "주차가 편리해 차량 이용을 고려하는 분께 적합",
}

# 광고 상단은 지역 홍보 대신 매물의 성격을 짧게 설명한다.
# 신축급/구축과 강조유형은 사용자가 직접 선택하며, DB 값으로 추정하지 않는다.
PROPERTY_POSITIONING_COPY = {
    "신축급": {
        "컨디션": {
            "headline": "깔끔한 컨디션을 중요하게 본다면 살펴볼 신축급 {room_type}",
            "points": ["깔끔하게 관리된 신축급 컨디션", "깨끗한 주거환경을 중요하게 보는 분께 추천"],
        },
        "공간": {
            "headline": "여유 있는 공간감이 장점인 신축급 {room_type}",
            "points": ["여유 있는 공간감이 장점인 구조", "방 크기와 실사용 공간을 중요하게 보는 분께 추천"],
        },
        "특별매물": {
            "headline": "특별한 구성을 직접 확인해 볼 수 있는 신축급 {room_type}",
            "points": [],
        },
    },
    "구축": {
        "가격": {
            "headline": "주거비 부담을 낮춰 찾는 분께 좋은 실속형 {room_type}",
            "points": ["부담을 낮춘 임대조건이 장점인 매물", "주거비를 중요하게 보는 분께 적합"],
        },
        "공간": {
            "headline": "가격과 공간을 함께 고려하기 좋은 {room_type}",
            "points": ["여유 있는 실사용 공간이 장점인 매물", "방 크기를 중요하게 보는 분께 비교하기 좋은 조건"],
        },
        "계약조건": {
            "headline": "필요한 거주기간과 조건을 맞춰보기 좋은 {room_type}",
            "points": ["거주기간과 입주 일정을 함께 확인해 볼 수 있는 매물", "거주기간과 입주일정을 중요하게 보는 분께 적합"],
        },
        "특별매물": {
            "headline": "특별한 구성을 직접 확인해 볼 수 있는 {room_type}",
            "points": [],
        },
    },
}

LEAD_DEFAULT_OPTION_TEXT = "냉장고, 세탁기, 에어컨 등 생활 기본 옵션을 갖춘 실용적인 구성"
LEAD_COMPARISON_CONSULTATION_TEXT = (
    "다양한 원룸·투룸 매물을 보유하고 있어",
    "원하시는 조건에 맞춰 비교 상담해드립니다.",
)
LEAD_TOP_INTRO_TEXT = "찾으시는 조건에 맞춰 다양한 매물을 비교해드립니다."

# 지역 핵심요약은 광고에 바로 쓰는 고정 템플릿이다. 개별 매물의 거리·주차·옵션은
# 확인 전에는 넣지 않고, 선택한 지역과 실제 주소가 맞는 경우에만 사용한다.
REGION_SUMMARY_TEMPLATES = {
    "북수리": {
        "배방·월천 생활권형": [
            "배방·월천 생활권을 함께 고려하기 좋은 위치",
            "배방과 탕정 방향 생활권 이용을 살펴보기 좋은 지역",
            "생활 편의와 주거 환경을 함께 비교하는 분께 추천",
        ],
        "실거주 생활권형": [
            "배방 생활권에서 편하게 거주할 곳을 찾는 분께 추천",
            "일상 이동과 생활 편의를 함께 고려하기 좋은 지역",
            "원룸·투룸 조건을 비교하며 찾기 좋은 배방 생활권",
        ],
    },
    "장재리": {
        "천안아산역 생활권형": [
            "천안아산역과 배방 생활권을 함께 고려하는 위치",
            "광역 교통 이용을 중요하게 보는 분께 추천",
            "생활권과 이동 편의를 함께 비교하기 좋은 장재리",
        ],
        "배방 신도시 생활권형": [
            "배방 신도시 생활권을 고려하는 분께 추천",
            "주거·생활 편의와 이동 동선을 함께 살펴보기 좋은 지역",
            "원룸·투룸을 비교하며 찾기 좋은 장재리 생활권",
        ],
    },
    "공수리": {
        "배방복합커뮤니티센터 생활권형": [
            "배방복합커뮤니티센터 생활권을 고려하는 위치",
            "배방 생활권의 생활 편의를 함께 살펴보기 좋은 지역",
            "교통과 일상 편의를 함께 비교하는 분께 추천",
        ],
        "배방 생활권형": [
            "배방 생활권에서 실거주 매물을 찾는 분께 추천",
            "생활 편의와 주거 환경을 함께 고려하기 좋은 공수리",
            "원룸·투룸 조건을 비교하며 찾기 좋은 배방 생활권",
        ],
    },
    "월천지구": {
        "배방·탕정 생활권형": [
            "배방·탕정 생활권을 함께 고려하는 위치",
            "인근 생활권과 이동 동선을 함께 살펴보기 좋은 지역",
            "생활 편의와 주거 환경을 비교하는 분께 추천",
        ],
        "배방 생활권형": [
            "배방 생활권에서 거주할 곳을 찾는 분께 추천",
            "일상생활과 인근 업무지역 이동을 함께 고려하기 좋은 위치",
            "원룸·투룸을 비교하며 찾기 좋은 월천지구 생활권",
        ],
    },
}


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


def room_title_templates_for_room_type(room_type: str) -> list[str]:
    """방 형태에 맞는 광고 제목 템플릿만 돌려준다."""
    title_family = "원룸" if room_type == "원룸" else "쓰리룸" if room_type == "쓰리룸" else "투룸"
    return ROOM_TITLE_TEMPLATES[title_family]


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
        core_lines.append(f"✔ 입주가능일: {available_date.strip()}")
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
        notices.insert(1 if include_actual_listing_notice else 0, "사진은 실제 해당 호실 촬영본입니다. 촬영 이후 청소·가구 배치·시설 상태 등에 일부 변동이 있을 수 있으므로 방문 시 최종 확인 부탁드립니다.")
    lines.extend(["", "📌 안내사항"])
    lines.extend(f"✔ {notice}" for notice in notices)
    return {"title": title, "body": "\n".join(lines)}


def parse_optional_amount(value: str, label: str) -> int | None:
    """광고 직접입력에서 비울 수 있는 금액을 만원 단위 숫자로 받는다."""
    if not value.strip():
        return None
    return parse_amount(value, label)


def generate_lead_ad_copy(
    *,
    location: str,
    room_type: str,
    title_template: str,
    transaction_type: str,
    deposit: int | None,
    rent: int | None,
    management_fee: int | None,
    available_date: str,
    property_condition: str,
    positioning_type: str,
    special_point: str,
    option_text: str,
    include_actual_listing_notice: bool,
    include_actual_photo_notice: bool,
) -> dict[str, str]:
    """직접 선택한 매물 성격과 확인된 사실만으로 광고문을 만든다."""
    if room_type not in ROOM_TYPES:
        raise ValueError("방 형태를 다시 선택해 주세요.")
    if transaction_type not in {"월세", "전세", "보증부월세", "가격 문의"}:
        raise ValueError("거래 방식을 다시 선택해 주세요.")
    if property_condition not in PROPERTY_POSITIONING_COPY:
        raise ValueError("매물 컨디션을 신축급 또는 구축으로 선택해 주세요.")
    positioning = PROPERTY_POSITIONING_COPY[property_condition].get(positioning_type)
    if positioning is None:
        raise ValueError("선택한 매물 컨디션에 맞는 강조유형을 선택해 주세요.")

    clean = lambda value: str(value or "").strip()
    allowed_title_templates = room_title_templates_for_room_type(room_type)
    if title_template and title_template not in allowed_title_templates:
        raise ValueError("방 형태에 맞는 제목 템플릿을 선택해 주세요.")
    title = clean(title_template) or " ".join(part for part in (clean(location), room_type) if part) or room_type
    cleaned_special_point = clean(special_point)
    if positioning_type == "특별매물" and not cleaned_special_point:
        raise ValueError("특별매물은 이 매물의 특별한 점을 한 줄로 입력해 주세요.")
    positioning_points = [point.format(room_type=room_type) for point in positioning["points"]]
    if cleaned_special_point:
        positioning_points.append(cleaned_special_point)

    price_parts: list[str] = []
    if transaction_type == "전세":
        if deposit is not None:
            price_parts.append(f"전세: {deposit:,}만원")
    elif transaction_type == "가격 문의":
        price_parts.append("가격은 문의로 확인해 주세요.")
    else:
        if deposit is not None:
            price_parts.append(f"보증금: {deposit:,}만원")
        if rent is not None:
            price_parts.append(f"월세: {rent:,}만원")
    if management_fee is not None:
        price_parts.append(f"관리비: {management_fee:,}만원")
    if clean(available_date):
        price_parts.append(f"입주가능일: {clean(available_date)}")
    if not price_parts:
        price_parts.append("가격은 문의로 확인해 주세요.")

    notices = ["다가구주택은 호실별 전용면적을 참고용으로 안내드립니다.", "계약 가능 여부 및 옵션은 실시간으로 변경될 수 있으므로 방문 전 문의 부탁드립니다."]
    if include_actual_listing_notice:
        notices.insert(0, "본 매물은 실매물입니다.")
    if include_actual_photo_notice:
        notices.insert(1 if include_actual_listing_notice else 0, "사진은 실제 해당 호실 촬영본입니다. 촬영 이후 청소·가구 배치·시설 상태 등에 일부 변동이 있을 수 있으므로 방문 시 최종 확인 부탁드립니다.")

    lines = [
        LEAD_TOP_INTRO_TEXT,
        "",
        "────────────",
        "",
        positioning["headline"].format(room_type=room_type),
        "",
        "① 이 매물의 포인트",
    ]
    lines.extend(f"• {point}" for point in positioning_points)
    lines.extend(["", "💰 조건"])
    lines.extend(price_parts)
    lines.extend(["", "📍 위치", clean(location) or "위치는 문의로 확인해 주세요."])
    lines.extend(["", "🛋️ 옵션", clean(option_text) or LEAD_DEFAULT_OPTION_TEXT])
    lines.extend([
        "", "🤝 비교 상담", *LEAD_COMPARISON_CONSULTATION_TEXT,
        "", "📌 안내사항",
    ])
    lines.extend(f"✔ {notice}" for notice in notices)
    return {"title": title, "body": "\n".join(lines)}
