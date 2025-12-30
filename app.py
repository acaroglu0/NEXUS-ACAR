import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import plotly.graph_objects as go
import time
import os
import datetime
import base64
import numpy as np

# --- 1. AYARLAR ---
st.set_page_config(layout="wide", page_title="NEXUS AI", page_icon="🦁", initial_sidebar_state="collapsed")

# SESSION STATE
if 'theme_color' not in st.session_state: st.session_state.theme_color = '#F7931A'
if 'currency' not in st.session_state: st.session_state.currency = 'usd'
if 'language' not in st.session_state: st.session_state.language = 'TR'
if 'app_mode' not in st.session_state: st.session_state.app_mode = 'TERMINAL'
if 'selected_coin' not in st.session_state: st.session_state.selected_coin = 'ethereum' 

if 'posts' not in st.session_state: 
    st.session_state.posts = [
        {"user": "Admin 🦁", "msg": "NEXUS v19.0: 3 Farklı Mod Yayında! (Terminal, Pro, Portal)", "time": "Now"},
    ]

THEMES = {
    "Bitcoin Turuncusu 🟠": "#F7931A",
    "Neon Mavi 🔵": "#00d2ff",
    "Matrix Yeşili 🟢": "#00FF41",
    "Siber Mor 🟣": "#BC13FE",
    "Alarm Kırmızısı 🔴": "#FF0033"
}

# --- LOGO YÜKLEME ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

logo_path = "logo.jpeg"
logo_base64 = get_base64_of_bin_file(logo_path) if os.path.exists(logo_path) else None

# --- TEKNİK ANALİZ MOTORU ---
def calculate_indicators(df):
    if df.empty or len(df) < 26: return None
    
    delta = df['price'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    df['sma20'] = df['price'].rolling(window=20).mean()
    
    # Bollinger
    df['std_dev'] = df['price'].rolling(window=20).std()
    df['upper_bb'] = df['sma20'] + (df['std_dev'] * 2)
    df['lower_bb'] = df['sma20'] - (df['std_dev'] * 2)
    
    # MACD
    exp1 = df['price'].ewm(span=12, adjust=False).mean()
    exp2 = df['price'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()

    last = df.iloc[-1]
    
    trend = "YÜKSELİŞ" if last['price'] > last['sma20'] else "DÜŞÜŞ"
    rsi_status = "NÖTR"
    if last['rsi'] > 70: rsi_status = "AŞIRI ALIM"
    elif last['rsi'] < 30: rsi_status = "AŞIRI SATIM"
    
    return {
        "rsi": last['rsi'], "rsi_msg": rsi_status, 
        "trend": trend, "sma20": last['sma20'],
        "macd": last['macd'], "macd_sig": last['signal'],
        "upper_bb": last['upper_bb'], "lower_bb": last['lower_bb']
    }

# --- 2. CSS ---
st.markdown(f"""
<style>
    [data-testid="stSidebar"] {{display: none;}}
    .main .block-container {{ max-width: 98vw; padding: 1rem; }}
    .nexus-panel {{ background-color: #1E1E1E; padding: 10px; border-radius: 12px; border: 1px solid #333; margin-bottom: 10px; }}
    
    /* TABLO */
    .coin-header {{ display: flex; justify-content: space-between; color: gray; font-size: 12px; padding: 5px 10px; font-weight: bold; }}
    .coin-row {{ display: flex; align-items: center; justify-content: space-between; background-color: #151515; border-bottom: 1px solid #333; padding: 12px 10px; border-radius: 6px; margin-bottom: 5px; }}
    .coin-row:hover {{ background-color: #252525; }}
    .row-left {{ display: flex; align-items: center; flex: 1.5; }}
    .row-right {{ display: flex; align-items: center; flex: 2; justify-content: flex-end; }}
    .price-col {{ width: 30%; text-align: right; font-family: monospace; font-weight: bold; color: white; }}
    .stat-col {{ width: 20%; text-align: right; font-size: 14px; }}
    
    /* LOGO */
    .logo-container {{ display: flex; align-items: center; justify-content: flex-start; margin-bottom: 15px; flex-wrap: nowrap !important; overflow: hidden; }}
    .logo-img {{ width: 50px; height: auto; margin-right: 10px; border-radius: 10px; flex-shrink: 0; }}
    .logo-text {{ color: {st.session_state.theme_color}; margin: 0; font-size: 22px; font-weight: 900; letter-spacing: 1px; line-height: 1; white-space: nowrap !important; }}
    
    div.stButton > button {{ width: 100%; border-radius: 8px; font-weight: 700; text-transform: uppercase; }}
    div.stButton > button[kind="primary"] {{ background-color: {st.session_state.theme_color}; color: black; border: none; }}
</style>
""", unsafe_allow_html=True)

# --- API ---
try:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if api_key: genai.configure(api_key=api_key)
except: pass

@st.cache_resource
def get_model():
    try: return genai.GenerativeModel("gemini-pro", generation_config={"temperature": 0.2})
    except: pass
    return None

# --- VERİ MOTORU ---
@st.cache_data(ttl=3600) 
def search_coin_id(query):
    try:
        url = f"https://api.coingecko.com/api/v3/search?query={query}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()
        if r.get('coins'): return r['coins'][0]['id']
    except: return None
    return None

@st.cache_data(ttl=180)
def get_coin_data(coin_id, currency):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={currency}&include_24hr_change=true&include_24hr_vol=true"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code != 200: return None
        data = r.json()
        if coin_id in data: return data[coin_id]
    except: return None
    return None

@st.cache_data(ttl=86400) 
def get_global_data():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        return requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()['data']
    except: return None

@st.cache_data(ttl=600)
def get_top10_coins(currency):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency={currency}&order=market_cap_desc&per_page=10&page=1&sparkline=false&price_change_percentage=1h,24h,7d"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code != 200: return [] 
        return r.json()
    except: return []

@st.cache_data(ttl=1800)
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

# --- PRO İÇİN OHLC (MUM) VERİSİ ---
@st.cache_data(ttl=1800)
def get_ohlc_data(coin_id, currency, days):
    # CoinGecko OHLC endpointi (1/7/14/30/90/180/365/max)
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc?vs_currency={currency}&days={days}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code != 200: return pd.DataFrame()
        data = r.json()
        # [time, open, high, low, close]
        df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def get_news(topic):
    try:
        import xml.etree.ElementTree as ET
        rss_url = f"https://news.google.com/rss/search?q={topic}&hl=tr&gl=TR&ceid=TR:tr"
        r = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        root = ET.fromstring(r.content)
        return [{"title": i.find("title").text, "link": i.find("link").text} for i in root.findall(".//item")[:10]]
    except: return []

# --- GRAFİK 1: BASİT (TERMINAL) ---
def create_mini_chart(df, price_change, currency_symbol, height=350):
    fig = go.Figure()
    if df.empty: return fig
    color = '#ea3943' if price_change < 0 else '#16c784'
    fill = 'rgba(234, 57, 67, 0.2)' if price_change < 0 else 'rgba(22, 199, 132, 0.2)' 
    fig.add_trace(go.Scatter(x=df['time'], y=df['price'], mode='lines', line=dict(color=color, width=2), fill='tozeroy', fillcolor=fill))
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False), yaxis=dict(side='right', visible=True, gridcolor='rgba(128,128,128,0.1)', tickprefix=currency_symbol))
    return fig

# --- GRAFİK 2: PRO (MUM ÇUBUKLARI) ---
def create_pro_chart(df, coin_name, currency_symbol):
    fig = go.Figure()
    if df.empty: return fig
    
    # Mum Grafiği
    fig.add_trace(go.Candlestick(
        x=df['time'],
        open=df['open'], high=df['high'],
        low=df['low'], close=df['close'],
        name=coin_name
    ))
    
    fig.update_layout(
        height=500, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor='#1E1E1E', plot_bgcolor='#1E1E1E',
        xaxis_rangeslider_visible=False,
        xaxis=dict(gridcolor='rgba(128,128,128,0.1)'),
        yaxis=dict(side='right', gridcolor='rgba(128,128,128,0.1)', tickprefix=currency_symbol),
        title=f"{coin_name.upper()} - PRO CHART"
    )
    return fig

# --- LAYOUT ---
layout_cols = [1, 4, 1] if st.session_state.app_mode in ["TERMINAL", "PRO TERMINAL"] else [1, 5]
cols = st.columns(layout_cols)
col_nav = cols[0]
col_main = cols[1]
col_right = cols[2] if len(cols) > 2 else None

# --- SOL PANEL ---
with col_nav:
    with st.container(border=True):
        if logo_base64:
            st.markdown(f"""<div class="logo-container"><img src="data:image/jpeg;base64,{logo_base64}" class="logo-img"><h1 class="logo-text">NEXUS</h1></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"<h1 style='color: {st.session_state.theme_color}; text-align: center; margin:0; font-size: 22px;'>🦁 NEXUS</h1>", unsafe_allow_html=True)
        st.markdown("---")
        
        # NAVİGASYON (3 MODLU)
        st.caption("🌐 **MOD**")
        # Radio buton yerine selectbox kullanabiliriz alan darsa, ama radio iyi
        mode_select = st.radio("Mod:", ["TERMINAL", "PRO TERMINAL", "PORTAL"], label_visibility="collapsed")
        if mode_select != st.session_state.app_mode:
            st.session_state.app_mode = mode_select
            st.rerun()

        st.markdown("---")
        
        if st.session_state.app_mode in ["TERMINAL", "PRO TERMINAL"]:
            st.caption("🔍 **KRİPTO SEÇ**")
            coin_input = st.text_input("Coin Ara:", st.session_state.selected_coin, label_visibility="collapsed")
            if coin_input != st.session_state.selected_coin: st.session_state.selected_coin = coin_input
            
            st.markdown("<br>", unsafe_allow_html=True)
            analyze_btn = st.button("ANALİZİ BAŞLAT", type="primary")
            st.markdown("---")
            
            st.caption("⏳ **SÜRE**")
            day_opt = st.radio("Süre:", ["24 Saat", "7 Gün", "1 Ay", "6 Ay"], horizontal=True, label_visibility="collapsed")
            
            if day_opt == "24 Saat": days_api = "1"
            elif day_opt == "7 Gün": days_api = "7"
            elif day_opt == "1 Ay": days_api = "30"
            else: days_api = "180"

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("🌍 **DİL**")
        lng = st.radio("Dil:", ["TR", "EN", "DE"], horizontal=True, label_visibility="collapsed")
        st.session_state.language = lng
        
        if st.session_state.app_mode == "PORTAL":
            st.markdown("---")
            st.caption("⚙️ **AYARLAR**")
            curr_opt = st.selectbox("Para Birimi", ["USD", "TRY", "EUR"], label_visibility="collapsed")
            st.session_state.currency = curr_opt.lower()
            thm = st.selectbox("Tema", list(THEMES.keys()), label_visibility="collapsed")
            st.session_state.theme_color = THEMES[thm]

# --- ANA İÇERİK ---
with col_main:
    
    # === MOD 1: TERMINAL (KLASİK - HIZLI - BASİT) ===
    if st.session_state.app_mode == "TERMINAL":
        raw_input = st.session_state.selected_coin.lower().strip()
        curr = st.session_state.currency
        curr_sym = "$" if curr == 'usd' else "₺" if curr == 'try' else "€"
        
        user_coin_id = raw_input
        user_data = get_coin_data(user_coin_id, curr)
        if user_data is None:
            found_id = search_coin_id(raw_input)
            if found_id:
                user_coin_id = found_id
                user_data = get_coin_data(user_coin_id, curr)

        btc_data = get_coin_data("bitcoin", curr)
        
        if user_data and btc_data:
            c_chart1, c_chart2 = st.columns(2)
            
            with c_chart1:
                u_change = user_data.get(f'{curr}_24h_change', 0)
                u_color = "#ea3943" if u_change < 0 else "#16c784"
                cl1, cl2 = st.columns([1, 1])
                cl1.markdown(f"<h2 style='margin:0;'>{user_coin_id.upper()}</h2>", unsafe_allow_html=True)
                cl2.markdown(f"<h3 style='text-align:right; color:{u_color}; margin:0;'>{curr_sym}{user_data[curr]:,.2f} (%{u_change:.2f})</h3>", unsafe_allow_html=True)
                
                # Grafik verisini al (Line Chart)
                u_df = get_chart_data(user_coin_id, curr, days_api)
                technical_data = calculate_indicators(u_df) 
                
                st.plotly_chart(create_mini_chart(u_df, u_change, curr_sym), use_container_width=True, config={'displayModeBar': False})

            with c_chart2:
                b_change = btc_data.get(f'{curr}_24h_change', 0)
                b_color = "#ea3943" if b_change < 0 else "#16c784"
                cr1, cr2 = st.columns([1, 1])
                cr1.markdown(f"<h2 style='margin:0;'>BITCOIN</h2>", unsafe_allow_html=True)
                cr2.markdown(f"<h3 style='text-align:right; color:{b_color}; margin:0;'>{curr_sym}{btc_data[curr]:,.2f} (%{b_change:.2f})</h3>", unsafe_allow_html=True)
                b_df = get_chart_data("bitcoin", curr, days_api)
                st.plotly_chart(create_mini_chart(b_df, b_change, curr_sym), use_container_width=True, config={'displayModeBar': False})

            c_bot1, c_bot2, c_bot3 = st.columns(3)
            with c_bot1:
                with st.container(border=True):
                    st.caption(f"🤖 **NEXUS AI SOR**")
                    user_q = st.text_input("Soru:", placeholder="Destek neresi?", label_visibility="collapsed")
                    if st.button("GÖNDER", key="ai_ask"):
                         if not st.secrets.get("GEMINI_API_KEY"): st.error("API Key Yok")
                         else:
                             with st.spinner(".."):
                                 try:
                                     m = get_model()
                                     r = m.generate_content(f"Coin: {user_coin_id}. Fiyat: {user_data[curr]}. Soru: {user_q}. Kısa cevapla.")
                                     st.info(r.text)
                                 except: pass

            with c_bot2:
                with st.container(border=True):
                    st.markdown("""<div class="box-content"><div class="ad-placeholder">REKLAM ALANI</div></div>""", unsafe_allow_html=True)

            with c_bot3:
                with st.container(border=True):
                    global_data = get_global_data()
                    if global_data:
                        total_cap = global_data['total_market_cap'][curr]
                        total_change = global_data['market_cap_change_percentage_24h_usd']
                        arrow = "⬆" if total_change > 0 else "⬇"
                        t_color = "#16c784" if total_change > 0 else "#ea3943"
                        if total_cap > 1_000_000_000_000: t_fmt = f"{total_cap/1_000_000_000_000:.2f} T"
                        else: t_fmt = f"{total_cap/1_000_000_000:.2f} B"
                        st.markdown(f"""<div class="box-content"><h3 style="color: gray; margin: 0; font-size: 13px;">GLOBAL MARKET CAP</h3><h1 style="color: white; margin: 5px 0; font-size: 26px;">{curr_sym}{t_fmt}</h1><h3 style="color: {t_color}; margin: 0; font-size: 18px;">{arrow} %{total_change:.2f}</h3></div>""", unsafe_allow_html=True)
            
            if analyze_btn:
                 st.markdown("---")
                 st.subheader(f"🧠 NEXUS: Temel Analiz")
                 if not st.secrets.get("GEMINI_API_KEY"): st.error("API Key Yok")
                 else:
                     with st.spinner("Analiz Yapılıyor..."):
                         try:
                             model = get_model()
                             price_now = user_data[curr]
                             # BASİT ANALİZ PROMPTU
                             simple_prompt = f"""
                             Coin: {user_coin_id.upper()}, Fiyat: {price_now} {curr.upper()}.
                             Yatırımcı için kısa, net ve anlaşılır bir durum özeti geç. Çok teknik terim kullanma. Yön ne tarafa?
                             Dil: {st.session_state.language}
                             """
                             res = model.generate_content(simple_prompt)
                             st.markdown(res.text, unsafe_allow_html=True)
                         except: st.error("Bağlantı hatası.")
        else:
            st.warning(f"⚠️ Veri alınamadı (Limit/Hata). Lütfen 1 dakika bekleyin.")

    # === MOD 2: PRO TERMINAL (YENİ - PROFESYONEL) ===
    elif st.session_state.app_mode == "PRO TERMINAL":
        raw_input = st.session_state.selected_coin.lower().strip()
        curr = st.session_state.currency
        curr_sym = "$" if curr == 'usd' else "₺" if curr == 'try' else "€"
        
        user_coin_id = raw_input
        user_data = get_coin_data(user_coin_id, curr)
        if user_data is None:
            found_id = search_coin_id(raw_input)
            if found_id:
                user_coin_id = found_id
                user_data = get_coin_data(user_coin_id, curr)
        
        if user_data:
            # ÜST BİLGİ ŞERİDİ
            u_change = user_data.get(f'{curr}_24h_change', 0)
            u_vol = user_data.get(f'{curr}_24h_vol', 0)
            u_color = "#ea3943" if u_change < 0 else "#16c784"
            
            c_info1, c_info2, c_info3, c_info4 = st.columns(4)
            c_info1.markdown(f"## {user_coin_id.upper()}")
            c_info2.markdown(f"<h3 style='color:{u_color}'>{curr_sym}{user_data[curr]:,.2f} (%{u_change:.2f})</h3>", unsafe_allow_html=True)
            c_info3.metric("24s Hacim", f"{curr_sym}{u_vol:,.0f}")
            
            # CHART & TECH DATA
            # Pro modda OHLC (Mum) verisi çekmeye çalışıyoruz
            ohlc_df = get_ohlc_data(user_coin_id, curr, days_api)
            
            # Eğer OHLC çekemezse normal line chart verisini alıp hesaplama yapalım
            line_df = get_chart_data(user_coin_id, curr, days_api)
            tech = calculate_indicators(line_df) # İndikatörler line df'den hesaplanır
            
            if not ohlc_df.empty:
                st.plotly_chart(create_pro_chart(ohlc_df, user_coin_id.upper(), curr_sym), use_container_width=True)
            else:
                st.warning("Mum verisi alınamadı, Çizgi grafik gösteriliyor.")
                st.plotly_chart(create_mini_chart(line_df, u_change, curr_sym, height=500), use_container_width=True)
            
            # İNDİKATÖR PANELİ (GÖRSEL)
            if tech:
                st.markdown("### 📊 Teknik Göstergeler")
                i1, i2, i3, i4 = st.columns(4)
                i1.metric("RSI (14)", f"{tech['rsi']:.2f}", tech['rsi_msg'])
                i2.metric("MACD", f"{tech['macd']:.4f}", tech['macd_sig']:.4f)
                i3.metric("SMA (20)", f"{tech['sma20']:.2f}", tech['trend'])
                i4.metric("Bollinger", "Band", f"{tech['upper_bb']:.2f} / {tech['lower_bb']:.2f}")
            
            # PROFESYONEL ANALİZ BUTONU
            if analyze_btn:
                st.markdown("---")
                st.subheader(f"🦁 NEXUS PRO: Advanced Market Analysis")
                if not st.secrets.get("GEMINI_API_KEY"): st.error("API Key Yok")
                elif tech is None: st.warning("Yeterli teknik veri yok.")
                else:
                    with st.spinner("Elliott Dalgaları ve Harmonik Formasyonlar Taranıyor..."):
                        try:
                            model = get_model()
                            price_now = user_data[curr]
                            
                            # --- EXPERT PROMPT (Senin istediğin John Murphy / Scott Carney metni) ---
                            expert_prompt = f"""
                            Sen John Murphy ve Scott Carney'in öğretileriyle donatılmış, Elliott Dalgalarını sayabilen, Harmonik formasyonları görebilen elit bir "Teknik Analist"sin.
                            DİL: {st.session_state.language}
                            
                            **KESİN MATEMATİKSEL VERİLER:**
                            * Coin: {user_coin_id.upper()}
                            * Fiyat: {price_now} {curr.upper()}
                            * RSI (14): {tech['rsi']:.2f} ({tech['rsi_msg']})
                            * Trend (SMA 20): {tech['trend']}
                            * MACD: {tech['macd']:.4f} (Sinyal: {tech['macd_sig']:.4f})
                            * Bollinger: Üst {tech['upper_bb']:.2f} / Alt {tech['lower_bb']:.2f}
                            
                            **ANALİZ GÖREVİN (4 DİSİPLİN):**
                            1. **Piyasa Yapısı:** Trend kanalları, Destek/Direnç ve Emir Blokları (Order Blocks) durumu ne?
                            2. **Gelişmiş Formasyonlar:** Olası bir Elliott Dalga sayımı (İtki mi düzeltme mi?) veya Harmonik yapı (W, M, OBO vb.) var mı?
                            3. **İndikatör Uyumu:** RSI ve MACD fiyatı doğruluyor mu yoksa "Uyumsuzluk" (Divergence) var mı?
                            4. **SONUÇ ve RİSK:** Profesyonel bir dille risk/ödül analizi yap.
                            
                            **ÖNEMLİ:** En sona "BASİT ÖZET" başlığı aç ve orada bu teknik detayları bilmeyen biri için 1 cümlelik net sonuç yaz.
                            """
                            res = model.generate_content(expert_prompt)
                            st.markdown(res.text, unsafe_allow_html=True)
                        except: st.error("Bağlantı hatası.")

        else:
            st.warning("Veri yükleniyor...")

    # === MOD 3: PORTAL (CMC LİSTESİ) ===
    else:
        st.markdown(f"<h3 style='color:{st.session_state.theme_color}'>🏆 TOP 10 PIYASA</h3>", unsafe_allow_html=True)
        top10 = get_top10_coins(st.session_state.currency)
        curr_sym = "$" if st.session_state.currency == 'usd' else "₺"
        
        if top10:
            st.markdown(f"""
            <div class="coin-header">
                <div style="flex:1.5;">COIN</div>
                <div style="flex:2; display:flex; justify-content:flex-end;">
                    <div style="width:30%; text-align:right;">FIYAT</div>
                    <div style="width:20%; text-align:right;">1s</div>
                    <div style="width:20%; text-align:right;">24s</div>
                    <div style="width:20%; text-align:right;">7g</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            for idx, coin in enumerate(top10[:10]): 
                p = coin['current_price']
                price_fmt = f"{curr_sym}{p:,.2f}" if p > 1 else f"{curr_sym}{p:.6f}"
                p1 = coin.get('price_change_percentage_1h_in_currency') or 0
                p24 = coin.get('price_change_percentage_24h_in_currency') or 0
                p7 = coin.get('price_change_percentage_7d_in_currency') or 0
                c1 = "#16c784" if p1 > 0 else "#ea3943"
                c24 = "#16c784" if p24 > 0 else "#ea3943"
                c7 = "#16c784" if p7 > 0 else "#ea3943"

                st.markdown(f"""
                <div class="coin-row">
                    <div class="row-left">
                        <span class="coin-rank">{idx+1}</span>
                        <img src="{coin['image']}" width="24" height="24">
                        <span class="coin-name">{coin['symbol'].upper()}</span>
                    </div>
                    <div class="row-right">
                        <div class="price-col">{price_fmt}</div>
                        <div class="stat-col" style="color:{c1};">%{p1:.1f}</div>
                        <div class="stat-col" style="color:{c24};">%{p24:.1f}</div>
                        <div class="stat-col" style="color:{c7};">%{p7:.1f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else: st.info("⚠️ Veri yükleniyor...")

        st.markdown("---")
        c_news, c_social = st.columns([1, 1])
        with c_news:
            st.subheader("📰 GÜNDEM")
            news_items = get_news("crypto market")
            with st.container(height=500):
                for n in news_items:
                    st.markdown(f"""<div class="news-card"><a href="{n['link']}" target="_blank" style="text-decoration: none; color: white; font-weight: bold;">{n['title']}</a></div>""", unsafe_allow_html=True)
        with c_social:
            st.subheader("💬 TOPLULUK")
            with st.container(border=True):
                user_msg = st.text_input("Yorum Yaz:", placeholder="Düşüncelerin...")
                if st.button("PAYLAŞ", use_container_width=True):
                    if user_msg:
                        st.session_state.posts.insert(0, {"user": "Misafir", "msg": user_msg, "time": datetime.datetime.now().strftime("%H:%M")})
                        st.rerun()
            with st.container(height=380):
                for p in st.session_state.posts:
                    st.markdown(f"""<div class="social-card"><span style="color:{st.session_state.theme_color}; font-weight:bold;">@{p['user']}</span> <span style="color:gray; font-size:10px;">{p['time']}</span><br>{p['msg']}</div>""", unsafe_allow_html=True)

# --- SAĞ PANEL (Sadece Terminal ve Pro Modda) ---
if col_right and st.session_state.app_mode != "PORTAL":
    with col_right:
        with st.container(border=True):
            st.markdown("#### ⚙️ Ayarlar")
            curr_opt = st.selectbox("Para Birimi", ["USD", "TRY", "EUR"], label_visibility="collapsed")
            st.session_state.currency = curr_opt.lower()
            st.markdown("<br>", unsafe_allow_html=True)
            thm = st.selectbox("Tema", list(THEMES.keys()), label_visibility="collapsed")
            st.session_state.theme_color = THEMES[thm]
            st.markdown("---")
            target = user_coin_id if 'user_coin_id' in locals() else 'bitcoin'
            st.markdown(f"#### 📰 Haberler")
            news = get_news(target)
            if news:
                for n in news:
                    st.markdown(f"<div style='background-color: #262730; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 12px;'><a href='{n['link']}' style='color: white; text-decoration: none;'>{n['title']}</a></div>", unsafe_allow_html=True)
