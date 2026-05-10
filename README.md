# Swing Visualizer

Generates candlestick charts for swing trading setups detected by swing-screener-v2. Reads the screener's CSV output and produces annotated charts with pattern overlays, moving averages, and volume bars.

---

## Quick Start

Double-click `run_visualizer.bat`

```
Prompts:
  1. Daily  (120 candles, 6 months of price history)
  2. Weekly (60 candles, resampled from daily data)

Charts saved to: charts/YYYY-MM-DD/daily/   or   charts/YYYY-MM-DD/weekly/
```

---

## Installation

```bash
git clone https://github.com/karthik0419/swing-visualizer
cd swing-visualizer
pip install -r requirements.txt
```

**requirements.txt**
```
pandas
numpy
yfinance
mplfinance
matplotlib
jugaad-data
```

---

## How to Run

### Option 1 — BAT file (recommended)
```
Double-click run_visualizer.bat
  -> prompts Daily or Weekly
  -> auto-picks latest results_*.csv from swing-screener-v2
  -> generates all charts, prints output path
```

### Option 2 — Command line
```bash
# Daily charts from a specific CSV
python visualize.py --csv path/to/results.csv --timeframe daily

# Weekly charts
python visualize.py --csv path/to/results.csv --timeframe weekly

# Specify output folder
python visualize.py --csv results.csv --timeframe daily --outdir my_charts

# Single stock
python visualize.py --symbols TITAN BHARATFORG --timeframe daily
```

---

## Output

Charts are saved to dated folders so you can track setups day by day:

```
charts/
  2026-05-10/
    daily/
      TITAN.png
      BHARATFORG.png
      GMRAIRPORT.png
      ...
    weekly/
      TITAN.png
      BHARATFORG.png
      ...
  2026-05-09/
    daily/
      ...
```

Each chart contains:
- Candlestick OHLCV
- 20-day and 50-day moving averages
- Volume bars (color-coded: green up days / red down days)
- Pattern overlay shape (Cup & Handle arc, Triangle lines, Channel bounds, S&R zones etc.)
- Pattern name, entry, stop, target annotated in the title
- Timeframe label (Daily / Weekly) in chart title

---

## Chart Patterns Visualized

| Pattern | Overlay |
|---------|---------|
| Cup & Handle | Arc curve over cup, box over handle |
| Darvas Box | Horizontal box around consolidation |
| Flag / Pennant | Parallel trendlines over flag pole |
| Breakout | Horizontal resistance line |
| Break & Retest | Resistance line + retest zone box |
| Ascending Triangle | Flat top + rising bottom trendlines |
| Symmetrical Triangle | Converging trendlines |
| S&R Levels | Horizontal support/resistance zones |
| Descending Channel | Parallel channel lines |

---

## Project Structure

```
swing-visualizer/
|
|-- visualize.py          # Main chart generator
|-- run_visualizer.bat    # One-click runner with timeframe prompt
|-- requirements.txt
|
|-- data/
|   |-- fetcher.py        # Price fetch via yfinance + disk cache
|   |-- __init__.py
|
|-- patterns/             # Pattern shape renderers (shared with screener)
|   |-- cup_handle.py
|   |-- darvas_box.py
|   |-- flags.py
|   |-- breakout.py
|   |-- break_retest.py
|   |-- triangle.py
|   |-- sr_levels.py
|   |-- channel.py
|   |-- retest.py
|   |-- double_top_bottom.py
|   |-- compression.py
|
|-- charts/               # Auto-generated output (gitignored)
|-- cache/                # Price data cache (gitignored)
```

---

## Version History

### v1.0 — Initial build (2026-05-08)
- Candlestick chart generation from screener CSV output
- MA20, MA50 overlays, volume bars
- Auto-reads `results_*.csv` from swing-screener-v2
- Charts saved flat to `charts/` folder

### v2.0 — Pattern overlays (2026-05-08)
- Added visual shape overlays for all 9 pattern types
- Cup & Handle: arc curve rendered over cup formation
- Triangle: trendlines drawn on chart
- Darvas Box: box rendered around consolidation zone
- Channel: parallel lines for descending channel
- S&R Levels: horizontal zone bands

### v3.0 — Timeframe selection + dated folders (2026-05-09)
- `--timeframe daily/weekly` argument added
- Weekly mode: fetches 400 days of data, resamples to weekly candles, plots 60 bars
- Daily mode: 120 candles (6 months)
- Charts saved to `charts/YYYY-MM-DD/daily/` and `charts/YYYY-MM-DD/weekly/`
  so each day's charts are isolated and comparable across days
- `run_visualizer.bat` updated to prompt for timeframe selection
- Timeframe shown in chart title

---

## Works With

This visualizer reads CSV output from **swing-screener-v2**. Point it at any `results_*.csv` file from that screener. The columns it needs: `symbol`, `pattern`, `entry`, `stop_loss`, `target`, `breakout`.

---

## Disclaimer

For educational and research purposes only. Not financial advice.
