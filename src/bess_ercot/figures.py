"""Publication figures (Figures 1-5). Saved as 600 dpi PNG and vector PDF."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.ticker import FuncFormatter

from . import config

INK, INK_2, GRID = "#0b0b0b", "#52514e", "#d9d8d4"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"   # validated categorical slots 1-3
SCENARIO_COLORS = {"Low": BLUE, "Reference": ORANGE, "High": AQUA}

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "font.size": 10, "axes.labelsize": 10, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "legend.fontsize": 9, "axes.edgecolor": INK_2, "axes.labelcolor": INK,
    "xtick.color": INK_2, "ytick.color": INK_2, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "savefig.dpi": 600, "savefig.bbox": "tight",
})

usd = FuncFormatter(lambda v, _: f"${v:,.0f}")
thousands = FuncFormatter(lambda v, _: f"{v:,.0f}")


def _save(fig, name: str) -> None:
    config.FIGURES_DIR.mkdir(exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(config.FIGURES_DIR / f"{name}.{ext}")
    plt.close(fig)


def _grid(ax, axis="y"):
    ax.grid(axis=axis, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def figure1_framework() -> None:
    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    def box(x, y, w, h, title, sub=None):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                    linewidth=1.0, edgecolor=INK, facecolor="#f4f3f0"))
        if sub:
            ax.text(x + w / 2, y + h - 0.38, title, ha="center", va="center", fontsize=10.5, weight="bold")
            ax.text(x + w / 2, (y + h - 0.7) / 2 + y / 2, sub, ha="center", va="center", fontsize=8.5,
                    color=INK_2, linespacing=1.3)
        else:
            ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=10.5, weight="bold")

    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12,
                                     linewidth=1.0, color=INK))

    box(0.3, 8.4, 6.6, 1.2, "AI-related demand and market uncertainty")
    box(0.3, 6.1, 6.6, 1.5, "Observed 2025 ERCOT prices", "and illustrative low, reference and high price scenarios")
    box(0.3, 3.0, 6.6, 2.3, "Storage revenue structures",
        "merchant arbitrage, merchant stacking, contracted\navailability, hybrid, renewable co-location,\ndata-centre-linked")
    box(7.4, 3.6, 2.4, 1.3, "Financing", "discount rates 5-15%")
    box(0.3, 0.6, 6.6, 1.6, "Investment viability", "LCOS, NPV, IRR, payback, P(NPV > 0)")
    arrow(3.6, 8.4, 3.6, 7.65)
    arrow(3.6, 6.1, 3.6, 5.35)
    arrow(3.6, 3.0, 3.6, 2.25)
    ax.add_patch(FancyArrowPatch((8.6, 3.6), (6.95, 1.4), arrowstyle="-|>", mutation_scale=12,
                                 linewidth=1.0, color=INK, connectionstyle="angle,angleA=-90,angleB=180"))
    _save(fig, "Figure_1")


def figure2_ancillary(by_service: dict) -> None:
    order = sorted(by_service, key=by_service.get)
    labels = [config.AS_NAMES[s] for s in order]
    values = [by_service[s] for s in order]
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    bars = ax.barh(labels, values, color=BLUE, height=0.6)
    for b, v in zip(bars, values):
        ax.text(v + max(values) * 0.01, b.get_y() + b.get_height() / 2, f"${v:,.0f}",
                va="center", fontsize=9, color=INK)
    ax.xaxis.set_major_formatter(usd)
    ax.set_xlim(0, max(values) * 1.15)
    ax.set_xlabel("Indicative annual capacity-price value (USD/year, 1 MW, 100% realisation)")
    _grid(ax, "x")
    _save(fig, "Figure_2")


def figure3_spread(spread_df) -> None:
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    bars = ax.bar(spread_df["case"], spread_df["energy_gross_margin"], color=BLUE, width=0.55)
    for b, v in zip(bars, spread_df["energy_gross_margin"]):
        ax.text(b.get_x() + b.get_width() / 2, v + 900, f"${v:,.0f}", ha="center", fontsize=9)
    ax.yaxis.set_major_formatter(usd)
    ax.set_ylim(0, spread_df["energy_gross_margin"].max() * 1.18)
    ax.set_ylabel("Annual arbitrage gross margin (USD/year)")
    ax.set_xlabel("Intraday price-spread case")
    _grid(ax)
    _save(fig, "Figure_3")


def figure4_npv(grid) -> None:
    sub = grid[grid["rate"] == config.REFERENCE_RATE]
    short = {"Merchant arbitrage": "Merchant\narbitrage", "Merchant stacking": "Merchant\nstacking",
             "Contracted availability": "Contracted\navailability", "Hybrid": "Hybrid",
             "Renewable co-location": "Renewable\nco-location", "Data-centre-linked": "Data-centre-\nlinked"}
    fig, ax = plt.subplots(figsize=(6.8, 3.9))
    width = 0.26
    for i, scen in enumerate(config.PRICE_SCENARIOS):
        vals = [sub[(sub["model"] == m) & (sub["scenario"] == scen)]["npv"].iloc[0] / 1000
                for m in config.MODELS]
        xs = [j + (i - 1) * width for j in range(len(config.MODELS))]
        ax.bar(xs, vals, width=width - 0.03, color=SCENARIO_COLORS[scen], label=scen)
        for x, v in zip(xs, vals):
            if abs(v) < 1:
                ax.text(x, 12, "0", ha="center", fontsize=7.5, color=INK_2)
    ax.axhline(0, color=INK, linewidth=0.8)
    ax.set_xticks(range(len(config.MODELS)))
    ax.set_xticklabels([short[m] for m in config.MODELS])
    ax.yaxis.set_major_formatter(thousands)
    ax.set_ylabel("NPV at 8% (USD thousand)")
    ax.legend(title="Price scenario", frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    _grid(ax)
    _save(fig, "Figure_4")


def figure5_montecarlo(mc) -> None:
    sub = mc[(mc["rate"] == config.REFERENCE_RATE) & mc["model"].isin(["Hybrid", "Data-centre-linked"])]
    fig, ax = plt.subplots(figsize=(6.0, 3.9))
    for j, model in enumerate(["Hybrid", "Data-centre-linked"]):
        for i, scen in enumerate(config.PRICE_SCENARIOS):
            r = sub[(sub["model"] == model) & (sub["scenario"] == scen)].iloc[0]
            x = j + (i - 1) * 0.22
            ax.vlines(x, r["p05_npv"] / 1000, r["p95_npv"] / 1000, color=SCENARIO_COLORS[scen], linewidth=2)
            ax.plot(x, r["median_npv"] / 1000, "o", markersize=8, color=SCENARIO_COLORS[scen],
                    markeredgecolor="white", markeredgewidth=1.5, label=scen if j == 0 else None)
    ax.axhline(0, color=INK, linewidth=0.8)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Hybrid", "Data-centre-linked"])
    ax.set_xlim(-0.6, 1.6)
    ax.yaxis.set_major_formatter(thousands)
    ax.set_ylabel("NPV at 8% (USD thousand)")
    ax.legend(title="Price scenario", frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    _grid(ax)
    _save(fig, "Figure_5")
