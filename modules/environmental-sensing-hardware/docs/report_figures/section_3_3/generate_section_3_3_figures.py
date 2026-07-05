#!/usr/bin/env python3
"""Generate Section 3.3 report-quality figures.

Figures:
    图3-10 预测误差关键指标图
    图3-11 任务总能耗与剩余电量对比图
    图3-12 沿航程累计能耗与剩余电量变化图
    图3-13 规划航线预计飞行时长与预测可持续飞行时长对照图
    图3-14 不同输入特征方案的预测误差对比图

Outputs are written as high-resolution PNG plus SVG/PDF vector files.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"


COLORS = {
    "blue": "#1F77B4",
    "deep_blue": "#174A7E",
    "cyan": "#17A2B8",
    "orange": "#F28E2B",
    "red": "#D94841",
    "green": "#2E7D32",
    "gray": "#6B7280",
    "light_gray": "#F3F6FA",
    "grid": "#D8DEE9",
    "text": "#1F2937",
    "muted": "#4B5563",
    "risk_fill": "#FDEDEC",
    "note_fill": "#F7FAFC",
    "conclusion_fill": "#FFF7ED",
}


FONT_CANDIDATES = [
    "Noto Sans CJK SC",
    "Noto Sans CJK JP",
    "Source Han Sans SC",
    "Microsoft YaHei",
    "SimHei",
    "WenQuanYi Zen Hei",
    "Arial Unicode MS",
    "DejaVu Sans",
]

FONT_FILE_CANDIDATES = [
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
]


FIGURE_DPI = 300
FIGSIZE = (12.8, 8.0)


FIGURES = {
    "fig3_10": {
        "caption": "图3-10 预测误差关键指标图",
        "caption_note": "该图展示模型验证集误差水平，用于支撑预测可信度与航线能耗排序应用。",
    },
    "fig3_11": {
        "caption": "图3-11 任务总能耗与剩余电量对比图",
        "caption_note": "该图展示典型压力任务下预测能耗显著超过电池容量，系统应提前判定任务不可直接执行。",
    },
    "fig3_12": {
        "caption": "图3-12 沿航程累计能耗与剩余电量变化图",
        "caption_note": "该图定位电量耗尽首次出现的位置，用于说明任务不可达并辅助返航阈值设置。",
    },
    "fig3_13": {
        "caption": "图3-13 规划航线预计飞行时长与预测可持续飞行时长对照图",
        "caption_note": "该图区分规划航线所需飞行时间与当前条件下可持续飞行时间，避免与算法运行耗时混淆。",
    },
    "fig3_14": {
        "caption": "图3-14 不同输入特征方案的预测误差对比图",
        "caption_note": "该图比较不同输入特征组合的误差表现，突出板端风场采集对能耗波动刻画的工程价值。",
    },
}


def pick_font() -> str:
    """Return the first available Chinese-capable font."""
    for font_file in FONT_FILE_CANDIDATES:
        if font_file.exists():
            fm.fontManager.addfont(str(font_file))
            return fm.FontProperties(fname=str(font_file)).get_name()

    available = {f.name for f in fm.fontManager.ttflist}
    for font_name in FONT_CANDIDATES:
        if font_name in available:
            return font_name
    return "DejaVu Sans"


def configure_style() -> None:
    font_name = pick_font()
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [font_name, "DejaVu Sans"],
            "axes.unicode_minus": False,
            "figure.dpi": FIGURE_DPI,
            "savefig.dpi": FIGURE_DPI,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.edgecolor": "#9AA4B2",
            "axes.labelcolor": COLORS["text"],
            "xtick.color": COLORS["text"],
            "ytick.color": COLORS["text"],
            "text.color": COLORS["text"],
        }
    )


def setup_figure(title: str, subtitle: str) -> tuple[plt.Figure, plt.Axes]:
    fig = plt.figure(figsize=FIGSIZE, facecolor="white")
    ax = fig.add_axes([0.08, 0.22, 0.70, 0.58])
    fig.text(0.08, 0.925, title, fontsize=22, fontweight="bold", color=COLORS["text"])
    fig.text(0.08, 0.885, subtitle, fontsize=13.5, color=COLORS["muted"])
    return fig, ax


def style_axis(ax: plt.Axes, y_grid: bool = True) -> None:
    ax.set_facecolor("white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#A8B0BB")
    ax.spines["bottom"].set_color("#A8B0BB")
    if y_grid:
        ax.grid(axis="y", color=COLORS["grid"], linestyle="-", linewidth=0.9, alpha=0.8)
        ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=11)


def add_text_box(
    fig: plt.Figure,
    x: float,
    y: float,
    text: str,
    title: str | None = None,
    width: float | None = None,
    fill: str = "#F7FAFC",
    edge: str = "#C7D2E0",
    color: str = "#1F2937",
    fontsize: float = 10.2,
) -> None:
    content = f"{title}\n{text}" if title else text
    fig.text(
        x,
        y,
        content,
        ha="left",
        va="top",
        fontsize=fontsize,
        color=color,
        linespacing=1.55,
        bbox={
            "boxstyle": "round,pad=0.55,rounding_size=0.08",
            "facecolor": fill,
            "edgecolor": edge,
            "linewidth": 1.0,
        },
        wrap=True,
    )


def add_caption(fig: plt.Figure, key: str) -> None:
    meta = FIGURES[key]
    fig.text(
        0.5,
        0.095,
        meta["caption"],
        ha="center",
        va="center",
        fontsize=13.2,
        fontweight="bold",
        color=COLORS["text"],
    )
    fig.text(
        0.5,
        0.055,
        meta["caption_note"],
        ha="center",
        va="center",
        fontsize=10.5,
        color=COLORS["muted"],
    )


def save_figure(fig: plt.Figure, stem: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ["png", "svg", "pdf"]:
        fig.savefig(OUTPUT_DIR / f"{stem}.{suffix}", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def annotate_bars(
    ax: plt.Axes,
    bars,
    unit: str = "",
    fmt: str = "{:.2f}",
    dy: float = 0.02,
    color: str = COLORS["text"],
) -> None:
    ymax = ax.get_ylim()[1]
    for bar in bars:
        value = bar.get_height()
        label = f"{fmt.format(value)}{unit}"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + ymax * dy,
            label,
            ha="center",
            va="bottom",
            fontsize=10.5,
            fontweight="bold",
            color=color,
        )


def draw_fig3_10() -> None:
    df = pd.DataFrame(
        {
            "指标": ["段级 MAE", "段级 RMSE", "段级 P90", "航次平均绝对误差", "航次 P90 绝对误差"],
            "误差值": [0.46, 0.59, 0.86, 0.56, 1.02],
            "层级": ["段级指标", "段级指标", "段级指标", "航次级指标", "航次级指标"],
        }
    )

    fig, ax = setup_figure(
        "预测误差关键指标图",
        "验证集段级与航次级误差指标对比，反映模型平均精度、稳定性与高分位风险。",
    )
    style_axis(ax)

    x = np.arange(len(df))
    bar_colors = [COLORS["blue"] if level == "段级指标" else COLORS["cyan"] for level in df["层级"]]
    bars = ax.bar(x, df["误差值"], width=0.58, color=bar_colors, edgecolor="white", linewidth=1.2)
    ax.set_xticks(x)
    ax.set_xticklabels(df["指标"], rotation=0, ha="center")
    ax.set_ylabel("误差值（Wh）", fontsize=12.5, fontweight="bold")
    ax.set_xlabel("预测误差指标", fontsize=12.5, fontweight="bold", labelpad=12)
    ax.set_ylim(0, 1.22)
    annotate_bars(ax, bars, unit=" Wh", fmt="{:.2f}", dy=0.018)

    handles = [
        plt.Rectangle((0, 0), 1, 1, color=COLORS["blue"], label="段级指标"),
        plt.Rectangle((0, 0), 1, 1, color=COLORS["cyan"], label="航次级指标"),
    ]
    ax.legend(handles=handles, loc="upper left", frameon=False, fontsize=11)

    add_text_box(
        fig,
        0.805,
        0.79,
        "该图用于评估能耗预测模型在验证集上的精度表现，适用于说明“模型是否可靠”。\n\n应用：竞赛答辩、模型性能展示、任务前预测可信度说明。",
        title="场景说明",
        fill=COLORS["note_fill"],
    )
    add_text_box(
        fig,
        0.805,
        0.51,
        "MAE 反映平均误差水平；RMSE 对较大误差更敏感；P90 反映高分位误差，体现模型稳定性与鲁棒性。",
        title="指标说明",
        fill="#EEF8FB",
        edge="#B8DDE8",
    )
    add_text_box(
        fig,
        0.805,
        0.30,
        "误差整体处于较低水平，适合用于候选航线能耗排序与风险提示。",
        title="结论摘要",
        fill=COLORS["conclusion_fill"],
        edge="#FDBA74",
    )
    add_caption(fig, "fig3_10")
    save_figure(fig, "fig3_10_prediction_error_metrics")


def draw_fig3_11() -> None:
    labels = ["电池容量", "预测总能耗", "终点剩余电量"]
    values = [130.0, 820.1, 0.0]
    colors = [COLORS["blue"], COLORS["red"], COLORS["gray"]]
    ratio = values[1] / values[0]

    fig, ax = setup_figure(
        "任务总能耗与剩余电量对比图",
        "典型压力任务下，预测总能耗与电池容量、终点剩余电量的直接对照。",
    )
    style_axis(ax)

    y = np.arange(len(labels))
    bars = ax.barh(y, values, color=colors, edgecolor="white", linewidth=1.2, height=0.55)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=12)
    ax.invert_yaxis()
    ax.set_xlabel("能量（Wh）", fontsize=12.5, fontweight="bold")
    ax.set_ylabel("任务能量指标", fontsize=12.5, fontweight="bold")
    ax.set_xlim(0, 900)
    ax.axvline(values[0], color=COLORS["blue"], linestyle="--", linewidth=1.4, alpha=0.8)
    ax.text(values[0] + 8, -0.43, "电池容量阈值 130.0 Wh", fontsize=10.5, color=COLORS["blue"])

    for bar, value in zip(bars, values):
        ax.text(
            max(value + 14, 14),
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f} Wh",
            va="center",
            ha="left",
            fontsize=11,
            fontweight="bold",
            color=COLORS["text"],
        )

    ax.annotate(
        f"预测总能耗约为电池容量的 {ratio:.2f} 倍",
        xy=(values[1], 1),
        xytext=(430, 1.55),
        arrowprops={"arrowstyle": "->", "color": COLORS["red"], "lw": 1.4},
        fontsize=12,
        fontweight="bold",
        color=COLORS["red"],
        bbox={"boxstyle": "round,pad=0.35", "fc": "#FFF1F0", "ec": "#FCA5A5"},
    )

    add_text_box(
        fig,
        0.805,
        0.79,
        "本图对应“典型压力任务场景”，用于展示复杂城市低空任务中路线过长或风场不利时，系统如何提前识别“电量不足”。\n\n应用：任务前可行性评估、风险告警说明。",
        title="场景说明",
        fill=COLORS["note_fill"],
    )
    add_text_box(
        fig,
        0.805,
        0.47,
        "当前任务明显超出电池约束，应判定为“不可直接执行”。建议缩短航线、降低载荷、更换电池或重新规划。",
        title="结论摘要",
        fill="#FFF1F0",
        edge="#FCA5A5",
        color="#991B1B",
    )
    add_caption(fig, "fig3_11")
    save_figure(fig, "fig3_11_energy_vs_battery")


def build_route_profile() -> pd.DataFrame:
    distance = np.linspace(0.0, 25.0, 26)
    # Smooth monotonic trend data constructed from the reported battery and total energy constraints.
    # The curve reaches the 130 Wh battery limit exactly at 4 km, then continues to
    # show the planned route's energy demand for "unreachable-task" explanation only.
    cumulative = np.empty_like(distance)
    before_limit = distance <= 4.0
    cumulative[before_limit] = 130.0 * (distance[before_limit] / 4.0) ** 1.03
    cumulative[~before_limit] = 130.0 + (820.1 - 130.0) * (
        (distance[~before_limit] - 4.0) / (distance.max() - 4.0)
    ) ** 1.08
    remaining = np.maximum(130.0 - cumulative, 0.0)
    return pd.DataFrame({"距离_km": distance, "累计能耗_Wh": cumulative, "剩余电量_Wh": remaining})


def draw_fig3_12() -> None:
    profile = build_route_profile()
    sustainable_distance = 4.0

    fig = plt.figure(figsize=FIGSIZE, facecolor="white")
    ax = fig.add_axes([0.08, 0.22, 0.67, 0.58])
    fig.text(0.08, 0.925, "沿航程累计能耗与剩余电量变化图", fontsize=22, fontweight="bold", color=COLORS["text"])
    fig.text(
        0.08,
        0.885,
        "双纵轴展示规划航程能量需求与电池可用余额，明确风险首次出现的位置。",
        fontsize=13.5,
        color=COLORS["muted"],
    )
    style_axis(ax)
    ax2 = ax.twinx()
    ax2.spines["top"].set_visible(False)
    ax2.spines["left"].set_visible(False)
    ax2.spines["right"].set_color("#A8B0BB")
    ax2.tick_params(axis="y", labelsize=11, colors=COLORS["orange"])

    cumulative_line = ax.plot(
        profile["距离_km"],
        profile["累计能耗_Wh"],
        color=COLORS["deep_blue"],
        marker="o",
        markersize=4.4,
        linewidth=2.5,
        label="累计能耗",
    )[0]
    remaining_line = ax2.plot(
        profile["距离_km"],
        profile["剩余电量_Wh"],
        color=COLORS["orange"],
        marker="o",
        markersize=4.4,
        linewidth=2.5,
        label="剩余电量",
    )[0]

    ax.axvspan(sustainable_distance, profile["距离_km"].max(), color=COLORS["risk_fill"], alpha=0.72, zorder=0)
    ax.axvline(sustainable_distance, color=COLORS["red"], linestyle="--", linewidth=1.8)
    ax.annotate(
        "剩余电量 = 0 Wh\n理论最远可持续飞行距离 ≈ 4 km",
        xy=(sustainable_distance, 130),
        xytext=(5.1, 245),
        arrowprops={"arrowstyle": "->", "lw": 1.4, "color": COLORS["red"]},
        fontsize=11.2,
        fontweight="bold",
        color=COLORS["red"],
        bbox={"boxstyle": "round,pad=0.42", "fc": "#FFF1F0", "ec": "#FCA5A5"},
    )
    ax.text(
        11.7,
        720,
        "浅红区域：继续按规划路线推演时任务需求仍在增加；\n但实际飞行中此后已不具备持续飞行条件，\n该部分仅用于说明任务不可达，不表示飞机还能继续飞行。",
        fontsize=10.4,
        color="#991B1B",
        ha="center",
        va="center",
        bbox={"boxstyle": "round,pad=0.45", "fc": "#FFF7F7", "ec": "#FCA5A5", "alpha": 0.96},
    )

    ax.set_xlabel("距起点航程距离（km）", fontsize=12.5, fontweight="bold", labelpad=12)
    ax.set_ylabel("累计能耗（Wh）", fontsize=12.5, fontweight="bold", color=COLORS["deep_blue"])
    ax2.set_ylabel("剩余电量（Wh）", fontsize=12.5, fontweight="bold", color=COLORS["orange"])
    ax.set_xlim(0, 25)
    ax.set_ylim(0, 900)
    ax2.set_ylim(0, 145)
    ax.tick_params(axis="y", colors=COLORS["deep_blue"])

    ax.legend(
        [cumulative_line, remaining_line],
        ["累计能耗", "剩余电量"],
        loc="upper left",
        frameon=False,
        fontsize=11,
    )

    add_text_box(
        fig,
        0.775,
        0.79,
        "本图与图3-11对应同一“压力任务场景”，用于展示风险沿航程如何逐步显现。\n\n应用：解释任务不可达、辅助返航阈值、局部重规划和风险告警。",
        title="场景说明",
        fill=COLORS["note_fill"],
        fontsize=9.8,
    )
    add_text_box(
        fig,
        0.775,
        0.47,
        "累计能耗表示完成当前已规划航段所需的总能量需求；剩余电量表示当前电池约束下的可用能量余额；两曲线结合可定位风险首次出现的位置。",
        title="指标说明",
        fill="#EEF8FB",
        edge="#B8DDE8",
        fontsize=9.8,
    )
    add_text_box(
        fig,
        0.775,
        0.23,
        "风险不是只在终点出现，而是在约 4 km 处已出现“电量耗尽”。",
        title="结论摘要",
        fill=COLORS["conclusion_fill"],
        edge="#FDBA74",
        fontsize=9.8,
    )
    add_caption(fig, "fig3_12")
    save_figure(fig, "fig3_12_route_energy_remaining")


def draw_fig3_13() -> None:
    labels = ["预测可持续飞行时长", "规划航线预计飞行时长"]
    values = [7.7, 47.1]
    colors = [COLORS["blue"], COLORS["red"]]
    ratio = values[1] / values[0]

    fig, ax = setup_figure(
        "规划航线预计飞行时长与预测可持续飞行时长对照图",
        "区分航线执行所需时间与当前电池、环境条件下可持续飞行时间。",
    )
    style_axis(ax)

    y = np.arange(len(labels))
    bars = ax.barh(y, values, height=0.52, color=colors, edgecolor="white", linewidth=1.2)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=12)
    ax.invert_yaxis()
    ax.set_xlabel("飞行时长（min）", fontsize=12.5, fontweight="bold")
    ax.set_ylabel("时长指标", fontsize=12.5, fontweight="bold")
    ax.set_xlim(0, 52)

    for bar, value in zip(bars, values):
        ax.text(
            value + 0.9,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f} min",
            va="center",
            ha="left",
            fontsize=11,
            fontweight="bold",
            color=COLORS["text"],
        )

    ax.annotate(
        f"所需飞行时长约为可持续飞行时长的 {ratio:.2f} 倍",
        xy=(47.1, 1),
        xytext=(21, 1.42),
        arrowprops={"arrowstyle": "->", "color": COLORS["red"], "lw": 1.4},
        fontsize=11.5,
        fontweight="bold",
        color=COLORS["red"],
        bbox={"boxstyle": "round,pad=0.36", "fc": "#FFF1F0", "ec": "#FCA5A5"},
    )

    add_text_box(
        fig,
        0.805,
        0.79,
        "该图对应典型长航程或高负载压力任务，用于说明任务的“时间可行性”和“续航可行性”之间存在差异。\n\n应用：起飞前决策、物流时效分析、巡检任务时间窗口判断。",
        title="场景说明",
        fill=COLORS["note_fill"],
    )
    add_text_box(
        fig,
        0.805,
        0.48,
        "47.1 min 指执行该规划航线预计需要的飞行时间；7.7 min 指当前电池与环境条件下模型预测最多可持续飞行的时间。该指标不是算法计算耗时，不应与全局规划耗时 118 ms 混淆。",
        title="指标说明",
        fill="#EEF8FB",
        edge="#B8DDE8",
        fontsize=9.8,
    )
    add_text_box(
        fig,
        0.805,
        0.22,
        "规划航线虽然在空间上可生成，但在时间/电量约束下不可完成；“能规划出来”不等于“能飞得完”。",
        title="结论摘要",
        fill=COLORS["conclusion_fill"],
        edge="#FDBA74",
        fontsize=9.8,
    )
    add_caption(fig, "fig3_13")
    save_figure(fig, "fig3_13_required_vs_sustainable_time")


def draw_fig3_14() -> None:
    df = pd.DataFrame(
        {
            "特征方案": ["任务参数方案", "历史天气方案", "板端风场方案", "综合天气方案"],
            "MAE": [1.81, 1.94, 1.85, 1.96],
            "RMSE": [3.21, 3.20, 3.11, 3.18],
        }
    )

    fig, ax = setup_figure(
        "不同输入特征方案的预测误差对比图",
        "对比不同特征组合下 MAE 与 RMSE 表现，评估现场风场输入的工程价值。",
    )
    style_axis(ax)

    x = np.arange(len(df))
    width = 0.34
    bars_mae = ax.bar(x - width / 2, df["MAE"], width, label="MAE", color=COLORS["blue"], edgecolor="white", linewidth=1.2)
    bars_rmse = ax.bar(x + width / 2, df["RMSE"], width, label="RMSE", color=COLORS["orange"], edgecolor="white", linewidth=1.2)

    min_rmse_idx = int(df["RMSE"].idxmin())
    bars_rmse[min_rmse_idx].set_color(COLORS["green"])
    bars_rmse[min_rmse_idx].set_edgecolor(COLORS["text"])
    bars_rmse[min_rmse_idx].set_linewidth(1.4)

    ax.set_xticks(x)
    ax.set_xticklabels(df["特征方案"], fontsize=11.2)
    ax.set_ylabel("误差值（Wh/km）", fontsize=12.5, fontweight="bold")
    ax.set_xlabel("输入特征方案", fontsize=12.5, fontweight="bold", labelpad=12)
    ax.set_ylim(0, 3.75)
    ax.legend(loc="upper left", frameon=False, fontsize=11)
    annotate_bars(ax, bars_mae, unit="", fmt="{:.2f}", dy=0.013)
    annotate_bars(ax, bars_rmse, unit="", fmt="{:.2f}", dy=0.013)

    ax.annotate(
        "RMSE 最低：3.11 Wh/km",
        xy=(x[min_rmse_idx] + width / 2, df.loc[min_rmse_idx, "RMSE"]),
        xytext=(x[min_rmse_idx] + 0.3, 3.48),
        arrowprops={"arrowstyle": "->", "color": COLORS["green"], "lw": 1.4},
        fontsize=11.3,
        fontweight="bold",
        color=COLORS["green"],
        bbox={"boxstyle": "round,pad=0.35", "fc": "#F0FDF4", "ec": "#86EFAC"},
    )

    add_text_box(
        fig,
        0.805,
        0.79,
        "该图用于比较不同输入特征组合对能耗预测效果的影响。\n\n应用：说明为什么接入板端传感器、为什么现场风场值得采集，并展示模型输入设计合理性。",
        title="场景说明",
        fill=COLORS["note_fill"],
    )
    add_text_box(
        fig,
        0.805,
        0.49,
        "板端风速风向输入对模型修正具有实际工程价值；综合天气方案有利于后续融合拓展。",
        title="指标说明",
        fill="#EEF8FB",
        edge="#B8DDE8",
    )
    add_text_box(
        fig,
        0.805,
        0.29,
        "各方案误差差异不大，但板端风场方案在 RMSE 上更优，说明现场风场采集有助于刻画能耗波动。",
        title="结论摘要",
        fill=COLORS["conclusion_fill"],
        edge="#FDBA74",
    )
    add_caption(fig, "fig3_14")
    save_figure(fig, "fig3_14_feature_scheme_error_comparison")


def draw_combined_preview() -> None:
    image_paths = [
        OUTPUT_DIR / "fig3_10_prediction_error_metrics.png",
        OUTPUT_DIR / "fig3_11_energy_vs_battery.png",
        OUTPUT_DIR / "fig3_12_route_energy_remaining.png",
        OUTPUT_DIR / "fig3_13_required_vs_sustainable_time.png",
        OUTPUT_DIR / "fig3_14_feature_scheme_error_comparison.png",
    ]
    fig = plt.figure(figsize=(16, 20), facecolor="white")
    fig.text(
        0.5,
        0.985,
        "第 3.3 节“特性成果”图组排版预览",
        ha="center",
        va="top",
        fontsize=24,
        fontweight="bold",
        color=COLORS["text"],
    )
    fig.text(
        0.5,
        0.965,
        "统一蓝/青/橙配色，包含图题、副标题、图例、数值标注、场景说明与结论摘要。",
        ha="center",
        va="top",
        fontsize=12.5,
        color=COLORS["muted"],
    )
    grid = fig.add_gridspec(3, 2, left=0.04, right=0.96, top=0.94, bottom=0.03, hspace=0.10, wspace=0.045)
    positions = [(0, 0), (0, 1), (1, 0), (1, 1), (2, slice(0, 2))]
    for path, pos in zip(image_paths, positions):
        ax = fig.add_subplot(grid[pos])
        ax.imshow(plt.imread(path))
        ax.set_axis_off()
    for suffix in ["png", "svg", "pdf"]:
        fig.savefig(OUTPUT_DIR / f"section_3_3_combined_preview.{suffix}", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    configure_style()
    draw_fig3_10()
    draw_fig3_11()
    draw_fig3_12()
    draw_fig3_13()
    draw_fig3_14()
    draw_combined_preview()
    print(f"Generated figures in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
