"""
14. SQLite 적재 및 SQL 검증·집계
=================================
CSV 로 흩어져 있던 산출물을 관계형 DB 하나로 모으고, SQL 로 다시 확인한다.

왜 하는가:
  (1) 데이터 모델링 — 어떤 표로 나누고 무엇을 키로 삼을지 명시한다.
      기본키를 걸어두면 중복 적재나 잘못된 조인으로 행이 불어나는 사고를
      DB가 막아준다. pandas 로만 하면 이런 보호 장치가 없다.

  (2) 교차 검증 — pandas 로 만든 파생 지표를 SQL 윈도우 함수로 다시 계산하고
      두 결과가 일치하는지 확인한다. 서로 다른 두 경로가 같은 답을 내면
      어느 쪽 구현도 신뢰할 수 있다.

DB 파일은 재생성 가능한 산출물이므로 저장소에 두지 않는다(.gitignore).
남는 것은 sql/*.sql 과 이 스크립트다.

실행:  python src/14_build_db.py
출력:  data/analysis.db
"""

import re
import sqlite3

import numpy as np
import pandas as pd

from config import DATA_DIR, ROOT

SQL_DIR = ROOT / "sql"
DB_PATH = DATA_DIR / "analysis.db"

# CSV 는 한글 컬럼명을 쓰지만 DB 스키마는 영문으로 둔다.
# SQL 안에서 따옴표 없이 쓸 수 있고, 스키마 자체가 읽기 쉬워진다.
COLMAP = {
    "stocks": {
        "종목코드": "code", "종목명": "name", "시장": "market",
        "유형": "sector", "포함버전": "version",
        "첫거래일": "first_trade", "시가총액": "market_cap",
    },
    "financials": {
        "종목코드": "code", "연도": "year", "분기": "quarter",
        "매출액": "revenue", "영업이익": "op_income", "당기순이익": "net_income",
        "자산총계": "assets", "부채총계": "liabilities", "자본총계": "equity",
        "OPM": "opm", "기준": "basis", "산출방식": "method",
    },
    "events": {
        "종목코드": "code", "대상연도": "year", "대상분기": "quarter",
        "발표일": "announce_date", "접수번호": "rcept_no",
        "세부구분": "kind", "정보출처": "source", "상장직후": "early_listing",
    },
    "prices": {
        "종목코드": "code", "일자": "date", "종가": "close",
        "거래량": "volume", "수익률": "ret",
    },
    "car": {
        "종목코드": "code", "모델": "model", "beta_시장": "beta_mkt", "R2": "r2",
        "CAR_0_1": "car_0_1", "CAR_0_5": "car_0_5",
        "CAR_0_20": "car_0_20", "CAR_PRE": "car_pre",
    },
    "features_pandas": {
        "종목코드": "code", "매출YoY": "revenue_yoy", "OPM변화": "opm_chg",
        "추세이탈도": "trend_dev", "로그자산": "log_assets",
    },
}


def ensure_math_functions(con: sqlite3.Connection) -> None:
    """LN·SQRT 를 쓸 수 있는지 확인하고, 없으면 파이썬 함수로 등록한다.

    SQLite 의 수학 함수는 빌드 옵션에 따라 빠져 있을 수 있다.
    없는 환경에서도 같은 SQL 이 돌아가도록 미리 채워둔다.
    """
    for name, fn in [("ln", np.log), ("sqrt", np.sqrt)]:
        try:
            con.execute(f"SELECT {name}(1.0)").fetchone()
        except sqlite3.OperationalError:
            con.create_function(name, 1, lambda x, f=fn: None if x is None else float(f(x)))
            print(f"  ({name}() 내장 함수 없음 → 파이썬 함수로 등록)")


def split_year_quarter(s: pd.Series) -> pd.DataFrame:
    """'2024Q1' 형태를 연도·분기로 나눈다."""
    parts = s.astype(str).str.extract(r"(\d{4})Q(\d)")
    return pd.DataFrame({"year": parts[0].astype(int),
                         "quarter": parts[1].astype(int)})


def load_tables(con: sqlite3.Connection) -> None:
    print("=" * 70)
    print("1. CSV → SQLite 적재")
    print("=" * 70)

    def put(df: pd.DataFrame, table: str) -> None:
        cols = COLMAP[table]
        out = df.rename(columns=cols)[list(cols.values())]
        out.to_sql(table, con, if_exists="append", index=False)
        print(f"  {table:<16s} {len(out):>6,}행")

    # --- 종목 마스터 (v1/v2 후보 모두 넣는다) ---
    uni = pd.read_csv(DATA_DIR / "universe.csv", dtype={"종목코드": str})
    uni["첫거래일"] = pd.to_datetime(uni["첫거래일"]).dt.strftime("%Y-%m-%d")
    put(uni, "stocks")

    # --- 분기 재무 ---
    fin = pd.read_csv(DATA_DIR / "financials_quarterly.csv", dtype={"종목코드": str})
    put(fin, "financials")

    # --- 이벤트 ---
    ev = pd.read_csv(DATA_DIR / "events.csv", dtype={"종목코드": str})
    ev["발표일"] = pd.to_datetime(ev["발표일"]).dt.strftime("%Y-%m-%d")
    ev["상장직후"] = ev["상장직후"].astype(int)
    put(ev, "events")

    # --- 주가 ---
    px = pd.read_csv(DATA_DIR / "prices.csv", dtype={"종목코드": str})
    px["일자"] = pd.to_datetime(px["일자"]).dt.strftime("%Y-%m-%d")
    put(px, "prices")

    # --- CAR ---
    car = pd.read_csv(DATA_DIR / "car.csv", dtype={"종목코드": str})
    car = pd.concat([car, split_year_quarter(car["분기"])], axis=1)
    car = car.rename(columns=COLMAP["car"])
    car[["code", "year", "quarter", "model", "beta_mkt", "r2",
         "car_0_1", "car_0_5", "car_0_20", "car_pre"]].to_sql(
        "car", con, if_exists="append", index=False)
    print(f"  {'car':<16s} {len(car):>6,}행")

    # --- pandas 계산 결과 (대조용) ---
    ds = pd.read_csv(DATA_DIR / "dataset.csv", dtype={"종목코드": str})
    ds = pd.concat([ds, split_year_quarter(ds["분기"])], axis=1)
    ds = ds.rename(columns=COLMAP["features_pandas"])
    ds[["code", "year", "quarter", "revenue_yoy", "opm_chg",
        "trend_dev", "log_assets"]].to_sql(
        "features_pandas", con, if_exists="append", index=False)
    print(f"  {'features_pandas':<16s} {len(ds):>6,}행")


def read_blocks(path) -> list[tuple[str, str]]:
    """-- @name: 로 구분된 쿼리들을 (제목, SQL) 목록으로 읽는다."""
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^--\s*@name:\s*(.+)$", text, flags=re.MULTILINE)
    blocks = []
    for i in range(1, len(parts), 2):
        title, body = parts[i].strip(), parts[i + 1].strip()
        if body:
            blocks.append((title, body.rstrip(";").strip()))
    return blocks


def run_validation(con: sqlite3.Connection) -> None:
    print()
    print("=" * 70)
    print("2. 검증 — 결과가 0행이면 통과")
    print("=" * 70)

    failed = 0
    for title, sql in read_blocks(SQL_DIR / "03_validation.sql"):
        df = pd.read_sql_query(sql, con)
        if df.empty:
            print(f"  [통과] {title}")
        else:
            failed += 1
            print(f"  [확인] {title} — {len(df)}건")
            print(df.head(8).to_string(index=False).replace("\n", "\n        "))
    print()
    print(f"  검증 항목 중 확인 필요 {failed}건")


def run_analysis(con: sqlite3.Connection) -> None:
    print()
    print("=" * 70)
    print("3. 집계")
    print("=" * 70)

    for title, sql in read_blocks(SQL_DIR / "04_analysis.sql"):
        df = pd.read_sql_query(sql, con)
        print(f"\n--- {title} ---")
        print(df.to_string(index=False))


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    ensure_math_functions(con)

    # 스키마 생성
    con.executescript((SQL_DIR / "01_schema.sql").read_text(encoding="utf-8"))

    load_tables(con)
    con.commit()

    # 파생 지표 뷰 (윈도우 함수)
    con.executescript((SQL_DIR / "02_features.sql").read_text(encoding="utf-8"))

    run_validation(con)
    run_analysis(con)

    con.close()
    print(f"\n저장: {DB_PATH}  ({DB_PATH.stat().st_size / 1024:,.0f} KB)")


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    main()
