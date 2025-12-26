import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import plotly.graph_objects as go
import time
import os
import datetime
import base64

# --- 1. AYARLAR ---
st.set_page_config(layout="wide", page_title="NEXUS AI", page_icon="🦁", initial_sidebar_state="collapsed")

# SESSION STATE
if 'theme_color' not in st.session_state: st.session_state.theme_color = '#F7931A'
if 'currency' not in st.session_state: st.session_state.currency = 'usd'
if 'language' not in st.session_state: st.session_state.language = 'TR'
if 'app_mode' not in st.session_state: st.session_state.app_mode = 'TERMINAL'
if 'selected_coin' not in st.session_state: st.session_state.selected_coin = 'ethereum' # DEFAULT ETH

if 'posts' not in st.session_state: 
    st.session_state.posts = [
        {"user": "Admin 🦁", "msg": "NEXUS Portal stabil sürüme döndü.", "time": "10:00"},
        {"user": "Trader_01", "msg": "ETH grafiği harika görünüyor.", "time": "10:05"}
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

# --- 2. CSS ---
st.markdown(f"""
<style>
    [data-testid="stSidebar"] {{display: none;}}
    
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }}
    
    .nexus-panel {{
        background-color: #1E1E1E;
        padding: 10px;
        border-radius: 12px;
        border: 1px solid #333;
        margin-bottom: 10px;
    }}
    
    /* CMC TARZI TABLO */
    .coin-header {{
        display: flex;
        justify-content: space-between;
        color: gray;
        font-size: 12px;
        padding: 5px 10px;
        margin-bottom: 5px;
        font-weight: bold;
    }}
    
    .coin-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: #151515;
        border-bottom: 1px solid #333;
        padding: 12px 10px;
        transition: background 0.2s;
        border-radius: 6px;
        margin-bottom: 5px;
    }}
    .coin-row:hover {{
        background-color: #252525;
    }}
    
    .row-left {{ display: flex; align-items: center; flex: 1.5; }}
    .coin-rank {{ color: gray; font-size: 12px; margin-right: 10px; min-width: 20px; }}
    .coin-name {{ font-weight: bold; color: white; margin-left: 10px; font-size: 15px; }}
    
    .row-right {{ display: flex; align-items: center; flex: 2; justify-content: flex-end; }}
    .stat-col {{ width: 20%; text-align: right; font-size: 14px; }}
    .price-col {{ width: 30%; text-align: right; font-family: monospace; font-weight: bold; color: white; }}
    
    @media only screen and (max-width: 600px) {{
        .stat-col {{ font-size: 11px; width: 22%; }}
        .price-col {{ font-size: 12px; width: 34%; }}
        .coin-name {{ font-size: 13px; }}
    }}

    /* LOGO DUZENİ */
    .logo-container {{
        display: flex;
        align-items: center; 
        justify-content: flex-start;
        margin-bottom: 15px;
        flex-wrap: nowrap;
    }}
    .logo-img {{
        width: 60px; 
        height: auto;
        margin-right: 12px;
        border-radius: 10px;
        flex-shrink: 0;
    }}
    .logo-text {{
        color: {st.session_state.theme_color};
        margin: 0;
        font-size: 26px;
        font-weight: 900;
        letter-spacing: 1px;
        line-height: 1;
        white-space: nowrap;
    }}
    
    div.stButton > button {{
        width: 100%;
        border-radius: 8px;
        font-weight: 700 !important;
        font-size: 13px;
        text-transform: uppercase;
        padding: 8px 0px; 
    }}
    
    div.stButton > button[kind="primary"] {{
        background-color: {st.session_state.theme_color};
        color: black;
        border: none;
        font-size: 14px;
        font-weight: 900 !important;
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
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name: return genai.GenerativeModel(m.name)
    except: pass
    return genai.GenerativeModel("gemini-pro")

# --- VERİ MOTORU ---

@st.cache_data(ttl=3600) 
def search_coin_id(query):
    try:
        url = f"https://api.coingecko.com/api/v3/search?query={query}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()
        coins = r.get('coins', [])
        if not coins: return None
        for coin in coins:
            if coin['symbol'].lower() == query.lower():
                return coin['id']
        return coins[0]['id']
    except: return None

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

@st.cache_data(ttl=86400) 
def get_global_data():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        return requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()['data']
    except: return None

@st.cache_data(ttl=300)
def get_top10_coins(currency):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency={currency}&order=market_cap_desc&per_page=10&page=1&sparkline=false&price_change_percentage=1h,24h,7d"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code != 200: return [] 
        data = r.json()
        if isinstance(data, list): return data
        return []
    except: return []

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

@st.cache_data(ttl=600)
def get_news(topic):
    try:
        import xml.etree.ElementTree as ET
        rss_url = f"https://news.google.com/rss/search?q={topic}&hl=tr&gl=TR&ceid=TR:tr"
        r = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        root = ET.fromstring(r.content)
        return [{"title": i.find("title").text, "link": i.find("link").text} for i in root.findall(".//item")[:10]]
    except: return []

# --- GRAFİK ---
def create_mini_chart(df, price_change, currency_symbol, height=350):
    fig = go.Figure()
    if df.empty:
        fig.update_layout(height=height, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(visible=False), yaxis=dict(visible=False),
                          annotations=[dict(text="Veri Yok", xref="paper", yref="paper", showarrow=False, font=dict(color="gray"))])
        return fig

    main_color = '#ea3943' if price_change < 0 else '#16c784'
    fill_color = 'rgba(234, 57, 67, 0.2)' if price_change < 0 else 'rgba(22, 199, 132, 0.2)' 

    min_p = df['price'].min()
    max_p = df['price'].max()
    padding = (max_p - min_p) * 0.05
    
    fig.add_trace(go.Scatter(
        x=df['time'], y=df['price'], mode='lines', 
        line=dict(color=main_color, width=2), 
        fill='tozeroy', fillcolor=fill_color, showlegend=False
    ))
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified', dragmode='pan',
        xaxis=dict(showgrid=False, visible=False),
        yaxis=dict(side='right', visible=True, showgrid=True, gridcolor='rgba(128,128,128,0.1)', color='white', range=[min_p-padding, max_p+padding], tickprefix=currency_symbol)
    )
    return fig

# --- LAYOUT ---
layout_cols = [1, 4, 1] if st.session_state.app_mode == "TERMINAL" else [1, 5]
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
            st.markdown(f"<h1 style='color: {st.session_state.theme_color}; text-align: center; margin:0; font-size: 24px;'>🦁 NEXUS</h1>", unsafe_allow_html=True)
            
        st.markdown("---")
        
        if st.session_state.app_mode == "TERMINAL":
            st.caption("🔍 **KRİPTO SEÇ**")
            coin_input = st.text_input("Coin Ara:", st.session_state.selected_coin, label_visibility="collapsed")
            if coin_input != st.session_state.selected_coin:
                st.session_state.selected_coin = coin_input
            
            st.markdown("<br>", unsafe_allow_html=True)
            analyze_btn = st.button("ANALİZİ BAŞLAT", type="primary")
            
            st.markdown("---")
            st.caption("🚀 **HIZLI ERİŞİM (TOP 10)**")
            top10_data = get_top10_coins(st.session_state.currency)
            
            if top10_data:
                cols_quick = st.columns(3)
                for i, coin in enumerate(top10_data[:10]):
                    if cols_quick[i % 3].button(coin['symbol'].upper(), key=f"qbtn_{coin['id']}"):
                        st.session_state.selected_coin = coin['id']
                        st.rerun()
            else:
                st.caption("Liste yükleniyor...")

            st.markdown("---")
            st.caption("⏳ **SÜRE**")
            day_opt = st.radio("Süre:", ["24 Saat", "7 Gün"], horizontal=True, label_visibility="collapsed")
            days_api = "1" if day_opt == "24 Saat" else "7"

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("🌐 **MOD**")
        mode_select = st.radio("Mod:", ["TERMINAL", "PORTAL"], horizontal=True, label_visibility="collapsed")
        if mode_select != st.session_state.app_mode:
            st.session_state.app_mode = mode_select
            st.rerun()
            
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("🌍 **DİL**")
        lng = st.radio("Dil:", ["TR", "EN"], horizontal=True, label_visibility="collapsed")
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
    
    # --- MOD 1: TERMINAL ---
    if st.session_state.app_mode == "TERMINAL":
        raw_input = st.session_state.selected_coin.lower().strip()
        btc_id = "bitcoin"
        curr = st.session_state.currency
        curr_sym = "$" if curr == 'usd' else "₺" if curr == 'try' else "€"
        
        user_coin_id = raw_input
        user_data = get_coin_data(user_coin_id, curr)
        
        if user_data is None:
            found_id = search_coin_id(raw_input)
            if found_id:
                user_coin_id = found_id
                user_data = get_coin_data(user_coin_id, curr)

        btc_data = get_coin_data(btc_id, curr)
        
        if user_data == "LIMIT" or btc_data == "LIMIT":
            st.warning("⚠️ **API Limiti:** Veri sağlayıcı yoğun. Lütfen 1 dakika bekleyin.")
        
        elif user_data and btc_data:
            c_chart1, c_chart2 = st.columns(2)
            
            with c_chart1:
                u_change = user_data.get(f'{curr}_24h_change', 0)
                u_color = "#ea3943" if u_change < 0 else "#16c784"
                cl1, cl2 = st.columns([1, 1])
                cl1.markdown(f"<h2 style='margin:0;'>{user_coin_id.upper()}</h2>", unsafe_allow_html=True)
                cl2.markdown(f"<h3 style='text-align:right; color:{u_color}; margin:0;'>{curr_sym}{user_data[curr]:,.2f} (%{u_change:.2f})</h3>", unsafe_allow_html=True)
                u_df = get_chart_data(user_coin_id, curr, days_api)
                st.plotly_chart(create_mini_chart(u_df, u_change, curr_sym), use_container_width=True, config={'displayModeBar': False}, key="user_chart")

            with c_chart2:
                b_change = btc_data.get(f'{curr}_24h_change', 0)
                b_color = "#ea3943" if b_change < 0 else "#16c784"
                cr1, cr2 = st.columns([1, 1])
                cr1.markdown(f"<h2 style='margin:0;'>BITCOIN</h2>", unsafe_allow_html=True)
                cr2.markdown(f"<h3 style='text-align:right; color:{b_color}; margin:0;'>{curr_sym}{btc_data[curr]:,.2f} (%{b_change:.2f})</h3>", unsafe_allow_html=True)
                b_df = get_chart_data(btc_id, curr, days_api)
                st.plotly_chart(create_mini_chart(b_df, b_change, curr_sym), use_container_width=True, config={'displayModeBar': False}, key="btc_chart")

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
                    else: st.caption("Veri güncelleniyor...")
            
            if analyze_btn:
                 st.markdown("---")
                 st.subheader(f"🧠 NEXUS: Detaylı Rapor")
                 if not st.secrets.get("GEMINI_API_KEY"): st.error("API Key Yok")
                 else:
                     with st.spinner("Analiz ediliyor..."):
                         try:
                             model = get_model()
                             price_now = user_data[curr]
                             structured_prompt = f"""
                             Sen uzman bir kripto analistisin. Coin: {user_coin_id.upper()}. Fiyat: {price_now} {curr.upper()}.
                             Analizi şu 3 başlıkta yap (Dil: {st.session_state.language}):
                             **1. GENEL BAKIŞ & HABERLER** (Proje ve piyasa algısı özeti)
                             **2. RİSK ANALİZİ** (Risk durumu)
                             **3. FİYAT TAHMİNİ (ÖNEMLİ)**
                             * Teknik analiz özeti.
                             * **KISA VADE (1-3 GÜN):** Tahminini tam olarak şu HTML formatında yaz (Emoji KULLANMA, sadece yazı):
                               <span style='color:#16c784; font-size:24px; font-weight:bold;'>%X.XX YÜKSELİŞ</span> (Eğer artışsa)
                               <span style='color:#ea3943; font-size:24px; font-weight:bold;'>%X.XX DÜŞÜŞ</span> (Eğer düşüşse)
                             * **UZUN VADE:** Beklentini yaz.
                             """
                             res = model.generate_content(structured_prompt)
                             st.markdown(res.text, unsafe_allow_html=True)
                         except: st.error("Bağlantı hatası.")
        else:
            st.warning(f"⚠️ '{raw_input}' bulunamadı.")

    # --- MOD 2: PORTAL (CMC TARZI LİSTE) ---
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
        else:
            st.info("⚠️ Top 10 verisi yükleniyor...")

        st.markdown("---")
        c_news, c_social = st.columns([1, 1])
        
        with c_news:
            st.subheader("📰 GÜNDEM")
            news_items = get_news("crypto market")
            with st.container(height=500):
                if news_items:
                    for n
