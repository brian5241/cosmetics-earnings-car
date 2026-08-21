"""
07. 주가 및 지수 수집
=====================
종목별 일별 주가와 시장지수를 받아 수익률을 계산한다.

수집 대상:
  - 분석 대상 종목의 일별 종가 (수정주가)
  - KOSPI(KS11), KOSDAQ(KQ11) 지수

왜 두 지수를 다 받는가:
  유니버스에 KOSPI 종목과 KOSDAQ 종목이 섞여 있다.
  각 종목의 소속 시장 지수를 벤치마크로 써야 '정상 수익률' 추정이 정확하다.

섹터 지수는 여기서 만들지 않는다.
  KRX 화장품 업종지수를 무료로 받기 어려워 유니버스 종목으로 직접 구성하는데,
  이때 대상 종목 자신이 지수에 포함되면 안 된다(자기 자신을 벤치마크로 쓰는 셈).
  종목마다 '자신을 뺀' 지수가 필요하므로 CAR 계산 단계에서 만든다.

실행:  python src/07_fetch_prices.py
출력:  data/prices.csv    종목 일별 주가·수익률
       data/indices.csv   지수 일별 종가·수익률
"""

import time

import FinanceDataReader as fdr
import pandas as pd

from config import DATA_DIR, PRICE_START, PRICE_END, UNIVERSE

# 시장 구분 → FDR 지수 심볼
INDEX_SYMBOLS = {
    "KOSPI": "KS11",
    "KOSDAQ": "KQ11",
}


def fetch_prices() -> pd.DataFrame:
    """종목별 일별 주가를 수집한다."""
    print("=" * 70)
    print("1. 종목 주가")
    print("=" * 70)

    frames = []
    for code, name, sector, version in UNIVERSE:
        try:
            px = fdr.DataReader(code, PRICE_START, PRICE_END)
        except Exception as e:
            print(f"[{code}] {name}: 실패 - {e}")
            continue

        if px.empty:
            print(f"[{code}] {name}: 데이터 없음")
            continue

        df = px[["Close", "Volume"]].copy()
        df.columns = ["종가", "거래량"]
        df["종목코드"] = code
        df["종목명"] = name
        df = df.reset_index().rename(columns={"Date": "일자"})

        # 일별 수익률. 첫날은 직전 종가가 없어 NaN.
        df["수익률"] = df["종가"].pct_change()

        frames.append(df)
        print(f"[{code}] {name}: {len(df):,}일  "
              f"({df['일자'].min().date()} ~ {df['일자'].max().date()})")
        time.sleep(0.2)

    return pd.concat(frames, ignore_index=True)


def fetch_indices() -> pd.DataFrame:
    """시장지수를 수집한다."""
    print()
    print("=" * 70)
    print("2. 시장지수")
    print("=" * 70)

    frames = []
    for market, symbol in INDEX_SYMBOLS.items():
        idx = fdr.DataReader(symbol, PRICE_START, PRICE_END)
        df = idx[["Close"]].copy()
        df.columns = ["지수종가"]
        df["시장"] = market
        df = df.reset_index().rename(columns={"Date": "일자"})
        df["지수수익률"] = df["지수종가"].pct_change()
        frames.append(df)
        print(f"[{symbol}] {market}: {len(df):,}일  "
              f"({df['일자'].min().date()} ~ {df['일자'].max().date()})")

    return pd.concat(frames, ignore_index=True)


def main():
    prices = fetch_prices()
    indices = fetch_indices()

    prices.to_csv(DATA_DIR / "prices.csv", index=False, encoding="utf-8-sig")
    indices.to_csv(DATA_DIR / "indices.csv", index=False, encoding="utf-8-sig")

    # ---------------- 검증 ----------------
    print()
    print("=" * 70)
    print("3. 검증")
    print("=" * 70)

    print(f"\n주가: {len(prices):,}행 / {prices['종목코드'].nunique()}종목")
    print(f"지수: {len(indices):,}행 / {indices['시장'].nunique()}개")

    print("\n--- 결측 ---")
    print(prices[["종가", "수익률"]].isna().sum().to_string())

    # 수익률 이상치. 상하한가가 30%이므로 그 밖의 값은 확인이 필요하다.
    print("\n--- 일간 수익률 분포 ---")
    r = prices["수익률"].dropna()
    print(f"평균 {r.mean():+.4%}  표준편차 {r.std():.4%}")
    print(f"최소 {r.min():+.2%}  최대 {r.max():+.2%}")

    extreme = prices[prices["수익률"].abs() > 0.31]
    if len(extreme):
        print(f"\n[확인 필요] 상하한가(±30%) 초과 {len(extreme)}건 "
              f"— 액면분할·병합 가능성")
        print(extreme[["일자", "종목명", "종가", "수익률"]].to_string(index=False))
    else:
        print("\n[OK] ±30% 초과 수익률 없음 (수정주가 정상 반영)")

    # 거래정지 등으로 거래량 0인 날 확인
    zero_vol = prices[prices["거래량"] == 0]
    if len(zero_vol):
        print(f"\n[참고] 거래량 0인 날 {len(zero_vol)}건")
        print(zero_vol.groupby("종목명").size().to_string())

    print(f"\n저장: {DATA_DIR / 'prices.csv'}")
    print(f"저장: {DATA_DIR / 'indices.csv'}")


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    main()
