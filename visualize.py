"""
Swing Visualizer — Standalone with Pattern Overlays
Reads a results CSV, fetches OHLCV, generates annotated candlestick charts
with actual pattern shapes drawn on them.

Usage:
  python visualize.py --csv results_2026-05-09.csv
  python visualize.py --csv results_2026-05-09.csv --top 10
"""

import sys, os, argparse, warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import mplfinance as mpf
from datetime import date

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.fetcher import fetch_cached
from data.loader import _resample_weekly

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
#  LEVEL HELPERS
# ──────────────────────────────────────────────

def _hline(ax, y, color, label, linestyle="--", linewidth=1.2):
    ax.axhline(y=y, color=color, linestyle=linestyle, linewidth=linewidth, alpha=0.85)
    ax.annotate(
        f" {label}: {y:,.2f}",
        xy=(1.0, y), xycoords=("axes fraction", "data"),
        fontsize=7.5, color=color, va="center",
        bbox=dict(boxstyle="round,pad=0.2", fc="#0d1117", ec=color, alpha=0.8),
    )


def _shade_region(ax, x0, x1, y0, y1, color, alpha=0.12):
    ax.axvspan(x0, x1, ymin=0, ymax=1, color=color, alpha=0.0)  # no full span
    ax.fill_betweenx([y0, y1], x0, x1, color=color, alpha=alpha)


# ──────────────────────────────────────────────
#  PATTERN OVERLAY DRAWERS
# ──────────────────────────────────────────────

def _draw_cup_handle(ax, df_plot, breakout_level, pat_color):
    n = len(df_plot)
    closes = df_plot["Close"].values
    highs  = df_plot["High"].values
    lows   = df_plot["Low"].values
    xs     = np.arange(n)

    # Find cup region: last 60-70 bars, handle = last 15 bars
    handle_bars = min(15, n // 5)
    cup_end     = n - handle_bars
    cup_start   = max(0, cup_end - 65)

    cup_lows  = lows[cup_start:cup_end]
    cup_xs    = xs[cup_start:cup_end]
    bottom_i  = int(np.argmin(cup_lows))

    # Draw smooth cup arc using quadratic curve through 3 points
    if len(cup_xs) >= 5:
        x_left   = cup_xs[0]
        x_bottom = cup_xs[bottom_i]
        x_right  = cup_xs[-1]
        y_left   = highs[cup_start]
        y_bottom = cup_lows[bottom_i]
        y_right  = highs[cup_end - 1]

        # Bezier-style quadratic arc
        t = np.linspace(0, 1, 120)
        arc_x = (1 - t)**2 * x_left + 2 * (1 - t) * t * x_bottom + t**2 * x_right
        arc_y = (1 - t)**2 * y_left + 2 * (1 - t) * t * y_bottom + t**2 * y_right
        ax.plot(arc_x, arc_y, color=pat_color, linewidth=1.8, alpha=0.7,
                linestyle="-", zorder=3, label="Cup")

        # Shade cup interior
        ax.fill_between(arc_x, arc_y - (y_left - y_bottom) * 0.02, arc_y,
                         color=pat_color, alpha=0.07)

    # Draw handle box (last handle_bars bars)
    handle_xs   = xs[cup_end:]
    handle_high = float(np.max(highs[cup_end:]))
    handle_low  = float(np.min(lows[cup_end:]))
    rect = mpatches.FancyBboxPatch(
        (handle_xs[0] - 0.5, handle_low),
        handle_xs[-1] - handle_xs[0] + 1,
        handle_high - handle_low,
        boxstyle="round,pad=0.3",
        linewidth=1.4, edgecolor=pat_color, facecolor=pat_color, alpha=0.10,
    )
    ax.add_patch(rect)
    ax.text(handle_xs[0] + (handle_xs[-1] - handle_xs[0]) / 2,
            handle_high + (handle_high - handle_low) * 0.05,
            "Handle", fontsize=7, color=pat_color, ha="center", alpha=0.85)


def _draw_break_retest(ax, df_plot, breakout_level, pat_color):
    n = len(df_plot)
    closes = df_plot["Close"].values
    highs  = df_plot["High"].values
    lows   = df_plot["Low"].values
    xs     = np.arange(n)

    # Find where price first crossed above breakout (the breakout bar)
    breakout_bar = None
    for i in range(n - 1, max(n - 30, 0), -1):
        if closes[i] > breakout_level and (i == 0 or closes[i - 1] <= breakout_level):
            breakout_bar = i
            break
    if breakout_bar is None:
        for i in range(n - 1, max(n - 30, 0), -1):
            if highs[i] > breakout_level * 1.01:
                breakout_bar = i
                break

    if breakout_bar:
        # Vertical marker at breakout bar
        ax.axvline(x=breakout_bar, color=pat_color, linewidth=1.5,
                   linestyle="-", alpha=0.6, zorder=2)
        ax.text(breakout_bar, breakout_level * 1.005, " Breakout",
                fontsize=7, color=pat_color, va="bottom", alpha=0.9)

    # Shade retest zone: between breakout level and current close
    cur = float(closes[-1])
    zone_top = max(cur, breakout_level) * 1.015
    zone_bot = breakout_level * 0.985
    ax.fill_between(xs, zone_bot, zone_top,
                    where=np.ones(n, dtype=bool),
                    color=pat_color, alpha=0.06)
    ax.annotate("Retest Zone", xy=(n - 1, (zone_top + zone_bot) / 2),
                fontsize=7, color=pat_color, ha="right", va="center", alpha=0.8)


def _draw_channel(ax, df_plot, breakout_level, pat_color):
    n = len(df_plot)
    highs = df_plot["High"].values
    lows  = df_plot["Low"].values
    xs    = np.arange(n)

    window = 4
    swing_hi_idx, swing_hi_val = [], []
    swing_lo_idx, swing_lo_val = [], []

    for i in range(window, n - window):
        if highs[i] == max(highs[i - window: i + window + 1]):
            swing_hi_idx.append(i)
            swing_hi_val.append(highs[i])
        if lows[i] == min(lows[i - window: i + window + 1]):
            swing_lo_idx.append(i)
            swing_lo_val.append(lows[i])

    if len(swing_hi_idx) < 2 or len(swing_lo_idx) < 2:
        return

    h_slope, h_int = np.polyfit(swing_hi_idx, swing_hi_val, 1)
    l_slope, l_int = np.polyfit(swing_lo_idx, swing_lo_val, 1)

    upper = h_slope * xs + h_int
    lower = l_slope * xs + l_int

    ax.plot(xs, upper, color=pat_color, linewidth=1.6, linestyle="--",
            alpha=0.75, label="Upper Channel", zorder=3)
    ax.plot(xs, lower, color=pat_color, linewidth=1.6, linestyle="--",
            alpha=0.75, label="Lower Channel", zorder=3)
    ax.fill_between(xs, lower, upper, color=pat_color, alpha=0.07)

    ax.text(2, upper[2] + (upper[2] - lower[2]) * 0.05,
            "Channel", fontsize=7.5, color=pat_color, alpha=0.85)


def _draw_triangle(ax, df_plot, breakout_level, pat_color, pattern):
    n = len(df_plot)
    highs = df_plot["High"].values
    lows  = df_plot["Low"].values
    xs    = np.arange(n)

    window = 3
    swing_hi_idx, swing_hi_val = [], []
    swing_lo_idx, swing_lo_val = [], []

    for i in range(window, n - window):
        if highs[i] == max(highs[i - window: i + window + 1]):
            swing_hi_idx.append(i)
            swing_hi_val.append(highs[i])
        if lows[i] == min(lows[i - window: i + window + 1]):
            swing_lo_idx.append(i)
            swing_lo_val.append(lows[i])

    if len(swing_hi_idx) < 2 or len(swing_lo_idx) < 2:
        return

    h_slope, h_int = np.polyfit(swing_hi_idx, swing_hi_val, 1)
    l_slope, l_int = np.polyfit(swing_lo_idx, swing_lo_val, 1)

    upper = h_slope * xs + h_int
    lower = l_slope * xs + l_int

    ax.plot(xs, upper, color=pat_color, linewidth=1.5, linestyle="-",
            alpha=0.75, zorder=3)
    ax.plot(xs, lower, color=pat_color, linewidth=1.5, linestyle="-",
            alpha=0.75, zorder=3)
    ax.fill_between(xs, lower, upper, color=pat_color, alpha=0.08)

    label = "Flat Resistance" if pattern == "Ascending Triangle" else "Converging"
    ax.text(xs[len(xs) // 3], upper[len(xs) // 3] * 1.005,
            label, fontsize=7, color=pat_color, alpha=0.85)


def _draw_sr_zone(ax, df_plot, breakout_level, pat_color, pattern):
    n = len(df_plot)
    xs = np.arange(n)

    zone_top = breakout_level * 1.02
    zone_bot = breakout_level * 0.98

    ax.fill_between(xs, zone_bot, zone_top,
                    color=pat_color, alpha=0.15)
    ax.axhline(y=breakout_level, color=pat_color,
               linewidth=1.4, linestyle="-", alpha=0.6)

    label = "Support Zone" if pattern == "S&R Support" else "Resistance Zone"
    ax.text(2, breakout_level * 1.022, label,
            fontsize=7.5, color=pat_color, alpha=0.85)


def _draw_darvas_box(ax, df_plot, breakout_level, pat_color):
    n = len(df_plot)
    highs = df_plot["High"].values
    lows  = df_plot["Low"].values
    xs    = np.arange(n)

    # Box: recent 20-bar high/low as the box boundary
    lookback = min(30, n)
    box_top = float(np.max(highs[-lookback:]))
    box_bot = float(np.min(lows[-lookback:]))
    box_start = n - lookback

    rect = mpatches.Rectangle(
        (box_start - 0.5, box_bot),
        lookback,
        box_top - box_bot,
        linewidth=1.5, edgecolor=pat_color,
        facecolor=pat_color, alpha=0.08, zorder=2,
    )
    ax.add_patch(rect)
    ax.text(box_start + lookback / 2, box_top * 1.003,
            "Darvas Box", fontsize=7.5, color=pat_color,
            ha="center", alpha=0.85)


def _draw_flag(ax, df_plot, breakout_level, pat_color):
    n = len(df_plot)
    highs  = df_plot["High"].values
    lows   = df_plot["Low"].values
    closes = df_plot["Close"].values
    xs     = np.arange(n)

    # Flagpole: sharp move up in last 15-30 bars before consolidation
    flag_bars  = min(15, n // 4)
    pole_start = max(0, n - flag_bars - 20)
    pole_end   = max(0, n - flag_bars)

    if pole_start < pole_end:
        pole_low  = float(np.min(lows[pole_start:pole_end]))
        pole_high = float(np.max(highs[pole_start:pole_end]))
        ax.annotate("", xy=(pole_end, pole_high),
                    xytext=(pole_start, pole_low),
                    arrowprops=dict(arrowstyle="->", color=pat_color,
                                   lw=1.5, alpha=0.7))
        ax.text(pole_start + (pole_end - pole_start) // 2,
                (pole_high + pole_low) / 2,
                " Pole", fontsize=7, color=pat_color, alpha=0.8)

    # Flag: consolidation (last flag_bars)
    flag_xs   = xs[-flag_bars:]
    flag_high = float(np.max(highs[-flag_bars:]))
    flag_low  = float(np.min(lows[-flag_bars:]))
    rect = mpatches.Rectangle(
        (flag_xs[0] - 0.5, flag_low),
        flag_bars,
        flag_high - flag_low,
        linewidth=1.3, edgecolor=pat_color,
        facecolor=pat_color, alpha=0.10, zorder=2,
    )
    ax.add_patch(rect)
    ax.text(flag_xs[0] + flag_bars / 2, flag_high * 1.002,
            "Flag", fontsize=7, color=pat_color, ha="center", alpha=0.85)


PATTERN_DRAWERS = {
    "Cup & Handle":          _draw_cup_handle,
    "Cup & Handle (Weekly)": _draw_cup_handle,
    "Break & Retest":        _draw_break_retest,
    "Channel Breakout":      _draw_channel,
    "Ascending Triangle":    _draw_triangle,
    "Symmetrical Triangle":  _draw_triangle,
    "Darvas Box":            _draw_darvas_box,
    "S&R Support":           _draw_sr_zone,
    "S&R Breakout":          _draw_sr_zone,
    "Bullish Flag":          _draw_flag,
    "Bullish Pennant":       _draw_flag,
}


# ──────────────────────────────────────────────
#  CHART GENERATOR
# ──────────────────────────────────────────────

def generate_chart(row, df, out_dir, tail_bars=80, timeframe="daily"):
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

    df_plot = df.tail(tail_bars).copy()
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

    # ── Pattern shape overlay ──
    drawer = PATTERN_DRAWERS.get(pattern)
    if drawer:
        try:
            if pattern in ("Ascending Triangle", "Symmetrical Triangle", "S&R Support", "S&R Breakout"):
                drawer(ax, df_plot, breakout, pat_color, pattern)
            else:
                drawer(ax, df_plot, breakout, pat_color)
        except Exception:
            pass  # never let overlay crash the chart

    # ── Key level lines ──
    _hline(ax, breakout, "#ffd700", "Breakout", linestyle="-",  linewidth=1.8)
    _hline(ax, target,   "#56d364", "Target",   linestyle="--", linewidth=1.2)
    _hline(ax, stop,     "#f78166", "Stop",     linestyle="--", linewidth=1.2)
    _hline(ax, cmp,      "#c9d1d9", "CMP",      linestyle=":",  linewidth=0.9)

    # ── Title ──
    sym_clean = symbol.replace(".NS", "").replace(".BO", "")
    fig.suptitle(
        f"{sym_clean}  |  {pattern}  |  {timeframe.upper()}  |  Score: {score:.0f}  |  RR: {rr}  |  Upside: {upside}%  |  RSI: {rsi}",
        fontsize=11, color="#c9d1d9", fontweight="bold", y=0.98,
    )

    # ── Reasons strip ──
    if reasons and reasons != "nan":
        ax.text(
            0.01, 0.03, reasons,
            transform=ax.transAxes,
            fontsize=7, color="#8b949e",
            bbox=dict(boxstyle="round,pad=0.3", fc="#161b22", ec="#30363d", alpha=0.9),
            verticalalignment="bottom",
        )

    # ── Pattern badge ──
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
    parser.add_argument("--csv",       required=True, help="Path to results CSV from screener")
    parser.add_argument("--top",       type=int, default=15)
    parser.add_argument("--outdir",    default=CHARTS_DIR)
    parser.add_argument("--timeframe", choices=["daily", "weekly"], default="daily")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"CSV not found: {args.csv}")
        sys.exit(1)

    tf = args.timeframe
    days = 400 if tf == "weekly" else 120
    tail_bars = 60 if tf == "weekly" else 80

    dated_dir = os.path.join(args.outdir, str(date.today()), tf)
    os.makedirs(dated_dir, exist_ok=True)
    args.outdir = dated_dir

    print(f"Reading: {args.csv}")
    print(f"Timeframe: {tf.upper()}\n")
    results = pd.read_csv(args.csv).head(args.top)
    print(f"Generating charts for {len(results)} stocks...\n")

    ok = fail = 0
    for _, row in results.iterrows():
        sym = row["symbol"]
        print(f"  {sym}...", end=" ", flush=True)
        try:
            df = fetch_cached(sym, days=days)
            if tf == "weekly":
                df = _resample_weekly(df) if df is not None else None
            if df is None or len(df) < 40:
                print("no data")
                fail += 1
                continue
            fname = generate_chart(row, df, args.outdir, tail_bars=tail_bars, timeframe=tf)
            print(f"saved -> {os.path.basename(fname)}")
            ok += 1
        except Exception as e:
            print(f"err: {e}")
            fail += 1

    print(f"\nDone. {ok} charts saved to: {args.outdir}")
    if fail:
        print(f"  {fail} skipped.")


if __name__ == "__main__":
    main()
