"""
test_fetch.py - Verification script for the yahoo poller fix.
Run with: python test_fetch.py   (from the project root with venv activated)
"""
import sys
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.WARNING)  # Suppress yfinance noise

# ── Import project modules ────────────────────────────────────────────────────
from config import SYMBOL_MAP, WS_EXCLUDED_SYMBOLS
from historical import YFINANCE_TICKERS, get_historical_prices

# Re-use the same function from main.py without importing FastAPI
import yfinance as yf
from typing import Optional, Dict

def get_current_yahoo_price(symbol: str) -> Optional[Dict]:
    ticker = YFINANCE_TICKERS.get(symbol, symbol)
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        price = getattr(info, "last_price", None)
        if price is None:
            price = getattr(info, "regular_market_price", None)
        if price is None:
            hist = t.history(period="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
        if price is not None and float(price) > 0:
            return {"p": float(price), "ticker": ticker}
    except Exception as e:
        print(f"  ERROR {symbol} ({ticker}): {e}")
    return None

# ── Determine yahoo-only symbols ──────────────────────────────────────────────
ws_symbols = {
    s for s in SYMBOL_MAP
    if (s.startswith("OANDA:") or s.startswith("BINANCE:"))
    and s not in WS_EXCLUDED_SYMBOLS
}
yahoo_symbols = [s for s in SYMBOL_MAP if s not in ws_symbols]

print(f"\n{'='*60}")
print(f" Yahoo Finance Price Fetch Test ({len(yahoo_symbols)} symbols)")
print(f"{'='*60}")

passed, failed = 0, 0
for sym in yahoo_symbols:
    result = get_current_yahoo_price(sym)
    name = SYMBOL_MAP[sym]
    ticker = YFINANCE_TICKERS.get(sym, sym)
    if result:
        print(f"  PASS  {name:<22} ({ticker:<12})  price = {result['p']:.4f}")
        passed += 1
    else:
        print(f"  FAIL  {name:<22} ({ticker:<12})  NO DATA")
        failed += 1

print(f"\n{'-'*60}")
print(f"  Results: {passed} passed / {failed} failed out of {len(yahoo_symbols)} symbols")

# ── Historical data spot-check ────────────────────────────────────────────────
print(f"\n{'='*60}")
print(" Historical Data Spot-check (GOLD, ^NSEI, BTU)")
print(f"{'='*60}")
end = datetime.now()
start = end - timedelta(days=7)
for sym in ["OANDA:XAU_USD", "^NSEI", "BTU"]:
    data = get_historical_prices(sym, start, end)
    name = SYMBOL_MAP.get(sym, sym)
    if data:
        print(f"  PASS  {name} -- {len(data)} data points, latest = {data[-1]['price']:.4f}")
    else:
        print(f"  FAIL  {name} -- NO HISTORICAL DATA")

print(f"\n{'='*60}")
sys.exit(0 if failed == 0 else 1)
