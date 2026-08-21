"""
08. CAR (누적초과수익률) 계산
=============================
이벤트별로 '실적 발표가 만든 주가 반응'만 뽑아낸다.

    초과수익률 AR = 실제 수익률 - 정상 수익률(그 사건이 없었다면 났을 수익률)
    CAR = 이벤트 윈도우 구간의 AR 합계

정상 수익률 추정 모델 (이벤트마다 자동 선택):

  [1] 2팩터 시장모델 (기본)
        R = a + b1*시장수익률 + b2*섹터수익률 + e
      추정 구간 [-250, -30] 거래일. 발표 직전 30일은 기대감에 오염되어 제외한다.
      섹터 수익률은 '자기 자신을 뺀' 유니버스 동일가중 수익률을 쓴다.
      자기가 포함된 지수를 벤치마크로 쓰면 초과수익률이 축소되기 때문이다.

  [2] 시장조정모델 (폴백)
        AR = R - 시장수익률          (베타를 1로 고정)
      상장한 지 얼마 안 되어 추정 구간이 부족한 이벤트에 쓴다.
      종목 단위가 아니라 '이벤트 단위'로 판정한다. 상장 초기 몇 건만 부족하고
      이후 이벤트는 정상적으로 추정할 수 있기 때문이다.

어느 모델을 썼는지 컬럼으로 남겨 결과 해석 시 구분할 수 있게 한다.

실행:  python src/08_compute_car.py
출력:  data/car.csv
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm

from config import DATA_DIR, ESTIMATION_WINDOW, EVENT_WINDOWS

# 2팩터 모델을 쓰기 위한 최소 추정 관측치. 미달이면 시장조정모델로 폴백한다.
MIN_ESTIMATION_OBS = 60

# 시각화용 AR 경로를 남길 구간 (발표일 기준 거래일)
PATH_LO, PATH_HI = -20, 20


def build_returns() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """수익률 행렬과 시장수익률을 준비한다.

    반환:
      ret     : 일자 x 종목코드 수익률 행렬
      mkt     : 일자 x 시장(KOSPI/KOSDAQ) 수익률 행렬
      market_of : 종목코드 -> 소속 시장
    """
    prices = pd.read_csv(DATA_DIR / "prices.csv",
                         dtype={"종목코드": str}, parse_dates=["일자"])
    indices = pd.read_csv(DATA_DIR / "indices.csv", parse_dates=["일자"])
    uni = pd.read_csv(DATA_DIR / "universe.csv", dtype={"종목코드": str})

    ret = prices.pivot(index="일자", columns="종목코드", values="수익률")
    mkt = indices.pivot(index="일자", columns="시장", values="지수수익률")

    # KOSDAQ GLOBAL 같은 세부 구분은 KOSDAQ 지수를 쓴다
    market_of = {}
    for _, r in uni.iterrows():
        m = str(r["시장"])
        market_of[r["종목코드"]] = "KOSPI" if m.startswith("KOSPI") else "KOSDAQ"

    return ret, mkt, market_of


def sector_return_excluding(ret: pd.DataFrame, code: str) -> pd.Series:
    """자기 자신을 뺀 유니버스 동일가중 수익률."""
    others = [c for c in ret.columns if c != code]
    return ret[others].mean(axis=1, skipna=True)


def find_event_day(dates: pd.DatetimeIndex, announce: pd.Timestamp) -> int | None:
    """발표일에 해당하는 거래일 위치를 찾는다.

    발표일이 휴장일이면 다음 거래일을 t=0 으로 본다.
    """
    pos = dates.searchsorted(announce, side="left")
    return int(pos) if pos < len(dates) else None


def main():
    ret, mkt, market_of = build_returns()
    events = pd.read_csv(DATA_DIR / "events.csv",
                         dtype={"종목코드": str}, parse_dates=["발표일"])

    print(f"이벤트 {len(events)}건 처리 시작")

    # 종목별로 미리 계산해두면 반복 비용이 줄어든다
    sector_cache = {c: sector_return_excluding(ret, c) for c in ret.columns}

    est_lo, est_hi = ESTIMATION_WINDOW

    records, paths = [], []
    for _, ev in events.iterrows():
        code = ev["종목코드"]
        r_i = ret[code].dropna()
        dates = r_i.index

        t0 = find_event_day(dates, ev["발표일"])
        rec = {
            "종목코드": code, "종목명": ev["종목명"], "분기": ev["분기"],
            "발표일": ev["발표일"], "정보출처": ev["정보출처"],
            "유형": ev["유형"], "포함버전": ev["포함버전"],
            "상장직후": ev["상장직후"],
        }

        # t=0 자체를 못 찾거나 다음 거래일이 없으면 계산 불가.
        # 긴 윈도우(예: +20일)가 아직 안 채워진 최근 이벤트라도
        # 짧은 윈도우는 계산할 수 있으므로 여기서 일괄 제외하지 않는다.
        # 윈도우별 가용 여부는 아래에서 따로 판정한다.
        if t0 is None or t0 + 1 >= len(dates):
            rec.update({"모델": "계산불가", "사유": "발표 후 거래일 부족"})
            records.append(rec)
            continue

        rec["거래일t0"] = dates[t0]

        # --- 정상 수익률 추정 ---
        s_lo, s_hi = max(0, t0 + est_lo), t0 + est_hi
        est_idx = dates[s_lo:s_hi]

        m_i = mkt[market_of[code]].reindex(dates)
        s_i = sector_cache[code].reindex(dates)

        est = pd.DataFrame({
            "r": r_i.loc[est_idx],
            "m": m_i.loc[est_idx],
            "s": s_i.loc[est_idx],
        }).dropna()

        if len(est) >= MIN_ESTIMATION_OBS:
            # 섹터 팩터 직교화.
            # 섹터 지수(유니버스 동일가중)는 시장 움직임을 이미 포함하고 있어
            # 그대로 넣으면 두 팩터가 겹쳐 시장 베타가 섹터 쪽으로 빨려간다.
            # 섹터를 시장에 회귀한 뒤 잔차만 쓰면
            # beta_시장이 통상적인 시장 베타로 해석된다.
            orth = sm.OLS(est["s"], sm.add_constant(est["m"])).fit()
            s_orth_i = s_i - (orth.params["const"] + orth.params["m"] * m_i)

            est2 = est.assign(s_orth=s_orth_i.loc[est.index])
            X = sm.add_constant(est2[["m", "s_orth"]])
            fit = sm.OLS(est2["r"], X).fit()
            alpha = fit.params["const"]
            beta_m, beta_s = fit.params["m"], fit.params["s_orth"]
            expected = alpha + beta_m * m_i + beta_s * s_orth_i
            rec.update({
                "모델": "2팩터시장모델", "추정관측수": len(est),
                "alpha": alpha, "beta_시장": beta_m, "beta_섹터": beta_s,
                "R2": fit.rsquared,
            })
        else:
            # 베타를 1로 고정하고 시장수익률만 차감
            expected = m_i
            rec.update({
                "모델": "시장조정모델", "추정관측수": len(est),
                "alpha": np.nan, "beta_시장": 1.0, "beta_섹터": np.nan,
                "R2": np.nan,
            })

        ar = (r_i - expected).reindex(dates)

        # --- 윈도우별 CAR ---
        for wname, (lo, hi) in EVENT_WINDOWS.items():
            a, b = t0 + lo, t0 + hi
            if a < 0 or b >= len(dates):
                rec[wname] = np.nan
                continue
            seg = ar.iloc[a:b + 1]
            # 구간 내 결측이 있으면 신뢰할 수 없다
            rec[wname] = seg.sum() if seg.notna().all() else np.nan

        # --- AR 경로 저장 ---
        # 시각화(평균 CAR 궤적)에서 재계산하지 않도록 여기서 남긴다.
        # 직교화 계수까지 다시 만들 필요가 없어진다.
        path = {}
        for k in range(PATH_LO, PATH_HI + 1):
            j = t0 + k
            path[k] = ar.iloc[j] if 0 <= j < len(dates) else np.nan
        paths.append({"이벤트키": f"{code}_{ev['분기']}", **path})

        rec["이벤트키"] = f"{code}_{ev['분기']}"
        rec["사유"] = ""
        records.append(rec)

    car = pd.DataFrame(records)
    car.to_csv(DATA_DIR / "car.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(paths).to_csv(DATA_DIR / "ar_paths.csv",
                               index=False, encoding="utf-8-sig")

    # ---------------- 검증 ----------------
    print()
    print("=" * 70)
    print(f"결과: {len(car)}건")
    print("=" * 70)

    print("\n--- 모델별 ---")
    print(car["모델"].value_counts().to_string())

    bad = car[car["모델"] == "계산불가"]
    if len(bad):
        print(f"\n[제외] {len(bad)}건")
        print(bad[["종목명", "분기", "발표일", "사유"]].to_string(index=False))

    ok = car[car["모델"] != "계산불가"]

    print("\n--- 시장조정모델로 폴백된 이벤트 ---")
    fb = ok[ok["모델"] == "시장조정모델"]
    if len(fb):
        print(fb[["종목명", "분기", "추정관측수"]].to_string(index=False))
    else:
        print("없음")

    print("\n--- 추정 품질 (2팩터모델) ---")
    mm = ok[ok["모델"] == "2팩터시장모델"]
    print(f"관측수  중앙값 {mm['추정관측수'].median():.0f}  최소 {mm['추정관측수'].min():.0f}")
    print(f"beta_시장 평균 {mm['beta_시장'].mean():.2f}  "
          f"beta_섹터 평균 {mm['beta_섹터'].mean():.2f}")
    print(f"R2 평균 {mm['R2'].mean():.3f}")

    print("\n--- CAR 분포 ---")
    for w in EVENT_WINDOWS:
        s = ok[w].dropna()
        if s.empty:
            continue
        print(f"{w:10s} n={len(s):3d}  평균 {s.mean():+.2%}  "
              f"중앙값 {s.median():+.2%}  표준편차 {s.std():.2%}  "
              f"최소 {s.min():+.1%}  최대 {s.max():+.1%}")

    # 최근 이벤트는 긴 윈도우가 아직 채워지지 않는다. 어느 건인지 남겨둔다.
    long_missing = ok[ok["CAR_0_20"].isna() & ok["CAR_0_1"].notna()]
    if len(long_missing):
        print(f"\n[참고] 긴 윈도우 미완성 {len(long_missing)}건 "
              f"(발표 후 20거래일 미경과 — 짧은 윈도우는 사용 가능)")
        print(long_missing.groupby("분기").size().to_string())

    print("\n--- 정보출처별 평균 CAR[0,+1] ---")
    print(ok.groupby("정보출처")["CAR_0_1"]
            .agg(["count", "mean", "std"]).to_string())

    print(f"\n저장: {DATA_DIR / 'car.csv'}")


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    main()
