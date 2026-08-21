"""
11. 회귀 분석
=============
"실적 발표의 어떤 항목이 발표 직후 주가 반응과 관련이 큰가"에 답한다.

두 가지 접근을 함께 쓴다. 목적이 다르다.

  OLS   : 해석용. 각 항목의 방향과 통계적 유의성을 본다.
          표준오차는 종목별 군집(cluster)으로 보정한다.
          같은 종목의 여러 분기 관측치는 서로 독립이 아니기 때문이다.

  Lasso : 변수 선택용. 계수를 0으로 죽여가며 살아남는 항목을 본다.
          "어떤 항목이 중요한가"라는 원 질문과 목적이 정확히 일치한다.
          교차검증은 TimeSeriesSplit 을 쓴다. 일반 K-fold 로 무작위 분할하면
          미래 데이터로 과거를 예측하게 되어 데이터 누수가 발생한다.

실행:  python src/11_regression.py
출력:  data/results_ols.csv, data/results_lasso.csv
"""

import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LassoCV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor

from config import DATA_DIR

# 분석에 쓸 특성.
# 흑자전환·적자전환·적자지속 더미는 실제 표본에 사례가 1건 이하라 제외했다.
# (화장품 11종목이 분석 기간 내내 흑자 기조였다)
FEATURES = [
    "매출YoY",      # 외형 성장
    "OPM변화",      # 수익성 개선
    "추세이탈도",    # 기대 대비 이탈 (서프라이즈 대리)
    "CAR_PRE",     # 발표 전 선반영 (통제)
    "로그자산",      # 규모 (통제)
    "잠정실적더미",   # 정보 신선도 (통제)
]

TARGETS = ["CAR_0_1", "CAR_0_5", "CAR_0_20"]

WINSOR_Q = 0.01   # 상하위 1% 절단


def winsorize(s: pd.Series, q: float = WINSOR_Q) -> pd.Series:
    """극단값을 분위수로 눌러 담는다. 잘라내지 않고 값만 제한한다."""
    lo, hi = s.quantile(q), s.quantile(1 - q)
    return s.clip(lo, hi)


def check_vif(X: pd.DataFrame) -> pd.DataFrame:
    """다중공선성 점검. 통상 VIF 10 이상이면 문제로 본다."""
    Xc = sm.add_constant(X)
    rows = []
    for i, name in enumerate(Xc.columns):
        if name == "const":
            continue
        rows.append({"변수": name, "VIF": variance_inflation_factor(Xc.values, i)})
    return pd.DataFrame(rows)


def run_ols(df: pd.DataFrame, target: str, features: list[str],
            label: str) -> tuple[pd.DataFrame, dict]:
    """종목 군집 표준오차를 쓴 OLS."""
    d = df[features + [target, "종목코드"]].dropna()
    y = d[target]
    X = sm.add_constant(d[features])

    fit = sm.OLS(y, X).fit(cov_type="cluster",
                           cov_kwds={"groups": d["종목코드"]})

    res = pd.DataFrame({
        "변수": fit.params.index,
        "계수": fit.params.values,
        "표준오차": fit.bse.values,
        "t값": fit.tvalues.values,
        "p값": fit.pvalues.values,
    })
    res["유의"] = pd.cut(res["p값"], [0, 0.01, 0.05, 0.10, 1],
                       labels=["***", "**", "*", ""])
    res.insert(0, "모형", label)
    res.insert(1, "종속변수", target)

    info = {"모형": label, "종속변수": target, "n": int(fit.nobs),
            "R2": fit.rsquared, "adj_R2": fit.rsquared_adj}
    return res, info


def run_lasso(df: pd.DataFrame, target: str, features: list[str]) -> pd.DataFrame:
    """TimeSeriesSplit 교차검증을 쓴 Lasso.

    시계열이므로 무작위 분할을 쓰면 안 된다.
    발표일 순으로 정렬한 뒤 앞 기간으로 학습하고 뒤 기간으로 검증한다.
    """
    d = df.sort_values("발표일")[features + [target]].dropna()
    X, y = d[features].to_numpy(), d[target].to_numpy()

    # Lasso 는 스케일에 민감하므로 표준화가 필수다.
    model = make_pipeline(
        StandardScaler(),
        LassoCV(cv=TimeSeriesSplit(n_splits=5),
                max_iter=100_000, random_state=0),
    )
    model.fit(X, y)
    lasso = model.named_steps["lassocv"]

    res = pd.DataFrame({
        "변수": features,
        "표준화계수": lasso.coef_,
    })
    res["선택됨"] = res["표준화계수"] != 0
    res = res.reindex(res["표준화계수"].abs().sort_values(ascending=False).index)
    res.insert(0, "종속변수", target)
    res.attrs["alpha"] = lasso.alpha_
    return res


def main():
    df = pd.read_csv(DATA_DIR / "dataset.csv", dtype={"종목코드": str},
                     parse_dates=["발표일"])
    df = df[df["분석표본"]].copy()

    print("=" * 70)
    print(f"분석 표본: {len(df)}건 / {df['종목코드'].nunique()}종목")
    print(f"기간: {df['발표일'].min().date()} ~ {df['발표일'].max().date()}")
    print("=" * 70)

    # ---------- 다중공선성 ----------
    print("\n--- 다중공선성 (VIF) ---")
    vif = check_vif(df[FEATURES].dropna())
    print(vif.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    if (vif["VIF"] > 10).any():
        print("  [주의] VIF 10 초과 변수 있음")
    else:
        print("  [OK] 전부 10 미만")

    all_res, all_info = [], []

    # ---------- 기본 모형 ----------
    print()
    print("=" * 70)
    print("OLS — 기본 모형 (종속변수: CAR[0,+1])")
    print("=" * 70)
    res, info = run_ols(df, "CAR_0_1", FEATURES, "기본")
    all_res.append(res); all_info.append(info)
    print(res.drop(columns=["모형", "종속변수"]).to_string(
        index=False, float_format=lambda x: f"{x:+.4f}"))
    print(f"\nn = {info['n']}   R2 = {info['R2']:.3f}   "
          f"adj R2 = {info['adj_R2']:.3f}")

    # ---------- 강건성 검증 ----------
    print()
    print("=" * 70)
    print("강건성 검증")
    print("=" * 70)

    # (1) 극단값 윈저라이징
    dw = df.copy()
    dw["CAR_0_1"] = winsorize(dw["CAR_0_1"])
    res, info = run_ols(dw, "CAR_0_1", FEATURES, "윈저라이징")
    all_res.append(res); all_info.append(info)

    # (2) 실리콘투 제외 — CAR 변동성이 20.5%로 2위와도 격차가 커
    #     소수 관측치가 결과를 끌고 갈 위험이 있다
    d2 = df[df["종목명"] != "실리콘투"]
    res, info = run_ols(d2, "CAR_0_1", FEATURES, "실리콘투제외")
    all_res.append(res); all_info.append(info)

    # (3) 달바글로벌 제외 — 유효 이벤트가 3건뿐
    d3 = df[df["종목명"] != "달바글로벌"]
    res, info = run_ols(d3, "CAR_0_1", FEATURES, "달바제외")
    all_res.append(res); all_info.append(info)

    # (4) 종속변수 윈도우 변경
    for t in ["CAR_0_5", "CAR_0_20"]:
        res, info = run_ols(df, t, FEATURES, f"윈도우{t[-4:]}")
        all_res.append(res); all_info.append(info)

    results = pd.concat(all_res, ignore_index=True)
    results.to_csv(DATA_DIR / "results_ols.csv", index=False, encoding="utf-8-sig")

    # 모형별 계수 비교표
    print("\n--- 모형별 계수 비교 (별표 = 유의수준) ---")
    pivot = results[results["변수"] != "const"].copy()
    pivot["표시"] = (pivot["계수"].map(lambda x: f"{x:+.3f}")
                   + pivot["유의"].astype(str))
    tbl = pivot.pivot(index="변수", columns="모형", values="표시")
    order = [i["모형"] for i in all_info]
    tbl = tbl[[c for c in order if c in tbl.columns]].reindex(FEATURES)
    print(tbl.to_string())

    print("\n--- 모형별 적합도 ---")
    print(pd.DataFrame(all_info).to_string(
        index=False, float_format=lambda x: f"{x:.3f}"))

    # ---------- Lasso ----------
    print()
    print("=" * 70)
    print("Lasso — 변수 선택 (TimeSeriesSplit 5-fold)")
    print("=" * 70)

    lasso_all = []
    for t in TARGETS:
        lr = run_lasso(df, t, FEATURES)
        lasso_all.append(lr)
        print(f"\n[{t}]  최적 alpha = {lr.attrs['alpha']:.5f}")
        print(lr.drop(columns=["종속변수"]).to_string(
            index=False, float_format=lambda x: f"{x:+.4f}"))
        kept = lr[lr["선택됨"]]["변수"].tolist()
        print(f"  선택된 변수: {', '.join(kept) if kept else '없음'}")

    pd.concat(lasso_all, ignore_index=True).to_csv(
        DATA_DIR / "results_lasso.csv", index=False, encoding="utf-8-sig")

    print(f"\n저장: {DATA_DIR / 'results_ols.csv'}")
    print(f"저장: {DATA_DIR / 'results_lasso.csv'}")


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    main()
