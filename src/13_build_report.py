"""
13. 분석 보고서 생성
====================
분석 결과를 하나의 HTML 보고서로 묶는다.
그림은 data URI 로 삽입해 파일 하나로 완결되게 한다.

실행:  python src/13_build_report.py
출력:  report.html
"""

import base64

from config import ROOT

FIG_DIR = ROOT / "figures"


def data_uri(name: str) -> str:
    b64 = base64.b64encode((FIG_DIR / name).read_bytes()).decode()
    return f"data:image/png;base64,{b64}"


CSS = """
:root {
  color-scheme: light;
  --ground:      #fbfbfa;
  --panel:       #f2f3f0;
  --ink:         #14161c;
  --ink-2:       #565c68;
  --ink-3:       #8b909c;
  --rule:        #e4e4df;
  --rule-strong: #c9cac4;
  --accent:      #2a78d6;
  --accent-deep: #17458c;
  --neg:         #c8443d;
  --figure-bg:   #fcfcfb;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --ground:      #16171a;
    --panel:       #1e2024;
    --ink:         #f2f2ef;
    --ink-2:       #a9adb6;
    --ink-3:       #7c818c;
    --rule:        #2b2d31;
    --rule-strong: #3c3f45;
    --accent:      #5b9df0;
    --accent-deep: #8ab6f5;
    --neg:         #e8736c;
    --figure-bg:   #fcfcfb;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --ground:      #16171a;
  --panel:       #1e2024;
  --ink:         #f2f2ef;
  --ink-2:       #a9adb6;
  --ink-3:       #7c818c;
  --rule:        #2b2d31;
  --rule-strong: #3c3f45;
  --accent:      #5b9df0;
  --accent-deep: #8ab6f5;
  --neg:         #e8736c;
  --figure-bg:   #fcfcfb;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--ground);
  color: var(--ink);
  font-family: "IBM Plex Sans KR", system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 16px;
  line-height: 1.75;
  -webkit-font-smoothing: antialiased;
}

.wrap {
  display: grid;
  grid-template-columns: 1fr;
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 24px 120px;
}
@media (min-width: 1080px) {
  .wrap { grid-template-columns: 190px minmax(0, 1fr); gap: 56px; }
}

/* ---------- 목차 레일 ---------- */
nav.toc { display: none; }
@media (min-width: 1080px) {
  nav.toc {
    display: block;
    position: sticky;
    top: 0;
    align-self: start;
    padding-top: 148px;
    max-height: 100vh;
    overflow-y: auto;
  }
}
nav.toc ol { list-style: none; margin: 0; padding: 0; }
nav.toc li { margin: 0 0 2px; }
nav.toc a {
  display: flex;
  gap: 10px;
  padding: 5px 0;
  color: var(--ink-3);
  text-decoration: none;
  font-size: 13px;
  line-height: 1.45;
  border-bottom: 1px solid transparent;
}
nav.toc a:hover, nav.toc a:focus-visible { color: var(--accent); }
nav.toc a .n {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 11px;
  padding-top: 2px;
  font-variant-numeric: tabular-nums;
}

main { min-width: 0; }

/* ---------- 표제 ---------- */
header.masthead {
  padding: 116px 0 40px;
  border-bottom: 2px solid var(--ink);
}
.eyebrow {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 11.5px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink-3);
  margin: 0 0 22px;
}
h1 {
  font-family: "Nanum Myeongjo", Georgia, serif;
  font-weight: 700;
  font-size: clamp(2.1rem, 5.2vw, 3.1rem);
  line-height: 1.24;
  letter-spacing: -0.015em;
  margin: 0 0 20px;
  text-wrap: balance;
  max-width: 20ch;
}
.standfirst {
  font-size: 1.06rem;
  color: var(--ink-2);
  margin: 0 0 34px;
  max-width: 62ch;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0 34px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 12.5px;
  color: var(--ink-2);
  font-variant-numeric: tabular-nums;
}
.meta b { color: var(--ink); font-weight: 600; }

/* ---------- 섹션 ---------- */
section { padding-top: 68px; scroll-margin-top: 24px; }
h2 {
  font-family: "Nanum Myeongjo", Georgia, serif;
  font-size: 1.62rem;
  font-weight: 700;
  line-height: 1.35;
  margin: 0 0 8px;
  display: flex;
  gap: 16px;
  align-items: baseline;
  text-wrap: balance;
}
h2 .n {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 0.78rem;
  color: var(--accent);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  flex: none;
}
.rule { height: 1px; background: var(--rule-strong); margin: 0 0 30px; }
h3 {
  font-size: 1.02rem;
  font-weight: 600;
  margin: 40px 0 12px;
  letter-spacing: -0.005em;
}
p { margin: 0 0 18px; max-width: 68ch; }
strong { font-weight: 600; }
a { color: var(--accent-deep); text-decoration-thickness: 1px; text-underline-offset: 2px; }

ul, ol { max-width: 66ch; padding-left: 20px; margin: 0 0 20px; }
li { margin-bottom: 7px; }
li::marker { color: var(--ink-3); }

/* ---------- 핵심 결과 ---------- */
.findings {
  display: grid;
  gap: 1px;
  background: var(--rule);
  border: 1px solid var(--rule);
  margin: 4px 0 34px;
}
@media (min-width: 720px) { .findings { grid-template-columns: repeat(3, 1fr); } }
.finding { background: var(--ground); padding: 24px 22px 26px; }
.finding .k {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-3);
  margin-bottom: 14px;
}
.finding .v {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 2.05rem;
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.02em;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
  margin-bottom: 12px;
}
.finding .v.plain { color: var(--ink); }
.finding p { font-size: 0.9rem; color: var(--ink-2); margin: 0; line-height: 1.6; }

/* ---------- 표 ---------- */
.tablewrap { overflow-x: auto; margin: 0 0 12px; }
table {
  border-collapse: collapse;
  width: 100%;
  min-width: 480px;
  font-size: 0.875rem;
  font-variant-numeric: tabular-nums;
}
caption {
  caption-side: top;
  text-align: left;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-3);
  padding-bottom: 10px;
}
th, td { padding: 9px 14px 9px 0; text-align: left; vertical-align: top; }
thead th {
  border-bottom: 1.5px solid var(--ink);
  font-weight: 600;
  font-size: 0.8rem;
  color: var(--ink);
  white-space: nowrap;
}
tbody tr { border-bottom: 1px solid var(--rule); }
tbody tr:last-child { border-bottom: 1px solid var(--rule-strong); }
td.num, th.num { text-align: right; font-family: "IBM Plex Mono", ui-monospace, monospace; }
tr.hi td { background: var(--panel); font-weight: 600; }
.sig { color: var(--accent); font-family: "IBM Plex Mono", ui-monospace, monospace; }
.dim { color: var(--ink-3); }
.tnote { font-size: 0.8rem; color: var(--ink-3); margin: 0 0 26px; max-width: 68ch; }

/* ---------- 그림 ---------- */
figure { margin: 30px 0 34px; }
/* 그림 PNG 자체에 밝은 배경이 박혀 있다.
   같은 색으로 여백을 둘러 다크 모드에서도 '인쇄된 도판'처럼 보이게 한다.
   (배경색을 다르게 두면 이음매가 드러난다) */
figure img {
  display: block;
  width: 100%;
  height: auto;
  padding: 10px;
  background: var(--figure-bg);
  border: 1px solid var(--rule);
}
figcaption {
  font-size: 0.83rem;
  color: var(--ink-2);
  margin-top: 12px;
  max-width: 68ch;
  line-height: 1.6;
}
figcaption b {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 0.76rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-3);
  font-weight: 500;
  margin-right: 8px;
}

/* ---------- 판단 노트 ---------- */
.note {
  background: var(--panel);
  padding: 22px 24px;
  margin: 26px 0 30px;
  border-top: 2px solid var(--rule-strong);
}
.note .label {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 11px;
  letter-spacing: 0.11em;
  text-transform: uppercase;
  color: var(--ink-3);
  margin-bottom: 12px;
}
.note p:last-child { margin-bottom: 0; }
.note code, code {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 0.86em;
  background: var(--ground);
  padding: 1px 5px;
  border: 1px solid var(--rule);
}
.note code { background: var(--ground); }

pre {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 0.8rem;
  line-height: 1.7;
  background: var(--panel);
  padding: 18px 20px;
  overflow-x: auto;
  margin: 0 0 24px;
  border-top: 2px solid var(--rule-strong);
}
pre code { background: none; border: none; padding: 0; font-size: 1em; }

footer {
  margin-top: 84px;
  padding-top: 26px;
  border-top: 1px solid var(--rule);
  font-size: 0.83rem;
  color: var(--ink-3);
}
footer p { max-width: 68ch; }

:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }

@media print {
  nav.toc { display: none; }
  .wrap { grid-template-columns: 1fr; max-width: none; }
  section { page-break-inside: avoid; padding-top: 34px; }
  header.masthead { padding-top: 0; }
}
"""

SECTIONS = [
    ("summary", "요약"),
    ("question", "배경과 연구 질문"),
    ("data", "데이터"),
    ("method", "방법"),
    ("decisions", "전처리에서 내린 판단"),
    ("results", "결과"),
    ("limits", "한계"),
    ("conclusion", "결론"),
]


def build() -> str:
    toc = "\n".join(
        f'<li><a href="#{sid}"><span class="n">{i:02d}</span>'
        f'<span>{name}</span></a></li>'
        for i, (sid, name) in enumerate(SECTIONS, 1)
    )

    return f"""<title>실적 항목과 주가 반응</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+KR:wght@300;400;500;600&family=Nanum+Myeongjo:wght@400;700;800&display=swap">
<style>{CSS}</style>

<div class="wrap">
<nav class="toc" aria-label="목차"><ol>{toc}</ol></nav>
<main>

<header class="masthead">
  <p class="eyebrow">이벤트 스터디 · 화장품 섹터</p>
  <h1>실적 발표의 어떤 항목이 주가를 움직이는가</h1>
  <p class="standfirst">
    화장품 섹터 11개 종목의 4년치 분기 실적 발표 155건을 대상으로,
    재무 항목별 주가 반응을 측정했다. 증권사 추정치를 쓰지 않고
    과거 실적 추세로 기대치를 직접 구성했다.
  </p>
  <div class="meta">
    <span>표본 <b>155건</b></span>
    <span>종목 <b>11</b></span>
    <span>기간 <b>2022Q3–2026Q2</b></span>
    <span>종속변수 <b>CAR[0,+1]</b></span>
    <span>작성 <b>2026-08-21</b></span>
  </div>
</header>

<section id="summary">
<h2><span class="n">01</span>요약</h2><div class="rule"></div>

<div class="findings">
  <div class="finding">
    <div class="k">가장 강한 항목</div>
    <div class="v">+3.1<span style="font-size:.5em">%p</span></div>
    <p>추세 대비 이탈(서프라이즈)이 1 표준편차 커질 때의 CAR 변화.
       6개 항목 중 가장 크고, 모든 강건성 검증에서 유의했다.</p>
  </div>
  <div class="finding">
    <div class="k">설명력</div>
    <div class="v plain">0.146</div>
    <p>결정계수 R². 주가 변동의 약 15%를 실적 항목으로 설명한다.
       주가 수익률 분석에서는 낮지 않은 수준이다.</p>
  </div>
  <div class="finding">
    <div class="k">발표일 변동성</div>
    <div class="v plain">2.03<span style="font-size:.5em">배</span></div>
    <p>발표일 주가 변동성이 평상시의 두 배였다.
       실적 발표가 주가를 움직인다는 전제 자체의 확인이다.</p>
  </div>
</div>

<p>
  분석의 결론은 하나로 모인다. <strong>주가를 움직이는 것은 "좋은 실적"이 아니라
  "기대보다 좋은 실적"이다.</strong> 매출이 얼마나 늘었는지보다, 시장이 예상했을 법한
  수준에서 얼마나 벗어났는지가 발표 직후 주가 반응과 훨씬 강하게 연결됐다.
</p>
<p>
  해석용 OLS와 변수 선택용 Lasso를 각각 돌렸고, 목적이 다른 두 방법이 같은 결론에
  도달했다. 통제변수로 넣은 선반영·기업 규모·정보 신선도는 두 방법 모두에서
  효과가 확인되지 않았다.
</p>
<p>
  이 프로젝트에서 가장 많은 시간이 든 부분은 모델링이 아니라 <strong>데이터를 시점
  정합성에 맞춰 이어붙이는 작업</strong>이었다. 특히 증권사 추정치(컨센서스)를 사용하지
  않기로 한 판단이 분석 설계 전체를 좌우했다.
</p>
</section>

<section id="question">
<h2><span class="n">02</span>배경과 연구 질문</h2><div class="rule"></div>

<p>
  기업은 분기마다 실적을 발표하고, 그 안에는 매출·영업이익·이익률 등 여러 항목이
  함께 담긴다. 시장이 이 중 무엇에 반응하는지는 실무에서 자주 언급되지만
  대체로 경험적 인상에 의존한다. 이 분석은 그것을 데이터로 확인한다.
</p>

<h3>세 가지 방법론적 문제</h3>
<div class="tablewrap">
<table>
  <caption>문제와 대응</caption>
  <thead><tr><th>문제</th><th>대응</th></tr></thead>
  <tbody>
    <tr><td>주가는 실적 외 요인으로도 움직인다</td>
        <td>시장·섹터 수익률을 차감한 <strong>초과수익률(CAR)</strong> 사용</td></tr>
    <tr><td>기대가 이미 주가에 반영돼 있다</td>
        <td>발표 전 CAR을 통제변수로 투입, 짧은 윈도우 [0,+1] 사용</td></tr>
    <tr><td>개별 이벤트의 교란 요인을 통제할 수 없다</td>
        <td>155건을 모아 평균에서 상쇄</td></tr>
  </tbody>
</table>
</div>

<div class="note">
  <div class="label">통제 판단 기준</div>
  <p>
    무엇을 통제하고 무엇을 놔둘지는 하나의 기준으로 정했다.
    <strong>랜덤이면 표본 평균이 처리하도록 놔두고, 체계적이면 통제한다.</strong>
    발표일에 우연히 나온 개별 뉴스는 방향이 제각각이라 155건 평균에서 상쇄되지만,
    시장 전체 등락과 섹터 업황은 모든 이벤트에 같은 방향으로 걸려 상쇄되지 않는다.
    그래서 앞의 것은 통제하지 않고 뒤의 것만 벤치마크로 차감했다.
  </p>
</div>
</section>

<section id="data">
<h2><span class="n">03</span>데이터</h2><div class="rule"></div>

<h3>대상 선정</h3>
<p>
  종목은 다음 기준으로 선정했다. 자의적 선택으로 보이지 않도록 기준을 먼저 세우고
  일관되게 적용했다.
</p>
<blockquote style="margin:0 0 22px;padding-left:18px;border-left:2px solid var(--rule-strong);color:var(--ink-2)">
  화장품 매출이 전사 매출의 과반이고, 분석 기간 내 최소 4개 분기를 확보할 수 있는 상장사.
  지주사와 사업회사가 중복될 경우 사업회사만 채택한다.
</blockquote>

<div class="tablewrap">
<table>
  <caption>제외 종목과 사유</caption>
  <thead><tr><th>종목</th><th>사유</th></tr></thead>
  <tbody>
    <tr><td>LG생활건강, 애경산업</td><td>생활용품·음료 비중이 커 실적 동인이 화장품 외 요인에 좌우됨</td></tr>
    <tr><td>아모레G</td><td>아모레퍼시픽과 실적 발표가 중복되어 동일 이벤트를 두 번 세게 됨</td></tr>
    <tr><td>파마리서치, 휴젤, 클래시스</td><td>화장품 밸류체인 밖(의료기기·의약품)</td></tr>
  </tbody>
</table>
</div>
<p class="tnote">
  섹터 정의를 협의(화장품)와 광의(K뷰티) 두 가지로 놓고 유니버스가 어떻게 달라지는지
  비교한 뒤 협의를 택했다. 광의로 넓히면 미용기기·톡신 종목이 들어오는데,
  이들은 실적보다 허가·소송에 주가가 반응해 섹터를 한정한 목적 자체가 무너진다.
</p>

<h3>구성</h3>
<div class="tablewrap">
<table>
  <caption>최종 유니버스</caption>
  <thead><tr><th>유형</th><th>종목</th><th class="num">이벤트</th></tr></thead>
  <tbody>
    <tr><td>브랜드</td><td>아모레퍼시픽 · 클리오 · 브이티 · 네오팜 · 에이피알 · 달바글로벌</td><td class="num">78</td></tr>
    <tr><td>ODM</td><td>한국콜마 · 코스맥스 · 코스메카코리아</td><td class="num">48</td></tr>
    <tr><td>유통</td><td>실리콘투 · 아이패밀리에스씨</td><td class="num">32</td></tr>
    <tr class="hi"><td>합계</td><td>11종목</td><td class="num">155</td></tr>
  </tbody>
</table>
</div>

<div class="tablewrap">
<table>
  <caption>출처</caption>
  <thead><tr><th>항목</th><th>출처</th><th>비고</th></tr></thead>
  <tbody>
    <tr><td>실적</td><td>DART OpenAPI (주요계정)</td><td>매출액·영업이익·당기순이익·자산총계 등</td></tr>
    <tr><td>주가·지수</td><td>FinanceDataReader / pykrx</td><td>수정주가 기준</td></tr>
    <tr><td>컨센서스</td><td class="dim">미사용</td><td>사유는 05장</td></tr>
  </tbody>
</table>
</div>
</section>

<section id="method">
<h2><span class="n">04</span>방법</h2><div class="rule"></div>

<h3>이벤트 정의</h3>
<p>
  분석 단위는 종목 × 분기이며, 한 분기에 이벤트는 하나다.
  기준 시점(<code>t=0</code>)은 <strong>그 분기 실적이 처음 공개된 날</strong>로 정의했다.
</p>
<p>
  잠정실적 공시는 법적 의무가 아니라 회사 재량이어서 관행이 갈린다. 매 분기 공시하는
  종목이 있는가 하면 결산기에만 내는 종목도 있다. 잠정실적만 쓰면 표본의 절반이 사라지므로,
  잠정실적이 있으면 그날을, 없으면 정기보고서 제출일을 기준으로 삼았다.
  <strong>어느 경로로 잡혔는지는 변수로 기록</strong>해 통제했다. 최초 공개와 확정 공시는
  정보의 신선도가 다르기 때문이다.
</p>
<p class="tnote">
  같은 날 연결·별도 실적을 모두 공시하는 기업(한국콜마)이나 결산기에 잠정실적과
  손익구조변동 공시가 겹치는 경우는 우선순위를 정해 1건으로 축약했다.
  정정공시는 원공시가 이미 있으므로 제외했다.
</p>

<h3>초과수익률 산출</h3>
<pre><code>AR  = 실제 수익률 − 정상 수익률
CAR = 이벤트 윈도우 구간의 AR 합계</code></pre>
<p>
  정상 수익률은 발표 이전 <code>[-250, -30]</code> 거래일 구간으로 추정한 시장모델에서 구한다.
  발표 직전 30일을 제외하는 것은 그 구간이 이미 실적 기대감에 오염되어 있기 때문이다.
</p>

<div class="tablewrap">
<table>
  <caption>모델 선택</caption>
  <thead><tr><th>모델</th><th>적용 조건</th><th class="num">건수</th></tr></thead>
  <tbody>
    <tr><td>2팩터 시장모델 (시장 + 섹터)</td><td>추정 구간 60거래일 이상 확보</td><td class="num">174</td></tr>
    <tr><td>시장조정모델 (β = 1 고정)</td><td>상장 직후로 추정 구간 부족</td><td class="num">2</td></tr>
  </tbody>
</table>
</div>
<p class="tnote">
  모델 선택은 종목 단위가 아니라 <strong>이벤트 단위</strong>로 판정했다. 상장 이력이 짧은
  종목도 초기 몇 건만 구간이 부족하고 이후 이벤트는 정상 추정이 가능하기 때문이다.
  종목 전체를 폴백시키면 불필요하게 정보를 버리게 된다.
</p>

<div class="note">
  <div class="label">섹터 팩터 직교화</div>
  <p>
    섹터 지수는 유니버스 종목의 동일가중 수익률로 구성하되 <strong>대상 종목 자신은 제외</strong>했다.
    자기가 포함된 지수를 벤치마크로 쓰면 초과수익률이 축소되기 때문이다.
  </p>
  <p>
    그런데 이 섹터 지수는 시장 움직임을 이미 품고 있어, 시장 팩터와 함께 넣으면
    두 변수가 겹친다. 실제로 그대로 회귀했을 때 <strong>시장 베타가 0.22</strong>로
    비정상적으로 낮게 나왔다. 섹터를 시장에 회귀한 잔차만 사용하도록 바꾸자
    <strong>0.73</strong>으로 정상화됐다.
  </p>
</div>

<h3>변수</h3>
<div class="tablewrap">
<table>
  <caption>독립변수 6개</caption>
  <thead><tr><th>변수</th><th>정의</th><th>역할</th></tr></thead>
  <tbody>
    <tr><td>매출 YoY</td><td>전년 동분기 대비 매출 성장률</td><td>외형</td></tr>
    <tr><td>OPM 변화</td><td>영업이익률의 전년 동분기 대비 변화폭</td><td>수익성</td></tr>
    <tr><td>추세이탈도</td><td>(실제 영업이익 − 과거 4분기 추세 예측) ÷ 매출액</td><td>기대 대비 이탈</td></tr>
    <tr><td>발표 전 CAR</td><td>CAR[-20,-1]</td><td>통제 · 선반영</td></tr>
    <tr><td>로그 자산총계</td><td>동일 분기 자산총계의 자연로그</td><td>통제 · 규모</td></tr>
    <tr><td>잠정실적 더미</td><td>잠정실적으로 잡힌 이벤트 = 1</td><td>통제 · 정보 신선도</td></tr>
  </tbody>
</table>
</div>
<p class="tnote">
  흑자전환·적자전환 더미도 설계했으나 실제 표본에 사례가 1건 이하여서 제외했다.
  분석 대상 11종목이 4년 내내 흑자 기조였기 때문이다. VIF는 전부 1.4 미만으로
  다중공선성 문제는 없었다.
</p>

<h3>모형</h3>
<p>
  목적이 다른 두 방법을 함께 사용했다. <strong>OLS</strong>는 각 항목의 방향과 유의성을
  해석하기 위해, <strong>Lasso</strong>는 계수를 0으로 죽여가며 살아남는 항목을 가려내기
  위해 썼다. 같은 종목의 여러 분기 관측치는 서로 독립이 아니므로 OLS의 표준오차는
  종목 단위로 군집 보정했다.
</p>

<div class="note">
  <div class="label">부스팅을 쓰지 않은 이유</div>
  <p>
    트리 앙상블은 통상 변수당 관측치 50~100개를 요구한다. 특성 6개면 최소 400~800건이
    필요한데 표본은 155건이다. 게다가 주가 수익률은 신호 대비 잡음이 매우 커서
    이런 환경에서 부스팅은 신호 대신 노이즈를 학습한다.
    데이터에 맞지 않는 모델을 얹는 것보다 배제 근거를 남기는 편이 낫다고 판단했다.
  </p>
</div>
</section>

<section id="decisions">
<h2><span class="n">05</span>전처리에서 내린 판단</h2><div class="rule"></div>

<h3>컨센서스를 사용하지 않은 이유</h3>
<p>
  당초 설계는 증권사 추정치(컨센서스)와 실제 실적을 비교해 서프라이즈를 측정하는 것이었다.
  "기대보다 좋았나"를 정확히 재려면 그 값이 필요하다.
</p>
<p>
  그러나 무료로 조회 가능한 컨센서스는 <strong>현재 시점 기준으로 갱신된 값</strong>이다.
  "2023년 3분기 발표 직전에 시장이 기대한 값"은 어디에도 보존되어 있지 않다.
  이를 과거 이벤트에 결합하면 미래에 알게 된 정보로 과거를 설명하게 된다.
</p>

<div class="note">
  <div class="label">데이터 누수</div>
  <p>
    유료 데이터 단말은 추정치를 시점별로 아카이빙하므로 과거 임의 시점의 컨센서스를
    복원할 수 있다. 접근이 없는 상황에서 갱신값으로 대체하는 것은
    <strong>look-ahead bias</strong>를 만든다. 결과는 그럴듯하게 나오지만 재현되지 않는다.
    비용이 아니라 정합성 때문에 포기한 것이다.
  </p>
  <p>
    같은 원칙을 모델링 단계에도 적용했다. 시계열 데이터이므로 교차검증에 일반 K-fold 대신
    <code>TimeSeriesSplit</code>을 썼다. 무작위 분할은 미래 데이터로 과거를 예측하는
    누수가 된다.
  </p>
</div>

<p>대신 두 가지 대리변수를 직접 구성했다.</p>
<ul>
  <li><strong>추세이탈도</strong> — 과거 4분기 선형 추세로 기대치를 만들고 실제와의 편차를 매출액으로 정규화</li>
  <li><strong>발표 전 CAR</strong> — 발표 직전 20거래일 누적초과수익률. 시장이 미리 반영한 기대의 직접 측정치</li>
</ul>

<h3>영업이익 성장률을 특성에서 제외한 이유</h3>
<p>
  기저가 적자일 때 관행적인 전년 대비 성장률 공식은 <strong>증감 방향을 반대로 기록</strong>한다.
  분모가 음수이기 때문이다.
</p>

<div class="tablewrap">
<table>
  <caption>계산식별 기록값 비교</caption>
  <thead><tr>
    <th>사례</th><th>실제 의미</th>
    <th class="num">(t−t₄)/t₄</th><th class="num">(t−t₄)/|t₄|</th><th class="num">매출 대비</th>
  </tr></thead>
  <tbody>
    <tr><td>−10억 → −20억</td><td>악화</td>
        <td class="num" style="color:var(--neg)">+100%</td><td class="num">−100%</td><td class="num">−1.0%p</td></tr>
    <tr><td>−10억 → −5억</td><td>개선</td>
        <td class="num" style="color:var(--neg)">−50%</td><td class="num">+50%</td><td class="num">+0.5%p</td></tr>
    <tr><td>−0.1억 → +3억</td><td>흑자전환</td>
        <td class="num" style="color:var(--neg)">+3100%</td><td class="num" style="color:var(--neg)">+3100%</td><td class="num">+0.31%p</td></tr>
  </tbody>
</table>
</div>
<p class="tnote">
  절댓값 분모는 부호 역전만 해결하고, 기저가 0에 가까울 때의 값 폭발은 막지 못한다.
  이는 적자 문제가 아니라 분모가 작을 때 생기는 문제여서 흑자 구간에서도 발생한다.
</p>
<p>
  그래서 영업이익 변화를 <strong>매출 성장률 + 영업이익률 변화</strong>로 분해했다.
  매출은 음수가 될 수 없고 영업이익률은 비율의 차이라, 두 문제가 동시에 사라진다.
  부수적으로 해석도 선명해졌다. "외형이 커진 것인가, 마진이 좋아진 것인가"를
  분리해서 볼 수 있게 됐기 때문이다.
</p>

<h3>4분기 실적 산출과 검산</h3>
<p>
  DART는 1분기·반기·3분기·연간 보고서를 제공하고 <strong>4분기 단독 보고서는 없다.</strong>
  <code>연간 − 3분기 누계</code>로 역산해야 한다.
</p>
<p>
  역산은 틀려도 겉으로 드러나지 않으므로 전수 검산했다.
</p>
<pre><code>Q1 + Q2 + Q3 + Q4 == 연간

검산 대상 54개 종목·연도 → 불일치 0건</code></pre>
<p class="tnote">
  수집 과정에서 결측 1건(코스메카코리아 2025년 1분기 매출액)이 발견됐다. DART 측 계정 누락이었다.
  반기 누계에서 2분기 금액을 빼는 방식으로 복원했고, 이 값도 연간 검산을 통과했다.
  최종 분기 재무 패널 246행에 결측은 없다.
</p>
</section>

<section id="results">
<h2><span class="n">06</span>결과</h2><div class="rule"></div>

<h3>회귀 결과</h3>
<div class="tablewrap">
<table>
  <caption>OLS · 종속변수 CAR[0,+1] · 종목 군집 표준오차</caption>
  <thead><tr>
    <th>변수</th><th class="num">계수</th><th class="num">p값</th>
    <th class="num">1 표준편차 효과</th>
  </tr></thead>
  <tbody>
    <tr class="hi"><td>추세이탈도</td><td class="num">+0.576</td>
        <td class="num">0.0007 <span class="sig">***</span></td><td class="num">+3.1%p</td></tr>
    <tr class="hi"><td>매출 YoY</td><td class="num">+0.052</td>
        <td class="num">0.010 <span class="sig">**</span></td><td class="num">+1.8%p</td></tr>
    <tr><td>OPM 변화</td><td class="num">+0.227</td><td class="num dim">0.152</td><td class="num">+1.3%p</td></tr>
    <tr><td>로그 자산총계</td><td class="num">+0.004</td><td class="num dim">0.501</td><td class="num">+0.5%p</td></tr>
    <tr><td>잠정실적 더미</td><td class="num">−0.002</td><td class="num dim">0.866</td><td class="num">−0.1%p</td></tr>
    <tr><td>발표 전 CAR</td><td class="num">−0.012</td><td class="num dim">0.832</td><td class="num">−0.1%p</td></tr>
  </tbody>
</table>
</div>
<p class="tnote">n = 155 · R² = 0.146 · adj R² = 0.111 · *** p&lt;0.01, ** p&lt;0.05</p>

<figure>
  <img src="{data_uri('fig1_effects.png')}" alt="항목별 효과 크기. 추세 대비 이탈이 +3.1%p로 가장 크고, 매출 성장률이 +1.8%p로 뒤를 잇는다. 나머지 네 항목은 신뢰구간이 0을 포함한다.">
  <figcaption><b>그림 1</b>단위가 다른 항목을 비교할 수 있도록 각 변수의 표준편차를 곱해
  같은 잣대로 환산했다. 가로선은 95% 신뢰구간이며, 0을 걸치지 않는 두 항목만 유의하다.</figcaption>
</figure>

<p>
  추세이탈도의 계수 0.576은 이 지표가 1 표준편차(5.45%p) 커질 때 CAR이 약 3.1%p
  상승한다는 의미다. 매출 성장률의 1 표준편차 효과(+1.8%p)보다 크다.
  <strong>컨센서스를 대체하기 위해 만든 변수가 실제로 가장 강하게 작동했다.</strong>
</p>

<h3>발표일에 갈라진다</h3>
<figure>
  <img src="{data_uri('fig2_car_path.png')}" alt="서프라이즈 3분위 그룹별 누적초과수익률 궤적. 발표 20일 전까지 세 그룹이 붙어 있다가 발표일에 급격히 갈라져 상위 +5.9%, 하위 −4.8%로 벌어지고 이후 유지된다.">
  <figcaption><b>그림 2</b>추세이탈도 3분위 그룹의 평균 누적초과수익률.
  발표 전까지 세 그룹이 붙어 있다가 발표일에 갈라지고, 이후 되돌아오지 않는다.</figcaption>
</figure>

<p>
  이 그림이 결과 중 가장 설득력이 크다. 갈라지는 시점이 발표 <em>직전</em>이 아니라
  발표 <em>당일</em>이라는 점이 중요하다. 사전 유출이나 선반영이 아니라
  발표 그 자체가 정보를 전달했다는 뜻이기 때문이다.
  벌어진 격차가 이후 20거래일 동안 좁혀지지 않는다는 점도 일시적 과잉반응이 아님을 시사한다.
</p>

<h3>항목마다 반영 속도가 다르다</h3>
<figure>
  <img src="{data_uri('fig4_windows.png')}" alt="이벤트 윈도우를 늘려가며 본 계수 변화. 매출 성장률은 +1.8%p에서 +3.5%p로 커지고, 영업이익률 변화는 0 근처에 머물다 음수로 내려간다. 추세이탈도는 계속 크게 유지된다.">
  <figcaption><b>그림 4</b>윈도우별 1 표준편차 효과. 음영은 95% 신뢰구간이며,
  0선을 걸치면 통계적으로 유의하지 않다.</figcaption>
</figure>

<p>
  매출 성장률은 윈도우를 늘릴수록 계수가 커진다(+1.8%p → +3.5%p).
  실적 발표 후 표류(post-earnings announcement drift) 패턴과 일치한다.
  영업이익률 변화는 어느 윈도우에서도 신뢰구간이 0을 걸쳐, 즉각적이든 지연되든
  뚜렷한 반응을 확인하기 어려웠다.
</p>

<h3>강건성</h3>
<div class="tablewrap">
<table>
  <caption>설정을 바꿔가며 본 계수</caption>
  <thead><tr>
    <th>변수</th><th class="num">기본</th><th class="num">윈저라이징</th>
    <th class="num">실리콘투 제외</th><th class="num">달바 제외</th>
    <th class="num">CAR[0,+5]</th><th class="num">CAR[0,+20]</th>
  </tr></thead>
  <tbody>
    <tr class="hi"><td>추세이탈도</td>
      <td class="num">+0.576<span class="sig">***</span></td>
      <td class="num">+0.544<span class="sig">***</span></td>
      <td class="num">+0.493<span class="sig">***</span></td>
      <td class="num">+0.545<span class="sig">***</span></td>
      <td class="num">+0.705<span class="sig">***</span></td>
      <td class="num">+0.840<span class="sig">**</span></td></tr>
    <tr><td>매출 YoY</td>
      <td class="num">+0.052<span class="sig">**</span></td>
      <td class="num">+0.042<span class="sig">***</span></td>
      <td class="num">+0.032<span class="sig">*</span></td>
      <td class="num">+0.052<span class="sig">**</span></td>
      <td class="num dim">+0.035</td>
      <td class="num">+0.099<span class="sig">***</span></td></tr>
    <tr><td>OPM 변화</td>
      <td class="num dim">+0.227</td><td class="num dim">+0.231</td>
      <td class="num dim">+0.255</td><td class="num dim">+0.237</td>
      <td class="num">+0.275<span class="sig">**</span></td>
      <td class="num dim">−0.110</td></tr>
  </tbody>
</table>
</div>
<p class="tnote">
  추세이탈도는 모든 설정에서 유의하게 유지된다. CAR 변동성이 가장 큰 실리콘투
  (표준편차 20.5%, 2위와 격차가 크다)를 제외해도 결과가 바뀌지 않는다.
</p>

<h3>Lasso 변수 선택</h3>
<pre><code>CAR[0,+1]    추세이탈도 (0.024) &gt; 매출YoY (0.012) &gt; OPM변화 (0.008)
CAR[0,+5]    추세이탈도
CAR[0,+20]   추세이탈도</code></pre>
<p>
  선반영·규모·정보출처 통제변수는 모든 윈도우에서 계수가 0으로 축소됐다.
  해석을 목적으로 한 OLS와 변수 선택을 목적으로 한 Lasso가 같은 결론에 도달했다.
</p>

<h3>원자료 검증</h3>
<p>
  계산된 CAR을 원본 종가로 되짚어 확인했다. 극단값은 버그가 아니라 전부 실제 거래였다.
</p>
<pre><code>실리콘투 2024Q1   t0 +29.82% → t+1 +29.95%  (상한가 2연속)
                  CAR[0,+1] = +48.06%</code></pre>
<p>
  이 과정에서 부수적으로 확인된 사실이 있다. <strong>실적 발표일의 주가 변동성은
  평상시의 2.03배</strong>였다(일간 수익률 표준편차 3.46% → 발표일 7.01%).
  CAR 표준편차가 11.1%로 큰 이유도 여기서 설명된다.
</p>

<figure>
  <img src="{data_uri('fig3_scatter.png')}" alt="추세이탈도와 CAR의 산점도. 우상향 관계가 보이지만 흩어짐도 크다. 상관계수 0.30.">
  <figcaption><b>그림 3</b>가장 강한 관계를 원자료로 확인한 것.
  우상향 경향이 보이는 동시에 흩어짐도 크다는 점이 R² 0.146과 일관된다.</figcaption>
</figure>

<h3>예상이 빗나간 것</h3>
<p>
  <strong>선반영 가설은 지지되지 않았다.</strong> 발표 전에 오른 종목은 기대가 이미
  반영되어 발표 후 반응이 작을 것으로 예상했으나, 계수 −0.012, p = 0.83으로
  사실상 관계가 없었다.
</p>
<p>
  <strong>적자 기저 대비 설계는 이 표본에서 발동하지 않았다.</strong> 흑자전환 1건,
  적자전환 0건으로 전환 더미를 제외했다. 다만 영업이익 성장률을 분해한 설계 자체는
  유효했으며, 종목 범위를 넓히면 필요해진다.
</p>
</section>

<section id="limits">
<h2><span class="n">07</span>한계</h2><div class="rule"></div>
<ol>
  <li>컨센서스 부재로 실적을 예상된 부분과 놀라운 부분으로 분해할 수 없어 <strong>계수가 과소추정</strong>될 수 있다. 시장이 이미 예상한 성장분이 독립변수에 그대로 포함되기 때문이다.</li>
  <li>표본 155건으로 통계적 검정력이 제한적이다. 효과가 실제로 존재해도 유의하게 잡히지 않을 수 있다.</li>
  <li>단일 섹터 분석이므로 다른 섹터로 일반화할 수 없다.</li>
  <li>OpenDART가 접수 시각을 제공하지 않아 장중·장후 발표를 구분하지 못했다. CAR[0,+1] 윈도우가 이 차이를 상당 부분 흡수하도록 설계했으나 완전하지는 않다.</li>
  <li>규모 통제변수가 시가총액이 아닌 장부상 자산총계다. 이벤트 시점 시가총액을 무료로 확보할 수 없었다.</li>
  <li>일부 종목은 화장품 외 잔여 사업을 보유한다(한국콜마의 제약 CMO 등).</li>
  <li>상장 이력이 짧은 2건은 다른 모델(시장조정)로 산출됐다.</li>
</ol>
</section>

<section id="conclusion">
<h2><span class="n">08</span>결론</h2><div class="rule"></div>
<p>
  화장품 섹터 11종목의 분기 실적 발표 155건을 분석한 결과,
  <strong>발표 직후 주가 반응과 가장 강하게 연결된 항목은 기대 대비 이탈이었다.</strong>
  매출 성장률이 그다음이었고, 영업이익률 변화는 뚜렷한 반응을 확인하기 어려웠다.
  선반영·기업 규모·정보 신선도는 효과가 관찰되지 않았다.
</p>
<p>
  실무적으로는 실적의 절대 수준보다 <strong>기존 추세에서 얼마나 벗어났는지</strong>를
  보는 것이 주가 반응을 이해하는 데 더 유용하다는 뜻이 된다.
  증권사 추정치가 없어도 과거 실적 흐름만으로 그 기대치를 근사할 수 있고,
  그렇게 만든 지표가 실제로 작동했다.
</p>
<p>
  방법론적으로 이 분석의 중심은 모델이 아니라 <strong>시점 정합성</strong>이었다.
  컨센서스를 배제한 것도, 교차검증에 시계열 분할을 쓴 것도, 4분기 역산을 전수 검산한 것도
  같은 원칙에서 나왔다. 그 시점에 알 수 없었던 정보가 섞이지 않게 하는 일이
  전체 작업의 대부분을 차지했다.
</p>

<h3>확장 방향</h3>
<div class="tablewrap">
<table>
  <thead><tr><th>단계</th><th>범위</th><th class="num">이벤트</th><th>추가 분석</th></tr></thead>
  <tbody>
    <tr class="hi"><td>현재</td><td>화장품 11종목 × 4년</td><td class="num">155</td><td>OLS + Lasso</td></tr>
    <tr><td>확장 1</td><td>K뷰티 20종목+ × 4년</td><td class="num">약 320</td><td>사업 유형별 상호작용, 섹터 정의 민감도</td></tr>
    <tr><td>확장 2</td><td>코스피200 × 10년</td><td class="num">약 8,000</td><td>부스팅 적용 가능 규모</td></tr>
  </tbody>
</table>
</div>
<p class="tnote">
  두 확장의 축은 다르다. 확장 1은 <em>정의</em>를 넓혀 분석 질문을 심화하는 것이고,
  확장 2는 <em>규모</em>를 키워 모델 복잡도를 확보하는 것이다.
</p>
</section>

<footer>
  <p>
    화장품 섹터 실적 발표와 주가 반응 분석 · 2026-08-21 ·
    데이터 출처 DART OpenAPI, FinanceDataReader ·
    분석 코드와 전체 설계 기록은 저장소의 <code>docs/design-log.md</code>에 있다.
  </p>
</footer>

</main>
</div>
"""


if __name__ == "__main__":
    out = ROOT / "report.html"
    out.write_text(build(), encoding="utf-8")
    print(f"저장: {out}  ({out.stat().st_size / 1024:,.0f} KB)")
