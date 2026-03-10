import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import SYMBOL_MAP, CATEGORIES, WS_EXCLUDED_SYMBOLS
from PricesStore import PricesStore
from WebSocket import WebSocketManager
from NewsStore import NewsStore
from historical import get_historical_prices
from news import fetch_commodity_news_async

# ── Logging Setup ───────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Load Environment ────────────────────────────────────────────────────────
load_dotenv()
finhub_api_key = os.getenv("FinHubAPI")

# ── Global Stores ───────────────────────────────────────────────────────────
price_store = PricesStore()
news_store = NewsStore(api_token=finhub_api_key)
# WebSocket symbols: OANDA/BINANCE prefixed, minus any explicitly excluded ones
ws_symbols = [
    s for s in SYMBOL_MAP.keys()
    if (s.startswith("OANDA:") or s.startswith("BINANCE:"))
    and s not in WS_EXCLUDED_SYMBOLS
]
# Yahoo-polled: everything not going through the WebSocket
yahoo_symbols = [s for s in SYMBOL_MAP.keys() if s not in ws_symbols]

websocket_manager = WebSocketManager(
    symbols=ws_symbols,
    store=price_store,
    FINNHUB_TOKEN=finhub_api_key,
    excluded_symbols=WS_EXCLUDED_SYMBOLS,
)


# ── Historical Cache ────────────────────────────────────────────────────────
historical_cache = {}
CACHE_TTL = timedelta(minutes=60)

RANGE_MAP = {
    "1M": timedelta(days=30),
    "3M": timedelta(days=90),
    "6M": timedelta(days=180),
    "1Y": timedelta(days=365),
    "5Y": timedelta(days=365*5),
    "MAX": timedelta(days=365*10),
}

import yfinance as yf
def get_current_yahoo_price(symbol: str) -> Optional[Dict]:
    """
    Fetch the current price for a symbol via yfinance.
    fast_info is NOT a dict — access its attributes via getattr.
    Falls back to recent 1-day history if fast_info attributes are unavailable.
    """
    from historical import YFINANCE_TICKERS
    ticker = YFINANCE_TICKERS.get(symbol, symbol)
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info  # LazyTimedCache object, NOT a dict

        # Try preferred attribute, then fallback attribute
        price = getattr(info, 'last_price', None)
        if price is None:
            price = getattr(info, 'regular_market_price', None)

        if price is None:
            # Last resort: pull the most recent close from 1-day history
            hist = t.history(period="1d")
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])

        if price is not None and float(price) > 0:
            return {
                "p": float(price),
                "v": 0.0,
                "t": int(datetime.now().timestamp() * 1000),
            }
        else:
            logger.warning(f"[Yahoo] No valid price for {symbol} (ticker={ticker})")
    except Exception as e:
        logger.error(f"[Yahoo] Error polling {symbol} (ticker={ticker}): {e}")
    return None


# ── Background Tasks ────────────────────────────────────────────────────────
async def news_fetcher_task():
    """Periodically fetches news to keep the store updated."""
    while True:
        try:
            logger.info("Background news fetch triggered")
            await news_store.update_news()
        except Exception as e:
            logger.error(f"Error in background news fetch: {e}")
        
        await asyncio.sleep(600) # Fetch every 10 minutes

async def yahoo_poller_task():
    """Periodically fetches prices from Yahoo Finance for non-WS symbols."""
    while True:
        if not yahoo_symbols:
            break
        
        logger.info(f"Polling Yahoo Finance for {len(yahoo_symbols)} symbols")
        # Run in executor to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        for sym in yahoo_symbols:
            try:
                data = await loop.run_in_executor(None, get_current_yahoo_price, sym)
                if data:
                    price_store.update(
                        raw_symbol=sym,
                        price=data["p"],
                        volume=data["v"],
                        ts_ms=data["t"]
                    )
            except Exception as e:
                logger.error(f"Failed to poll {sym}: {e}")
        
        await asyncio.sleep(120) # Poll every 2 minutes

async def cache_cleanup_task():
    """Periodically cleans up the historical data cache."""
    while True:
        now = datetime.now()
        expired_keys = [k for k, (ts, _) in historical_cache.items() if now - ts > CACHE_TTL]
        for k in expired_keys:
            del historical_cache[k]
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        await asyncio.sleep(1800) # Every 30 minutes

# ── Lifespan Manager ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    loop = asyncio.get_running_loop()
    websocket_manager.start(loop)
    
    # Start background tasks
    news_task = asyncio.create_task(news_fetcher_task())
    cleanup_task = asyncio.create_task(cache_cleanup_task())
    yahoo_task = asyncio.create_task(yahoo_poller_task())
    
    logger.info("Application started, background tasks running")
    yield
    
    # Shutdown
    await websocket_manager.stop()
    news_task.cancel()
    cleanup_task.cancel()
    yahoo_task.cancel()
    logger.info("Application shutting down")

# ── FastAPI App ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Live Market Data API",
    version="1.1.0",
    description="Optimized API for fetching live market data",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Endpoints ───────────────────────────────────────────────────────────────
@app.get("/prices")
async def get_all_prices():
    """Return latest prices for every tracked symbol."""
    return {
        "data": price_store.get_all(),
        "categories": CATEGORIES,
        "server_time": datetime.now().isoformat() + "Z"
    }

@app.get("/prices/{symbol_name}")
async def get_symbol_price(symbol_name: str):
    """Return latest price for a single symbol."""
    record = price_store.get_symbol(symbol_name)
    if record is None:
        return JSONResponse(status_code=404, content={"error": f"Symbol '{symbol_name}' not found."})
    return record

@app.get("/news")
async def get_news(since_timestamp: Optional[str] = None):
    """Return news strictly newer than since_timestamp (optional)."""
    # Note: NewsStore.get_news_since is still technically synchronous
    # but it's called in a thread-safe way.
    return news_store.get_news_since(since_timestamp)

@app.get("/api/historical")
async def get_historical(symbol: str, range: str = "1Y"):
    """Return historical prices for a symbol."""
    actual_symbol = None
    for sym_key, name in SYMBOL_MAP.items():
        if name.upper() == symbol.upper() or sym_key.upper() == symbol.upper():
            actual_symbol = sym_key
            break
            
    if not actual_symbol:
        raise HTTPException(status_code=400, detail=f"Invalid symbol: {symbol}")
        
    range_delta = RANGE_MAP.get(range.upper(), RANGE_MAP["1Y"])
    now = datetime.now()
    start_date = now - range_delta
    
    cache_key = (actual_symbol, range.upper())
    if cache_key in historical_cache:
        ts, cached_data = historical_cache[cache_key]
        if now - ts < CACHE_TTL:
            return {"symbol": symbol, "range": range, "data": cached_data, "cached": True}
            
    # Fetch from Yahoo Finance (synchronous, but in a thread pool by FastAPI if def, 
    # but here it's async def, so it will block. Let's run it in a thread pool).
    loop = asyncio.get_running_loop()
    try:
        data = await loop.run_in_executor(None, get_historical_prices, actual_symbol, start_date, now)
        if data:
            historical_cache[cache_key] = (now, data)
            return {"symbol": symbol, "range": range, "data": data, "cached": False}
        else:
            raise HTTPException(status_code=404, detail="No historical data available.")
    except Exception as e:
        logger.error(f"Error fetching historical: {e}")
        raise HTTPException(status_code=500, detail="Internal server error fetching historical data.")

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "tracked_symbols": len(SYMBOL_MAP),
        "active_prices": len(price_store.get_all()),
        "ws_active": websocket_manager._task is not None and not websocket_manager._task.done(),
        "ws_token_configured": bool(finhub_api_key),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
