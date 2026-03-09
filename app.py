"""
Live Market Data Dashboard – Streamlit Frontend
Optimized for performance and aesthetics.
"""

import os
import time
from datetime import datetime
import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

import technical

# ── Config ────────────────────────────────────────────────────────────────────
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DEFAULT_REFRESH_INTERVAL = 3000  # 3 seconds in milliseconds

CATEGORY_ICONS = {
    "Commodities": "🏅",
    "Bonds": "📊",
    "Indices": "📈",
    "Crypto": "🪙",
    "Risk Factors": "⚠️",
}

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Live Market Tracker",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Load CSS ──────────────────────────────────────────────────────────────────
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

if os.path.exists("style.css"):
    load_css("style.css")

# ── Helpers ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=2)
def fetch_prices() -> dict:
    try:
        r = requests.get(f"{BACKEND_URL}/prices", timeout=4)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "data": {}, "categories": {}}

def fetch_news(since=None) -> dict:
    url = f"{BACKEND_URL}/news"
    if since:
        url += f"?since_timestamp={since}"
    try:
        r = requests.get(url, timeout=4)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"items": [], "scraped_at": None, "error": str(e)}

@st.cache_data(ttl=60)
def fetch_historical(symbol: str, time_range: str = "1Y") -> dict:
    try:
        r = requests.get(f"{BACKEND_URL}/api/historical?symbol={symbol}&range={time_range}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "data": []}

def fmt_price(price: float, symbol: str) -> str:
    if symbol and any(c in symbol for c in ["BTC", "ETH", "SOL"]):
        return f"{price:,.2f}"
    if price >= 10_000:
        return f"{price:,.1f}"
    if price >= 100:
        return f"{price:,.2f}"
    return f"{price:,.4f}"

def render_card(record: dict) -> str:
    symbol  = record["symbol"]
    price   = record["price"]
    chg_pct = record.get("change_pct", 0)
    vol     = record.get("volume", 0)
    t       = record.get("time", "—")
    arrow   = "▲" if chg_pct >= 0 else "▼"
    cls     = "card-change-up" if chg_pct >= 0 else "card-change-down"

    return f"""
    <a href="/?symbol={symbol}" target="_self" style="text-decoration: none; color: inherit;">
        <div class="price-card">
            <div class="card-symbol">{symbol}</div>
            <div class="card-price">{fmt_price(price, symbol)}</div>
            <div class="{cls}">{arrow} {abs(chg_pct):.3f}%</div>
            <div class="card-time">🕐 {t}</div>
            <div class="card-vol">vol {vol:,.2f}</div>
        </div>
    </a>
    """

def render_no_data() -> str:
    return '<div class="price-card"><div class="no-data">⏳ Waiting for data…</div></div>'

def render_historical_page(symbol: str):
    if st.button("← Back to Dashboard"):
        st.query_params.clear()
        st.rerun()
    
    st.markdown(f'<div class="dash-title">📉 {symbol} Historical</div>', unsafe_allow_html=True)
    
    col_range, col_ind = st.columns([1, 2])
    with col_range:
        time_range = st.select_slider(
            "Range",
            options=["1M", "3M", "6M", "1Y", "5Y", "MAX"],
            value="1Y"
        )
    
    with col_ind:
        selected_indicators = st.multiselect(
            "Technical Indicators",
            options=["SMA 20", "SMA 50", "EMA 20", "Bollinger Bands", "RSI 14"],
            default=[]
        )
    
    with st.spinner(f"Fetching data..."):
        result = fetch_historical(symbol, time_range)
    
    if "error" in result:
        st.error(f"Error: {result['error']}")
        return
    
    data = result.get("data", [])
    if not data:
        st.warning("No data available.")
        return
    
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    
    if selected_indicators:
        df = technical.calculate_indicators(df)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['price'], mode='lines', name='Price', line=dict(color='#00e5a0', width=2)))
    
    if selected_indicators:
        technical.add_indicators_to_fig(fig, df, selected_indicators)
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font_color='#c9d8e8', margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(showgrid=True, gridcolor='#1a2a40'),
        yaxis=dict(showgrid=True, gridcolor='#1a2a40'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    if "RSI 14" in selected_indicators:
        rsi_fig = px.line(df, x='date', y='RSI_14', range_y=[0, 100], height=200)
        rsi_fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#c9d8e8', margin=dict(l=0, r=0, t=20, b=0))
        rsi_fig.add_hline(y=70, line_dash="dash", line_color="red")
        rsi_fig.add_hline(y=30, line_dash="dash", line_color="green")
        st.plotly_chart(rsi_fig, use_container_width=True)

# ── Main ──────────────────────────────────────────────────────────────────────
target_symbol = st.query_params.get("symbol")
if target_symbol:
    render_historical_page(target_symbol)
    st.stop()

# Auto-refresh
refresh_secs = st.sidebar.slider("Refresh (seconds)", 1, 30, 3)
st_autorefresh(interval=refresh_secs * 1000, key="data_refresh")

# Header
st.markdown(
    """
    <div class="dash-header">
        <div>
            <div class="dash-title">📡 MARKET TRACKER</div>
            <div class="dash-subtitle"><span class="live-dot"></span>Live prices · Finnhub WebSocket</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Fetch data
payload = fetch_prices()
prices = payload.get("data", {})
cats = payload.get("categories", {})
err = payload.get("error")

if err:
    st.error(f"⚠️ Backend error: {err}")
    st.stop()

# Sidebar info
with st.sidebar:
    st.markdown("### ⚙️ Info")
    st.info(f"Connected to {BACKEND_URL}")
    if st.button("🔄 Reload Page"):
        st.rerun()

# News handling in session state
if "news_items" not in st.session_state:
    st.session_state.news_items = []
if "last_news_fetch" not in st.session_state:
    st.session_state.last_news_fetch = 0

if time.time() - st.session_state.last_news_fetch > 300: # 5 mins
    news_res = fetch_news()
    st.session_state.news_items = news_res.get("items", [])[:20]
    st.session_state.last_news_fetch = time.time()

# Layout
main_col, news_col = st.columns([3, 1], gap="medium")

with main_col:
    # Top metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Active Feeds", len(prices))
    m2.metric("Total Tracked", sum(len(v) for v in cats.values()))
    m3.metric("Last Update", datetime.now().strftime("%H:%M:%S"))

    # Grids
    for cat_name, symbols in cats.items():
        icon = CATEGORY_ICONS.get(cat_name, "📌")
        st.markdown(f'<div class="cat-header">{icon} {cat_name}</div>', unsafe_allow_html=True)
        cols = st.columns(4)
        for i, sym in enumerate(symbols):
            record = prices.get(sym)
            with cols[i % 4]:
                if record:
                    st.markdown(render_card(record), unsafe_allow_html=True)
                else:
                    st.markdown(render_no_data(), unsafe_allow_html=True)

with news_col:
    st.markdown("### 📰 Latest News")
    for item in st.session_state.news_items:
        st.markdown(f"""
        <div style='margin-bottom: 12px; border-bottom: 1px solid #1a2a40; padding-bottom: 8px;'>
            <div style='font-size: 0.85em; font-weight: bold;'>
                <a href='{item.get("url")}' target='_blank' style='color: #c9d8e8; text-decoration: none;'>{item.get("title")}</a>
            </div>
            <div style='font-size: 0.65em; color: #5a7a9a;'>{item.get("source_name")}</div>
        </div>
        """, unsafe_allow_html=True)

# Status bar
st.markdown(
    f"""
    <div class="status-bar">
        <span>MARKET TRACKER v1.1</span>
        <span>STATUS: ONLINE</span>
        <span>REFRESH: {refresh_secs}s</span>
    </div>
    """,
    unsafe_allow_html=True,
)
