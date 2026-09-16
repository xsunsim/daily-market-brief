#!/usr/bin/env python3
"""Generate today's US market brief.

Run by GitHub Actions every trading day after market close. Fetches daily
candles from Yahoo Finance (free, no key), writes reports/YYYY-MM-DD.md, and
updates README.md with the latest numbers. Exits quietly when there is no
fresh data (market closed), so no empty commit is made.
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(REPO_ROOT, "reports")

INDICES = {"^GSPC": "S&P 500", "^NDX": "Nasdaq 100", "^DJI": "Dow Jones"}
STOCKS = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "Nvidia",
    "TSLA": "Tesla",
    "META": "Meta",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet",
}
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


def fetch_daily(symbol):
    """Return [(date_str_et, close), ...] for recent trading days."""
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        + urllib.parse.quote(symbol, safe="")
        + "?interval=1d&range=5d"
    )
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    result = data["chart"]["result"][0]
    closes = result["indicators"]["quote"][0]["close"]
    out = []
    for ts, close in zip(result["timestamp"], closes):
        if close is None:
            continue
        day = datetime.fromtimestamp(ts, ET).strftime("%Y-%m-%d")
        out.append((day, close))
    return out


def row(name, days):
    latest_close = days[-1][1]
    prev_close = days[-2][1] if len(days) > 1 else None
    if prev_close:
        pct = (latest_close - prev_close) / prev_close * 100
        change = f"{'+' if pct >= 0 else ''}{pct:.2f}%"
    else:
        change = "—"
    return (name, f"{latest_close:,.2f}", change)


def table(rows):
    lines = ["| | Close | Day |", "|---|---|---|"]
    lines += [f"| {n} | {c} | {ch} |" for n, c, ch in rows]
    return "\n".join(lines)


def main():
    today = datetime.now(ET).strftime("%Y-%m-%d")
    series = {}
    for sym in list(INDICES) + list(STOCKS):
        days = fetch_daily(sym)
        if not days:
            raise RuntimeError(f"no data for {sym}")
        series[sym] = days

    if series["^GSPC"][-1][0] != today:
        print(f"No fresh data for {today} (market closed) — skipping.")
        return

    os.makedirs(REPORTS_DIR, exist_ok=True)
    index_rows = [row(n, series[s]) for s, n in INDICES.items()]
    stock_rows = [row(n, series[s]) for s, n in STOCKS.items()]

    weekday = datetime.now(ET).strftime("%A, %B %d, %Y")
    report = f"""# Market Brief — {weekday}

## Indices

{table(index_rows)}

## Big Tech

{table(stock_rows)}

_Data: Yahoo Finance. Generated automatically after market close._
"""
    with open(os.path.join(REPORTS_DIR, f"{today}.md"), "w") as f:
        f.write(report)

    archive = sorted(
        (fn[:-3] for fn in os.listdir(REPORTS_DIR) if fn.endswith(".md")),
        reverse=True,
    )[:10]
    archive_lines = "\n".join(f"- [{d}](reports/{d}.md)" for d in archive)
    readme = f"""# Daily Market Brief

US market snapshot, auto-generated every trading day after close.

## Latest — {today}

### Indices

{table(index_rows)}

### Big Tech

{table(stock_rows)}

## Archive

{archive_lines}
"""
    with open(os.path.join(REPO_ROOT, "README.md"), "w") as f:
        f.write(readme)
    print(f"Wrote report for {today}.")


if __name__ == "__main__":
    main()
