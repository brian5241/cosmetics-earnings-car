-- =====================================================================
-- 01. 스키마 정의
-- =====================================================================
-- CSV 하나에 모든 컬럼을 몰아넣는 대신, 성격이 다른 데이터를 표로 나눈다.
-- 같은 값을 여러 곳에 중복 저장하지 않게 하고(정규화),
-- 표 사이를 키로 연결한다.
--
--   stocks      종목 마스터    — 종목당 1행
--   financials  분기 재무      — 종목 x 분기당 1행
--   events      실적 발표      — 종목 x 분기당 1행
--   prices      일별 주가      — 종목 x 날짜당 1행
--   car         분석 결과      — 종목 x 분기당 1행
--
-- 모든 표가 stocks.code 를 기준으로 이어진다.
-- =====================================================================

DROP VIEW  IF EXISTS v_features;
DROP TABLE IF EXISTS features_pandas;
DROP TABLE IF EXISTS car;
DROP TABLE IF EXISTS prices;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS financials;
DROP TABLE IF EXISTS stocks;


-- ---------------------------------------------------------------------
-- 종목 마스터
-- ---------------------------------------------------------------------
-- PRIMARY KEY: 이 표에서 행을 유일하게 식별하는 열.
--              같은 종목코드가 두 번 들어가는 것을 DB가 막아준다.
CREATE TABLE stocks (
    code        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    market      TEXT,               -- KOSPI / KOSDAQ
    sector      TEXT,               -- 브랜드 / ODM / 유통
    version     TEXT,               -- v1 / v2  (분석 대상 버전)
    first_trade TEXT,               -- 첫 거래일 (YYYY-MM-DD)
    market_cap  INTEGER
);


-- ---------------------------------------------------------------------
-- 분기 재무
-- ---------------------------------------------------------------------
-- PRIMARY KEY 가 세 열의 조합이다.
-- "한 종목의 한 분기는 한 행뿐"이라는 규칙을 DB가 강제한다.
-- 중복 적재나 잘못된 조인으로 행이 불어나는 사고를 원천 차단한다.
CREATE TABLE financials (
    code        TEXT    NOT NULL,
    year        INTEGER NOT NULL,
    quarter     INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    revenue     REAL,               -- 매출액
    op_income   REAL,               -- 영업이익
    net_income  REAL,               -- 당기순이익
    assets      REAL,               -- 자산총계
    liabilities REAL,               -- 부채총계
    equity      REAL,               -- 자본총계
    opm         REAL,               -- 영업이익률
    basis       TEXT,               -- 연결 / 별도
    method      TEXT,               -- 직접 / 역산 / 누계보완
    PRIMARY KEY (code, year, quarter),
    FOREIGN KEY (code) REFERENCES stocks(code)
);


-- ---------------------------------------------------------------------
-- 실적 발표 이벤트
-- ---------------------------------------------------------------------
CREATE TABLE events (
    code          TEXT    NOT NULL,
    year          INTEGER NOT NULL,
    quarter       INTEGER NOT NULL,
    announce_date TEXT    NOT NULL, -- 실적이 처음 공개된 날
    rcept_no      TEXT,             -- DART 접수번호
    kind          TEXT,             -- 연결잠정 / 별도잠정 / 손익변동 / 정기보고서
    source        TEXT,             -- 잠정실적 / 정기보고서
    early_listing INTEGER,          -- 상장 직후 여부 (0/1)
    PRIMARY KEY (code, year, quarter),
    FOREIGN KEY (code) REFERENCES stocks(code)
);


-- ---------------------------------------------------------------------
-- 일별 주가
-- ---------------------------------------------------------------------
CREATE TABLE prices (
    code   TEXT NOT NULL,
    date   TEXT NOT NULL,
    close  REAL,
    volume INTEGER,
    ret    REAL,                    -- 일간 수익률
    PRIMARY KEY (code, date),
    FOREIGN KEY (code) REFERENCES stocks(code)
);


-- ---------------------------------------------------------------------
-- CAR 산출 결과
-- ---------------------------------------------------------------------
CREATE TABLE car (
    code     TEXT    NOT NULL,
    year     INTEGER NOT NULL,
    quarter  INTEGER NOT NULL,
    model    TEXT,                  -- 2팩터시장모델 / 시장조정모델
    beta_mkt REAL,
    r2       REAL,
    car_0_1  REAL,
    car_0_5  REAL,
    car_0_20 REAL,
    car_pre  REAL,
    PRIMARY KEY (code, year, quarter),
    FOREIGN KEY (code) REFERENCES stocks(code)
);


-- ---------------------------------------------------------------------
-- pandas 계산 결과 (대조용)
-- ---------------------------------------------------------------------
-- 분석 파이프라인이 pandas 로 만든 파생 지표를 그대로 적재한다.
-- 같은 값을 SQL 로도 계산한 뒤 두 결과가 일치하는지 확인하기 위한 표다.
-- 분석에는 쓰지 않는다. 검증 전용이다.
CREATE TABLE features_pandas (
    code        TEXT    NOT NULL,
    year        INTEGER NOT NULL,
    quarter     INTEGER NOT NULL,
    revenue_yoy REAL,
    opm_chg     REAL,
    trend_dev   REAL,
    log_assets  REAL,
    PRIMARY KEY (code, year, quarter)
);


-- ---------------------------------------------------------------------
-- 인덱스
-- ---------------------------------------------------------------------
-- 자주 조건으로 쓰는 열에 인덱스를 만들면 조회가 빨라진다.
-- 책 뒤의 '찾아보기'와 같은 역할이다.
CREATE INDEX idx_prices_date ON prices(date);
CREATE INDEX idx_events_date ON events(announce_date);
CREATE INDEX idx_stocks_version ON stocks(version);
