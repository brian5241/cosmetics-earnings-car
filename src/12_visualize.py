"""
12. 결과 시각화
===============
분석 결과를 네 장의 그림으로 정리한다.

  fig1  항목별 효과 크기      — 어떤 항목이 얼마나 관련 있나 (핵심 결과)
  fig2  평균 CAR 경로        — 서프라이즈 상위/하위 그룹의 주가 궤적
  fig3  추세이탈도 vs CAR    — 가장 강한 관계를 원자료로 확인
  fig4  윈도우별 계수 변화    — 즉시 반영 vs 지연 반영

실행:  python src/12_visualize.py
출력:  figures/*.png
"""

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import DATA_DIR, ROOT

FIG_DIR = ROOT / "figures"
FIG_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------
# 색과 서체
# 색은 역할에 따라 고른다. 순서를 돌려쓰지 않는다.
#   파랑/빨강 = 발산형 양극 (좋은 서프라이즈 / 나쁜 서프라이즈)
#   파랑·주황·청록 = 범주형 1~3번 슬롯
# ---------------------------------------------------------------
BLUE, ORANGE, AQUA, RED = "#2a78d6", "#eb6834", "#1baf7a", "#e34948"
SURFACE = "#fcfcfb"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE = "#e1e0d9", "#c3c2b7"

mpl.rcParams.update({
    "font.family": "Malgun Gothic",   # 윈도우 한글 서체
    "axes.unicode_minus": False,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "text.color": INK,
    "axes.labelcolor": INK2,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.edgecolor": BASELINE,
    "font.size": 11,
})

FEATURE_LABELS = {
    "추세이탈도": "추세 대비 이탈\n(서프라이즈)",
    "매출YoY": "매출 성장률\n(전년 대비)",
    "OPM변화": "영업이익률 변화",
    "CAR_PRE": "발표 전 주가\n(선반영)",
    "로그자산": "기업 규모",
    "잠정실적더미": "잠정실적 여부",
}


def style_axes(ax, xgrid=False):
    """공통 축 스타일. 격자와 축은 뒤로 물린다."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(BASELINE)
        ax.spines[side].set_linewidth(1)
    ax.grid(axis="x" if xgrid else "y", color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)


def add_title(ax, title, subtitle):
    """제목과 부제를 축 위쪽에 겹치지 않게 배치한다.

    ax.set_title 과 fig.text 를 섞으면 좌표계가 달라 겹친다.
    둘 다 축 좌표계(transAxes)로 두고 높이를 명시한다.
    """
    ax.text(0, 1.15, title, transform=ax.transAxes, fontsize=15,
            fontweight="bold", color=INK, va="bottom", ha="left")
    ax.text(0, 1.04, subtitle, transform=ax.transAxes, fontsize=10,
            color=INK2, va="bottom", ha="left")


def finish(fig, name):
    fig.tight_layout()
    fig.subplots_adjust(top=0.82)
    fig.savefig(FIG_DIR / name, dpi=160)
    plt.close(fig)
    print(f"  {name}")


# ===============================================================
# fig1 — 항목별 효과 크기
# ===============================================================
def fig1_effects(df, ols):
    """1 표준편차 변화가 CAR을 몇 %p 움직이는지.

    원래 계수는 변수마다 단위가 달라 크기를 직접 비교할 수 없다.
    각 변수의 표준편차를 곱해 '같은 잣대'로 바꾼다.
    """
    base = ols[(ols["모형"] == "기본") & (ols["변수"] != "const")].copy()
    sds = df[base["변수"]].std()

    base["효과"] = base["계수"].values * sds[base["변수"]].values * 100
    base["오차"] = base["표준오차"].values * sds[base["변수"]].values * 100 * 1.96
    base["유의함"] = base["p값"] < 0.05
    base = base.sort_values("효과")

    fig, ax = plt.subplots(figsize=(9.4, 5.2))
    y = np.arange(len(base))

    # 값 라벨은 한 열로 정렬한다. 막대 끝에 붙이면 선과 겹친다.
    label_x = (base["효과"] + base["오차"]).max() + 0.45

    for i, (_, r) in enumerate(base.iterrows()):
        color = BLUE if r["유의함"] else MUTED
        ax.plot([r["효과"] - r["오차"], r["효과"] + r["오차"]], [i, i],
                color=color, linewidth=2, solid_capstyle="round",
                alpha=1.0 if r["유의함"] else 0.55, zorder=3)
        ax.scatter(r["효과"], i, s=90, color=color, zorder=4,
                   edgecolor=SURFACE, linewidth=2)
        # 값을 직접 붙인다 (색만으로 의미를 전달하지 않기 위해서이기도 하다)
        ax.text(label_x, i, f"{r['효과']:+.1f}%p",
                va="center", ha="left",
                color=INK if r["유의함"] else MUTED, fontsize=10,
                fontweight="bold" if r["유의함"] else "normal")
        if r["유의함"]:
            ax.text(label_x + 1.5, i, "유의", va="center", ha="left",
                    color=BLUE, fontsize=10, fontweight="bold")

    ax.axvline(0, color=BASELINE, linewidth=1.5, zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels([FEATURE_LABELS[v] for v in base["변수"]], fontsize=10)
    ax.set_xlabel("1 표준편차 변화가 만드는 CAR[0,+1] 변화 (%p)", fontsize=10)
    ax.set_xlim(-2.2, label_x + 2.4)
    style_axes(ax, xgrid=True)

    add_title(ax, "실적 항목별 주가 반응 크기",
              "가로선은 95% 신뢰구간 · 파란색은 통계적으로 유의(p<0.05)")
    finish(fig, "fig1_effects.png")


# ===============================================================
# fig2 — 평균 CAR 경로
# ===============================================================
def load_ar_paths(df):
    """08단계가 저장한 이벤트별 AR 경로(t-20 ~ t+20)를 불러온다.

    직교화 계수를 다시 만들 필요가 없도록 계산 단계에서 미리 남겨두었다.
    구간에 결측이 하나라도 있으면 평균 궤적을 왜곡하므로 제외한다.
    """
    raw = pd.read_csv(DATA_DIR / "ar_paths.csv").set_index("이벤트키")
    raw.columns = raw.columns.astype(int)
    raw = raw.dropna()

    keys = df.set_index("이벤트키").index
    common = [k for k in keys if k in raw.index]
    paths = raw.loc[common]
    paths.index = df.set_index("이벤트키").loc[common].index
    return paths


def fig2_car_path(df):
    paths = load_ar_paths(df)
    d = df.set_index("이벤트키").loc[paths.index].copy()

    # 서프라이즈 3분위. 순서가 있는 구분이므로 발산형(음/양)으로 색을 준다.
    d["그룹"] = pd.qcut(d["추세이탈도"], 3,
                      labels=["하위 (부정적)", "중위", "상위 (긍정적)"])

    fig, ax = plt.subplots(figsize=(9, 5.4))
    x = paths.columns.to_numpy()

    spec = [("상위 (긍정적)", BLUE, 2.4), ("중위", MUTED, 1.8),
            ("하위 (부정적)", RED, 2.4)]
    for name, color, lw in spec:
        idx = d.index[d["그룹"] == name]
        car = paths.loc[idx].mean(axis=0).cumsum() * 100
        ax.plot(x, car, color=color, linewidth=lw, zorder=3,
                solid_capstyle="round", label=f"{name}  (n={len(idx)})")
        # 선 끝에 직접 라벨
        ax.text(x[-1] + 0.6, car.iloc[-1], f"{car.iloc[-1]:+.1f}%",
                color=color, fontsize=10, fontweight="bold", va="center")

    ax.axvline(0, color=BASELINE, linewidth=1.5, zorder=2)
    ax.axhline(0, color=BASELINE, linewidth=1, zorder=2)
    ax.text(0.4, ax.get_ylim()[1] * 0.94, "발표일", color=INK2, fontsize=10)

    ax.set_xlabel("발표일 기준 거래일", fontsize=10)
    ax.set_ylabel("누적초과수익률 (%)", fontsize=10)
    ax.set_xlim(-20, 26)
    style_axes(ax)
    ax.legend(loc="upper left", frameon=False, fontsize=10,
              labelcolor=INK2)

    add_title(ax, "서프라이즈 크기별 주가 궤적",
              "추세 대비 이탈도 3분위 그룹의 평균 누적초과수익률")
    finish(fig, "fig2_car_path.png")


# ===============================================================
# fig3 — 산점도
# ===============================================================
def fig3_scatter(df):
    x = df["추세이탈도"] * 100
    y = df["CAR_0_1"] * 100

    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    ax.scatter(x, y, s=46, color=BLUE, alpha=0.55,
               edgecolor=SURFACE, linewidth=1.2, zorder=3)

    b, a = np.polyfit(x, y, 1)
    xs = np.linspace(x.min(), x.max(), 100)
    ax.plot(xs, a + b * xs, color=INK, linewidth=2, zorder=4)

    r = np.corrcoef(x, y)[0, 1]
    ax.text(0.975, 0.06, f"상관계수  r = {r:.2f}\n기울기  {b:.2f}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=11, color=INK2)

    ax.axhline(0, color=BASELINE, linewidth=1, zorder=2)
    ax.axvline(0, color=BASELINE, linewidth=1, zorder=2)
    ax.set_xlabel("추세 대비 영업이익 이탈도 (매출 대비 %p)", fontsize=10)
    ax.set_ylabel("CAR[0,+1] (%)", fontsize=10)
    style_axes(ax)

    add_title(ax, "기대를 벗어난 정도와 주가 반응",
              f"화장품 11종목 · 분기 실적 발표 {len(df)}건")
    finish(fig, "fig3_scatter.png")


# ===============================================================
# fig4 — 윈도우별 계수
# ===============================================================
def fig4_windows(df, ols):
    windows = {"기본": "[0,+1]", "윈도우_0_5": "[0,+5]", "윈도우0_20": "[0,+20]"}
    targets = ["추세이탈도", "매출YoY", "OPM변화"]
    colors = {"추세이탈도": BLUE, "매출YoY": ORANGE, "OPM변화": AQUA}

    sds = df[targets].std()

    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    xpos = np.arange(len(windows))

    for var in targets:
        vals, errs = [], []
        for m in windows:
            row = ols[(ols["모형"] == m) & (ols["변수"] == var)]
            vals.append(row["계수"].iloc[0] * sds[var] * 100)
            errs.append(row["표준오차"].iloc[0] * sds[var] * 100 * 1.96)
        ax.plot(xpos, vals, color=colors[var], linewidth=2.4, marker="o",
                markersize=9, markeredgecolor=SURFACE, markeredgewidth=2,
                zorder=3, label=FEATURE_LABELS[var].replace("\n", " "))
        ax.fill_between(xpos, np.array(vals) - np.array(errs),
                        np.array(vals) + np.array(errs),
                        color=colors[var], alpha=0.12, zorder=1)
        ax.text(xpos[-1] + 0.08, vals[-1], f"{vals[-1]:+.1f}%p",
                color=colors[var], fontsize=10, fontweight="bold", va="center")

    ax.axhline(0, color=BASELINE, linewidth=1.5, zorder=2)
    ax.set_xticks(xpos)
    ax.set_xticklabels(windows.values())
    ax.set_xlim(-0.25, 2.5)
    ax.set_xlabel("이벤트 윈도우 (거래일)", fontsize=10)
    ax.set_ylabel("1 표준편차 효과 (%p)", fontsize=10)
    style_axes(ax)
    ax.legend(loc="upper left", frameon=False, fontsize=10, labelcolor=INK2)

    add_title(ax, "반영 속도의 차이",
              "음영은 95% 신뢰구간 · 0선을 걸치면 통계적으로 유의하지 않음")
    finish(fig, "fig4_windows.png")


def main():
    df = pd.read_csv(DATA_DIR / "dataset.csv", dtype={"종목코드": str},
                     parse_dates=["발표일", "거래일t0"])
    df = df[df["분석표본"]].reset_index(drop=True)
    ols = pd.read_csv(DATA_DIR / "results_ols.csv")

    print(f"표본 {len(df)}건으로 그림 생성")
    fig1_effects(df, ols)
    fig2_car_path(df)
    fig3_scatter(df)
    fig4_windows(df, ols)
    print(f"\n저장 위치: {FIG_DIR}")


if __name__ == "__main__":
    main()
