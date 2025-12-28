import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import plotly.graph_objects as go
import time
import os
import base64

# --- 1. AYARLAR ---
st.set_page_config(layout="wide", page_title="NEXUS ENTERPRISE", page_icon="🦁", initial_sidebar_state="collapsed")

# SESSION STATE
if 'theme_color' not in st.session_state: st.session_state.theme_color = '#00E396' # Daha modern bir yeşil
if 'currency' not in st.session_state: st.session_state.currency = 'usd'
if 'language' not in st.session_state: st.session_state.language = 'TR'
if 'app_mode' not in st.session_state: st.session_state.app_mode = 'TERMINAL'
if 'selected_coin' not in st.session_state: st.session_state.selected_coin = 'ethereum' 

# --- CSS (PREMIUM & MINIMALIST) ---
st.markdown(f"""
<style>
    [data-testid="stSidebar"] {{display: none;}}
    .block-container {{ padding-top: 1rem; padding-bottom: 2rem; max-width: 100%; }}
    
    /* GENEL ARKAPLAN */
    .stApp {{ background-color: #0E1117; }}
    
    /* LOGO */
    .logo-text {{ 
        color: white; 
        margin: 0; 
        font-size: 24px; 
        font-weight: 800; 
        letter-spacing: 2px; 
        font-family: 'Helvetica Neue', sans-serif;
    }}
    .logo-sub {{ color: gray; font-size: 10px; letter-spacing: 1px; }}
    
    /* MINIMALIST KART */
    .metric-card {{
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
    }}
    .coin-title {{ font-size: 18px; font-weight: bold; color: #8B949E; margin-bottom: 5px; }}
    .coin-price {{ font-size: 32px; font-weight: 900; color: white; margin: 0; line-height: 1; }}
    .coin-change {{ font-size: 16px; font-weight: bold; margin-left: 10px; }}
    
    /* BUTONLAR */
    div.stButton > button {{ 
        border-radius: 8px; 
        font-weight: 600 !important; 
        background-color: #21262D; 
        color: white; 
        border: 1px solid #30363D;
        transition: all 0.2s;
    }}
    div.stButton > button:hover {{ 
        border-color: {st.session_state.theme_color}; 
        color: {st.session_state.theme_color}; 
    }}
    div.stButton > button[kind="primary"] {{ 
        background-color: {st.session_state.theme_color}; 
        color: black; 
        border: none; 
        font-weight: 800 !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- API ---
try:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if api_key: genai.configure(api_key=api_key)
except: pass

@st.cache_resource
def get_model():
    try:
        return genai.GenerativeModel("gemini-pro", generation_config={"temperature": 0.2})
    except: pass
    return None

# --- VERİ FONKSİYONLARI ---
@st.cache_data(ttl=3600) 
def search_coin_id(query):
    try:
        url = f"https://api.coingecko.com/api/v3/search?query={query}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()
        if r.get('coins'): return r['coins'][0]['id']
    except: return None
    return None

@st.cache_data(ttl=60)
def get_coin_data(coin_id, currency):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={currency}&include_24hr_change=true"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code != 200: return "LIMIT"
        data = r.json()
        if coin_id in data: return data[coin_id]
    except: return None
    return None

@st.cache_data(ttl=300)
def get_chart_data(coin_id, currency, days):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency={currency}&days={days}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code != 200: return pd.DataFrame()
        data = r.json()
        if 'prices' not in data: return pd.DataFrame()
        df = pd.DataFrame(data['prices'], columns=['time', 'price'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        return df
    except: return pd.DataFrame()

# --- TEKNİK ANALİZ (TUTARLILIK PROTOKOLÜ) ---
def calculate_tech(df):
    if df.empty or len(df) < 50: return None
    # RSI
    delta = df['price'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs)).iloc[-1]
    
    # Trend
    sma50 = df['price'].rolling(50).mean().iloc[-1]
    last = df['price'].iloc[-1]
    
    return {"rsi": rsi, "trend": "YÜKSELİŞ" if last > sma50 else "DÜŞÜŞ", "sma": sma50}

# --- MINIMALIST "SPARKLINE" GRAFİK (CHATGPT TARZI) ---
def create_sparkline(df, change_pct):
    if df.empty: return go.Figure()
    
    color = '#00E396' if change_pct >= 0 else '#FF4560' # Neon Yeşil / Neon Kırmızı
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['time'], 
        y=df['price'], 
        mode='lines', 
        line=dict(color=color, width=3), # Kalın çizgi
        fill='tozeroy',
        fillcolor=f"rgba{tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (0.1,)}" # Hafif dolgu
    ))
    
    fig.update_layout(
        height=250, # Daha kompakt
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False), # Eksenleri gizle (Sadelik)
        yaxis=dict(visible=False), # Eksenleri gizle
        hovermode='x unified'
    )
    return fig

# --- DÜZEN ---
# Mobilde tek sütun, PC'de 2 sütun (Terminal)
col_nav, col_main = st.columns([1, 4]) if st.session_state.app_mode == "TERMINAL" else st.columns([1, 5])

# SOL PANEL
with col_nav:
    st.markdown("""
    <div style="margin-bottom: 20px;">
        <h1 class="logo-text">NEXUS</h1>
        <span class="logo-sub">INTELLIGENCE PRO</span>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.app_mode == "TERMINAL":
        coin_input = st.text_input("ARA", st.session_state.selected_coin, label_visibility="collapsed")
        if coin_input != st.session_state.selected_coin: st.session_state.selected_coin = coin_input
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("ANALİZ ET", type="primary", use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("FAVORİLER")
        colq1, colq2 = st.columns(2)
        if colq1.button("ETH", use_container_width=True): 
            st.session_state.selected_coin = "ethereum"
            st.rerun()
        if colq2.button("BTC", use_container_width=True): 
            st.session_state.selected_coin = "bitcoin"
            st.rerun()
        if colq1.button("SOL", use_container_width=True): 
            st.session_state.selected_coin = "solana"
            st.rerun()
        if colq2.button("XRP", use_container_width=True): 
            st.session_state.selected_coin = "ripple"
            st.rerun()

# ANA EKRAN
with col_main:
    curr = st.session_state.currency
    sym = "$"
    
    coin = st.session_state.selected_coin.lower()
    data = get_coin_data(coin, curr)
    if not data:
        fid = search_coin_id(coin)
        if fid: 
            coin = fid
            data = get_coin_data(coin, curr)
    
    btc_data = get_coin_data("bitcoin", curr)

    if data and data != "LIMIT" and btc_data:
        # ÜST BİLGİ KARTLARI (CHATGPT GİBİ TEMİZ)
        c1, c2 = st.columns(2)
        
        # KULLANICI COIN
        with c1:
            chg = data[f'{curr}_24h_change']
            clr = "#00E396" if chg >= 0 else "#FF4560"
            st.markdown(f"""
            <div class="metric-card">
                <div class="coin-title">{coin.upper()}</div>
                <div style="display: flex; align-items: baseline;">
                    <h1 class="coin-price">{sym}{data[curr]:,.2f}</h1>
                    <span class="coin-change" style="color: {clr};">%{chg:.2f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            # SPARKLINE GRAFİK
            chart_df = get_chart_data(coin, curr, 1) # 24 Saatlik detay
            st.plotly_chart(create_sparkline(chart_df, chg), use_container_width=True, config={'displayModeBar': False, 'staticPlot': True}) # staticPlot=True ile tamamen etkileşimsiz, resim gibi yapabiliriz istersen.

        # BITCOIN (KIYASLAMA)
        with c2:
            b_chg = btc_data[f'{curr}_24h_change']
            b_clr = "#00E396" if b_chg >= 0 else "#FF4560"
            st.markdown(f"""
            <div class="metric-card">
                <div class="coin-title">BITCOIN (Piyasa Yönü)</div>
                <div style="display: flex; align-items: baseline;">
                    <h1 class="coin-price">{sym}{btc_data[curr]:,.2f}</h1>
                    <span class="coin-change" style="color: {b_clr};">%{b_chg:.2f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            b_chart_df = get_chart_data("bitcoin", curr, 1)
            st.plotly_chart(create_sparkline(b_chart_df, b_chg), use_container_width=True, config={'displayModeBar': False, 'staticPlot': True})

        # YAPAY ZEKA ANALİZİ (AŞAĞIDA TEMİZ BİR KART OLARAK)
        if analyze_btn:
            tech = calculate_tech(chart_df)
            if tech:
                st.markdown("<br>", unsafe_allow_html=True)
                with st.container(border=True):
                    st.markdown(f"### 🦁 NEXUS INTELLIGENCE: {coin.upper()}")
                    prompt = f"""
                    Sen BtcTurk veya Binance için çalışan kıdemli bir analistsin.
                    Coin: {coin.upper()}, Fiyat: {data[curr]}
                    Matematiksel Veriler: RSI={tech['rsi']:.1f}, Trend={tech['trend']}, SMA50={tech['sma']:.2f}
                    
                    Tek bir paragraf halinde, yatırımcıya profesyonel, güven veren ve net bir piyasa yorumu yap.
                    Asla "tavsiye değildir" gibi klişeler kullanma, sadece durumu analiz et.
                    """
                    with st.spinner("Piyasa verileri işleniyor..."):
                        try:
                            ai = get_model()
                            res = ai.generate_content(prompt)
                            st.write(res.text)
                        except: st.error("AI Bağlantı Hatası")
            else:
                st.warning("Yeterli veri yok.")

    else:
        st.info("Piyasa verileri yükleniyor...")
