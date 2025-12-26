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
if 'portal_view' not in st.session_state: st.session_state.portal_view = 'LIST' # LIST veya DETAIL
if 'detail_coin' not in st.session_state: st.session_state.detail_coin = None

if 'posts' not in st.session_state: 
    st.session_state.posts = [
        {"user": "Admin 🦁", "msg": "Sistem restore edildi. Stabilite %100.", "time": "10:00"},
    ]

THEMES = {
    "Bitcoin Turuncusu 🟠": "#F7931A",
    "Neon Mavi 🔵": "#00d2ff",
    "Matrix Yeşili 🟢": "#00FF41",
    "Siber Mor 🟣": "#BC13FE",
    "Alarm Kırmızısı 🔴": "#FF0033"
}

# --- YARDIMCI FONKSİYONLAR ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f: data = f.read()
    return base64.b64encode(data).decode()

logo_path = "logo.jpeg"
logo_base64 = get_base64_of_bin_file(logo_path) if os.path.exists(logo_path) else None

# --- 2. CSS ---
st.markdown(f"""
<style>
    [data-testid="stSidebar"] {{display: none;}}
    .block-container {{ padding-top: 2rem; padding-bottom: 2rem; padding-left: 1rem; padding-right: 1rem; max-width: 100%; }}
    
    .nexus-panel {{ background-color: #1E1E1E; padding: 10px; border-radius: 12px; border: 1px solid #333; margin-bottom: 10px; }}
    
    /* LOGO DUZENİ (FIXED) */
    .logo-container {{ display: flex; align-items: center; margin-bottom: 20px; flex-wrap: nowrap; }}
    .logo-img {{ width: 75px; height: auto; margin-right: 15px; border-radius: 12px; flex-shrink: 0; }}
    .logo-text {{ color: {st.session_state.theme_color}; margin: 0; font-size: 30px; font-weight: 900; letter-spacing: 2px; line-height: 1; white-space: nowrap; }}
    
    /* TABLO */
    .coin-header {{ display: flex; justify-content: space-between; color: gray; font-size: 12px; padding: 5px 10px; font-weight: bold; }}
    .coin-row {{ display: flex; align-items: center; justify-content: space-between; background-color: #151515; border-bottom: 1px solid #333; padding: 12px 10px; border-radius: 6px; margin-bottom: 5px; }}
    .coin-row:hover {{ background-color: #252525; }}
    
    .row-left {{ display: flex; align-items: center; flex: 1.5; }}
    .row-right {{ display: flex; align-items: center; flex: 2; justify-content: flex-end; }}
    
    .price-col {{ width: 30%; text-align: right; font-family: monospace; font-weight: bold; color: white; }}
    .stat-col {{ width: 20%; text-align: right; font-size: 14px; }}
    
    /* DETAY KARTLARI */
    .stat-box {{ background-color: #1E1E1E; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #333; margin-bottom: 10px; }}
    
    div.stButton > button {{ border-radius: 8px; font-weight: 700 !important; text-transform: uppercase; }}
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
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name: return genai.GenerativeModel(m.name)
    except: pass
    return genai.GenerativeModel("gemini-pro")

# --- VERİ ---
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
def get_top10_coins(currency):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency={currency}&order=market_cap_desc&per_page=10&page=1&sparkline=false&price_change_percentage=1h,24h,7d"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code != 200: return []
        return r.json()
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
def create_chart(df, price_change, currency_symbol, height=350):
    fig = go.Figure()
    if df.empty:
        fig.update_layout(height=height, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False), yaxis=dict(visible=False))
        return fig
    
    color = '#16c784' if price_change >= 0 else '#ea3943'
    fill = 'rgba(22, 199, 132, 0.2)' if price_change >= 0 else 'rgba(234, 57, 67, 0.2)'
    
    fig.add_trace(go.Scatter(x=df['time'], y=df['price'], mode='lines', line=dict(color=color, width=2), fill='tozeroy', fillcolor=fill))
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                      hovermode='x unified', xaxis=dict(showgrid=False, visible=False), 
                      yaxis=dict(side='right', gridcolor='rgba(128,128,128,0.1)', tickprefix=currency_symbol))
    return fig

# --- DÜZEN MANTIĞI (BU KISIM ÇOK ÖNEMLİ) ---
# Terminal ise 3 sütun (Eski düzen), Portal ise 2 sütun (Geniş düzen)
layout_cols = [1, 4, 1] if st.session_state.app_mode == "TERMINAL" else [1, 5]
cols = st.columns(layout_cols)
col_nav = cols[0]
col_main = cols[1]
col_right = cols[2] if len(cols) > 2 else None

# --- 1. SOL PANEL ---
with col_nav:
    with st.container(border=True):
        # LOGO
        if logo_base64:
            st.markdown(f"""<div class="logo-container"><img src="data:image/jpeg;base64,{logo_base64}" class="logo-img"><h1 class="logo-text">NEXUS</h1></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"<h1 style='color: {st.session_state.theme_color}; text-align: center; margin:0; font-size: 24px;'>🦁 NEXUS</h1>", unsafe_allow_html=True)
        st.markdown("---")
        
        # SADECE TERMINAL MODUNDA MENÜ
        if st.session_state.app_mode == "TERMINAL":
            st.caption("🔍 **KRİPTO SEÇ**")
            # Default ETH gelecek
            coin_input = st.text_input("Coin Ara:", st.session_state.selected_coin, label_visibility="collapsed")
            if coin_input != st.session_state.selected_coin: st.session_state.selected_coin = coin_input
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("ANALİZİ BAŞLAT", type="primary")
            
            st.markdown("---")
            st.caption("🚀 **HIZLI ERİŞİM**")
            top10 = get_top10_coins("usd")
            if top10:
                cq = st.columns(3)
                for i, c in enumerate(top10[:9]):
                    if cq[i%3].button(c['symbol'].upper(), key=f"qk_{c['id']}"):
                        st.session_state.selected_coin = c['id']
                        st.rerun()
            
            st.markdown("---")
            st.caption("⏳ **SÜRE**")
            st.radio("Süre:", ["24 Saat", "7 Gün"], horizontal=True, label_visibility="collapsed")

        # ORTAK AYARLAR
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("🌐 **MOD**")
        mode = st.radio("Mod:", ["TERMINAL", "PORTAL"], horizontal=True, label_visibility="collapsed")
        if mode != st.session_state.app_mode:
            st.session_state.app_mode = mode
            st.session_state.portal_view = 'LIST' # Mod değişince listeye dön
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("🌍 **DİL**")
        st.radio("Dil:", ["TR", "EN"], horizontal=True, label_visibility="collapsed")
        
        if st.session_state.app_mode == "PORTAL":
            st.markdown("---")
            st.caption("⚙️ **AYARLAR**")
            c_opt = st.selectbox("Para Birimi", ["USD", "TRY", "EUR"], label_visibility="collapsed")
            st.session_state.currency = c_opt.lower()
            thm = st.selectbox("Tema", list(THEMES.keys()), label_visibility="collapsed")
            st.session_state.theme_color = THEMES[thm]

# --- 2. ANA İÇERİK ---
with col_main:
    curr = st.session_state.currency
    csym = "$" if curr=='usd' else "₺"

    # --- MOD: TERMINAL ---
    if st.session_state.app_mode == "TERMINAL":
        coin = st.session_state.selected_coin.lower()
        u_data = get_coin_data(coin, curr)
        
        if not u_data: # Bulamazsa search yap
            fid = search_coin_id(coin)
            if fid: 
                coin = fid
                u_data = get_coin_data(coin, curr)
        
        btc_data = get_coin_data("bitcoin", curr)
        
        if u_data and u_data!="LIMIT" and btc_data:
            c1, c2 = st.columns(2)
            with c1:
                chg = u_data[f'{curr}_24h_change']
                clr = "#16c784" if chg>=0 else "#ea3943"
                st.markdown(f"### {coin.upper()}")
                st.markdown(f"<h2 style='color:{clr}'>{csym}{u_data[curr]:,.2f} (%{chg:.2f})</h2>", unsafe_allow_html=True)
                st.plotly_chart(create_chart(get_chart_data(coin, curr, 1), chg, csym), use_container_width=True, config={'displayModeBar':False})
            with c2:
                bchg = btc_data[f'{curr}_24h_change']
                bclr = "#16c784" if bchg>=0 else "#ea3943"
                st.markdown(f"### BITCOIN")
                st.markdown(f"<h2 style='color:{bclr}'>{csym}{btc_data[curr]:,.2f} (%{bchg:.2f})</h2>", unsafe_allow_html=True)
                st.plotly_chart(create_chart(get_chart_data("bitcoin", curr, 1), bchg, csym), use_container_width=True, config={'displayModeBar':False})
            
            c_ask, c_ad, c_glob = st.columns(3)
            with c_ask:
                with st.container(border=True):
                    st.caption("🤖 **AI SOR**")
                    st.text_input("Soru:", placeholder="Destek neresi?", label_visibility="collapsed")
                    st.button("GÖNDER")
            with c_ad:
                with st.container(border=True):
                    st.markdown("<div style='height:100px; display:flex; align-items:center; justify-content:center; color:gray;'>REKLAM ALANI</div>", unsafe_allow_html=True)
            with c_glob:
                with st.container(border=True):
                    gdata = get_global_data()
                    if gdata:
                        cap = gdata['total_market_cap'][curr]
                        if cap > 1e12: cap_s = f"{cap/1e12:.2f} T"
                        else: cap_s = f"{cap/1e9:.2f} B"
                        st.metric("Global Cap", f"{csym}{cap_s}", f"%{gdata['market_cap_change_percentage_24h_usd']:.2f}")

        else:
            st.warning("Veri yükleniyor veya API limiti...")

    # --- MOD: PORTAL ---
    elif st.session_state.app_mode == "PORTAL":
        
        # A) LİSTE GÖRÜNÜMÜ
        if st.session_state.portal_view == 'LIST':
            st.markdown(f"<h3 style='color:{st.session_state.theme_color}'>🏆 TOP 10 (CMC)</h3>", unsafe_allow_html=True)
            
            # Başlıklar
            h1, h2, h3 = st.columns([0.5, 2, 2.5])
            h1.markdown("**#**")
            h2.markdown("**Coin**")
            h3.markdown("**Fiyat / Değişimler**") # Basitleştirilmiş başlık
            st.markdown("---")
            
            top10 = get_top10_coins(curr)
            if top10:
                for i, c in enumerate(top10[:10]):
                    cc1, cc2, cc3, cc4 = st.columns([0.5, 2, 2, 0.5])
                    
                    cc1.markdown(f"<span style='color:gray; line-height:35px;'>{i+1}</span>", unsafe_allow_html=True)
                    
                    cc2.markdown(f"""
                    <div style="display:flex; align-items:center; height:35px;">
                        <img src="{c['image']}" width="24" style="margin-right:10px; border-radius:50%;">
                        <span style="font-weight:bold;">{c['symbol'].upper()}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Fiyat ve Yüzdeler (Yan yana)
                    p = c['current_price']
                    p24 = c.get('price_change_percentage_24h_in_currency') or 0
                    clr = "#16c784" if p24>=0 else "#ea3943"
                    
                    cc3.markdown(f"""
                    <div style="text-align:right; line-height:35px;">
                        <span style="font-family:monospace; font-weight:bold;">{csym}{p:,.2f}</span>
                        <span style="color:{clr}; margin-left:10px; font-size:13px;">%{p24:.2f}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # İNCELE BUTONU (SATIR İÇİNDE)
                    if cc4.button("👁️", key=f"insp_{c['id']}", help="Detaylı İncele"):
                        st.session_state.detail_coin = c['id']
                        st.session_state.portal_view = 'DETAIL'
                        st.rerun()
                    
                    st.markdown("<div style='border-bottom:1px solid #333; margin:5px 0;'></div>", unsafe_allow_html=True)
            else:
                st.info("Veri yükleniyor...")
                
            # Alt Kısım (Haberler vb.)
            st.markdown("---")
            cn, cs = st.columns(2)
            with cn:
                st.subheader("📰 Gündem")
                news = get_news("crypto")
                with st.container(height=300):
                    for n in news: st.markdown(f"- [{n['title']}]({n['link']})")
            with cs:
                st.subheader("💬 Sohbet")
                with st.container(height=300):
                    for p in st.session_state.posts: st.text(f"{p['user']}: {p['msg']}")

        # B) DETAY GÖRÜNÜMÜ (PORTAL İÇİNDE)
        elif st.session_state.portal_view == 'DETAIL':
            # Geri Dön Butonu
            if st.button("⬅️ LİSTEYE DÖN", type="secondary"):
                st.session_state.portal_view = 'LIST'
                st.rerun()
            
            d_id = st.session_state.detail_coin
            try:
                url = f"https://api.coingecko.com/api/v3/coins/{d_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false"
                dd = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
                md = dd['market_data']
                
                # Başlık
                c_img, c_tit = st.columns([1, 6])
                c_img.image(dd['image']['large'], width=80)
                c_tit.markdown(f"<h1 style='margin:0'>{dd['name']} ({dd['symbol'].upper()})</h1>", unsafe_allow_html=True)
                
                # Fiyat
                dp = md['current_price'][curr]
                dpc = md['price_change_percentage_24h']
                dclr = "#16c784" if dpc>=0 else "#ea3943"
                st.markdown(f"<h2 style='color:{dclr}'>{csym}{dp:,.2f} (%{dpc:.2f})</h2>", unsafe_allow_html=True)
                
                # Grafik
                st.plotly_chart(create_chart(get_chart_data(d_id, curr, 7), dpc, csym), use_container_width=True)
                
                # İstatistikler
                s1, s2, s3 = st.columns(3)
                s1.metric("Market Cap", f"{csym}{md['market_cap'][curr]:,.0f}")
                s2.metric("24s Hacim", f"{csym}{md['total_volume'][curr]:,.0f}")
                s3.metric("ATH", f"{csym}{md['ath'][curr]:,.2f}")
                
                st.info(dd['description']['en'][:400] + "...")
                
            except:
                st.error("Detay verisi alınamadı.")

# --- 3. SAĞ PANEL (SADECE TERMINAL) ---
if col_right:
    with col_right:
        with st.container(border=True):
            st.markdown("#### ⚙️ Ayarlar")
            c_opt = st.selectbox("Para Birimi", ["USD", "TRY", "EUR"], label_visibility="collapsed", key="sb_curr")
            st.session_state.currency = c_opt.lower()
            st.markdown("<br>", unsafe_allow_html=True)
            thm = st.selectbox("Tema", list(THEMES.keys()), label_visibility="collapsed", key="sb_theme")
            st.session_state.theme_color = THEMES[thm]
            st.markdown("---")
            target = st.session_state.selected_coin
            st.markdown(f"#### 📰 Haberler")
            news = get_news(target)
            if news:
                for n in news:
                    st.markdown(f"<div style='background-color: #262730; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 12px;'><a href='{n['link']}' style='color: white; text-decoration: none;'>{n['title']}</a></div>", unsafe_allow_html=True)
