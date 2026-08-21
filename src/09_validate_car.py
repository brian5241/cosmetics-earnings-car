"""
09. CAR 계산 검증
=================
종속변수를 그대로 믿고 넘어가면 이후 분석 전체가 무의미해진다.
계산된 CAR이 실제 주가 움직임과 맞는지 원자료로 되짚어 확인한다.

확인 항목:
  1. CAR 상하위 이벤트를 원본 주가로 수동 재계산해 일치하는지
  2. 극단값이 데이터 오류인지 실제 사건인지
  3. 발표일 전후 주가가 상식적으로 움직였는지

실행:  python src/09_validate_car.py
"""

import pandas as pd

from config import DATA_DIR

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)


def load():
    car = pd.read_csv(DATA_DIR / "car.csv", dtype={"종목코드": str},
                      parse_dates=["발표일", "거래일t0"])
    prices = pd.read_csv(DATA_DIR / "prices.csv", dtype={"종목코드": str},
                         parse_dates=["일자"])
    indices = pd.read_csv(DATA_DIR / "indices.csv", parse_dates=["일자"])
    uni = pd.read_csv(DATA_DIR / "universe.csv", dtype={"종목코드": str})
    return car, prices, indices, uni


def show_event(ev, prices, indices, market_of):
    """한 이벤트의 발표일 전후 주가를 원자료로 출력한다."""
    code = ev["종목코드"]
    px = prices[prices["종목코드"] == code].sort_values("일자").reset_index(drop=True)
    t0 = px.index[px["일자"] == ev["거래일t0"]]
    if len(t0) == 0:
        print("  거래일 t0 를 찾을 수 없음")
        return
    t0 = int(t0[0])

    mkt = indices[indices["시장"] == market_of[code]].set_index("일자")["지수수익률"]

    win = px.iloc[max(0, t0 - 2):t0 + 4].copy()
    win["시장수익률"] = win["일자"].map(mkt)
    win["시점"] = [f"t{i - t0:+d}" if i != t0 else "t0"
                 for i in win.index]

    print(f"\n  {ev['종목명']} {ev['분기']}  발표 {ev['발표일'].date()}  "
          f"({ev['정보출처']}, {ev['모델']})")
    print(f"  CAR[0,+1] = {ev['CAR_0_1']:+.2%}   "
          f"beta_시장 {ev['beta_시장']:.2f}  alpha {ev.get('alpha', float('nan')):+.5f}")
    print(win[["시점", "일자", "종가", "수익률", "시장수익률"]]
          .to_string(index=False,
                     formatters={"수익률": "{:+.2%}".format,
                                 "시장수익률": "{:+.2%}".format}))


def main():
    car, prices, indices, uni = load()
    market_of = {r["종목코드"]: ("KOSPI" if str(r["시장"]).startswith("KOSPI")
                              else "KOSDAQ")
                 for _, r in uni.iterrows()}

    ok = car[car["CAR_0_1"].notna()].copy()

    print("=" * 70)
    print("1. CAR[0,+1] 상위 5건")
    print("=" * 70)
    for _, ev in ok.nlargest(5, "CAR_0_1").iterrows():
        show_event(ev, prices, indices, market_of)

    print()
    print("=" * 70)
    print("2. CAR[0,+1] 하위 5건")
    print("=" * 70)
    for _, ev in ok.nsmallest(5, "CAR_0_1").iterrows():
        show_event(ev, prices, indices, market_of)

    print()
    print("=" * 70)
    print("3. 분포 점검")
    print("=" * 70)

    s = ok["CAR_0_1"]
    print("\n--- 분위수 ---")
    print(s.quantile([0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
           .apply("{:+.2%}".format).to_string())

    print(f"\n|CAR| > 20% 인 이벤트: {(s.abs() > 0.20).sum()}건 "
          f"({(s.abs() > 0.20).mean():.1%})")
    print(f"|CAR| > 30% 인 이벤트: {(s.abs() > 0.30).sum()}건")

    print("\n--- 종목별 CAR 변동성 ---")
    print(ok.groupby("종목명")["CAR_0_1"]
            .agg(["count", "mean", "std"])
            .sort_values("std", ascending=False)
            .to_string(float_format=lambda x: f"{x:+.3f}"))

    print("\n--- 원본 일간 수익률과 비교 ---")
    r = prices["수익률"].dropna()
    print(f"전체 일간 수익률 표준편차      : {r.std():.2%}")
    print(f"이론상 2일 누적 (sqrt(2)배)   : {r.std() * (2 ** 0.5):.2%}")
    print(f"실제 CAR[0,+1] 표준편차       : {s.std():.2%}")
    print("→ 발표일 전후는 평상시보다 변동성이 크므로 실제값이 더 큰 것이 정상.")

    # 발표일 당일 원시 수익률의 변동성과 비교하면 더 정확하다
    t0_ret = []
    for _, ev in ok.iterrows():
        px = prices[(prices["종목코드"] == ev["종목코드"]) &
                    (prices["일자"] == ev["거래일t0"])]
        if len(px):
            t0_ret.append(px["수익률"].iloc[0])
    t0_ret = pd.Series(t0_ret).dropna()
    print(f"\n발표일 당일 원시 수익률 표준편차: {t0_ret.std():.2%}  (n={len(t0_ret)})")
    print(f"평상시 대비 배수                : {t0_ret.std() / r.std():.2f}배")


if __name__ == "__main__":
    main()
