from typing import Dict, List

# ── Symbol map ────────────────────────────────────────────────────────────────
# Keys:
#   OANDA:xxx  / BINANCE:xxx  → subscribed via Finnhub WebSocket
#   All other keys            → polled via Yahoo Finance every 2 minutes
SYMBOL_MAP: Dict[str, str] = {
    # ── Precious metals & base metals ─────────────────────────────────────────
    "OANDA:XAU_USD":    "GOLD",
    "OANDA:XAG_USD":    "SILVER",
    "OANDA:XCU_USD":    "COPPER",
    "OANDA:XPT_USD":    "PLATINUM",
    "OANDA:XPD_USD":    "PALLADIUM",
    # ── Energy ────────────────────────────────────────────────────────────────
    "OANDA:BCO_USD":    "BRENT OIL",
    "OANDA:WTICO_USD":  "WTI OIL",
    "OANDA:NATGAS_USD": "NAT GAS",
    # ── Agriculture ───────────────────────────────────────────────────────────
    "OANDA:WHEAT_USD":  "WHEAT",
    "OANDA:CORN_USD":   "CORN",
    "OANDA:SOYBN_USD":  "SOYBEANS",
    "OANDA:SUGAR_USD":  "SUGAR",
    # ── Bonds ─────────────────────────────────────────────────────────────────
    "OANDA:USB10Y_USD": "US 10Y NOTE",
    "OANDA:USB30Y_USD": "US 30Y BOND",
    "OANDA:UK10YB_GBP": "UK 10Y GILT",
    "OANDA:DE10YB_EUR": "GER 10Y BUND",
    # ── Major indices ─────────────────────────────────────────────────────────
    "OANDA:US30_USD":   "DOW JONES",
    "OANDA:NAS100_USD": "NASDAQ 100",
    "OANDA:SPX500_USD": "S&P 500",
    "OANDA:DE30_EUR":   "DAX 30",
    "OANDA:UK100_GBP":  "UK 100",
    # ── Asian indices (streamed via OANDA where supported) ────────────────────
    "OANDA:JP225_USD":  "NIKKEI 225",
    "OANDA:KR200_USD":  "KOSPI 200",
    "OANDA:HK33_HKD":   "HANG SENG",
    "OANDA:CN50_USD":   "SHANGHAI COMP",
    # ── Risk factors ──────────────────────────────────────────────────────────
    "OANDA:VIX_USD":    "VIX",
    "OANDA:USDOLLAR":   "DXY",
    # ── Crypto ────────────────────────────────────────────────────────────────
    "BINANCE:BTCUSDT":  "BTC/USDT",
    "BINANCE:ETHUSDT":  "ETH/USDT",
    "BINANCE:SOLUSDT":  "SOL/USDT",   # Fixed: was "SOLUSDT", must match CATEGORIES
    # ── Yahoo-polled only (no WS support on free Finnhub tier) ───────────────
    "^NSEI":            "NIFTY 50",   # Moved from OANDA:IN50_USD (not on free WS)
    "^BSESN":           "BSE SENSEX",
    "LNG":               "LNG",             # Fixed: JKM=F delisted, using Cheniere Energy (LNG) as proxy
    "LIT":              "LITHIUM & COBALT",
    "VLO":              "BITUMEN",
    "EPD":              "PROPANE & BUTANE",  # Fixed: SPH is not a valid Yahoo ticker
    "BTU":              "COAL",              # Fixed: COAL is not a valid Yahoo ticker
    "DC=F":             "MILK POWDER",
    "CF":               "UREA",             # Fixed: UFV=F is not a valid Yahoo ticker
    "MLM":              "CLINKER",
}

# ── Known WS exclusions (bad symbols on Finnhub free tier) ────────────────────
# These are excluded from WebSocket subscriptions even if they have an OANDA: prefix.
WS_EXCLUDED_SYMBOLS: List[str] = [
    "OANDA:IN50_USD",   # Not supported on free Finnhub WebSocket tier
]

CATEGORIES: Dict[str, list] = {
    "Commodities": [
        "GOLD", "SILVER", "BRENT OIL", "WTI OIL", "NAT GAS",
        "COPPER", "WHEAT", "CORN", "SOYBEANS", "SUGAR", "PLATINUM", "PALLADIUM",
        "LNG", "LITHIUM & COBALT", "BITUMEN", "PROPANE & BUTANE", "COAL",
        "MILK POWDER", "UREA", "CLINKER",
    ],
    "Bonds": [
        "US 10Y NOTE", "US 30Y BOND", "UK 10Y GILT", "GER 10Y BUND",
    ],
    "Indices": [
        "DOW JONES", "NASDAQ 100", "S&P 500", "DAX 30", "UK 100",
        "NIKKEI 225", "KOSPI 200", "HANG SENG", "SHANGHAI COMP", "NIFTY 50", "BSE SENSEX",
    ],
    "Crypto": [
        "BTC/USDT", "ETH/USDT", "SOL/USDT",
    ],
    "Risk Factors": [
        "VIX", "DXY",
    ],
}
