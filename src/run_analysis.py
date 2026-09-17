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

    pnl.to_csv(RESULTS_DIR / "01_monthly_pnl.csv", index=False)
    revenue_by_course.to_csv(RESULTS_DIR / "02_revenue_by_course.csv", index=False)
    channel_perf.to_csv(RESULTS_DIR / "03_marketing_channel_performance.csv", index=False)
    dropout.to_csv(RESULTS_DIR / "04_dropout_by_level.csv", index=False)
    enroll_trend.to_csv(RESULTS_DIR / "05_enrollment_trend.csv", index=False)
    cost_structure.to_csv(RESULTS_DIR / "06_cost_structure.csv", index=False)

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

    # ---- written summary ------------------------------------------------

    total_rev = pnl["revenue_vnd"].sum()
    total_cost = pnl["cost_vnd"].sum()
    best_channel = channel_perf.sort_values("revenue_per_vnd_spent", ascending=False, na_position="last").iloc[0]
    worst_level = dropout.sort_values("dropout_pct", ascending=False).iloc[0]
    top_course = revenue_by_course.sort_values("revenue_vnd", ascending=False).iloc[0]

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
        f"({100*(total_rev-total_cost)/total_rev:.1f}% margin).",
        f"- **Best-ROI channel:** {best_channel['channel']} returns {best_channel['revenue_per_vnd_spent']:.1f} VND "
        f"of revenue per VND spent (CAC {best_channel['cac_vnd']:,.0f} VND/student, "
        f"{best_channel['lead_to_student_pct']:.0f}% lead-to-student rate).",
        f"- **Highest-revenue course:** {top_course['course_name']} ({top_course['revenue_vnd']/1e6:,.1f}M VND, "
        f"{int(top_course['enrollments'])} enrollments).",
        f"- **Where students leak:** {worst_level['level']}-level courses have a {worst_level['dropout_pct']:.1f}% "
        f"dropout rate, dropping out around week {worst_level['avg_week_dropped']:.1f} on average.",
        "",
        "## Recommendation",
        "",
        f"Shift incremental marketing budget toward {best_channel['channel']} and away from the "
        "lowest revenue-per-VND channel; front-load teacher check-ins in the first two weeks of "
        f"{worst_level['level']}-level courses, where the dropout curve is steepest.",
    ]
    (RESULTS_DIR / "INSIGHTS.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nWrote {len(list(IMAGES_DIR.glob('*.png')))} charts to {IMAGES_DIR}/")
    print(f"Wrote {len(list(RESULTS_DIR.glob('*.csv')))} CSVs to {RESULTS_DIR}/")

    conn.close()


if __name__ == "__main__":
    main()
