import asyncio
import json
import os
import threading
from typing import Optional
import websocket


class WebSocketManager:
    def __init__(self, symbols: list[str], store: "PricesStore", FINNHUB_TOKEN: str):
        self.symbols = symbols
        self.store = store
        self.FINNHUB_TOKEN = FINNHUB_TOKEN
        self.ws = None
        self.thread = None
        self.running = False
        self._ws_thread: Optional[threading.Thread] = None

    def on_message(self,ws,message):
        try:
            data = json.loads(message)
            if data.get("type") == "trade":
                for trade in data.get("data", []):
                    self.store.update(
                        raw_symbol=trade.get("s", ""),
                        price=float(trade.get("p", 0)),
                        volume=float(trade.get("v", 0)),
                        ts_ms=int(trade.get("t", 0))
                    )
        except Exception as e:
            print(f"Error processing message: {e}")

    def on_error(self,ws, error):
        print(f"Error: {error}")
    
    def on_close(self,ws,code,msg):
        print(f"[WS] closed: {code} {msg}")
    
    def on_open(self,ws):
        print("[WS] connected to Finnhub")
        for symbol in self.symbols:
            ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))

    def start_websocket(self):
        if not self.FINNHUB_TOKEN:
            raise ValueError("FINNHUB_TOKEN is not set")

        def _run():
            websocket.enableTrace(True)
            self.ws = websocket.WebSocketApp(
                f"wss://ws.finnhub.io?token={self.FINNHUB_TOKEN}",
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
            )
            self.ws.run_forever(ping_interval=20, ping_payload=10)
        
        _ws_thread = threading.Thread(target=_run, daemon=True)
        _ws_thread.start()
        self._ws_thread = _ws_thread

