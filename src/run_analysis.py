"""
Run the SQL analysis in sql/queries.sql against brightpath.db, export each
result as a CSV in results/, render a chart per section in images/, and
write a short written summary to results/INSIGHTS.md.

Usage:
    python src/run_analysis.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "brightpath.db"
RESULTS_DIR = REPO_ROOT / "results"
IMAGES_DIR = REPO_ROOT / "images"
RESULTS_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

# Same custom palette as the Demand Forecasting project, for a consistent
# look across the two SQL/analytics case studies on the portfolio.
PALETTE = {
    "primary": "#2c4c73",
    "accent": "#c98a3e",
    "good": "#3f7d67",
    "warn": "#b3543f",
    "muted": "#aab2bd",
    "ink": "#20262e",
    "grid": "#e6e4dd",
    "card": "#fbfaf6",
}

plt.rcParams.update({
    "figure.facecolor": PALETTE["card"],
    "axes.facecolor": PALETTE["card"],
    "savefig.facecolor": PALETTE["card"],
    "text.color": PALETTE["ink"],
    "axes.labelcolor": PALETTE["ink"],
    "axes.edgecolor": PALETTE["grid"],
    "xtick.color": "#5c6470",
    "ytick.color": "#5c6470",
    "font.family": "sans-serif",
    "axes.titleweight": "600",
    "axes.titlelocation": "left",
    "axes.titlesize": 14,
    "axes.titlepad": 12,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "axes.axisbelow": True,
    "grid.color": PALETTE["grid"],
    "grid.linewidth": 0.9,
    "legend.frameon": False,
    "savefig.dpi": 170,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.35,
})


def _style_ax(ax):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(PALETTE["grid"])
    ax.tick_params(length=0, labelsize=10)


# ----------------------------------------------------------------------------
# Each analysis question lives in its own file under sql/
# ----------------------------------------------------------------------------

def load_query(name: str) -> str:
    return (REPO_ROOT / "sql" / name).read_text()


def main():
    conn = sqlite3.connect(DB_PATH)

    pnl = pd.read_sql(load_query("01_monthly_pnl.sql"), conn)
    revenue_by_course = pd.read_sql(load_query("02_revenue_by_course.sql"), conn)
    channel_perf = pd.read_sql(load_query("03_marketing_channel_performance.sql"), conn)
    dropout = pd.read_sql(load_query("04_dropout_by_level.sql"), conn)
    enroll_trend = pd.read_sql(load_query("05_enrollment_trend.sql"), conn)
    cost_structure = pd.read_sql(load_query("06_cost_structure.sql"), conn)
    dropout_by_channel = pd.read_sql(load_query("07_dropout_by_channel.sql"), conn)
    student_revenue = pd.read_sql(load_query("08_revenue_concentration.sql"), conn)

    # Month-over-month revenue growth: a simple derivative of the P&L query,
    # computed here rather than in SQL (would need window functions, which
    # MySQL 5.7 -- one of this project's two target databases -- doesn't have).
    pnl["revenue_mom_pct"] = (pnl["revenue_vnd"].pct_change() * 100).round(1)

    # Revenue concentration (Pareto/Lorenz): rank students by revenue, then
    # compute the cumulative share -- this needs a running total over ranked
    # rows, simplest done here rather than with SQL window functions.
    student_revenue = student_revenue.sort_values("revenue_vnd", ascending=False).reset_index(drop=True)
    student_revenue["cum_share_pct"] = (
        student_revenue["revenue_vnd"].cumsum() / student_revenue["revenue_vnd"].sum() * 100
    )
    student_revenue["rank"] = student_revenue.index + 1

    pnl.to_csv(RESULTS_DIR / "01_monthly_pnl.csv", index=False)
    revenue_by_course.to_csv(RESULTS_DIR / "02_revenue_by_course.csv", index=False)
    channel_perf.to_csv(RESULTS_DIR / "03_marketing_channel_performance.csv", index=False)
    dropout.to_csv(RESULTS_DIR / "04_dropout_by_level.csv", index=False)
    enroll_trend.to_csv(RESULTS_DIR / "05_enrollment_trend.csv", index=False)
    cost_structure.to_csv(RESULTS_DIR / "06_cost_structure.csv", index=False)
    dropout_by_channel.to_csv(RESULTS_DIR / "07_dropout_by_channel.csv", index=False)
    student_revenue.to_csv(RESULTS_DIR / "08_revenue_concentration.csv", index=False)

    # Power-BI-ready flat export: everything Power BI needs, one file per
    # table, so the CSVs can be loaded directly as a simple star schema.
    for name in ("courses", "students", "enrollments", "payments", "marketing_spend", "expenses"):
        pd.read_sql(f"SELECT * FROM {name}", conn).to_csv(RESULTS_DIR / f"powerbi_{name}.csv", index=False)

    # ---- charts -------------------------------------------------------

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(pnl["month"], pnl["revenue_vnd"] / 1e6, marker="o", lw=2.2, color=PALETTE["primary"], label="Revenue")
    ax.plot(pnl["month"], pnl["cost_vnd"] / 1e6, marker="o", lw=2.2, color=PALETTE["warn"], label="Cost")
    ax.fill_between(pnl["month"], pnl["revenue_vnd"] / 1e6, pnl["cost_vnd"] / 1e6,
                     where=(pnl["revenue_vnd"] >= pnl["cost_vnd"]), color=PALETTE["good"], alpha=0.15)
    ax.set_title("Monthly revenue vs. cost (million VND)")
    ax.set_ylabel("Million VND")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(loc="upper left")
    _style_ax(ax)
    fig.savefig(IMAGES_DIR / "01_monthly_pnl.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    rc = revenue_by_course.sort_values("revenue_vnd")
    ax.barh(rc["course_name"], rc["revenue_vnd"] / 1e6, color=PALETTE["primary"])
    ax.set_title("Revenue by course (million VND, full year)")
    ax.set_xlabel("Million VND")
    _style_ax(ax)
    fig.savefig(IMAGES_DIR / "02_revenue_by_course.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    cp = channel_perf.sort_values("revenue_per_vnd_spent", na_position="first")
    colors = [PALETTE["muted"] if pd.isna(v) else PALETTE["accent"] for v in cp["revenue_per_vnd_spent"]]
    ax.barh(cp["channel"], cp["revenue_per_vnd_spent"].fillna(0), color=colors)
    ax.set_title("Marketing ROI by channel (revenue per 1 VND spent)")
    ax.set_xlabel("Revenue VND returned per VND spent (0 = no direct spend, e.g. Referral/Walk-in)")
    _style_ax(ax)
    fig.savefig(IMAGES_DIR / "03_channel_roi.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5.5))
    dp = dropout.sort_values("dropout_pct")
    colors = [PALETTE["warn"] if v >= 15 else PALETTE["primary"] for v in dp["dropout_pct"]]
    ax.barh(dp["level"], dp["dropout_pct"], color=colors)
    for y, (_, row) in enumerate(dp.iterrows()):
        ax.text(row["dropout_pct"] + 0.3, y, f"{row['dropout_pct']:.1f}%", va="center", fontsize=10)
    ax.set_title("Dropout rate by course level")
    ax.set_xlabel("Dropout rate (%)")
    _style_ax(ax)
    fig.savefig(IMAGES_DIR / "04_dropout_by_level.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    cs = cost_structure.pivot(index="month", columns="category", values="amount_vnd").fillna(0) / 1e6
    cs = cs[["Rent", "Salaries", "Teacher Fees", "Marketing", "Utilities", "Materials"]]
    cs.plot(kind="bar", stacked=True, ax=ax,
            color=[PALETTE["primary"], PALETTE["accent"], PALETTE["good"], PALETTE["warn"], PALETTE["muted"], "#c9d2dc"])
    ax.set_title("Monthly cost structure by category (million VND)")
    ax.set_ylabel("Million VND")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(loc="upper left", ncol=2, fontsize=9)
    _style_ax(ax)
    fig.savefig(IMAGES_DIR / "06_cost_structure.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5.5))
    dc = dropout_by_channel.sort_values("dropout_pct")
    colors = [PALETTE["warn"] if v >= 15 else PALETTE["primary"] for v in dc["dropout_pct"]]
    ax.barh(dc["acquisition_channel"], dc["dropout_pct"], color=colors)
    for y, (_, row) in enumerate(dc.iterrows()):
        ax.text(row["dropout_pct"] + 0.3, y, f"{row['dropout_pct']:.1f}%", va="center", fontsize=10)
    ax.set_title("Dropout rate by acquisition channel")
    ax.set_xlabel("Dropout rate (%)")
    _style_ax(ax)
    fig.savefig(IMAGES_DIR / "07_dropout_by_channel.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(student_revenue["rank"], student_revenue["revenue_vnd"] / 1e6, color=PALETTE["muted"], width=1.0)
    ax2 = ax.twinx()
    ax2.plot(student_revenue["rank"], student_revenue["cum_share_pct"], color=PALETTE["accent"], lw=2.4)
    ax2.axhline(80, color=PALETTE["warn"], ls=":", lw=1.4)
    n_for_80 = int((student_revenue["cum_share_pct"] <= 80).sum() + 1)
    ax2.annotate(f"top {n_for_80} of {len(student_revenue)} students = 80% of revenue",
                 xy=(n_for_80, 80), xytext=(n_for_80 + 40, 55), fontsize=11,
                 color=PALETTE["ink"], arrowprops=dict(arrowstyle="->", color=PALETTE["warn"], lw=1.2))
    ax2.set_ylim(0, 105)
    ax2.set_ylabel("Cumulative share of revenue (%)")
    ax2.grid(False)
    ax2.spines["top"].set_visible(False)
    ax2.spines["left"].set_visible(False)
    ax2.tick_params(length=0, labelsize=10)
    ax.set_title("Revenue is broad-based, not concentrated (near-linear curve)")
    ax.set_xlabel("Students, ranked by revenue")
    ax.set_ylabel("Revenue per student (million VND)")
    _style_ax(ax)
    fig.savefig(IMAGES_DIR / "08_revenue_concentration.png")
    plt.close(fig)

    # ---- written summary ------------------------------------------------

    total_rev = pnl["revenue_vnd"].sum()
    total_cost = pnl["cost_vnd"].sum()
    best_month = pnl.loc[pnl["margin_pct"].idxmax()]
    worst_month = pnl.loc[pnl["margin_pct"].idxmin()]
    best_growth_month = pnl.loc[pnl["revenue_mom_pct"].idxmax()]
    worst_growth_month = pnl.loc[pnl["revenue_mom_pct"].idxmin()]

    paid_channels = channel_perf.dropna(subset=["revenue_per_vnd_spent"])
    best_channel = paid_channels.sort_values("revenue_per_vnd_spent", ascending=False).iloc[0]
    worst_channel = paid_channels.sort_values("revenue_per_vnd_spent", ascending=True).iloc[0]
    free_channels = channel_perf[channel_perf["spend_vnd"] == 0].sort_values(
        "lead_to_student_pct", ascending=False
    )

    worst_level = dropout.sort_values("dropout_pct", ascending=False).iloc[0]
    best_level = dropout.sort_values("dropout_pct", ascending=True).iloc[0]
    top_course = revenue_by_course.sort_values("revenue_vnd", ascending=False).iloc[0]

    worst_dropout_channel = dropout_by_channel.sort_values("dropout_pct", ascending=False).iloc[0]
    best_dropout_channel = dropout_by_channel.sort_values("dropout_pct", ascending=True).iloc[0]

    n_for_80 = int((student_revenue["cum_share_pct"] <= 80).sum() + 1)
    pct_students_for_80 = round(100 * n_for_80 / len(student_revenue), 1)

    lines = [
        "# BrightPath Language Center -- Analysis Summary",
        "",
        "_Generated by `src/run_analysis.py` from `brightpath.db`. See `images/` for charts,",
        "`results/*.csv` for the raw query outputs, and `results/powerbi_*.csv` for a flat",
        "star-schema export ready to load into Power BI._",
        "",
        "## Headlines",
        "",
        f"- **13-month revenue:** {total_rev/1e6:,.0f}M VND against {total_cost/1e6:,.0f}M VND in cost "
        f"({100*(total_rev-total_cost)/total_rev:.1f}% blended margin). Best month: {best_month['month']} "
        f"({best_month['margin_pct']:.1f}% margin). Worst month: {worst_month['month']} "
        f"({worst_month['margin_pct']:.1f}% margin).",
        f"- **Growth is choppy, not steady:** revenue swung from {worst_growth_month['revenue_mom_pct']:+.0f}% "
        f"({worst_growth_month['month']}) to {best_growth_month['revenue_mom_pct']:+.0f}% "
        f"({best_growth_month['month']}) month-over-month -- a cohort-batch business, not a smooth-growth one.",
        f"- **Best-ROI paid channel:** {best_channel['channel']} returns {best_channel['revenue_per_vnd_spent']:.1f} "
        f"VND per VND spent (CAC {best_channel['cac_vnd']:,.0f} VND/student); the weakest paid channel, "
        f"{worst_channel['channel']}, returns only {worst_channel['revenue_per_vnd_spent']:.1f}.",
        f"- **Free channels outperform every paid one on conversion:** {free_channels.iloc[0]['channel']} converts "
        f"{free_channels.iloc[0]['lead_to_student_pct']:.0f}% of leads at zero direct spend.",
        f"- **Highest-revenue course:** {top_course['course_name']} ({top_course['revenue_vnd']/1e6:,.1f}M VND, "
        f"{int(top_course['enrollments'])} enrollments).",
        f"- **Where students leak, by course:** {worst_level['level']}-level courses have a "
        f"{worst_level['dropout_pct']:.1f}% dropout rate (vs. {best_level['dropout_pct']:.1f}% for "
        f"{best_level['level']}), dropping out around week {worst_level['avg_week_dropped']:.1f} on average.",
        f"- **Where students leak, by channel:** students acquired via {worst_dropout_channel['acquisition_channel']} "
        f"drop out at {worst_dropout_channel['dropout_pct']:.1f}%, versus {best_dropout_channel['dropout_pct']:.1f}% "
        f"for {best_dropout_channel['acquisition_channel']} -- acquisition channel predicts commitment, not just cost.",
        f"- **Revenue is broad-based, not concentrated:** it takes {pct_students_for_80:.0f}% of students "
        f"({n_for_80} of {len(student_revenue)}) to reach 80% of total revenue -- close to what a perfectly "
        "even split would take, so no small group of students is carrying the business.",
        "",
        "## Recommendations",
        "",
        f"1. **Reallocate marketing budget toward {best_channel['channel']}** and away from "
        f"{worst_channel['channel']}; the gap in revenue-per-VND-spent "
        f"({best_channel['revenue_per_vnd_spent']:.1f} vs. {worst_channel['revenue_per_vnd_spent']:.1f}) is too "
        "large to ignore for the next budgeting cycle.",
        "2. **Build a formal referral incentive** -- referred and walk-in students already convert best for free; "
        "a small reward for existing students who refer a friend would scale a channel that already works, "
        "rather than pushing more spend into a weaker paid one.",
        f"3. **Front-load retention effort in {worst_level['level']}-level courses**, concentrated in the first "
        f"{worst_level['avg_week_dropped']:.0f} weeks where the dropout curve is steepest -- a check-in call or "
        "extra practice session at week 2-3 costs far less than replacing a lost student.",
        f"4. **Treat {worst_dropout_channel['acquisition_channel']}-acquired students as a higher-touch segment**: "
        "they convert acceptably but drop out more, so their onboarding may need to set clearer expectations "
        "up front about course pacing and commitment.",
        "5. **Cashflow risk from losing any single student is low** -- revenue is spread broadly across the "
        "base rather than resting on a few big spenders, so budgeting can reasonably assume a stable per-student "
        "average rather than building in a buffer for high-value churn.",
    ]
    (RESULTS_DIR / "INSIGHTS.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nWrote {len(list(IMAGES_DIR.glob('*.png')))} charts to {IMAGES_DIR}/")
    print(f"Wrote {len(list(RESULTS_DIR.glob('*.csv')))} CSVs to {RESULTS_DIR}/")

    conn.close()


if __name__ == "__main__":
    main()
