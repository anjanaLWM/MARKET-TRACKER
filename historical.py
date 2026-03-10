import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional

# Mapping from internal/Finnhub symbols to Yahoo Finance tickers.
# NB: Yahoo-only symbols (those without OANDA: or BINANCE: prefix in config.py)
#     map directly to themselves, but we list them here explicitly for clarity.
YFINANCE_TICKERS: Dict[str, str] = {
    # Precious metals & base metals
    "OANDA:XAU_USD":    "GC=F",      # Gold
    "OANDA:XAG_USD":    "SI=F",      # Silver
    "OANDA:XCU_USD":    "HG=F",      # Copper
    "OANDA:XPT_USD":    "PL=F",      # Platinum
    "OANDA:XPD_USD":    "PA=F",      # Palladium
    # Energy
    "OANDA:BCO_USD":    "BZ=F",      # Brent Crude
    "OANDA:WTICO_USD":  "CL=F",      # WTI Crude
    "OANDA:NATGAS_USD": "NG=F",      # Natural Gas
    # Agriculture
    "OANDA:WHEAT_USD":  "ZW=F",      # Wheat
    "OANDA:CORN_USD":   "ZC=F",      # Corn
    "OANDA:SOYBN_USD":  "ZS=F",      # Soybeans
    "OANDA:SUGAR_USD":  "SB=F",      # Sugar
    # Bonds
    "OANDA:USB10Y_USD": "^TNX",      # US 10Y
    "OANDA:USB30Y_USD": "^TYX",      # US 30Y
    # Indices
    "OANDA:US30_USD":   "^DJI",      # Dow Jones
    "OANDA:NAS100_USD": "^IXIC",     # Nasdaq
    "OANDA:SPX500_USD": "^GSPC",     # S&P 500
    "OANDA:DE30_EUR":   "^GDAXI",    # DAX
    "OANDA:UK100_GBP":  "^FTSE",     # FTSE 100
    # Asian indices
    "OANDA:JP225_USD":  "^N225",     # Nikkei 225
    "OANDA:KR200_USD":  "^KS11",     # KOSPI
    "OANDA:HK33_HKD":   "^HSI",      # Hang Seng
    "OANDA:CN50_USD":   "000001.SS", # Shanghai Composite
    # Risk factors
    "OANDA:VIX_USD":    "^VIX",      # VIX
    "OANDA:USDOLLAR":   "DX=F",      # US Dollar Index
    # Crypto
    "BINANCE:BTCUSDT":  "BTC-USD",
    "BINANCE:ETHUSDT":  "ETH-USD",
    "BINANCE:SOLUSDT":  "SOL-USD",
    # Yahoo-polled only
    "^NSEI":            "^NSEI",     # Nifty 50 (moved from OANDA:IN50_USD)
    "^BSESN":           "^BSESN",   # BSE Sensex
    "LNG":               "LNG",       # LNG proxy (Cheniere Energy); JKM=F is delisted
    "LIT":              "LIT",      # Lithium & Cobalt ETF
    "VLO":              "VLO",      # Bitumen proxy (Valero Energy)
    "EPD":              "EPD",      # Propane & Butane proxy (Enterprise Products)
    "BTU":              "BTU",      # Coal proxy (Peabody Energy)
    "DC=F":             "DC=F",     # Milk Powder futures
    "CF":               "CF",       # Urea proxy (CF Industries)
    "MLM":              "MLM",      # Clinker proxy (Martin Marietta Materials)
}


def get_historical_prices(
    symbol: str,
    start: datetime,
    end: datetime,
    api_token: Optional[str] = None,
) -> List[Dict]:
    """
    Fetch historical OHLCV candles using yfinance.
    Returns a list of { "date": ISO8601, "price": float }.
    Returns an empty list on any error so callers can handle gracefully.
    """
    ticker = YFINANCE_TICKERS.get(symbol)
    if not ticker:
        # Fallback: strip any exchange prefix (e.g. "OANDA:XAU_USD" → "XAU_USD")
        ticker = symbol.split(":")[-1] if ":" in symbol else symbol

    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[historical] Fetching {symbol} → {ticker}")

    try:
        data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)

        if data.empty:
            logger.warning(f"[historical] No data for ticker={ticker}")
            return []

        result = []
        for index, row in data.iterrows():
            try:
                # After auto_adjust=True the column may be a MultiIndex; handle both
                close_val = row["Close"]
                if hasattr(close_val, "iloc"):
                    close_val = close_val.iloc[0]
                price = float(close_val)
                result.append({
                    "date": index.strftime("%Y-%m-%dT%H:%M:%S"),
                    "price": price,
                })
            except Exception as row_err:
                logger.warning(f"[historical] Skipping row for {ticker}: {row_err}")

        logger.info(f"[historical] Retrieved {len(result)} points for {ticker}")
        return result

    except Exception as e:
        logger.error(f"[historical] Error fetching {ticker}: {e}")
        return []


if __name__ == "__main__":
    from datetime import timedelta
    end = datetime.now()
    start = end - timedelta(days=30)
    res = get_historical_prices("OANDA:XAU_USD", start, end)
    print(res[:5])