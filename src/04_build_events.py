"""
04. 이벤트 테이블 구성
======================
03에서 수집한 공시 목록을 '종목 x 분기' 단위 이벤트 1건씩으로 정리한다.

규칙:
  1. 분석 단위는 종목 x 분기. 한 분기에 이벤트는 하나다.
  2. t=0 은 그 분기 실적이 '처음 공개된 날'.
     → 대상 분기별로 가장 이른 접수일자를 고른다.
  3. [기재정정] 공시는 제외한다. 원공시가 이미 존재하기 때문이다.
  4. 같은 날 여러 건이 나오면 우선순위로 하나만 남긴다.
     (한국콜마는 연결·별도를 같은 날 둘 다 공시하고,
      결산 시점에는 잠정실적과 손익구조변동 공시가 겹친다)
  5. 어느 경로로 잡혔는지 '정보출처'로 기록한다.
     잠정실적 = 정보의 최초 공개, 정기보고서 = 이미 알려진 수치의 확정.
     주가 반응 크기가 다르므로 통제변수로 쓴다.

실행:  python src/04_build_events.py
출력:  data/events.csv
"""

import re

import pandas as pd

from config import DATA_DIR, UNIVERSE

# 분석 대상 분기 (16분기)
QUARTERS = [(y, q) for y in range(2022, 2027) for q in range(1, 5)]
QUARTERS = [(y, q) for (y, q) in QUARTERS
            if (y, q) >= (2022, 3) and (y, q) <= (2026, 2)]

# 공시 세부 구분과 우선순위.
# 숫자가 작을수록 우선. 같은 날 여러 건일 때 tie-break 로 쓴다.
DISCLOSURE_KINDS = [
    (1, "연결잠정",   re.compile(r"연결재무제표기준영업\(잠정\)실적")),
    (2, "별도잠정",   re.compile(r"영업\(잠정\)실적")),
    (3, "손익변동",   re.compile(r"손익구조.*변동")),
    (4, "정기보고서", re.compile(r"분기보고서|반기보고서|사업보고서")),
]


def classify_kind(name: str) -> tuple[int, str]:
    """공시명에서 세부 구분과 우선순위를 판정한다.

    연결/별도 판정은 순서가 중요하다.
    '연결재무제표기준영업(잠정)실적' 은 '영업(잠정)실적' 패턴도 만족하므로
    반드시 연결을 먼저 검사해야 한다.
    """
    for prio, kind, pat in DISCLOSURE_KINDS:
        if pat.search(name):
            return prio, kind
    return 99, "기타"


def main():
    src = pd.read_csv(DATA_DIR / "earnings_events.csv", dtype={"종목코드": str})

    print("=" * 70)
    print("1. 필터링")
    print("=" * 70)
    print(f"입력: {len(src):,}건")

    # --- 정정공시 제외 ---
    df = src[~src["정정여부"]].copy()
    print(f"정정공시 제외: {len(df):,}건  (-{len(src) - len(df)})")

    # --- 분기 판정 실패 건 제외 ---
    df = df[df["대상연도"].notna() & df["대상분기"].notna()].copy()
    df["대상연도"] = df["대상연도"].astype(int)
    df["대상분기"] = df["대상분기"].astype(int)
    print(f"분기 판정 성공: {len(df):,}건")

    # --- 분석 대상 분기로 한정 ---
    df["분기키"] = list(zip(df["대상연도"], df["대상분기"]))
    df = df[df["분기키"].isin(QUARTERS)].copy()
    print(f"분석 기간 내: {len(df):,}건  ({QUARTERS[0]} ~ {QUARTERS[-1]})")

    # --- 세부 구분 ---
    kinds = df["공시명"].apply(classify_kind)
    df["우선순위"] = [k[0] for k in kinds]
    df["세부구분"] = [k[1] for k in kinds]

    print("\n--- 세부 구분별 건수 ---")
    print(df["세부구분"].value_counts().to_string())

    print()
    print("=" * 70)
    print("2. 종목 x 분기 단위로 축약")
    print("=" * 70)

    # 가장 이른 접수일자 → 같은 날이면 우선순위 순
    df = df.sort_values(["종목코드", "대상연도", "대상분기", "접수일자", "우선순위"])
    events = df.groupby(["종목코드", "대상연도", "대상분기"], as_index=False).first()

    print(f"이벤트 {len(events):,}건  (공시 {len(df):,}건에서 축약)")

    # --- 정보출처: 잠정 vs 정기 ---
    events["정보출처"] = events["세부구분"].map({
        "연결잠정": "잠정실적",
        "별도잠정": "잠정실적",
        "손익변동": "잠정실적",
        "정기보고서": "정기보고서",
    })

    # --- 정리 ---
    events["분기"] = (events["대상연도"].astype(str)
                    + "Q" + events["대상분기"].astype(str))
    events["발표일"] = pd.to_datetime(events["접수일자"].astype(str), format="%Y%m%d")

    # --- 상장 전 이벤트 제외 ---
    # 비상장 시기에도 정기보고서를 제출한 기업이 있다(에이피알, 달바글로벌).
    # 주가가 없으므로 이벤트로 쓸 수 없다.
    # 01단계에서 확인한 첫 거래일을 기준으로 거른다.
    uni = pd.read_csv(DATA_DIR / "universe.csv", dtype={"종목코드": str})
    first_trade = dict(zip(uni["종목코드"], pd.to_datetime(uni["첫거래일"])))
    events["첫거래일"] = events["종목코드"].map(first_trade)

    before = len(events)
    pre_listing = events[events["발표일"] < events["첫거래일"]]
    if len(pre_listing):
        print("\n--- 상장 전 이벤트 제외 ---")
        print(pre_listing.groupby("종목명")["분기"]
              .agg(["count", "min", "max"]).to_string())
    events = events[events["발표일"] >= events["첫거래일"]].copy()
    print(f"\n상장 전 제외: {before} → {len(events)}건  (-{before - len(events)})")

    # 상장 후 경과 분기.
    # 상장 직후는 유통물량 부족·락업 해제 등으로 주가가 정상 상태가 아니므로
    # 이후 단계에서 첫 2개 분기를 제외할 수 있도록 표시해둔다.
    events["상장후개월"] = ((events["발표일"] - events["첫거래일"]).dt.days / 30.44).round(1)
    events["상장직후"] = events["상장후개월"] < 6

    cols = ["종목코드", "종목명", "유형", "포함버전", "corp_code",
            "대상연도", "대상분기", "분기", "발표일", "접수번호",
            "세부구분", "정보출처", "공시명", "첫거래일", "상장후개월", "상장직후"]
    events = events[cols].sort_values(["종목코드", "대상연도", "대상분기"])
    events.to_csv(DATA_DIR / "events.csv", index=False, encoding="utf-8-sig")

    # ---------------- 확인 출력 ----------------
    print("\n--- 정보출처 분포 ---")
    print(events["정보출처"].value_counts().to_string())

    print("\n--- 세부구분 분포 ---")
    print(events["세부구분"].value_counts().to_string())

    print("\n--- 종목별 이벤트 수 / 잠정실적 비율 ---")
    summary = events.groupby("종목명").agg(
        이벤트수=("분기", "count"),
        잠정실적=("정보출처", lambda s: (s == "잠정실적").sum()),
    )
    summary["잠정비율"] = (summary["잠정실적"] / summary["이벤트수"] * 100).round(0)
    print(summary.sort_values("이벤트수").to_string())

    print("\n--- 커버리지 (종목 x 분기, 값=정보출처) ---")
    mark = events.copy()
    mark["표시"] = mark["정보출처"].map({"잠정실적": "잠", "정기보고서": "정"})
    cov = mark.pivot(index="종목명", columns="분기", values="표시").fillna("·")
    print(cov.to_string())

    # --- 비어 있는 종목x분기 확인 ---
    v1_codes = {c for c, _, _, v in UNIVERSE if v == "v1"}
    expected = len(v1_codes) * len(QUARTERS)
    actual = len(events[events["포함버전"] == "v1"])
    print(f"\nv1 기준: {actual} / {expected} 분기 확보 "
          f"({actual / expected * 100:.0f}%)")

    print(f"\n저장: {DATA_DIR / 'events.csv'}")


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    main()
