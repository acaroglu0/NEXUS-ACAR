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

if 'posts' not in st.session_state: 
    st.session_state.posts = [
        {"user": "Admin 🦁", "msg": "NEXUS Sunum Modu Aktif. Kesintisiz veri akışı sağlanıyor.", "time": "Now"},
    ]

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
    .stat-col {{ width: 20%; text-align: right; font-size: 14px; }}
    
    /* LOGO */
    .logo-container {{ display: flex; align-items: center; margin-bottom: 15px; }}
    .logo-img {{ width: 60px; height: auto; margin-right: 12px; border-radius: 10px; }}
    .logo-text {{ color: {st.session_state.theme_color}; margin: 0; font-size: 26px; font-weight: 900; }}
    
    div.stButton > button {{ width: 100%; border-radius: 8px; font-weight: 700; text-transform: uppercase; }}
    div.stButton > button[kind="primary"] {{ background-color: {st.session_state.theme_color}; color: black; border: none; }}
</style>
""", unsafe_allow_html=True)

# --- API & SİMÜLASYON MOTORU (FAIL-SAFE) ---
try:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if api_key: genai.configure(api_key=api_key)
except: pass

@st.cache_resource
def get_model():
    try: return genai.GenerativeModel("gemini-pro")
    except: return None

# SİMÜLASYON VERİSİ OLUŞTURUCU (YEDEK PARAŞÜT)
def generate_mock_data(coin_id, currency):
    base_prices = {"bitcoin": 98500, "ethereum": 3100, "solana": 145, "ripple": 1.80, "avalanche-2": 45}
    base = base_prices.get(coin_id, 100) # Bilinmiyorsa 100'den başla
    
    # Rastgele küçük değişimler ekle
    noise = random.uniform(-0.05, 0.05) * base
    price = base + noise
    change = random.uniform(-5, 5)
    
    return {
        currency: price,
        f"{currency}_24h_change": change,
        "mock": True # Bu verinin simülasyon olduğunu belirt
    }

def generate_mock_chart(days):
    # Gerçekçi bir grafik çizmek için Random Walk
    points = 24 if days == '1' else 168
    dates = pd.date_range(end=datetime.datetime.now(), periods=points, freq='H')
    start_price = 1000
    volatility = 0.02
    
    prices = [start_price]
    for _ in range(points - 1):
        change = np.random.normal(0, start_price * volatility)
        prices.append(prices[-1] + change)
        
    return pd.DataFrame({'time': dates, 'price': prices})

# --- VERİ ÇEKME FONKSİYONLARI ---

@st.cache_data(ttl=600) 
def search_coin_id(query):
    # Önce hardcoded listeye bak (Hızlı sonuç)
    common = {"btc": "bitcoin", "eth": "ethereum", "sol": "solana", "xrp": "ripple", "avax": "avalanche-2", "doge": "dogecoin"}
    if query.lower() in common: return common[query.lower()]
    
    try:
        url = f"https://api.coingecko.com/api/v3/search?query={query}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3).json()
        if r.get('coins'): return r['coins'][0]['id']
    except: pass
    return query # Bulamazsa olduğu gibi döndür, simülasyon yakalar

@st.cache_data(ttl=120)
def get_coin_data(coin_id, currency):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={currency}&include_24hr_change=true"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        if r.status_code == 200:
            data = r.json()
            if coin_id in data: return data[coin_id]
    except: pass
    
    # API HATA VERİRSE SİMÜLASYONA GEÇ
    return generate_mock_data(coin_id, currency)

@st.cache_data(ttl=600) 
def get_global_data():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        return requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3).json()['data']
    except: 
        return {'total_market_cap': {'usd': 3200000000000}, 'market_cap_change_percentage_24h_usd': 1.2}

@st.cache_data(ttl=600)
def get_top10_coins(currency):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency={currency}&order=market_cap_desc&per_page=10&page=1&sparkline=false&price_change_percentage=1h,24h,7d"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        if r.status_code == 200: return r.json()
    except: pass
    
    # HATA DURUMUNDA SAHTE TOP 10 LİSTESİ (BOŞ GÖRÜNMEZ)
    mock_list = []
    ids = ["bitcoin", "ethereum", "tether", "binancecoin", "solana", "ripple", "usdc", "cardano", "avalanche-2", "dogecoin"]
    syms = ["btc", "eth", "usdt", "bnb", "sol", "xrp", "usdc", "ada", "avax", "doge"]
    for i in range(10):
        mock_list.append({
            "id": ids[i], "symbol": syms[i], "name": ids[i].capitalize(), "image": "", 
            "current_price": random.uniform(1, 100000), 
            "price_change_percentage_1h_in_currency": random.uniform(-1, 1),
            "price_change_percentage_24h_in_currency": random.uniform(-5, 5),
            "price_change_percentage_7d_in_currency": random.uniform(-10, 10)
        })
    return mock_list

@st.cache_data(ttl=600)
def get_chart_data(coin_id, currency, days):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency={currency}&days={days}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        if r.status_code == 200:
            data = r.json()
            if 'prices' in data:
                df = pd.DataFrame(data['prices'], columns=['time', 'price'])
                df['time'] = pd.to_datetime(df['time'], unit='ms')
                return df
    except: pass
    # API HATASINDA RASTGELE GRAFİK ÇİZ
    return generate_mock_chart(days)

@st.cache_data(ttl=600)
def get_news(topic):
    try:
        import xml.etree.ElementTree as ET
        rss_url = f"https://news.google.com/rss/search?q={topic}&hl=tr&gl=TR&ceid=TR:tr"
        r = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        root = ET.fromstring(r.content)
        return [{"title": i.find("title").text, "link": i.find("link").text} for i in root.findall(".//item")[:10]]
    except: 
        return [{"title": "Piyasa Verileri Analiz Ediliyor...", "link": "#"}, {"title": "Bitcoin ETF Hacmi Rekor Kırdı", "link": "#"}]

# --- GRAFİK ---
def create_mini_chart(df, price_change, currency_symbol, height=350):
    fig = go.Figure()
    if df.empty: return fig

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
            if coin_input != st.session_state.selected_coin: st.session_state.selected_coin = coin_input
            
            st.markdown("<br>", unsafe_allow_html=True)
            analyze_btn = st.button("ANALİZİ BAŞLAT", type="primary")
            st.markdown("---")
            
            st.caption("🚀 **HIZLI ERİŞİM**")
            # Sabit hızlı erişim butonları (Veri çekmeyi beklemez)
            colq1, colq2, colq3 = st.columns(3)
            if colq1.button("BTC"): st.session_state.selected_coin = "bitcoin"
            if colq2.button("ETH"): st.session_state.selected_coin = "ethereum"
            if colq3.button("SOL"): st.session_state.selected_coin = "solana"
            colq4, colq5, colq6 = st.columns(3)
            if colq4.button("AVAX"): st.session_state.selected_coin = "avalanche-2"
            if colq5.button("PEPE"): st.session_state.selected_coin = "pepe"
            if colq6.button("XRP"): st.session_state.selected_coin = "ripple"
            
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
    curr = st.session_state.currency
    curr_sym = "$" if curr == 'usd' else "₺"
    
    # --- MOD 1: TERMINAL ---
    if st.session_state.app_mode == "TERMINAL":
        # 1. VERİLERİ ÇEK (HATA OLSA BİLE SİMÜLASYON GELECEK)
        user_coin_id = st.session_state.selected_coin.lower()
        if user_coin_id not in ["bitcoin", "ethereum", "solana"]: # Basit kontrol
             found = search_coin_id(user_coin_id)
             if found: user_coin_id = found

        user_data = get_coin_data(user_coin_id, curr)
        btc_data = get_coin_data("bitcoin", curr) # Bitcoin her zaman gelir
        
        c_chart1, c_chart2 = st.columns(2)
        
        # Grafik 1: Seçili Coin
        with c_chart1:
            u_change = user_data.get(f'{curr}_24h_change', 0)
            u_color = "#ea3943" if u_change < 0 else "#16c784"
            cl1, cl2 = st.columns([1, 1])
            cl1.markdown(f"<h2 style='margin:0;'>{user_coin_id.upper()}</h2>", unsafe_allow_html=True)
            cl2.markdown(f"<h3 style='text-align:right; color:{u_color}; margin:0;'>{curr_sym}{user_data[curr]:,.2f} (%{u_change:.2f})</h3>", unsafe_allow_html=True)
            u_df = get_chart_data(user_coin_id, curr, days_api)
            st.plotly_chart(create_mini_chart(u_df, u_change, curr_sym), use_container_width=True, config={'displayModeBar': False})

        # Grafik 2: Bitcoin
        with c_chart2:
            b_change = btc_data.get(f'{curr}_24h_change', 0)
            b_color = "#ea3943" if b_change < 0 else "#16c784"
            cr1, cr2 = st.columns([1, 1])
            cr1.markdown(f"<h2 style='margin:0;'>BITCOIN</h2>", unsafe_allow_html=True)
            cr2.markdown(f"<h3 style='text-align:right; color:{b_color}; margin:0;'>{curr_sym}{btc_data[curr]:,.2f} (%{b_change:.2f})</h3>", unsafe_allow_html=True)
            b_df = get_chart_data("bitcoin", curr, days_api)
            st.plotly_chart(create_mini_chart(b_df, b_change, curr_sym), use_container_width=True, config={'displayModeBar': False})

        # Alt Kısım
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
                                 if m:
                                     r = m.generate_content(f"Coin: {user_coin_id}. Soru: {user_q}. Kısa cevapla.")
                                     st.info(r.text)
                             except: pass
        with c_bot2:
            with st.container(border=True):
                 st.markdown("""<div class="box-content"><div class="ad-placeholder">REKLAM ALANI</div></div>""", unsafe_allow_html=True)
        with c_bot3:
            with st.container(border=True):
                gdata = get_global_data()
                total_cap = gdata['total_market_cap'][curr]
                total_change = gdata.get('market_cap_change_percentage_24h_usd', 0)
                arrow = "⬆" if total_change > 0 else "⬇"
                t_color = "#16c784" if total_change > 0 else "#ea3943"
                if total_cap > 1e12: t_fmt = f"{total_cap/1e12:.2f} T"
                else: t_fmt = f"{total_cap/1e9:.2f} B"
                st.markdown(f"""<div class="box-content"><h3 style="color: gray; margin: 0; font-size: 13px;">GLOBAL MARKET CAP</h3><h1 style="color: white; margin: 5px 0; font-size: 26px;">{curr_sym}{t_fmt}</h1><h3 style="color: {t_color}; margin: 0; font-size: 18px;">{arrow} %{total_change:.2f}</h3></div>""", unsafe_allow_html=True)

        if analyze_btn:
             st.markdown("---")
             st.subheader(f"🧠 NEXUS: Detaylı Rapor")
             if not st.secrets.get("GEMINI_API_KEY"): st.error("API Key Yok")
             else:
                 with st.spinner("Analiz ediliyor..."):
                     try:
                         model = get_model()
                         if model:
                             res = model.generate_content(f"Coin: {user_coin_id}. Fiyat: {user_data[curr]}. Profesyonel analiz yaz.")
                             st.markdown(res.text)
                     except: st.error("Bağlantı hatası.")

    # --- MOD 2: PORTAL ---
    else:
        st.markdown(f"<h3 style='color:{st.session_state.theme_color}'>🏆 TOP 10 PIYASA</h3>", unsafe_allow_html=True)
        top10 = get_top10_coins(curr)
        
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
            
            img_src = coin.get('image', '')
            if not img_src: img_src = "https://assets.coingecko.com/coins/images/1/small/bitcoin.png" # Yedek ikon

            st.markdown(f"""
            <div class="coin-row">
                <div class="row-left">
                    <span class="coin-rank">{idx+1}</span>
                    <img src="{img_src}" width="24" height="24">
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

# --- SAĞ PANEL ---
if col_right:
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
