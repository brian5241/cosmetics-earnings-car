"""
03. 실적 발표 공시 목록 수집
============================
종목별로 4년치 공시 목록을 받아 '실적 발표 이벤트' 후보를 추린다.

두 종류를 모두 수집한다:
  - 잠정실적: 「연결재무제표기준영업(잠정)실적(공정공시)」 등  → 거래소공시(I)
  - 정기보고서: 분기/반기/사업보고서                          → 정기공시(A)

시장이 실제로 반응하는 시점은 잠정실적이므로 그쪽을 우선하되,
잠정실적을 내지 않는 종목·분기가 있어 정기보고서로 보완해야 한다.
어느 쪽을 쓸지는 수집 결과의 커버리지를 보고 결정한다.

실행:  python src/03_fetch_disclosures.py
출력:  data/disclosures_raw.csv   (수집한 전체 공시)
       data/earnings_events.csv   (실적 발표로 판정된 건만)
"""

import re
import time

import pandas as pd
import requests

from config import DART_API_KEY, DATA_DIR, EVENT_START, EVENT_END, UNIVERSE

BASE = "https://opendart.fss.or.kr/api"

# 공시 유형 코드
PBLNTF_TYPES = {
    "A": "정기공시",
    "I": "거래소공시",
}

# 잠정실적 공시 판별. 회사마다 표현이 조금씩 달라 넓게 잡는다.
#   예) 연결재무제표기준영업(잠정)실적(공정공시)
#       매출액또는손익구조30%(대규모법인은15%)이상변동
PAT_PROVISIONAL = re.compile(r"영업\(잠정\)실적|손익구조.*변동")

# 정기보고서 판별 및 결산기준일 추출.  예) "분기보고서 (2026.03)"
PAT_PERIODIC = re.compile(r"(분기보고서|반기보고서|사업보고서)")
PAT_PERIOD   = re.compile(r"\((\d{4})\.(\d{2})\)")

# 정정공시는 원공시와 중복되므로 표시해두고 나중에 제외 판단
PAT_AMENDED = re.compile(r"^\[기재정정\]|^\[첨부정정\]|^\[첨부추가\]")


def fetch_list(corp_code: str, pblntf_ty: str) -> list[dict]:
    """한 기업의 특정 유형 공시 목록을 전 페이지 수집한다.

    list.json 은 한 번에 최대 100건이라 total_page 만큼 반복해야 한다.
    """
    items, page = [], 1
    while True:
        resp = requests.get(f"{BASE}/list.json", params={
            "crtfc_key": DART_API_KEY,
            "corp_code": corp_code,
            "bgn_de": EVENT_START.replace("-", ""),
            "end_de": EVENT_END.replace("-", ""),
            "pblntf_ty": pblntf_ty,
            "page_no": str(page),
            "page_count": "100",
        }, timeout=30)
        data = resp.json()
        status = data.get("status")

        # 013 = 조회된 데이터 없음. 오류가 아니라 '해당 공시 없음'이다.
        if status == "013":
            break
        if status != "000":
            print(f"    [경고] status={status} {data.get('message')}")
            break

        items.extend(data.get("list", []))
        if page >= int(data.get("total_page", 1)):
            break
        page += 1
        time.sleep(0.1)   # 과도한 연속 호출 방지

    return items


def classify(report_nm: str, rcept_dt: str) -> dict:
    """공시명을 보고 실적 발표 여부와 대상 분기를 판정한다."""
    nm = report_nm.strip()
    result = {
        "공시명": nm,
        "정정여부": bool(PAT_AMENDED.search(nm)),
        "구분": None,
        "대상연도": None,
        "대상분기": None,
    }

    if PAT_PROVISIONAL.search(nm):
        result["구분"] = "잠정실적"
        # 잠정실적 공시명에는 대상 기간이 없다.
        # 발표 시점으로 역산한다 (1~3월 발표 → 전년 4분기, 이하 동일).
        y, m = int(rcept_dt[:4]), int(rcept_dt[4:6])
        if m <= 3:
            result["대상연도"], result["대상분기"] = y - 1, 4
        elif m <= 6:
            result["대상연도"], result["대상분기"] = y, 1
        elif m <= 9:
            result["대상연도"], result["대상분기"] = y, 2
        else:
            result["대상연도"], result["대상분기"] = y, 3

    elif PAT_PERIODIC.search(nm):
        result["구분"] = "정기보고서"
        # 정기보고서는 공시명에 결산기준일이 있어 정확히 알 수 있다.
        m = PAT_PERIOD.search(nm)
        if m:
            year, month = int(m.group(1)), int(m.group(2))
            result["대상연도"] = year
            result["대상분기"] = {3: 1, 6: 2, 9: 3, 12: 4}.get(month)

    return result


def main():
    rows = []
    for code, name, sector, version in UNIVERSE:
        corp_code = CORP_MAP[code]
        print(f"[{code}] {name}")
        for ty, ty_label in PBLNTF_TYPES.items():
            items = fetch_list(corp_code, ty)
            print(f"    {ty_label}: {len(items)}건")
            for it in items:
                info = classify(it["report_nm"], it["rcept_dt"])
                rows.append({
                    "종목코드": code,
                    "종목명": name,
                    "유형": sector,
                    "포함버전": version,
                    "corp_code": corp_code,
                    "공시유형": ty_label,
                    "접수일자": it["rcept_dt"],
                    "접수번호": it["rcept_no"],
                    "제출인": it["flr_nm"],
                    **info,
                })
            time.sleep(0.1)

    df = pd.DataFrame(rows)
    df.to_csv(DATA_DIR / "disclosures_raw.csv", index=False, encoding="utf-8-sig")

    events = df[df["구분"].notna()].copy()
    events = events.sort_values(["종목코드", "접수일자"])
    events.to_csv(DATA_DIR / "earnings_events.csv", index=False, encoding="utf-8-sig")

    # ---------------- 확인 출력 ----------------
    print()
    print("=" * 70)
    print(f"전체 공시 {len(df):,}건 → 실적 관련 {len(events):,}건")
    print("=" * 70)

    print("\n--- 구분별 건수 ---")
    print(events.groupby(["구분", "정정여부"]).size().to_string())

    print("\n--- 종목 x 구분 ---")
    pivot = events.pivot_table(index="종목명", columns="구분",
                               values="접수번호", aggfunc="count", fill_value=0)
    print(pivot.to_string())

    print("\n--- 잠정실적 커버리지 (종목 x 분기) ---")
    prov = events[(events["구분"] == "잠정실적") & (~events["정정여부"])].copy()
    prov["분기"] = prov["대상연도"].astype(str) + "Q" + prov["대상분기"].astype(str)
    cov = prov.pivot_table(index="종목명", columns="분기",
                           values="접수번호", aggfunc="count", fill_value=0)
    print(cov.to_string())

    print(f"\n저장: {DATA_DIR / 'disclosures_raw.csv'}")
    print(f"저장: {DATA_DIR / 'earnings_events.csv'}")


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)

    # 02단계에서 만든 고유번호 매핑을 읽어온다
    _m = pd.read_csv(DATA_DIR / "corp_code_map.csv", dtype={"종목코드": str, "corp_code": str})
    CORP_MAP = dict(zip(_m["종목코드"], _m["corp_code"]))

    main()
