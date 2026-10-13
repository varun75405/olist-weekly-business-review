import logging
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server-side rendering
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from src.config import CHARTS_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("generate_charts")

def chart_monthly_revenue(df: pd.DataFrame):
    """Chart 1: Monthly revenue trend with MoM growth annotations."""
    if df.empty:
        logger.warning("No data for monthly revenue chart.")
        return None

    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax2 = ax1.twinx()

    x_labels = df["month"].astype(str)
    x_pos = range(len(x_labels))

    bars = ax1.bar(x_pos, df["monthly_revenue"], color="#1565C0", alpha=0.85, label="Delivered Revenue (BRL)")
    ax1.set_xlabel("Purchase Month", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Monthly Revenue (BRL)", fontsize=11, fontweight="bold", color="#1565C0")
    ax1.tick_params(axis="y", labelcolor="#1565C0")
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(x_labels, rotation=45, ha="right", fontsize=9)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R$ {x/1e6:.1f}M"))

    # Safely handle MoM growth: filter zero/missing prior revenue & exclude extreme pilot artifacts (< 1,000 BRL baseline)
    # This ensures the first plotted comparison is the first valid operational comparison (Feb 2017 vs Jan 2017 at +112.8%)
    growth_data = df[
        df["pct_growth"].notna() &
        (df["prev_revenue"] >= 1000.0) &
        (df["monthly_revenue"] > 0) &
        (df["pct_growth"].abs() <= 500.0)
    ].copy()

    if not growth_data.empty:
        growth_idx = [list(df["month"]).index(m) for m in growth_data["month"]]
        ax2.plot(growth_idx, growth_data["pct_growth"], "o-", color="#D84315",
                 linewidth=2.2, markersize=5, label="MoM Revenue Growth (%)")
        ax2.axhline(0, color="gray", linestyle="--", linewidth=0.8, alpha=0.7)
        ax2.set_ylabel("MoM Revenue Growth (%)", fontsize=11, fontweight="bold", color="#D84315")
        ax2.tick_params(axis="y", labelcolor="#D84315")
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{y:+.0f}%"))
        ax2.set_ylim(-40, 140)

        # Annotate key operational inflection points (Feb 2017 launch, Nov 2017 peak, Dec 2017 drop)
        from decimal import Decimal, ROUND_HALF_UP
        for idx, pct, m in zip(growth_idx, growth_data["pct_growth"], growth_data["month"]):
            m_str = str(m)[:7]
            if m_str in ["2017-02", "2017-11", "2017-12"]:
                d_pct = Decimal(str(pct)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
                ax2.annotate(f"{d_pct:+.1f}%", (idx, pct), textcoords="offset points",
                             xytext=(0, 8 if pct > 0 else -12), ha="center", fontsize=8,
                             fontweight="bold", color="#D84315")

    fig.suptitle("Monthly Revenue Trend & MoM Growth — Olist E-Commerce (2016–2018)", fontsize=13, fontweight="bold")
    ax1.legend(loc="upper left")
    if not growth_data.empty:
        ax2.legend(loc="upper right")
    plt.tight_layout()

    out_path = CHARTS_DIR / "chart1_monthly_revenue.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info(f"Saved: {out_path}")
    return out_path

def chart_top_categories(df: pd.DataFrame):
    """Chart 2: Top 15 product categories by total delivered revenue across all states."""
    if df.empty:
        logger.warning("No data for top categories chart.")
        return None

    # If df is directly from dedicated overall query, take top 15 and sort ascending for horizontal bar chart
    if "revenue" in df.columns and "category_english" in df.columns:
        if "customer_state" in df.columns:
            # Fallback aggregation if state-partitioned data is passed
            agg = df.groupby("category_english", as_index=False)["revenue"].sum()
        else:
            agg = df.copy()
        agg = agg.nlargest(15, "revenue").sort_values("revenue", ascending=True)
    else:
        logger.warning("Unexpected schema for top categories chart.")
        return None

    fig, ax = plt.subplots(figsize=(11, 7))
    colors = plt.cm.Blues([0.3 + 0.6 * i / len(agg) for i in range(len(agg))])
    bars = ax.barh(agg["category_english"], agg["revenue"], color=colors)
    ax.set_xlabel("Total Delivered Revenue (BRL)", fontsize=11, fontweight="bold")
    ax.set_title("Top 15 Product Categories by Delivered Revenue — Olist E-Commerce", fontsize=13, fontweight="bold")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R$ {x/1e6:.2f}M"))

    for bar, val in zip(bars, agg["revenue"]):
        ax.text(bar.get_width() + 15000, bar.get_y() + bar.get_height()/2,
                f"R$ {val/1e6:.2f}M", va="center", fontsize=8.5, fontweight="bold")

    plt.tight_layout()
    out_path = CHARTS_DIR / "chart2_top_categories.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info(f"Saved: {out_path}")
    return out_path

def chart_delivery_vs_review(df: pd.DataFrame):
    """Chart 3: Average delivery delay vs average review score."""
    if df.empty:
        logger.warning("No data for delivery vs review chart.")
        return None

    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax2 = ax1.twinx()

    x_pos = range(len(df))
    labels = [f"Score {int(s)}" for s in df["review_score"]]

    # Palette showing performance progression: red (Score 1: high delay & 38% late) to dark green (Score 5: 12.7d early & 3% late)
    bar_colors = ["#E53935", "#FB8C00", "#FBC02D", "#7CB342", "#2E7D32"]
    bars = ax1.bar(x_pos, df["avg_delay_days"], color=bar_colors, alpha=0.88,
                   edgecolor="#37474F", linewidth=0.8, width=0.62, label="Avg Delivery vs Estimate (Days)")

    # Prominent zero reference line marking promised delivery estimate
    ax1.axhline(0, color="#C62828", linewidth=1.5, linestyle="--", zorder=4)
    ax1.set_ylim(-16, 5)
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(labels, fontsize=10, fontweight="bold")
    ax1.set_xlabel("Customer Review Score (1 to 5 Stars)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Avg Delivery Delay vs Estimate (Days)\n[ Negative = Delivered Early  |  Positive = Delivered Late ]",
                   fontsize=10, fontweight="bold", color="#1A237E")

    # Clear text annotation on the zero line
    ax1.text(len(df) - 0.4, 0.4, "Promised Estimate (Day 0)", color="#C62828",
             fontsize=8.5, fontweight="bold", ha="right", va="bottom")

    # Data labels inside bars: centered, showing days and count clearly
    for i, (delay, cnt) in enumerate(zip(df["avg_delay_days"], df["order_count"])):
        txt_color = "#212121" if i == 2 else "white"
        ax1.text(i, delay / 2.0, f"{delay:+.1f} days\n(n={cnt:,})", ha="center", va="center",
                 fontsize=8.5, fontweight="bold", color=txt_color, linespacing=1.2)

    # Secondary axis: Late delivery rate (%)
    line = ax2.plot(x_pos, df["late_pct"], "D-", color="#6A1B9A", linewidth=2.5, markersize=7.5,
                    label="Late Delivery Rate (%)", zorder=5)
    ax2.set_ylabel("Late Delivery Rate (%)", fontsize=10, fontweight="bold", color="#6A1B9A")
    ax2.tick_params(axis="y", labelcolor="#6A1B9A")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{y:.0f}%"))
    ax2.set_ylim(0, 48)

    # Annotate late % points cleanly
    for i, lp in enumerate(df["late_pct"]):
        y_off = 10 if i == 0 else -16
        ax2.annotate(f"{lp:.1f}% late", (i, lp), textcoords="offset points", xytext=(0, y_off),
                     ha="center", fontsize=8.5, fontweight="bold", color="#6A1B9A",
                     bbox=dict(boxstyle="round,pad=0.18", facecolor="#F3E5F5", edgecolor="#CE93D8", alpha=0.9))

    fig.suptitle("Delivery Delay vs Review Score — Olist E-Commerce", fontsize=13, fontweight="bold")

    # Combined legend in top-right
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=8.5, framealpha=0.95)

    plt.tight_layout()
    out_path = CHARTS_DIR / "chart3_delivery_vs_review.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info(f"Saved: {out_path}")
    return out_path

def chart_rolling_orders(df: pd.DataFrame):
    """Chart 4: Daily order count with 7-day rolling average."""
    if df.empty:
        logger.warning("No data for rolling orders chart.")
        return None

    df = df.copy()
    df["order_date"] = pd.to_datetime(df["order_date"])

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.fill_between(df["order_date"], df["daily_order_count"], alpha=0.25,
                    color="#1976D2", label="Daily Orders")
    ax.plot(df["order_date"], df["daily_order_count"], color="#1976D2", linewidth=0.6, alpha=0.7)
    ax.plot(df["order_date"], df["rolling_7day_avg"], color="#D84315",
            linewidth=2.2, label="7-Day Rolling Average")

    ax.set_xlabel("Order Date", fontsize=11, fontweight="bold")
    ax.set_ylabel("Order Count", fontsize=11, fontweight="bold")
    ax.set_title("Daily Order Volume & 7-Day Rolling Average — Olist E-Commerce", fontsize=13, fontweight="bold")
    ax.legend(fontsize=10, loc="upper left")
    ax.tick_params(axis="x", rotation=30)
    plt.tight_layout()

    out_path = CHARTS_DIR / "chart4_rolling_orders.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info(f"Saved: {out_path}")
    return out_path

def generate_all_charts(query_results: dict):
    """Generate all four charts from actual query result DataFrames."""
    logger.info("--- Starting Pipeline Stage 5: Chart Generation ---")
    paths = {}

    if "q01_monthly_revenue" in query_results:
        paths["chart1"] = chart_monthly_revenue(query_results["q01_monthly_revenue"])

    if "q02b_top_categories_overall" in query_results:
        paths["chart2"] = chart_top_categories(query_results["q02b_top_categories_overall"])
    elif "q02_top_categories_by_state" in query_results:
        paths["chart2"] = chart_top_categories(query_results["q02_top_categories_by_state"])

    if "q05_delivery_delay_reviews" in query_results:
        paths["chart3"] = chart_delivery_vs_review(query_results["q05_delivery_delay_reviews"])

    if "q03_rolling_orders" in query_results:
        paths["chart4"] = chart_rolling_orders(query_results["q03_rolling_orders"])

    logger.info("Chart generation complete.")
    return paths

if __name__ == "__main__":
    from src.run_queries import run_all_queries
    results = run_all_queries()
    generate_all_charts(results)
