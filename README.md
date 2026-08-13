# 화장품 섹터 실적 발표와 주가 반응 분석

분기 실적 발표에 담긴 재무 항목 중, **발표 직후 주가 반응(CAR)과 관련이 큰 항목이 무엇인지** 분석하는 이벤트 스터디 프로젝트.

> 작업 진행 중. 본 README는 분석 완료 후 작성한다.
> 현재 설계·의사결정 기록은 [`docs/design-log.md`](docs/design-log.md) 참조.

## 개요

| 항목 | 내용 |
|---|---|
| 대상 | 화장품 섹터 11종목 |
| 기간 | 4년 (분기 실적 발표 약 150건) |
| 종속변수 | CAR[0, +1] (누적초과수익률) |
| 데이터 | DART OpenAPI, FinanceDataReader / pykrx |
| 분석 | OLS, Lasso (TimeSeriesSplit 교차검증) |

## 구조

```
├── docs/design-log.md        설계 및 의사결정 기록
├── src/
│   └── 01_check_universe.py  유니버스 검증
└── data/universe.csv         종목 마스터
```

## 실행 준비

```bash
pip install pandas numpy statsmodels scikit-learn pykrx finance-datareader
cp .env.example .env   # DART_API_KEY 값을 채운다
```

DART 인증키는 [opendart.fss.or.kr](https://opendart.fss.or.kr)에서 발급받는다.
