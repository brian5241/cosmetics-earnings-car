-- =====================================================================
-- 02. 파생 지표 (윈도우 함수)
-- =====================================================================
-- pandas 의 groupby().shift(4) 로 하던 전년 동기 비교를 SQL 로 다시 쓴다.
--
-- 윈도우 함수란:
--   GROUP BY 는 여러 행을 하나로 '접어' 버린다. (종목별 평균 등)
--   윈도우 함수는 행을 그대로 두면서 "이 행 기준 몇 칸 앞의 값"을 가져온다.
--   시계열 데이터에서 전분기·전년 대비를 계산할 때 쓰는 표준 도구다.
--
--   LAG(revenue, 4) OVER (PARTITION BY code ORDER BY year, quarter)
--   └ 같은 종목(PARTITION BY) 안에서, 연도·분기 순으로 줄 세운 뒤(ORDER BY),
--     4칸 앞(= 전년 동분기)의 매출액을 가져온다.
-- =====================================================================

DROP VIEW IF EXISTS v_features;

CREATE VIEW v_features AS
WITH lagged AS (
    SELECT
        code, year, quarter, revenue, op_income, opm, assets,

        -- 전년 동분기 (4분기 전)
        LAG(revenue, 4) OVER w AS revenue_ly,
        LAG(opm,     4) OVER w AS opm_ly,

        -- 직전 4개 분기 (추세 예측에 사용)
        LAG(op_income, 1) OVER w AS op_1,
        LAG(op_income, 2) OVER w AS op_2,
        LAG(op_income, 3) OVER w AS op_3,
        LAG(op_income, 4) OVER w AS op_4

    FROM financials
    -- WINDOW 절: 같은 윈도우 정의를 여러 번 쓸 때 이름을 붙여 재사용한다.
    WINDOW w AS (PARTITION BY code ORDER BY year, quarter)
)
SELECT
    code, year, quarter,
    revenue, op_income, opm, assets,

    -- ---------------------------------------------------------------
    -- 매출액 전년 대비 성장률
    -- ---------------------------------------------------------------
    -- NULLIF(x, 0) 은 x 가 0이면 NULL 을 돌려준다.
    -- 0으로 나누는 사고를 막는 관용적인 방법이다.
    (revenue - revenue_ly) / NULLIF(revenue_ly, 0) AS revenue_yoy,

    -- ---------------------------------------------------------------
    -- 영업이익률 변화폭 (%p)
    -- ---------------------------------------------------------------
    -- 성장률이 아니라 '비율의 차이'다.
    -- 적자 구간에서도 개선/악화 방향이 뒤집히지 않는다.
    opm - opm_ly AS opm_chg,

    -- ---------------------------------------------------------------
    -- 추세 대비 이탈도 (서프라이즈 대리변수)
    -- ---------------------------------------------------------------
    -- 직전 4개 분기에 직선을 맞춰 이번 분기를 예측하고, 실제와의 차이를 본다.
    --
    -- 4개 점(x=0,1,2,3)의 최소제곱 직선을 x=4 로 외삽하면
    -- 계수가 다음처럼 정리된다. 회귀를 돌리지 않고 가중합으로 끝난다.
    --
    --     예측 = -0.5*(4분기 전) + 0.5*(2분기 전) + 1.0*(1분기 전)
    --
    -- 매출액으로 나누는 이유: 규모 차이를 없애고, 기저가 0에 가까울 때
    -- 값이 폭발하는 문제를 피하기 위해서다.
    (op_income - (-0.5 * op_4 + 0.5 * op_2 + 1.0 * op_1))
        / NULLIF(revenue, 0) AS trend_dev,

    -- 참고용 원자료
    revenue_ly,
    (-0.5 * op_4 + 0.5 * op_2 + 1.0 * op_1) AS op_trend_pred,

    -- 규모 통제변수
    LN(assets) AS log_assets

FROM lagged;
