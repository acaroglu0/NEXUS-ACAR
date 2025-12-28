import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import plotly.graph_objects as go
import time
import os
import datetime
import base64
import random
import numpy as np

# --- 1. AYARLAR ---
st.set_page_config(layout="wide", page_title="NEXUS AI", page_icon="🦁", initial_sidebar_state="collapsed")

# SESSION STATE
if 'theme_color' not in st.session_state: st.session_state.theme_color = '#F7931A'
if 'currency' not in st.session_state: st.session_state.currency = 'usd'
if 'language' not in st.session_state: st.session_state.language = 'TR'
if 'app_mode' not in st.session_state: st.session_state.app_mode = 'TERMINAL'
if 'selected_coin' not in st.session_state: st.session_state.selected_coin = 'ethereum' 

THEMES = {
    "Bitcoin Turuncusu 🟠": "#F7931A",
    "Neon Mavi 🔵": "#00d2ff",
    "Matrix Yeşili 🟢": "#00FF41",
    "Siber Mor 🟣": "#BC13FE",
    "Alarm Kırmızısı 🔴": "#FF0033"
}

# --- LOGO ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f: data = f.read()
    return base64.b64encode(data).decode()
logo_path = "logo.jpeg"
logo_base64 = get_base64_of_bin_file(logo_path) if os.path.exists(logo_path) else None

# --- CSS ---
st.markdown(f"""
<style>
    [data-testid="stSidebar"] {{display: none;}}
    .block-container {{ padding-top: 2rem; padding-bottom: 2rem; max-width: 100%; }}
    .nexus-panel {{ background-color: #1E1E1E; padding: 10px; border-radius: 12px; border: 1px solid #333; margin-bottom: 10px; }}
    
    /* TABLO */
    .coin-header {{ display: flex; justify-content: space-between; color: gray; font-size: 12px; padding: 5px 10px; margin-bottom: 5px; font-weight: bold; }}
    .coin-row {{ display: flex; align-items: center; justify-content: space-between; background-color: #151515; border-bottom: 1px solid #333; padding: 12px 10px; border-radius: 6px; margin-bottom: 5px; }}
    .coin-row:hover {{ background-color: #252525; }}
    .row-left {{ display: flex; align-items: center; flex: 1.5; }}
    .row-right {{ display: flex; align-items: center; flex: 2; justify-content: flex-end; }}
    .price-col {{ width: 30%; text-align: right; font-family: monospace; font-weight: bold; color: white; }}
    
    /* LOGO */
    .logo-container {{ display: flex; align-items: center; margin-bottom: 15px; }}
    .logo-img {{ width: 60px; height: auto; margin-right: 12px; border-radius: 10px; }}
    .logo-text {{ color: {st.session_state.theme_color}; margin: 0; font-size: 26px; font-weight: 900; }}
    
    div.stButton > button {{ width: 100%; border-radius: 8px; font-weight: 700; text-transform: uppercase; }}
    div.stButton > button[kind="primary"] {{ background-color: {st.session_state.theme_color}; color: black; border: none; }}
</style>
""", unsafe_allow_html=True)

# --- API KEY ---
try:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if api_key: genai.configure(api_key=api_key)
except: pass

@st.cache_resource
def get_model():
    try: return genai.GenerativeModel("gemini-pro")
    except: return None

# --- YENİ ÇİFT MOTORLU VERİ SİSTEMİ ---

# ID Eşleştirici (CoinGecko ID -> Binance Symbol)
def get_symbol_map(coin_id):
    mapping = {
        "bitcoin": "BTCUSDT", "ethereum": "ETHUSDT", "solana": "SOLUSDT", 
        "ripple": "XRPUSDT", "avalanche-2": "AVAXUSDT", "binancecoin": "BNBUSDT",
        "dogecoin": "DOGEUSDT", "cardano": "ADAUSDT", "tron": "TRXUSDT",
        "pepe": "PEPEUSDT", "shiba-inu": "SHIBUSDT"
    }
    return mapping.get(coin_id.lower(), None)

# MOTOR 1: BINANCE (Çok Hızlı, Yüksek Limit)
def fetch_binance_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        r = requests.get(url, timeout=2)
        if r.status_code == 200:
            d = r.json()
            return {
                "usd": float(d['lastPrice']),
                "usd_24h_change": float(d['priceChangePercent']),
                "source": "Binance"
            }
    except: pass
    return None

def fetch_binance_chart(symbol, limit=24):
    try:
        # Kline/Candlestick verisi
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit={limit}"
        r = requests.get(url, timeout=2)
        if r.status_code == 200:
            data = r.json()
            # Binance [OpenTime, Open, High, Low, Close, ...] döner. 0=Time, 4=ClosePrice
            df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
            df['time'] = pd.to_datetime(df['time'], unit='ms')
            df['price'] = df['close'].astype(float)
            return df[['time', 'price']]
    except: pass
    return pd.DataFrame()

# MOTOR 2: COINGECKO (Yedek, Daha Geniş Kapsam)
def fetch_coingecko_price(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
        r = requests.get(url, timeout=2)
        if r.status_code == 200:
            d = r.json().get(coin_id)
            if d:
                return {
                    "usd": d['usd'],
                    "usd_24h_change": d['usd_24h_change'],
                    "source": "CoinGecko"
                }
    except: pass
    return None

def fetch_coingecko_chart(coin_id, days):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}"
        r = requests.get(url, timeout=2)
        if r.status_code == 200:
            d = r.json()
            df = pd.DataFrame(d['prices'], columns=['time', 'price'])
            df['time'] = pd.to_datetime(df['time'], unit='ms')
            return df
    except: pass
    return pd.DataFrame()

# MOTOR 3: SIMULATION (Son Çare, Asla Boş Ekran Gösterme)
def generate_mock(coin_id):
    base = 100
    if "btc" in coin_id: base = 98000
    elif "eth" in coin_id: base = 3100
    return {
        "usd": base + random.uniform(-10, 10),
        "usd_24h_change": random.uniform(-5, 5),
        "source": "Simülasyon"
    }

def generate_mock_chart():
    dates = pd.date_range(end=datetime.datetime.now(), periods=24, freq='H')
    prices = np.linspace(100, 110, 24) + np.random.normal(0, 2, 24)
    return pd.DataFrame({'time': dates, 'price': prices})

# --- ANA VERİ YÖNETİCİSİ (AKILLI SEÇİM) ---
@st.cache_data(ttl=60) # 1 dk cache
def get_smart_data(coin_id):
    # 1. Binance Dene
    symbol = get_symbol_map(coin_id)
    if symbol:
        data = fetch_binance_price(symbol)
        if data: return data
    
    # 2. CoinGecko Dene
    data = fetch_coingecko_price(coin_id)
    if data: return data
    
    # 3. Simülasyon
    return generate_mock(coin_id)

@st.cache_data(ttl=300) # 5 dk cache
def get_smart_chart(coin_id, days):
    # 1. Binance Dene
    symbol = get_symbol_map(coin_id)
    if symbol:
        df = fetch_binance_chart(symbol, limit=24 if days=='1' else 168)
        if not df.empty: return df
        
    # 2. CoinGecko Dene
    df = fetch_coingecko_chart(coin_id, days)
    if not df.empty: return df
    
    # 3. Simülasyon
    return generate_mock_chart()

# --- GRAFİK ÇİZİCİ ---
def create_chart(df, change, symbol):
    if df.empty: return go.Figure()
    
    fig = go.Figure()
    color = '#16c784' if change >= 0 else '#ea3943'
    fill = 'rgba(22, 199, 132, 0.2)' if change >= 0 else 'rgba(234, 57, 67, 0.2)'
    
    fig.add_trace(go.Scatter(x=df['time'], y=df['price'], mode='lines', line=dict(color=color, width=2), fill='tozeroy', fillcolor=fill))
    fig.update_layout(
        height=350, margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified', xaxis=dict(visible=False), 
        yaxis=dict(side='right', visible=True, gridcolor='rgba(128,128,128,0.1)', tickprefix=symbol)
    )
    return fig

# --- DÜZEN ---
col_nav, col_main = st.columns([1, 4])

with col_nav:
    with st.container(border=True):
        if logo_base64:
            st.markdown(f"""<div class="logo-container"><img src="data:image/jpeg;base64,{logo_base64}" class="logo-img"><h1 class="logo-text">NEXUS</h1></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"<h1 style='color: {st.session_state.theme_color}; text-align: center; margin:0; font-size: 24px;'>🦁 NEXUS</h1>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.caption("KRİPTO SEÇ")
        # Text input state yönetimi
        def update_coin():
            st.session_state.selected_coin = st.session_state.coin_input_val
            
        st.text_input("Coin Ara:", value=st.session_state.selected_coin, key="coin_input_val", on_change=update_coin, label_visibility="collapsed")
        
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("ANALİZİ BAŞLAT", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.caption("HIZLI ERİŞİM")
        c1, c2 = st.columns(2)
        if c1.button("BTC"): st.session_state.selected_coin = "bitcoin"
        if c2.button("ETH"): st.session_state.selected_coin = "ethereum"
        if c1.button("SOL"): st.session_state.selected_coin = "solana"
        if c2.button("XRP"): st.session_state.selected_coin = "ripple"

with col_main:
    curr_sym = "$" # Varsayılan
    
    # 1. Coin Verisi
    user_coin = st.session_state.selected_coin.lower().strip()
    # Basit id mapping düzeltmesi
    if user_coin == "btc": user_coin = "bitcoin"
    if user_coin == "eth": user_coin = "ethereum"
    
    u_data = get_smart_data(user_coin)
    b_data = get_smart_data("bitcoin")
    
    # --- ÜST GRAFİKLER ---
    c_g1, c_g2 = st.columns(2)
    
    with c_g1:
        if u_data:
            chg = u_data['usd_24h_change']
            clr = "#16c784" if chg >= 0 else "#ea3943"
            st.markdown(f"<h2 style='margin:0'>{user_coin.upper()}</h2>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='color:{clr}; margin:0'>{curr_sym}{u_data['usd']:,.2f} (%{chg:.2f})</h3>", unsafe_allow_html=True)
            st.caption(f"Veri Kaynağı: {u_data['source']}")
            
            df = get_smart_chart(user_coin, '1')
            st.plotly_chart(create_chart(df, chg, curr_sym), use_container_width=True, config={'displayModeBar':False}, key="chart_u")
        else:
            st.error("Veri alınamadı.")

    with c_g2:
        if b_data:
            chg = b_data['usd_24h_change']
            clr = "#16c784" if chg >= 0 else "#ea3943"
            st.markdown(f"<h2 style='margin:0'>BITCOIN</h2>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='color:{clr}; margin:0'>{curr_sym}{b_data['usd']:,.2f} (%{chg:.2f})</h3>", unsafe_allow_html=True)
            
            df = get_smart_chart("bitcoin", '1')
            st.plotly_chart(create_chart(df, chg, curr_sym), use_container_width=True, config={'displayModeBar':False}, key="chart_b")

    # --- ALT KISIM ---
    c_ask, c_news = st.columns([1, 1])
    
    with c_ask:
        with st.container(border=True):
            st.caption("🤖 **YAPAY ZEKA ASİSTANI**")
            q = st.text_input("Soru:", placeholder="Analiz ne diyor?", label_visibility="collapsed")
            if st.button("GÖNDER"):
                if not st.secrets.get("GEMINI_API_KEY"): st.error("API Key Yok")
                else:
                    with st.spinner("Düşünülüyor..."):
                        try:
                            m = get_model()
                            res = m.generate_content(f"Coin: {user_coin}. Fiyat: {u_data['usd']}. Soru: {q}. Kısa cevap.")
                            st.info(res.text)
                        except: pass
    
    with c_news:
        if analyze_btn and u_data:
             with st.container(border=True):
                 st.caption("📊 **ANALİZ RAPORU**")
                 if not st.secrets.get("GEMINI_API_KEY"): st.error("API Key Yok")
                 else:
                     with st.spinner("Analiz yazılıyor..."):
                         try:
                             m = get_model()
                             prompt = f"""
                             Coin: {user_coin.upper()}. Fiyat: {u_data['usd']}. Değişim: %{u_data['usd_24h_change']}.
                             Kısa, net bir yatırımcı analizi yap. Yükseliş mi düşüş mü bekleniyor?
                             """
                             res = m.generate_content(prompt)
                             st.markdown(res.text)
                         except: pass
