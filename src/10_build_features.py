"""
10. 분석용 특성 생성 및 최종 데이터셋 구성
==========================================
분기 재무 패널에서 독립변수를 만들고, CAR과 합쳐 분석용 테이블을 완성한다.

특성 설계의 핵심 — 영업이익 성장률을 쓰지 않는 이유:

  기저가 적자면 관행적인 YoY 성장률 공식이 방향을 반대로 기록한다.
      -10억 -> -20억 (악화):  (-20-(-10))/(-10) = +100%  ← 개선으로 잘못 기록
      -10억 -> -5억  (개선):  ( -5-(-10))/(-10) =  -50%  ← 악화로 잘못 기록
  분모에 절댓값을 씌우면 부호는 잡히지만, 기저가 0에 가까우면 값이 폭발한다.
      -0.1억 -> +3억: +3100%

  그래서 영업이익 변화를 두 가지로 분해한다.
      매출액 YoY 성장률  (매출은 음수가 될 수 없어 부호 문제가 없다)
      OPM 변화폭 (%p)    (비율의 차이라 적자에서도 방향이 보존된다)
  서프라이즈 대리변수도 매출액으로 정규화해 같은 문제를 피한다.

실행:  python src/10_build_features.py
출력:  data/dataset.csv
"""

import numpy as np
import pandas as pd

from config import DATA_DIR

# 추세 예측에 쓸 과거 분기 수 (직전 4분기 = 1년)
TREND_LAGS = 4


def add_financial_features(fin: pd.DataFrame) -> pd.DataFrame:
    """분기 재무 패널에 파생 지표를 붙인다."""
    fin = fin.sort_values(["종목코드", "연도", "분기"]).copy()
    g = fin.groupby("종목코드", group_keys=False)

    # --- 전년 동분기 (4분기 전) ---
    for col in ["매출액", "영업이익", "OPM", "자산총계"]:
        fin[f"{col}_전년"] = g[col].shift(4)

    # --- 1. 매출액 YoY 성장률 ---
    # 매출은 음수가 될 수 없으므로 통상적인 성장률 공식이 안전하다.
    fin["매출YoY"] = (fin["매출액"] - fin["매출액_전년"]) / fin["매출액_전년"]

    # --- 2. OPM 변화폭 (%p) ---
    # 비율끼리의 차이라 적자 구간에서도 개선/악화 방향이 그대로 보존된다.
    fin["OPM변화"] = fin["OPM"] - fin["OPM_전년"]

    # --- 3. 영업이익 추세이탈도 (서프라이즈 대리) ---
    # 컨센서스를 쓸 수 없으므로 과거 4분기 추세로 기대치를 만든다.
    # 매출액으로 나눠 규모 차이를 제거하고 적자 기저 문제도 함께 피한다.
    def trend_expectation(s: pd.Series) -> pd.Series:
        """직전 4분기 선형 추세를 외삽해 이번 분기 예상치를 만든다."""
        out = []
        vals = s.to_numpy(dtype=float)
        for i in range(len(vals)):
            hist = vals[max(0, i - TREND_LAGS):i]
            hist = hist[~np.isnan(hist)]
            if len(hist) < TREND_LAGS:
                out.append(np.nan)
                continue
            x = np.arange(len(hist))
            slope, intercept = np.polyfit(x, hist, 1)
            out.append(intercept + slope * len(hist))
        return pd.Series(out, index=s.index)

    fin["영업이익_추세예측"] = g["영업이익"].apply(trend_expectation)
    fin["추세이탈도"] = (fin["영업이익"] - fin["영업이익_추세예측"]) / fin["매출액"]

    # --- 4~5. 흑자/적자 전환 더미 ---
    # 부호가 바뀌는 순간은 연속 지표로 표현되지 않는 질적 사건이다.
    prev_op = g["영업이익"].shift(1)
    fin["흑자전환"] = ((prev_op < 0) & (fin["영업이익"] >= 0)).astype(int)
    fin["적자전환"] = ((prev_op >= 0) & (fin["영업이익"] < 0)).astype(int)
    fin["적자지속"] = ((prev_op < 0) & (fin["영업이익"] < 0)).astype(int)

    # --- 규모 통제변수 ---
    # 이벤트 시점 시가총액을 무료로 확보할 수 없어 자산총계를 대리로 쓴다.
    # 동일 분기 재무제표 값이라 시점 정합성은 오히려 완전하다.
    fin["로그자산"] = np.log(fin["자산총계"])

    fin["분기라벨"] = fin["연도"].astype(str) + "Q" + fin["분기"].astype(str)
    return fin


def main():
    fin = pd.read_csv(DATA_DIR / "financials_quarterly.csv", dtype={"종목코드": str})
    car = pd.read_csv(DATA_DIR / "car.csv", dtype={"종목코드": str},
                      parse_dates=["발표일", "거래일t0"])

    print("=" * 70)
    print("1. 재무 특성 생성")
    print("=" * 70)
    fin = add_financial_features(fin)
    print(f"재무 패널: {len(fin)}행")

    # --- CAR과 결합 ---
    print()
    print("=" * 70)
    print("2. CAR과 결합")
    print("=" * 70)

    df = car.merge(
        fin[["종목코드", "분기라벨", "매출액", "영업이익", "OPM", "자산총계",
             "매출YoY", "OPM변화", "추세이탈도",
             "흑자전환", "적자전환", "적자지속", "로그자산", "기준", "산출방식"]],
        left_on=["종목코드", "분기"], right_on=["종목코드", "분기라벨"],
        how="left",
    ).drop(columns=["분기라벨"])

    print(f"결합 결과: {len(df)}행")
    unmatched = df[df["매출액"].isna()]
    if len(unmatched):
        print(f"[확인 필요] 재무 데이터가 붙지 않은 이벤트 {len(unmatched)}건")
        print(unmatched[["종목명", "분기"]].to_string(index=False))

    # --- 정보출처 더미 ---
    # 잠정실적 = 정보의 최초 공개, 정기보고서 = 이미 알려진 수치의 확정.
    # 주가 반응 크기가 다를 수밖에 없으므로 통제한다.
    df["잠정실적더미"] = (df["정보출처"] == "잠정실적").astype(int)

    # --- 분석 표본 정의 ---
    df["분석표본"] = (
        df["CAR_0_1"].notna()
        & df["매출YoY"].notna()
        & df["OPM변화"].notna()
        & df["추세이탈도"].notna()
        & df["CAR_PRE"].notna()
        & df["로그자산"].notna()
        & (~df["상장직후"])          # 상장 직후 2개 분기 제외
        & (df["포함버전"] == "v1")   # v2 후보(파마리서치)는 본 분석에서 제외
    )

    df.to_csv(DATA_DIR / "dataset.csv", index=False, encoding="utf-8-sig")

    # ---------------- 확인 ----------------
    print()
    print("=" * 70)
    print("3. 표본 구성")
    print("=" * 70)

    print("\n--- 단계별 표본 수 ---")
    steps = [
        ("전체 이벤트", len(df)),
        ("v1만", (df["포함버전"] == "v1").sum()),
        ("+ CAR 있음", ((df["포함버전"] == "v1") & df["CAR_0_1"].notna()).sum()),
        ("+ 상장직후 제외", ((df["포함버전"] == "v1") & df["CAR_0_1"].notna()
                        & ~df["상장직후"]).sum()),
        ("+ 특성 전부 있음 (최종)", df["분석표본"].sum()),
    ]
    for label, n in steps:
        print(f"  {label:<28s} {n:>4d}")

    smp = df[df["분석표본"]]

    print("\n--- 종목별 최종 표본 ---")
    print(smp.groupby("종목명").size().sort_values(ascending=False).to_string())

    print("\n--- 특성 기술통계 ---")
    feats = ["매출YoY", "OPM변화", "추세이탈도", "CAR_PRE", "로그자산"]
    print(smp[feats].describe().T.to_string(
        float_format=lambda x: f"{x:,.4f}"))

    print("\n--- 더미 변수 ---")
    for c in ["흑자전환", "적자전환", "적자지속", "잠정실적더미"]:
        print(f"  {c:<12s} {int(smp[c].sum()):>3d}건  ({smp[c].mean():.1%})")

    print("\n--- 종속변수 ---")
    print(smp[["CAR_0_1", "CAR_0_5", "CAR_0_20"]].describe().T.to_string(
        float_format=lambda x: f"{x:+.4f}"))

    print("\n--- 특성 간 상관계수 ---")
    print(smp[feats + ["CAR_0_1"]].corr().round(2).to_string())

    print(f"\n저장: {DATA_DIR / 'dataset.csv'}")


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    main()
