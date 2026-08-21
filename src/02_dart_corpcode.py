"""
02. DART 연결 확인 및 고유번호 매핑
===================================
(1) 발급받은 인증키가 정상 동작하는지 확인한다.
(2) DART 고유번호(corp_code) ↔ 종목코드 매핑 테이블을 만든다.

왜 (2)가 필요한가:
  DART API는 종목코드(예: 090430)가 아니라 자체 고유번호(8자리)로 조회한다.
  전체 기업의 매핑 정보를 zip으로 한 번 받아서 우리 종목만 추려 저장해둔다.

실행:  python src/02_dart_corpcode.py
출력:  data/corp_code_map.csv
"""

import io
import sys
import zipfile
import xml.etree.ElementTree as ET

import pandas as pd
import requests

from config import DART_API_KEY, DATA_DIR, RAW_DIR, UNIVERSE

BASE = "https://opendart.fss.or.kr/api"

# DART 응답 status 코드 의미 (개발가이드 기준)
STATUS_MESSAGE = {
    "000": "정상",
    "010": "등록되지 않은 키",
    "011": "사용할 수 없는 키 (오픈API에 등록되지 않았거나 삭제됨)",
    "012": "접근할 수 없는 IP",
    "013": "조회된 데이터 없음",
    "020": "요청 제한 초과 (일 20,000건)",
    "100": "필드의 부적절한 값",
    "800": "시스템 점검 중",
    "900": "정의되지 않은 오류",
    "901": "사용자 계정의 개인정보 보유기간 만료",
}


def check_api_key() -> bool:
    """인증키가 살아 있는지 가벼운 요청으로 확인한다.

    공시목록(list.json)을 아주 좁은 기간으로 1건만 요청해
    응답의 status 코드로 키 상태를 판단한다.
    """
    print("=" * 60)
    print("1. 인증키 확인")
    print("=" * 60)

    # 키가 노출되지 않도록 앞뒤 일부만 보여준다
    masked = f"{DART_API_KEY[:4]}...{DART_API_KEY[-4:]} (길이 {len(DART_API_KEY)})"
    print(f"키: {masked}")

    if len(DART_API_KEY) != 40:
        print(f"[경고] DART 인증키는 보통 40자입니다. 현재 {len(DART_API_KEY)}자입니다.")

    resp = requests.get(
        f"{BASE}/list.json",
        params={
            "crtfc_key": DART_API_KEY,
            "bgn_de": "20260801",
            "end_de": "20260810",
            "page_count": "1",
        },
        timeout=30,
    )
    data = resp.json()
    status = data.get("status")
    print(f"status: {status} — {STATUS_MESSAGE.get(status, data.get('message'))}")

    # 013(데이터 없음)은 키 자체는 정상이므로 통과로 본다
    if status in ("000", "013"):
        print("[OK] 인증키 정상")
        return True

    print("[실패] 인증키를 확인하세요.")
    return False


def fetch_corp_code_map() -> pd.DataFrame:
    """전체 기업의 고유번호 매핑을 받아 DataFrame으로 반환한다.

    corpCode.xml 은 zip으로 내려오며 안에 CORPCODE.xml 이 들어 있다.
    (약 10만 건이라 응답이 수 MB다. 원본은 data/raw 에 남겨 재다운로드를 피한다.)
    """
    print()
    print("=" * 60)
    print("2. 고유번호(corp_code) 매핑 수집")
    print("=" * 60)

    resp = requests.get(
        f"{BASE}/corpCode.xml",
        params={"crtfc_key": DART_API_KEY},
        timeout=120,
    )

    # 오류일 때는 zip이 아니라 XML/JSON 에러 메시지가 온다
    if not resp.content[:2] == b"PK":
        print("[실패] zip 응답이 아닙니다. 응답 앞부분:")
        print(resp.content[:300])
        sys.exit(1)

    raw_path = RAW_DIR / "corpCode.zip"
    raw_path.write_bytes(resp.content)
    print(f"원본 저장: {raw_path} ({len(resp.content):,} bytes)")

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        xml_bytes = zf.read(zf.namelist()[0])

    root = ET.fromstring(xml_bytes)
    rows = []
    for item in root.iter("list"):
        stock_code = (item.findtext("stock_code") or "").strip()
        rows.append({
            "corp_code":  (item.findtext("corp_code") or "").strip(),
            "corp_name":  (item.findtext("corp_name") or "").strip(),
            "종목코드":    stock_code,
            "modify_date": (item.findtext("modify_date") or "").strip(),
        })

    df = pd.DataFrame(rows)
    print(f"전체 기업 수: {len(df):,}")

    # 종목코드가 있는 것 = 상장사. 비상장사는 종목코드가 빈 값이다.
    listed = df[df["종목코드"] != ""]
    print(f"상장사 수: {len(listed):,}")
    return listed


def map_universe(listed: pd.DataFrame) -> pd.DataFrame:
    """분석 대상 종목만 추려 매핑 테이블을 만든다."""
    print()
    print("=" * 60)
    print("3. 분석 대상 매핑")
    print("=" * 60)

    lookup = listed.set_index("종목코드")
    rows = []
    for code, name, sector, version in UNIVERSE:
        if code in lookup.index:
            hit = lookup.loc[code]
            # 동일 종목코드가 중복될 경우 첫 건 사용 (정상적으로는 발생하지 않음)
            if isinstance(hit, pd.DataFrame):
                hit = hit.iloc[0]
            rows.append({
                "종목코드": code,
                "종목명": name,
                "유형": sector,
                "포함버전": version,
                "corp_code": hit["corp_code"],
                "DART기업명": hit["corp_name"],
                "매핑성공": True,
            })
        else:
            rows.append({
                "종목코드": code, "종목명": name, "유형": sector,
                "포함버전": version, "corp_code": None,
                "DART기업명": None, "매핑성공": False,
            })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.width", 200)

    if not check_api_key():
        sys.exit(1)

    listed = fetch_corp_code_map()
    mapped = map_universe(listed)

    out = DATA_DIR / "corp_code_map.csv"
    mapped.to_csv(out, index=False, encoding="utf-8-sig")

    print(mapped[["종목코드", "종목명", "corp_code", "DART기업명", "매핑성공"]].to_string(index=False))

    failed = mapped[~mapped["매핑성공"]]
    if failed.empty:
        print("\n[OK] 전 종목 매핑 성공")
    else:
        print(f"\n[확인 필요] 매핑 실패 {len(failed)}건")
        print(failed[["종목코드", "종목명"]].to_string(index=False))

    print(f"\n저장: {out}")
