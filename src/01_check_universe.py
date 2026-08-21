"""
01. 유니버스 검증
================
분석 대상 종목의 코드 유효성, 상장일, 주가 가용 구간, 시가총액을 확인하고
종목 마스터 CSV(data/universe.csv)를 생성한다.

DART API 키가 없어도 실행된다. (주가·종목정보는 FinanceDataReader 사용)

실행:  python src/01_check_universe.py
출력:  data/universe.csv
"""

from pathlib import Path

import FinanceDataReader as fdr
import pandas as pd

# ============================================================
# 설정 — 바꿀 값은 전부 여기에
# ============================================================

# 분석 대상 종목.
#   유형: 브랜드 / ODM / 유통  (v2에서 더미 변수로 사용)
#   버전: v1 = 화장품 협의, v2 = K뷰티 광의 확장 시 추가
UNIVERSE = [
    # (종목코드, 종목명, 유형, 버전)
    ("090430", "아모레퍼시픽",   "브랜드", "v1"),
    ("278470", "에이피알",       "브랜드", "v1"),
    ("237880", "클리오",         "브랜드", "v1"),
    ("018290", "브이티",         "브랜드", "v1"),
    ("092730", "네오팜",         "브랜드", "v1"),
    ("483650", "달바글로벌",     "브랜드", "v1"),
    ("161890", "한국콜마",       "ODM",   "v1"),
    ("192820", "코스맥스",       "ODM",   "v1"),
    ("241710", "코스메카코리아", "ODM",   "v1"),
    ("257720", "실리콘투",       "유통",  "v1"),
    ("114840", "아이패밀리에스씨", "유통", "v1"),
    # --- v2 확장 후보 (지금은 수집하지 않음) ---
    ("214450", "파마리서치",     "메디컬", "v2"),
]

# 분석 기간. 4년치 분기 실적을 보되,
# 베타 추정에 발표일 이전 약 1년(250거래일)이 더 필요하므로
# 주가는 이벤트 시작보다 1년 앞서 확보해야 한다.
EVENT_START = "2022-09-01"   # 첫 실적발표 이벤트 예상 시점
PRICE_START = "2021-06-01"   # 주가 수집 시작 (베타 추정용 여유분 포함)
TODAY       = "2026-08-21"

# 경로
ROOT     = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


# ============================================================
# 함수
# ============================================================

def load_krx_listing() -> pd.DataFrame:
    """KRX 전체 상장종목 정보(시총·상장주식수 포함)를 가져온다.

    왜 pykrx가 아니라 FDR인가:
    pykrx의 get_market_cap()은 KRX 로그인을 요구하도록 바뀌어 현재 동작하지 않는다.
    FDR의 StockListing은 로그인 없이 시총(Marcap)과 상장주식수(Stocks)를 준다.
    단 '오늘 기준 스냅샷'이라 과거 시점 시총은 얻을 수 없다.
    """
    return fdr.StockListing("KRX")


def check_price_history(code: str) -> dict:
    """종목별 주가 가용 구간을 확인한다.

    상장일 자체를 주는 무료 API가 마땅치 않아,
    충분히 이른 시점부터 주가를 요청해 '조회 가능 시작일'을 확인한다.

    주의: FDR은 한 번에 최대 3000행까지만 반환한다.
          거래일수가 정확히 3000이면 조회 한도에 걸린 것이므로
          '조회시작일'은 실제 상장일이 아니다. (예: 아모레퍼시픽은 2006년 상장)
          우리는 2021-06 이후 데이터만 필요하므로 분석에는 영향이 없다.
    """
    try:
        px = fdr.DataReader(code, "2010-01-01", TODAY)
    except Exception as e:
        return {"첫거래일": None, "마지막거래일": None, "거래일수": 0,
                "주가확보": False, "비고": f"조회실패: {e}"}

    if px.empty:
        return {"첫거래일": None, "마지막거래일": None, "거래일수": 0,
                "주가확보": False, "비고": "데이터 없음"}

    first, last = px.index[0], px.index[-1]

    # PRICE_START 이전부터 데이터가 있어야 베타 추정이 가능하다.
    has_full = first <= pd.Timestamp(PRICE_START)

    # 최근 거래가 끊겼으면 거래정지·상장폐지 의심 → 눈으로 확인 필요
    stale_days = (pd.Timestamp(TODAY) - last).days

    note = ""
    if not has_full:
        note = "베타 추정구간 부족 → 시장조정모델 폴백 대상"
    if stale_days > 30:
        note = (note + " / " if note else "") + f"최근 거래 {stale_days}일 전 (확인 필요)"

    return {
        "첫거래일": first.date(),
        "마지막거래일": last.date(),
        "거래일수": len(px),
        "주가확보": has_full,
        "비고": note,
    }


def build_universe() -> pd.DataFrame:
    listing = load_krx_listing()
    listing_idx = listing.set_index("Code")

    rows = []
    for code, name_expected, sector, version in UNIVERSE:
        row = {
            "종목코드": code,
            "종목명": name_expected,
            "유형": sector,
            "포함버전": version,
        }

        # --- 1) 종목코드가 실제로 존재하고 이름이 일치하는지 ---
        if code in listing_idx.index:
            actual = listing_idx.loc[code]
            row["실제종목명"] = actual["Name"]
            row["시장"] = actual["Market"]
            row["시가총액"] = int(actual["Marcap"])
            row["상장주식수"] = int(actual["Stocks"])
            row["코드유효"] = True
            row["이름일치"] = (actual["Name"] == name_expected)
        else:
            row.update({"실제종목명": None, "시장": None, "시가총액": None,
                        "상장주식수": None, "코드유효": False, "이름일치": False})

        # --- 2) 주가 가용 구간 ---
        row.update(check_price_history(code))
        rows.append(row)

    cols = ["종목코드", "종목명", "실제종목명", "코드유효", "이름일치", "시장", "유형",
            "포함버전", "시가총액", "상장주식수", "첫거래일", "마지막거래일",
            "거래일수", "주가확보", "비고"]
    return pd.DataFrame(rows)[cols]


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)

    print("KRX 상장종목 정보 조회 중...")
    df = build_universe()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / "universe.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")

    # --- 확인 출력 ---
    print(f"\nshape: {df.shape}")

    print("\n--- 검증 요약 ---")
    print(df[["종목코드", "종목명", "코드유효", "이름일치", "시장",
              "첫거래일", "거래일수", "주가확보"]].to_string(index=False))

    problems = df[~df["코드유효"] | ~df["이름일치"] | ~df["주가확보"]]
    if problems.empty:
        print("\n[OK] 전 종목 이상 없음")
    else:
        print(f"\n[확인 필요] {len(problems)}건")
        print(problems[["종목코드", "종목명", "코드유효", "이름일치",
                        "주가확보", "비고"]].to_string(index=False))

    print(f"\n저장: {out}")
