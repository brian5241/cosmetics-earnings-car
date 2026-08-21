-- =====================================================================
-- 04. 분석 쿼리
-- =====================================================================
-- 결과를 SQL 로 집계한다. 회귀 분석은 파이썬이 맡고,
-- 여기서는 표본 구성과 집단별 비교를 확인한다.
-- =====================================================================


-- @name: 표본 구성 — 종목별 이벤트 수와 잠정실적 비율
-- 조건부 집계: SUM(CASE WHEN 조건 THEN 1 ELSE 0 END) 은
-- "조건을 만족하는 행의 개수"를 센다. 자주 쓰는 관용구다.
SELECT
    s.name                                              AS 종목,
    s.sector                                            AS 유형,
    COUNT(*)                                            AS 이벤트,
    SUM(CASE WHEN e.source = '잠정실적' THEN 1 ELSE 0 END) AS 잠정,
    ROUND(100.0 * SUM(CASE WHEN e.source = '잠정실적' THEN 1 ELSE 0 END)
          / COUNT(*), 0)                                AS 잠정비율
FROM events e
JOIN stocks s ON s.code = e.code
WHERE s.version = 'v1'
GROUP BY s.code, s.name, s.sector
ORDER BY 이벤트 DESC, 종목;


-- @name: 서프라이즈 분위별 평균 CAR
-- NTILE(3) 은 정렬된 행을 3등분해 1,2,3 번호를 붙인다.
-- 파이썬의 qcut 과 같은 역할이며, 분위별 비교의 표준 도구다.
WITH sample AS (
    SELECT
        f.code, f.year, f.quarter,
        f.trend_dev,
        c.car_0_1, c.car_0_5, c.car_0_20
    FROM v_features f
    JOIN car    c ON c.code = f.code AND c.year = f.year AND c.quarter = f.quarter
    JOIN stocks s ON s.code = f.code
    JOIN events e ON e.code = f.code AND e.year = f.year AND e.quarter = f.quarter
    WHERE s.version = 'v1'
      AND e.early_listing = 0
      AND f.trend_dev IS NOT NULL
      AND c.car_0_1   IS NOT NULL
),
ranked AS (
    SELECT *, NTILE(3) OVER (ORDER BY trend_dev) AS tercile
    FROM sample
)
SELECT
    CASE tercile WHEN 1 THEN '하위 (부정적)'
                 WHEN 2 THEN '중위'
                 ELSE        '상위 (긍정적)' END      AS 서프라이즈그룹,
    COUNT(*)                                        AS 건수,
    ROUND(100.0 * AVG(trend_dev), 2)                AS 평균이탈도,
    ROUND(100.0 * AVG(car_0_1),  2)                 AS "평균CAR_0_1",
    ROUND(100.0 * AVG(car_0_5),  2)                 AS "평균CAR_0_5",
    ROUND(100.0 * AVG(car_0_20), 2)                 AS "평균CAR_0_20"
FROM ranked
GROUP BY tercile
ORDER BY tercile;


-- @name: 정보출처별 비교 — 잠정실적 vs 정기보고서
SELECT
    e.source                          AS 정보출처,
    COUNT(*)                          AS 건수,
    ROUND(100.0 * AVG(c.car_0_1), 2)  AS 평균CAR,
    ROUND(100.0 * MIN(c.car_0_1), 1)  AS 최소,
    ROUND(100.0 * MAX(c.car_0_1), 1)  AS 최대
FROM car c
JOIN events e ON e.code = c.code AND e.year = c.year AND e.quarter = c.quarter
JOIN stocks s ON s.code = c.code
WHERE s.version = 'v1' AND c.car_0_1 IS NOT NULL
GROUP BY e.source
ORDER BY 건수 DESC;


-- @name: 분기별 평균 CAR — 시기에 따른 변화
SELECT
    c.year || 'Q' || c.quarter        AS 분기,
    COUNT(*)                          AS 건수,
    ROUND(100.0 * AVG(c.car_0_1), 2)  AS 평균CAR,
    ROUND(100.0 * AVG(f.revenue_yoy), 1) AS 평균매출성장
FROM car c
JOIN stocks s     ON s.code = c.code
LEFT JOIN v_features f
       ON f.code = c.code AND f.year = c.year AND f.quarter = c.quarter
WHERE s.version = 'v1' AND c.car_0_1 IS NOT NULL
GROUP BY c.year, c.quarter
ORDER BY c.year, c.quarter;


-- @name: 발표일 변동성 — 평상시 대비 몇 배인가
-- 발표일에 해당하는 주가 행만 골라 표준편차를 재고,
-- 전체 기간 표준편차와 비교한다.
WITH announce_days AS (
    SELECT p.ret
    FROM prices p
    JOIN events e ON e.code = p.code AND e.announce_date = p.date
    JOIN stocks s ON s.code = p.code
    WHERE s.version = 'v1' AND p.ret IS NOT NULL
),
all_days AS (
    SELECT p.ret
    FROM prices p
    JOIN stocks s ON s.code = p.code
    WHERE s.version = 'v1' AND p.ret IS NOT NULL
),
stats AS (
    SELECT
        (SELECT COUNT(*) FROM announce_days) AS n_announce,
        -- SQLite 에는 표준편차 함수가 없어 정의대로 직접 계산한다.
        --   표준편차 = sqrt( 평균(x^2) - 평균(x)^2 )
        (SELECT SQRT(AVG(ret * ret) - AVG(ret) * AVG(ret)) FROM announce_days) AS sd_announce,
        (SELECT SQRT(AVG(ret * ret) - AVG(ret) * AVG(ret)) FROM all_days)      AS sd_all
)
SELECT
    n_announce                             AS 발표일수,
    ROUND(100.0 * sd_announce, 2)          AS "발표일 표준편차",
    ROUND(100.0 * sd_all, 2)               AS "평상시 표준편차",
    ROUND(sd_announce / sd_all, 2)         AS 배수
FROM stats;


-- @name: 성장률 상위 10건과 그날의 주가 반응
SELECT
    s.name                            AS 종목,
    f.year || 'Q' || f.quarter        AS 분기,
    ROUND(100.0 * f.revenue_yoy, 1)   AS 매출성장,
    ROUND(100.0 * f.opm_chg, 2)       AS "OPM변화(%p)",
    ROUND(100.0 * f.trend_dev, 2)     AS "이탈도(%p)",
    ROUND(100.0 * c.car_0_1, 1)       AS CAR
FROM v_features f
JOIN car    c ON c.code = f.code AND c.year = f.year AND c.quarter = f.quarter
JOIN stocks s ON s.code = f.code
WHERE s.version = 'v1' AND f.revenue_yoy IS NOT NULL
ORDER BY f.revenue_yoy DESC
LIMIT 10;
