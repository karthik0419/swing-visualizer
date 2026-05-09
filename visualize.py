"""
Swing Visualizer — Standalone
Reads a results CSV (from any screener), fetches OHLCV data independently,
and generates annotated candlestick charts saved as PNG files.

Usage:
  python visualize.py --csv results_2026-05-09.csv
  python visualize.py --csv results_2026-05-09.csv --top 10
  python visualize.py --csv results_2026-05-09.csv --outdir my_charts
"""

import sys, os, argparse, glob, warnings
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplfinance as mpf
from datetime import date

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.fetcher import fetch_cached

CHARTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)


# ──────────────────────────────────────────────
#  STYLE
# ──────────────────────────────────────────────

STYLE = mpf.make_mpf_style(
    base_mpf_style="nightclouds",
    facecolor="#0d1117",
    edgecolor="#30363d",
    figcolor="#0d1117",
    gridcolor="#21262d",
    gridstyle="--",
    rc={
        "axes.labelcolor": "#c9d1d9",
        "xtick.color": "#8b949e",
        "ytick.color": "#8b949e",
    },
)

PATTERN_COLOR = {
    "Cup & Handle":          "#00d4aa",
    "Cup & Handle (Weekly)": "#00d4aa",
    "Break & Retest":        "#f78166",
    "Channel Breakout":      "#d2a8ff",
    "Ascending Triangle":    "#ffa657",
    "Symmetrical Triangle":  "#ffa657",
    "Darvas Box":            "#79c0ff",
    "S&R Support":           "#56d364",
    "S&R Breakout":          "#56d364",
    "Bullish Flag":          "#e3b341",
    "Bullish Pennant":       "#e3b341",
    "Resistance Breakout":   "#f0883e",
    "No Pattern":            "#8b949e",
}


# ──────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────

def _hline(ax, y, color, label, linestyle="--", linewidth=1.2):
    ax.axhline(y=y, color=color, linestyle=linestyle, linewidth=linewidth, alpha=0.85)
    ax.annotate(
        f" {label}: {y:,.2f}",
        xy=(1.0, y), xycoords=("axes fraction", "data"),
        fontsize=7.5, color=color, va="center",
        bbox=dict(boxstyle="round,pad=0.2", fc="#0d1117", ec=color, alpha=0.8),
    )


# ──────────────────────────────────────────────
#  CHART
# ──────────────────────────────────────────────

def generate_chart(row, df, out_dir):
    symbol   = str(row["symbol"])
    pattern  = str(row["pattern"])
    cmp      = float(row["cmp"])
    breakout = float(row["breakout"])
    stop     = float(row["stop_loss"])
    target   = float(row["target"])
    rr       = float(row["rr"])
    score    = float(row["score"])
    upside   = float(row["upside_%"])
    rsi      = float(row["rsi"])
    reasons  = str(row.get("reasons", ""))

    df_plot = df.tail(80).copy()
    df_plot.index = pd.DatetimeIndex(df_plot.index)
    df_plot = df_plot[["Open", "High", "Low", "Close", "Volume"]].astype(float)

    pat_color = PATTERN_COLOR.get(pattern, "#8b949e")

    ma20 = df_plot["Close"].rolling(20).mean()
    ma50 = df_plot["Close"].rolling(50).mean()

    apds = [
        mpf.make_addplot(ma20, color="#f0883e", width=1.0, label="MA20"),
        mpf.make_addplot(ma50, color="#79c0ff", width=1.0, label="MA50"),
    ]

    fig, axes = mpf.plot(
        df_plot,
        type="candle",
        style=STYLE,
        addplot=apds,
        volume=True,
        returnfig=True,
        figsize=(14, 7),
        tight_layout=False,
        panel_ratios=(3, 1),
    )

    ax = axes[0]

    # Key levels
    _hline(ax, breakout, "#ffd700", "Breakout", linestyle="-",  linewidth=1.8)
    _hline(ax, target,   "#56d364", "Target",   linestyle="--", linewidth=1.2)
    _hline(ax, stop,     "#f78166", "Stop",     linestyle="--", linewidth=1.2)
    _hline(ax, cmp,      "#c9d1d9", "CMP",      linestyle=":",  linewidth=0.9)

    # Title
    sym_clean = symbol.replace(".NS", "").replace(".BO", "")
    fig.suptitle(
        f"{sym_clean}  |  {pattern}  |  Score: {score:.0f}  |  RR: {rr}  |  Upside: {upside}%  |  RSI: {rsi}",
        fontsize=11, color="#c9d1d9", fontweight="bold", y=0.98,
    )

    # Reasons strip
    if reasons and reasons != "nan":
        ax.text(
            0.01, 0.03, reasons,
            transform=ax.transAxes,
            fontsize=7, color="#8b949e",
            bbox=dict(boxstyle="round,pad=0.3", fc="#161b22", ec="#30363d", alpha=0.9),
            verticalalignment="bottom",
        )

    # Pattern badge
    ax.text(
        0.01, 0.97, f"  {pattern}  ",
        transform=ax.transAxes,
        fontsize=9, color="#0d1117", fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.4", fc=pat_color, ec=pat_color),
        verticalalignment="top",
    )

    plt.tight_layout(rect=[0, 0, 0.88, 0.96])

    fname = os.path.join(out_dir, f"{sym_clean}_{date.today()}.png")
    fig.savefig(fname, dpi=130, bbox_inches="tight", facecolor="#0d1117")
    plt.close(fig)
    return fname


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv",    required=True, help="Path to results CSV from screener")
    parser.add_argument("--top",    type=int, default=15)
    parser.add_argument("--outdir", default=CHARTS_DIR)
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"CSV not found: {args.csv}")
        sys.exit(1)

    os.makedirs(args.outdir, exist_ok=True)

    print(f"Reading: {args.csv}")
    results = pd.read_csv(args.csv).head(args.top)
    print(f"Generating charts for {len(results)} stocks...\n")

    ok = fail = 0
    for _, row in results.iterrows():
        sym = row["symbol"]
        print(f"  {sym}...", end=" ", flush=True)
        try:
            df = fetch_cached(sym, days=120)
            if df is None or len(df) < 40:
                print("no data")
                fail += 1
                continue
            fname = generate_chart(row, df, args.outdir)
            print(f"saved → {os.path.basename(fname)}")
            ok += 1
        except Exception as e:
            print(f"err: {e}")
            fail += 1

    print(f"\nDone. {ok} charts saved to: {args.outdir}")
    if fail:
        print(f"  {fail} skipped.")


if __name__ == "__main__":
    main()
