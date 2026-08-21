"""
06. 분기 재무 패널 구성
=======================
05에서 받은 원본을 '종목 x 분기' 패널로 정리한다.

핵심 처리 두 가지:

1) 연결(CFS) 우선, 없으면 별도(OFS) 폴백
   일부 종목·기간에는 연결재무제표가 없다. 어느 쪽을 썼는지 기록해둔다.

2) 분기 금액 산출
   손익계산서(IS)는 기간 개념이라 보고서마다 3개월치가 들어 있다.
     Q1 = 1분기 보고서 thstrm_amount
     Q2 = 반기   보고서 thstrm_amount
     Q3 = 3분기  보고서 thstrm_amount
     Q4 = 사업보고서 연간 - 3분기 누계(thstrm_add_amount)
   재무상태표(BS)는 시점 개념이라 각 보고서의 기말 잔액을 그대로 쓴다.

실행:  python src/06_build_panel.py
출력:  data/financials_quarterly.csv
"""

import numpy as np
import pandas as pd

from config import DATA_DIR, RAW_DIR

# 사용할 계정. 05 확인 결과 12종목 전부 동일한 명칭을 쓴다.
IS_ACCOUNTS = {"매출액": "매출액", "영업이익": "영업이익", "당기순이익(손실)": "당기순이익"}
BS_ACCOUNTS = {"자산총계": "자산총계", "부채총계": "부채총계", "자본총계": "자본총계"}
ALL_ACCOUNTS = {**IS_ACCOUNTS, **BS_ACCOUNTS}


def to_num(x) -> float:
    """DART 금액 문자열을 숫자로. 빈 값·'-'는 NaN."""
    if pd.isna(x):
        return np.nan
    s = str(x).strip().replace(",", "")
    if s in ("", "-", "0"):
        return 0.0 if s == "0" else np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def pick_fs_div(df: pd.DataFrame) -> pd.DataFrame:
    """종목 x 연도 x 보고서 단위로 연결(CFS)을 쓰고, 없으면 별도(OFS)로 폴백한다.

    지주·단일법인 구조에 따라 연결재무제표가 없는 기업·기간이 있다.
    어느 쪽을 썼는지 '기준' 컬럼에 남겨 나중에 해석할 때 구분할 수 있게 한다.
    """
    key = ["종목코드", "사업연도", "보고서"]
    has_cfs = df.groupby(key)["fs_div"].transform(lambda s: (s == "CFS").any())

    keep = np.where(has_cfs, df["fs_div"] == "CFS", df["fs_div"] == "OFS")
    out = df[keep].copy()
    out["기준"] = np.where(has_cfs[keep], "연결", "별도")
    return out


def main():
    raw = pd.read_csv(RAW_DIR / "financials_raw.csv", dtype={"종목코드": str, "사업연도": str})
    print(f"입력: {len(raw):,}행")

    # 필요한 계정만
    raw = raw[raw["account_nm"].isin(ALL_ACCOUNTS)].copy()
    print(f"대상 계정만: {len(raw):,}행")

    # --- 연결/별도 선택 ---
    raw = pick_fs_div(raw)

    print("\n--- 연결/별도 사용 현황 (종목x연도x보고서 단위) ---")
    basis = raw.drop_duplicates(["종목코드", "사업연도", "보고서"])[["종목명", "기준"]]
    print(basis.groupby(["종목명", "기준"]).size().to_string())

    # --- 숫자 변환 ---
    raw["금액"] = raw["thstrm_amount"].apply(to_num)
    raw["누계"] = raw["thstrm_add_amount"].apply(to_num) if "thstrm_add_amount" in raw.columns else np.nan
    raw["계정"] = raw["account_nm"].map(ALL_ACCOUNTS)

    # 같은 계정이 중복 등장하는 경우가 있다(예: 당기순이익(손실) 2행). 첫 건만 쓴다.
    raw = raw.drop_duplicates(["종목코드", "사업연도", "보고서", "계정"])

    # --- 넓은 형태로 ---
    wide = raw.pivot_table(
        index=["종목코드", "종목명", "사업연도", "보고서", "기준"],
        columns="계정", values=["금액", "누계"], aggfunc="first",
    )
    wide.columns = [f"{c[1]}_{c[0]}" for c in wide.columns]
    wide = wide.reset_index()

    # --- 분기 패널 조립 ---
    rows = []
    for (code, name, year), g in wide.groupby(["종목코드", "종목명", "사업연도"]):
        by_report = {r["보고서"]: r for _, r in g.iterrows()}

        # 보고서 → 분기 매핑 (IS는 3개월치가 그대로 들어 있다)
        direct = {1: "1분기", 2: "반기", 3: "3분기"}

        def is_value(q: int, rep: str, acc: str) -> tuple[float, str]:
            """분기 손익 값을 구한다. 직접 값이 없으면 누계 차이로 보완한다.

            DART 쪽 계정 누락으로 특정 보고서에서 항목이 빠지는 경우가 있다
            (예: 코스메카코리아 2025 1분기 연결 매출액).
            누계(thstrm_add_amount)는 남아 있는 경우가 많아
            인접 보고서의 누계 차이로 복원할 수 있다.
              Q1 = 반기누계 - 반기 3개월
              Q2 = 반기누계 - 1분기누계
              Q3 = 3분기누계 - 반기누계
            """
            r = by_report.get(rep)
            v = r.get(f"{acc}_금액") if r is not None else np.nan
            if pd.notna(v):
                return v, "직접"

            def cum(rp):
                rr = by_report.get(rp)
                return rr.get(f"{acc}_누계") if rr is not None else np.nan

            h = by_report.get("반기")
            if q == 1:
                a, b = cum("반기"), (h.get(f"{acc}_금액") if h is not None else np.nan)
                if pd.notna(a) and pd.notna(b):
                    return a - b, "누계보완"
            elif q == 2:
                a, b = cum("반기"), cum("1분기")
                if pd.notna(a) and pd.notna(b):
                    return a - b, "누계보완"
            elif q == 3:
                a, b = cum("3분기"), cum("반기")
                if pd.notna(a) and pd.notna(b):
                    return a - b, "누계보완"
            return np.nan, "결측"

        for q, rep in direct.items():
            if rep not in by_report:
                continue
            r = by_report[rep]
            row = {
                "종목코드": code, "종목명": name,
                "연도": int(year), "분기": q, "기준": r["기준"],
                "자산총계": r.get("자산총계_금액"),
                "부채총계": r.get("부채총계_금액"),
                "자본총계": r.get("자본총계_금액"),
            }
            methods = set()
            for acc in IS_ACCOUNTS.values():
                row[acc], how = is_value(q, rep, acc)
                methods.add(how)
            row["산출방식"] = "누계보완" if "누계보완" in methods else "직접"
            rows.append(row)

        # Q4 = 연간 - 3분기 누계
        if "사업보고서" in by_report:
            fy = by_report["사업보고서"]
            q3 = by_report.get("3분기")
            row = {
                "종목코드": code, "종목명": name,
                "연도": int(year), "분기": 4, "기준": fy["기준"],
                # BS는 시점값이므로 사업보고서 기말 잔액을 그대로 쓴다
                "자산총계": fy.get("자산총계_금액"),
                "부채총계": fy.get("부채총계_금액"),
                "자본총계": fy.get("자본총계_금액"),
                "산출방식": "역산",
            }
            for acc in IS_ACCOUNTS.values():
                annual = fy.get(f"{acc}_금액")
                cum3 = q3.get(f"{acc}_누계") if q3 is not None else np.nan
                row[acc] = (annual - cum3) if pd.notna(annual) and pd.notna(cum3) else np.nan
            rows.append(row)

    panel = pd.DataFrame(rows).sort_values(["종목코드", "연도", "분기"])

    # --- 파생 지표 ---
    panel["OPM"] = panel["영업이익"] / panel["매출액"]
    panel["분기라벨"] = panel["연도"].astype(str) + "Q" + panel["분기"].astype(str)

    panel.to_csv(DATA_DIR / "financials_quarterly.csv", index=False, encoding="utf-8-sig")

    # ---------------- 검증 ----------------
    print()
    print("=" * 70)
    print(f"분기 패널: {len(panel):,}행")
    print("=" * 70)

    print("\n--- 산출방식별 ---")
    print(panel["산출방식"].value_counts().to_string())

    print("\n--- 결측 현황 ---")
    print(panel[list(ALL_ACCOUNTS.values())].isna().sum().to_string())

    miss = panel[panel[list(ALL_ACCOUNTS.values())].isna().any(axis=1)]
    if len(miss):
        print("\n--- 결측 발생 행 (원인 확인 필요) ---")
        print(miss[["종목명", "분기라벨", "기준", "산출방식",
                    *ALL_ACCOUNTS.values()]].to_string(index=False))

    # 검산: 분기 합 == 연간
    print("\n--- 검산 (Q1+Q2+Q3+Q4 == 연간 매출) ---")
    ann = (pd.read_csv(RAW_DIR / "financials_raw.csv", dtype={"종목코드": str, "사업연도": str})
             .query("보고서 == '사업보고서' and account_nm == '매출액'"))
    ann = ann.drop_duplicates(["종목코드", "사업연도"], keep="first")
    ann["연간"] = ann["thstrm_amount"].apply(to_num)

    ann["연도"] = ann["사업연도"].astype(int)

    # 4개 분기가 모두 있는 연도만 검산한다
    qsum = (panel.groupby(["종목코드", "연도"])["매출액"]
                 .agg(["sum", "count"]).reset_index())
    qsum = qsum[qsum["count"] == 4]

    chk = qsum.merge(ann[["종목코드", "연도", "연간"]], on=["종목코드", "연도"], how="inner")
    chk["차이"] = (chk["sum"] - chk["연간"]).abs()
    chk["오차율"] = chk["차이"] / chk["연간"]
    bad = chk[chk["오차율"] > 1e-6]
    print(f"검산 대상 {len(chk)}건 중 불일치 {len(bad)}건")
    if len(bad):
        print(bad.to_string(index=False))

    print("\n--- 종목별 분기 수 ---")
    print(panel.groupby("종목명")["분기라벨"].count().to_string())

    print(f"\n저장: {DATA_DIR / 'financials_quarterly.csv'}")


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    main()
