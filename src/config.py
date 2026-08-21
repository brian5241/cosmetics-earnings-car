"""
프로젝트 공통 설정
==================
경로, API 키, 분석 기간 등 여러 스크립트가 함께 쓰는 값을 한 곳에 모은다.

다른 스크립트에서는 이렇게 쓴다:
    from config import DART_API_KEY, DATA_DIR, UNIVERSE
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Windows 콘솔 기본 인코딩(cp949)에서는 한글 출력이 깨지고
# 일부 특수문자는 UnicodeEncodeError 를 일으킨다. UTF-8 로 고정한다.
if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ============================================================
# 경로
# ============================================================

ROOT      = Path(__file__).resolve().parent.parent
DATA_DIR  = ROOT / "data"       # 정제된 산출물 (git 추적)
RAW_DIR   = DATA_DIR / "raw"    # 수집 원본 (gitignore 대상)
CACHE_DIR = DATA_DIR / "cache"  # 임시 캐시 (gitignore 대상)

for _d in (DATA_DIR, RAW_DIR, CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ============================================================
# API 키
# ============================================================

# .env 파일에서 키를 읽는다.
# .env 는 .gitignore 에 포함되어 저장소에 올라가지 않으므로
# 키가 코드나 커밋 이력에 남지 않는다.
load_dotenv(ROOT / ".env")

DART_API_KEY = os.getenv("DART_API_KEY", "").strip()

if not DART_API_KEY:
    raise RuntimeError(
        ".env 파일에 DART_API_KEY 가 없습니다.\n"
        f"  {ROOT / '.env'} 를 열어 키를 입력하세요.\n"
        "  형식: DART_API_KEY=발급받은키 (공백·따옴표 없이)"
    )


# ============================================================
# 분석 기간
# ============================================================

# 이벤트(실적 발표) 대상 구간
EVENT_START = "2022-09-01"
EVENT_END   = "2026-08-21"

# 주가 수집 구간.
# 베타 추정에 발표일 이전 약 1년(250거래일)이 필요하므로
# 이벤트 시작보다 앞서서 확보한다.
PRICE_START = "2021-06-01"
PRICE_END   = "2026-08-21"

# 이벤트 스터디 윈도우 (거래일 기준)
ESTIMATION_WINDOW = (-250, -30)   # 베타 추정 구간
EVENT_WINDOWS = {
    "CAR_0_1":  (0, 1),    # 주력
    "CAR_0_5":  (0, 5),    # 보조
    "CAR_0_20": (0, 20),   # 보조 (PEAD 확인용)
    "CAR_PRE":  (-20, -1), # 발표 전 선반영 측정
}

# 장 마감 시각. 이후 발표는 이벤트 기준일을 다음 거래일로 민다.
MARKET_CLOSE = "15:30"


# ============================================================
# 분석 대상 종목
# ============================================================

# 유형: 브랜드 / ODM / 유통  (v2에서 더미 변수로 사용)
# 버전: v1 = 화장품 협의, v2 = K뷰티 광의 확장 시 추가
UNIVERSE = [
    # (종목코드, 종목명, 유형, 버전)
    ("090430", "아모레퍼시픽",     "브랜드", "v1"),
    ("278470", "에이피알",         "브랜드", "v1"),
    ("237880", "클리오",           "브랜드", "v1"),
    ("018290", "브이티",           "브랜드", "v1"),
    ("092730", "네오팜",           "브랜드", "v1"),
    ("483650", "달바글로벌",       "브랜드", "v1"),
    ("161890", "한국콜마",         "ODM",   "v1"),
    ("192820", "코스맥스",         "ODM",   "v1"),
    ("241710", "코스메카코리아",   "ODM",   "v1"),
    ("257720", "실리콘투",         "유통",  "v1"),
    ("114840", "아이패밀리에스씨", "유통",  "v1"),
    # --- v2 확장 후보 (현재 수집 대상 아님) ---
    ("214450", "파마리서치",       "메디컬", "v2"),
]

# 현재 분석에 사용할 버전
ACTIVE_VERSION = "v1"


def active_codes() -> list[str]:
    """현재 버전에 해당하는 종목코드 목록."""
    return [c for c, _, _, v in UNIVERSE if v == ACTIVE_VERSION]
