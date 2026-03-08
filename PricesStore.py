from datetime import datetime
from typing import Dict, Optional
import threading
from config import SYMBOL_MAP

class PricesStore:
    def __init__(self):
        self.data: Dict[str, Dict] = {}
        self.lock = threading.Lock()

    def update(self, raw_symbol: str, price: float, volume: float, ts_ms:int):
        name = SYMBOL_MAP.get(raw_symbol, raw_symbol)
        dt = datetime.fromtimestamp(ts_ms / 1000.0)
        time_str = dt.strftime("%H:%M:%S")
        date_str = dt.strftime("%Y-%m-%d")

        with self.lock:
            prev = self.data.get(name, {})
            prev_price = prev.get("price", price)
            change = price - prev_price 
            change_pct = (change / prev_price) * 100 if prev_price != 0 else 0
            
            self.data[name] = {
                "symbol": name,
                "raw_symbol": raw_symbol,
                "price": price,
                "volume": volume,
                "time": time_str,
                "date": date_str,
                "timestamp_ms": ts_ms,
                "change": round(change, 6),
                "change_pct": round(change_pct, 4),
                "direction": "up" if change >= 0 else "down",
            }
            
    def get_all(self) -> dict:
        with self.lock:
            return dict(self.data)

    def get_symbol(self, name: str) -> Optional[dict]:
        with self.lock:
            return self.data.get(name)