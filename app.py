import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import plotly.graph_objects as go
import time
import os
import datetime

# --- 1. AYARLAR ---
st.set_page_config(layout="wide", page_title="NEXUS AI", page_icon="🦁", initial_sidebar_state="collapsed")

# SESSION STATE (AYARLAR & SOSYAL MEDYA)
if 'theme_color' not in st.session_state: st.session_state.theme_color = '#F7931A'
if 'currency' not in st.session_state: st.session_state.currency = 'usd'
if 'language' not in st.session_state: st.session_state.language = 'TR'
if 'app_mode' not in st.session_state: st.session_state.app_mode = 'TERMINAL'
if 'posts' not in st.session_state: 
    # Örnek başlangıç postları
    st.session_state.posts = [
        {"user": "Admin 🦁", "msg": "NEXUS Portal'a hoş geldiniz! Piyasa bugün hareketli.", "time": "10:00"},
        {"user": "Trader_01", "msg": "BTC dominansı düşüyor, altcoin rallisi yakın mı?", "time": "10:05"}
    ]

THEMES = {
    "Bitcoin Turuncusu 🟠": "#F7931A",
    "Neon Mavi 🔵": "#00d2ff",
    "Matrix Yeşili 🟢": "#00FF41",
    "Siber Mor 🟣": "#BC13FE",
    "Alarm Kırmızısı 🔴": "#FF0033"
}

# --- 2. CSS ---
st.markdown(f"""
<style>
    [data-testid="stSidebar"] {{display: none;}}
    
    .block-container {{
        padding-top: 3rem;
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

    .box-content {{
        height: 160px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
    }}
    
    /* PORTAL HABER KARTI */
    .news-card {{
        background-color: #151515;
        border-left: 4px solid {st.session_state.theme_color};
        padding: 15px;
        margin-bottom: 10px;
        border-radius: 4px;
    }}
    
    /* SOSYAL MEDYA KARTI */
    .social-card {{
        background-color: #202020;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
    }}
    
    div.stButton > button {{
        width: 100%;
        border-radius: 8px;
        font-weight: 800 !important;
        font-size: 14px;
        transition: all 0.3s;
        text-transform: uppercase;
    }}
    
    div.stButton > button[kind="primary"] {{
        background-color: {st.session_state.theme_color};
        color: black;
        border: none;
        margin-top: 5px;
        margin-bottom: 10px;
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
        if r.status_code == 429: return "LIMIT"
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
    # TOP 10 LISTESI
    try:
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency={currency}&order=market_cap_desc&per_page=10&page=1&sparkline=false"
        return requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()
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
        # Topic'e göre arama
        rss_url = f"https://news.google.com/rss/search?q={topic}&hl=tr&gl=TR&ceid=TR:tr"
        r = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        root = ET.fromstring(r.content)
        return [{"title": i.find("title").text, "link": i.find("link").text, "pubDate": i.find("pubDate").text} for i in root.findall(".//item")[:10]]
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

# --- EKRAN DÜZENİ MANTIĞI ---
# Terminal modunda 3 sütun (1-4-1), Portal modunda 2 sütun (1-5)
layout_cols = [1, 4, 1] if st.session_state.app_mode == "TERMINAL" else [1, 5]
cols = st.columns(layout_cols)
col_nav = cols[0]
col_main = cols[1]
col_right = cols[2] if len(cols) > 2 else None

# --- SOL PANEL (NAVİGASYON - HER ZAMAN SABİT) ---
with col_nav:
    with st.container(border=True):
        if os.path.exists("logo.jpeg"):
            c_logo, c_text = st.columns([1, 3]) 
            with c_logo: st.image("logo.jpeg", width=70)
            with c_text: st.markdown(f"<div style='display: flex; align-items: center; height: 100%;'><h1 style='color: {st.session_state.theme_color}; margin:0; font-size: 28px; font-weight: 900; letter-spacing: 2px;'>NEXUS</h1></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<h1 style='color: {st.session_state.theme_color}; text-align: center; margin:0; font-size: 24px;'>🦁 NEXUS</h1>", unsafe_allow_html=True)
            
        st.markdown("---")
        
        # SADECE TERMINAL MODUNDA GÖZÜKENLER
        if st.session_state.app_mode == "TERMINAL":
            st.caption("🔍 **KRİPTO SEÇ**")
            coin_input = st.text_input("Coin Ara:", "ethereum", label_visibility="collapsed")
            st.markdown("<br>", unsafe_allow_html=True)
            analyze_btn = st.button("ANALİZİ BAŞLAT", type="primary")
            st.markdown("---")
            st.caption("⏳ **SÜRE**")
            day_opt = st.radio("Süre:", ["24 Saat", "7 Gün"], horizontal=True, label_visibility="collapsed")
            days_api = "1" if day_opt == "24 Saat" else "7"
            st.markdown("<br>", unsafe_allow_html=True)

        # HER İKİ MODDA GÖZÜKENLER
        st.caption("🌐 **MOD SEÇİMİ**")
        mode_select = st.radio("Mod:", ["TERMINAL", "PORTAL"], horizontal=True, label_visibility="collapsed")
        # Mod değişirse sayfayı yenile ki layout güncellensin
        if mode_select != st.session_state.app_mode:
            st.session_state.app_mode = mode_select
            st.rerun()
            
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("🌍 **DİL**")
        lng = st.radio("Dil:", ["TR", "EN"], horizontal=True, label_visibility="collapsed")
        st.session_state.language = lng
        
        # PORTAL MODUNDA AYARLAR BURAYA GELİR (Çünkü sağ panel yok)
        if st.session_state.app_mode == "PORTAL":
            st.markdown("---")
            st.caption("⚙️ **AYARLAR**")
            curr_opt = st.selectbox("Para Birimi", ["USD", "TRY", "EUR"], label_visibility="collapsed")
            st.session_state.currency = curr_opt.lower()
            thm = st.selectbox("Tema", list(THEMES.keys()), label_visibility="collapsed")
            st.session_state.theme_color = THEMES[thm]


# --- ANA İÇERİK (MODA GÖRE DEĞİŞİR) ---
with col_main:
    
    # ==========================
    # MOD 1: TERMINAL (ESKİ DÜZEN)
    # ==========================
    if st.session_state.app_mode == "TERMINAL":
        raw_input = coin_input.lower().strip()
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
            st.warning("⚠️ **API Limiti:** Çok hızlı işlem yaptınız. Lütfen 1 dakika bekleyin.")
        
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
                     with st.spinner("Uzman görüşü hazırlanıyor..."):
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
            st.warning(f"⚠️ '{raw_input}' bulunamadı veya API limitine takıldı.")

    # ==========================
    # MOD 2: PORTAL (YENİ DÜZEN)
    # ==========================
    else:
        # 1. TOP 10 ŞERİDİ
        st.markdown(f"<h3 style='color:{st.session_state.theme_color}'>🏆 TOP 10 COIN (ANLIK)</h3>", unsafe_allow_html=True)
        top10 = get_top10_coins(st.session_state.currency)
        curr_sym = "$" if st.session_state.currency == 'usd' else "₺"
        
        if top10:
            cols_top = st.columns(5) # 5'erli 2 satır gibi gösteririz veya kayarız
            for idx, coin in enumerate(top10[:5]): # İlk 5'i gösterelim sığması için
                chg = coin.get('price_change_percentage_24h', 0)
                color = "#16c784" if chg > 0 else "#ea3943"
                with cols_top[idx]:
                    st.markdown(f"""
                    <div style="background-color: #1E1E1E; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #333;">
                        <img src="{coin['image']}" width="30">
                        <div style="font-weight: bold; margin-top:5px;">{coin['symbol'].upper()}</div>
                        <div style="font-size: 14px;">{curr_sym}{coin['current_price']}</div>
                        <div style="color: {color}; font-size: 12px;">%{chg:.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown("---")
        else:
            st.warning("Top 10 Verisi Alınamadı")

        # 2. İKİLİ KOLON: HABERLER (SOL) - SOSYAL (SAĞ)
        c_news, c_social = st.columns([1, 1])
        
        # --- HABERLER ---
        with c_news:
            st.subheader("📰 PİYASA GÜNDEMİ")
            # Genel piyasa haberlerini çek
            news_items = get_news("crypto market bitcoin economy")
            with st.container(height=600): # Scroll edilebilir alan
                if news_items:
                    for n in news_items:
                        st.markdown(f"""
                        <div class="news-card">
                            <a href="{n['link']}" target="_blank" style="text-decoration: none; color: white; font-weight: bold; font-size: 16px;">{n['title']}</a>
                            <br><span style="color: gray; font-size: 12px;">Kaynak: Google News</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("Haber akışı güncelleniyor...")

        # --- SOSYAL (FORUM) ---
        with c_social:
            st.subheader("💬 NEXUS TOPLULUK")
            
            # Yazı Yazma Alanı
            with st.container(border=True):
                user_msg = st.text_input("Ne düşünüyorsun?", placeholder="Fikirlerini paylaş...")
                if st.button("PAYLAŞ", use_container_width=True):
                    if user_msg:
                        new_post = {
                            "user": "Misafir", 
                            "msg": user_msg, 
                            "time": datetime.datetime.now().strftime("%H:%M")
                        }
                        # Listeyi başa ekle (En yeni en üstte)
                        st.session_state.posts.insert(0, new_post)
                        st.rerun()

            # Akış Alanı
            with st.container(height=450): # Scroll edilebilir alan
                for p in st.session_state.posts:
                    st.markdown(f"""
                    <div class="social-card">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span style="color: {st.session_state.theme_color}; font-weight: bold;">@{p['user']}</span>
                            <span style="color: gray; font-size: 12px;">{p['time']}</span>
                        </div>
                        <div style="color: #ddd;">{p['msg']}</div>
                        <div style="margin-top: 10px; font-size: 18px;">❤️ 🔁</div> 
                    </div>
                    """, unsafe_allow_html=True)

# --- SAĞ PANEL (SADECE TERMINAL MODUNDA VAR) ---
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
            st.markdown(f"#### 📰 {target.upper()} Haberleri")
            news = get_news(target)
            if news:
                for n in news:
                    st.markdown(f"<div style='background-color: #262730; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 12px;'><a href='{n['link']}' style='color: white; text-decoration: none;'>{n['title']}</a></div>", unsafe_allow_html=True)
