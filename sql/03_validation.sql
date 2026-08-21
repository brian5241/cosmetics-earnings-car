-- =====================================================================
-- 03. 검증 쿼리
-- =====================================================================
-- 데이터가 기대한 모양인지 SQL 로 확인한다.
-- 각 쿼리는 "문제가 있으면 행이 나오고, 없으면 0행"이 되도록 짰다.
-- 결과가 비어 있는 것이 통과다.
--
-- 실행기는 -- @name: 으로 시작하는 주석을 쿼리 제목으로 읽는다.
-- =====================================================================


-- @name: 재무 패널 결측 — 핵심 항목이 비어 있는 행
SELECT code, year, quarter, revenue, op_income, assets
FROM financials
WHERE revenue IS NULL
   OR op_income IS NULL
   OR assets IS NULL;


-- @name: 분기 연속성 — 중간에 빠진 분기
-- 종목별로 첫 분기부터 마지막 분기까지 몇 개가 있어야 하는지 계산하고
-- 실제 개수와 비교한다. 차이가 나면 중간이 비어 있다는 뜻이다.
WITH span AS (
    SELECT
        code,
        MIN(year * 4 + quarter) AS first_q,
        MAX(year * 4 + quarter) AS last_q,
        COUNT(*)                AS actual
    FROM financials
    GROUP BY code
)
SELECT
    code,
    last_q - first_q + 1 AS expected,
    actual,
    (last_q - first_q + 1) - actual AS missing
FROM span
WHERE actual <> last_q - first_q + 1;


-- @name: 이벤트-재무 연결 — 재무 데이터가 없는 이벤트
-- LEFT JOIN 은 왼쪽 표의 모든 행을 남긴다.
-- 오른쪽에 짝이 없으면 그 열이 NULL 이 되므로, 그걸로 누락을 찾는다.
SELECT e.code, e.year, e.quarter, e.announce_date
FROM events e
LEFT JOIN financials f
       ON f.code = e.code AND f.year = e.year AND f.quarter = e.quarter
WHERE f.code IS NULL;


-- @name: 영업이익률 재계산 대조 — 저장된 OPM 과 직접 계산값의 차이
-- 부동소수점 오차를 감안해 아주 작은 차이는 통과로 본다.
SELECT
    code, year, quarter,
    opm                          AS stored,
    op_income / NULLIF(revenue, 0) AS recomputed,
    ABS(opm - op_income / NULLIF(revenue, 0)) AS diff
FROM financials
WHERE revenue IS NOT NULL
  AND revenue <> 0
  AND ABS(opm - op_income / NULLIF(revenue, 0)) > 1e-9;


-- @name: 주가 이상치 — 하루 등락이 상하한가(±30%)를 넘는 경우
-- 수정주가가 제대로 반영됐다면 나오지 않아야 한다.
-- 나온다면 액면분할·병합이 반영되지 않았다는 신호다.
SELECT code, date, close, ret
FROM prices
WHERE ABS(ret) > 0.31
ORDER BY ABS(ret) DESC;


-- @name: 발표일이 거래일이 아닌 이벤트
-- 휴장일에 공시된 경우로, CAR 계산에서 다음 거래일로 밀어야 한다.
SELECT e.code, e.year, e.quarter, e.announce_date
FROM events e
LEFT JOIN prices p
       ON p.code = e.code AND p.date = e.announce_date
WHERE p.code IS NULL
ORDER BY e.announce_date;


-- @name: pandas 대조 — 매출 성장률
-- 같은 값을 pandas 와 SQL 로 각각 계산해 일치하는지 본다.
-- 두 경로가 같은 답을 내면 어느 쪽 구현도 신뢰할 수 있다.
SELECT
    s.code, s.year, s.quarter,
    p.revenue_yoy AS pandas_val,
    s.revenue_yoy AS sql_val,
    ABS(p.revenue_yoy - s.revenue_yoy) AS diff
FROM v_features s
JOIN features_pandas p
  ON p.code = s.code AND p.year = s.year AND p.quarter = s.quarter
WHERE p.revenue_yoy IS NOT NULL
  AND s.revenue_yoy IS NOT NULL
  AND ABS(p.revenue_yoy - s.revenue_yoy) > 1e-9;


-- @name: pandas 대조 — 영업이익률 변화폭
SELECT
    s.code, s.year, s.quarter,
    p.opm_chg AS pandas_val,
    s.opm_chg AS sql_val,
    ABS(p.opm_chg - s.opm_chg) AS diff
FROM v_features s
JOIN features_pandas p
  ON p.code = s.code AND p.year = s.year AND p.quarter = s.quarter
WHERE p.opm_chg IS NOT NULL
  AND s.opm_chg IS NOT NULL
  AND ABS(p.opm_chg - s.opm_chg) > 1e-9;


-- @name: pandas 대조 — 추세 이탈도
-- pandas 는 numpy.polyfit 으로 직선을 맞췄고,
-- SQL 은 그 해를 정리한 가중합으로 계산했다. 결과가 같아야 한다.
SELECT
    s.code, s.year, s.quarter,
    p.trend_dev AS pandas_val,
    s.trend_dev AS sql_val,
    ABS(p.trend_dev - s.trend_dev) AS diff
FROM v_features s
JOIN features_pandas p
  ON p.code = s.code AND p.year = s.year AND p.quarter = s.quarter
WHERE p.trend_dev IS NOT NULL
  AND s.trend_dev IS NOT NULL
  AND ABS(p.trend_dev - s.trend_dev) > 1e-9;
