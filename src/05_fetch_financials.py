"""
05. 재무제표 원본 수집
======================
DART 주요계정 API(fnlttSinglAcnt)로 종목 x 연도 x 보고서 단위 재무 데이터를 받는다.

이 단계에서는 가공하지 않고 원본을 그대로 저장한다.
계정과목명이 회사·연도마다 다르기 때문에,
실제로 어떤 이름들이 등장하는지 먼저 확인한 뒤 표준화 규칙을 만든다. (06단계)

금액 해석 (탐색으로 확인함):
  - 1분기/반기/3분기 보고서의 thstrm_amount = 해당 3개월치
  - thstrm_add_amount = 누계
  - 사업보고서의 thstrm_amount = 연간
  → Q1~Q3 는 그대로 사용, Q4 = 연간 - 3분기누계

실행:  python src/05_fetch_financials.py
출력:  data/raw/financials_raw.csv
"""

import time

import pandas as pd
import requests

from config import DART_API_KEY, DATA_DIR, RAW_DIR, UNIVERSE

BASE = "https://opendart.fss.or.kr/api"

# 보고서 코드 → 라벨
REPORTS = {
    "11013": "1분기",
    "11012": "반기",
    "11014": "3분기",
    "11011": "사업보고서",
}

# 2022~2026 사업연도.
# 2022는 3분기 이벤트부터 필요하지만 전년동기 비교를 위해 2021도 받는다.
YEARS = ["2021", "2022", "2023", "2024", "2025", "2026"]


def fetch_one(corp_code: str, year: str, reprt_code: str) -> pd.DataFrame | None:
    """한 기업의 한 보고서를 조회한다. 없으면 None."""
    resp = requests.get(f"{BASE}/fnlttSinglAcnt.json", params={
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
        "bsns_year": year,
        "reprt_code": reprt_code,
    }, timeout=30)
    data = resp.json()
    status = data.get("status")

    # 013 = 조회된 데이터 없음 (아직 발표 전이거나 비상장 시기)
    if status == "013":
        return None
    if status != "000":
        print(f"    [경고] {year} {REPORTS[reprt_code]}: status={status} {data.get('message')}")
        return None

    return pd.DataFrame(data["list"])


def main():
    frames = []
    for code, name, sector, version in UNIVERSE:
        corp_code = CORP_MAP[code]
        got = []
        for year in YEARS:
            for rc, rc_label in REPORTS.items():
                df = fetch_one(corp_code, year, rc)
                if df is None:
                    continue
                df["종목코드"] = code
                df["종목명"] = name
                df["사업연도"] = year
                df["보고서"] = rc_label
                frames.append(df)
                got.append(f"{year[2:]}{rc_label[:2]}")
                time.sleep(0.1)   # 과도한 연속 호출 방지
        print(f"[{code}] {name}: {len(got)}개 보고서")

    raw = pd.concat(frames, ignore_index=True)

    out = RAW_DIR / "financials_raw.csv"
    raw.to_csv(out, index=False, encoding="utf-8-sig")

    # ---------------- 확인 출력 ----------------
    print()
    print("=" * 70)
    print(f"수집 완료: {len(raw):,}행")
    print("=" * 70)

    print("\n--- 연결/별도 구분 ---")
    print(raw["fs_div"].value_counts().to_string())

    print("\n--- 재무제표 구분 ---")
    print(raw["sj_div"].value_counts().to_string())

    # 여기가 핵심. 회사마다 계정과목명이 어떻게 다른지 본다.
    for sj, label in [("IS", "손익계산서"), ("BS", "재무상태표")]:
        print(f"\n--- {label} 계정과목명 (등장 종목 수) ---")
        sub = raw[raw["sj_div"] == sj]
        counts = (sub.groupby("account_nm")["종목명"]
                     .nunique().sort_values(ascending=False))
        print(counts.to_string())

    print(f"\n저장: {out}")


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 100)

    _m = pd.read_csv(DATA_DIR / "corp_code_map.csv", dtype={"종목코드": str, "corp_code": str})
    CORP_MAP = dict(zip(_m["종목코드"], _m["corp_code"]))

    main()
