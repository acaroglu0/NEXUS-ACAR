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
if 'app_mode' not in st.session_state: st.session_state.app_mode = 'TERMINAL' # TERMINAL, PORTAL, DETAIL
if 'selected_coin' not in st.session_state: st.session_state.selected_coin = 'ethereum' # Varsayılan
if 'detail_id' not in st.session_state: st.session_state.detail_id = None # Detay sayfası için

if 'posts' not in st.session_state: 
    st.session_state.posts = [
        {"user": "Admin 🦁", "msg": "NEXUS v12.0: Artık coinlere tıklayıp detaylarına bakabilirsiniz!", "time": "09:00"},
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

def go_to_detail(coin_id):
    st.session_state.detail_id = coin_id
    st.session_state.app_mode = 'DETAIL'
    # Sayfayı yenilemeye gerek yok, script baştan çalışınca modu kontrol edecek

def go_back_to_portal():
    st.session_state.app_mode = 'PORTAL'
    st.session_state.detail_id = None

# --- 2. CSS ---
st.markdown(f"""
<style>
    [data-testid="stSidebar"] {{display: none;}}
    .block-container {{ padding-top: 2rem; padding-bottom: 2rem; max-width: 100%; }}
    
    /* LOGO KONTEYNER */
    .logo-container {{ display: flex; align-items: center; margin-bottom: 15px; }}
    .logo-img {{ width: 60px; height: auto; margin-right: 12px; border-radius: 10px; }}
    .logo-text {{ color: {st.session_state.theme_color}; margin: 0; font-size: 26px; font-weight: 900; letter-spacing: 1px; line-height: 1; }}
    
    /* BUTONLAR */
    div.stButton > button {{ border-radius: 8px; font-weight: 700 !important; text-transform: uppercase; }}
    div.stButton > button[kind="primary"] {{ background-color: {st.session_state.theme_color}; color: black; border: none; }}
    
    /* TABLO STİLİ (Streamlit Kolonları için) */
    .metric-pos {{ color: #16c784; font-weight: bold; }}
    .metric-neg {{ color: #ea3943; font-weight: bold; }}
    .coin-name-list {{ font-weight: bold; font-size: 15px; }}
    
    /* DETAY SAYFASI */
    .detail-header {{ font-size: 30px; font-weight: 900; color: white; }}
    .detail-price {{ font-size: 24px; font-family: monospace; color: {st.session_state.theme_color}; }}
    .stat-box {{ background-color: #1E1E1E; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #333; }}
    .stat-label {{ color: gray; font-size: 12px; }}
    .stat-val {{ color: white; font-size: 16px; font-weight: bold; }}
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
        # 1H, 24H, 7D verisi isteniyor
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

# --- NAVİGASYON (SOL PANEL) ---
# Detail modunda sol panel farklı görünebilir veya sabit kalabilir. Şimdilik sabit.
layout_cols = [1, 4, 1] if st.session_state.app_mode == "TERMINAL" else [1, 5]
if st.session_state.app_mode == "DETAIL": layout_cols = [1, 5] # Detay sayfasında da geniş

cols = st.columns(layout_cols)
col_nav = cols[0]
col_main = cols[1]
col_right = cols[2] if len(cols) > 2 else None

with col_nav:
    with st.container(border=True):
        if logo_base64:
            st.markdown(f"""<div class="logo-container"><img src="data:image/jpeg;base64,{logo_base64}" class="logo-img"><h1 class="logo-text">NEXUS</h1></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"<h1 style='color: {st.session_state.theme_color}; text-align: center; margin:0; font-size: 24px;'>🦁 NEXUS</h1>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # MENÜLER
        if st.session_state.app_mode == "DETAIL":
            if st.button("⬅️ LİSTEYE DÖN"):
                go_back_to_portal()
                st.rerun()
        
        elif st.session_state.app_mode == "TERMINAL":
            st.caption("🔍 **KRİPTO SEÇ**")
            coin_input = st.text_input("Coin Ara:", st.session_state.selected_coin, label_visibility="collapsed")
            if coin_input != st.session_state.selected_coin: st.session_state.selected_coin = coin_input
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("ANALİZİ BAŞLAT", type="primary")
            
            st.markdown("---")
            st.caption("🚀 **HIZLI ERİŞİM**")
            top10_ids = ["bitcoin", "ethereum", "solana", "avalanche-2", "pepe", "ripple"]
            c_q = st.columns(3)
            for i, cid in enumerate(top10_ids):
                if c_q[i%3].button(cid[:3].upper(), key=f"qk_{cid}"):
                    st.session_state.selected_coin = cid
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("🌐 **MOD**")
        # Detail modundaysa radyo butonunu gizleyebiliriz veya Portal'a dönmesini sağlarız
        current_mode = st.session_state.app_mode if st.session_state.app_mode != "DETAIL" else "PORTAL"
        mode_select = st.radio("Mod:", ["TERMINAL", "PORTAL"], index=0 if current_mode=="TERMINAL" else 1, horizontal=True, label_visibility="collapsed")
        
        if mode_select != current_mode and st.session_state.app_mode != "DETAIL":
            st.session_state.app_mode = mode_select
            st.rerun()
        elif mode_select != "PORTAL" and st.session_state.app_mode == "DETAIL":
             st.session_state.app_mode = mode_select
             st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("⚙️ **AYARLAR**")
        curr_opt = st.selectbox("Para Birimi", ["USD", "TRY", "EUR"], label_visibility="collapsed")
        st.session_state.currency = curr_opt.lower()

# --- ANA İÇERİK ---
with col_main:
    
    # ==========================
    # MOD: TERMINAL (GRAFİKLİ ANALİZ)
    # ==========================
    if st.session_state.app_mode == "TERMINAL":
        # ... (Eski Terminal Kodunun Aynısı - Varsayılan ETH)
        coin = st.session_state.selected_coin.lower()
        curr = st.session_state.currency
        csym = "$" if curr=='usd' else "₺"
        
        # Veri çek
        u_data = get_coin_data(coin, curr)
        if not u_data:
            found = search_coin_id(coin)
            if found: 
                coin = found
                u_data = get_coin_data(coin, curr)
        
        btc_data = get_coin_data("bitcoin", curr)
        
        if u_data and u_data != "LIMIT" and btc_data:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"### {coin.upper()}")
                chg = u_data[f'{curr}_24h_change']
                clr = "#16c784" if chg>0 else "#ea3943"
                st.markdown(f"<h2 style='color:{clr}'>{csym}{u_data[curr]:,.2f} (%{chg:.2f})</h2>", unsafe_allow_html=True)
                st.plotly_chart(create_chart(get_chart_data(coin, curr, 1), chg, csym), use_container_width=True, config={'displayModeBar':False})
            with c2:
                st.markdown(f"### BITCOIN")
                bchg = btc_data[f'{curr}_24h_change']
                bclr = "#16c784" if bchg>0 else "#ea3943"
                st.markdown(f"<h2 style='color:{bclr}'>{csym}{btc_data[curr]:,.2f} (%{bchg:.2f})</h2>", unsafe_allow_html=True)
                st.plotly_chart(create_chart(get_chart_data("bitcoin", curr, 1), bchg, csym), use_container_width=True, config={'displayModeBar':False})
        else:
            st.info("Veri bekleniyor...")

    # ==========================
    # MOD: PORTAL (CMC LISTE)
    # ==========================
    elif st.session_state.app_mode == "PORTAL":
        st.markdown(f"<h3 style='color:{st.session_state.theme_color}'>🏆 PİYASA (TOP 10)</h3>", unsafe_allow_html=True)
        
        # BAŞLIKLAR (Manuel grid ile)
        h1, h2, h3, h4, h5, h6 = st.columns([0.5, 2, 1.5, 1, 1, 1])
        h1.markdown("**#**")
        h2.markdown("**Coin**")
        h3.markdown("**Fiyat**")
        h4.markdown("**1s**")
        h5.markdown("**24s**")
        h6.markdown("**7g**")
        st.markdown("---")

        top10 = get_top10_coins(st.session_state.currency)
        curr_sym = "$" if st.session_state.currency == 'usd' else "₺"

        if top10:
            for i, c in enumerate(top10[:10]):
                # Verileri hazırla
                p = c['current_price']
                p_fmt = f"{curr_sym}{p:,.2f}" if p > 1 else f"{curr_sym}{p:.6f}"
                p1 = c.get('price_change_percentage_1h_in_currency') or 0
                p24 = c.get('price_change_percentage_24h_in_currency') or 0
                p7 = c.get('price_change_percentage_7d_in_currency') or 0
                
                # Renkler (CSS class yerine inline style daha kolay st.markdown için)
                c1 = "color:#16c784" if p1>=0 else "color:#ea3943"
                c24 = "color:#16c784" if p24>=0 else "color:#ea3943"
                c7 = "color:#16c784" if p7>=0 else "color:#ea3943"

                # SATIR YAPISI (Streamlit Kolonları ile İnteraktif)
                # Sütun oranları başlıklarla aynı olmalı
                c_rank, c_name, c_price, c_1h, c_24h, c_7d = st.columns([0.5, 2, 1.5, 1, 1, 1])
                
                c_rank.markdown(f"<span style='color:gray'>{i+1}</span>", unsafe_allow_html=True)
                
                # İsim ve Logo (Tek satırda)
                c_name.markdown(f"""
                <div style="display:flex; align-items:center;">
                    <img src="{c['image']}" width="20" style="margin-right:5px; border-radius:50%;">
                    <span style="font-weight:bold;">{c['symbol'].upper()}</span>
                </div>
                """, unsafe_allow_html=True)
                
                c_price.markdown(f"<span style='font-family:monospace'>{p_fmt}</span>", unsafe_allow_html=True)
                c_1h.markdown(f"<span style='{c1}; font-size:13px'>%{p1:.1f}</span>", unsafe_allow_html=True)
                c_24h.markdown(f"<span style='{c24}; font-size:13px'>%{p24:.1f}</span>", unsafe_allow_html=True)
                
                # Son sütuna BUTON koyuyoruz (Detay için)
                if c_7d.button("İncele", key=f"det_{c['id']}"):
                    go_to_detail(c['id'])
                    st.rerun()
                
                st.markdown("<div style='margin-bottom:5px; border-bottom: 1px solid #333;'></div>", unsafe_allow_html=True)
        else:
            st.info("Veri yükleniyor...")

        # HABERLER
        st.markdown("<br>", unsafe_allow_html=True)
        c_news, c_soc = st.columns(2)
        with c_news:
            st.subheader("📰 Gündem")
            news = get_news("crypto market")
            with st.container(height=300):
                for n in news: st.markdown(f"- [{n['title']}]({n['link']})")
        with c_soc:
            st.subheader("💬 Sohbet")
            txt = st.text_input("Mesaj:", placeholder="Yaz...")
            if st.button("Gönder") and txt:
                st.session_state.posts.insert(0, {"user":"Misafir", "msg":txt, "time":"Now"})
                st.rerun()
            with st.container(height=220):
                for p in st.session_state.posts: st.text(f"@{p['user']}: {p['msg']}")

    # ==========================
    # MOD: DETAIL (YENİ ÖZEL SAYFA)
    # ==========================
    elif st.session_state.app_mode == "DETAIL":
        d_id = st.session_state.detail_id
        curr = st.session_state.currency
        csym = "$" if curr=='usd' else "₺"
        
        # Veriyi çek (API'den taze taze)
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{d_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false"
            detail_data = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
            
            # ÜST BİLGİ: LOGO + İSİM + FİYAT
            col_head, col_price = st.columns([2, 1])
            with col_head:
                st.markdown(f"""
                <div style="display:flex; align-items:center;">
                    <img src="{detail_data['image']['large']}" width="60" style="margin-right:15px;">
                    <div>
                        <h1 style="margin:0; font-size:36px;">{detail_data['name']} ({detail_data['symbol'].upper()})</h1>
                        <span style="color:gray; background-color:#333; padding:2px 6px; border-radius:4px;">Rank #{detail_data['market_cap_rank']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_price:
                p = detail_data['market_data']['current_price'][curr]
                pc = detail_data['market_data']['price_change_percentage_24h']
                pclr = "#16c784" if pc >= 0 else "#ea3943"
                st.markdown(f"""
                <div style="text-align:right;">
                    <div style="font-size:32px; font-weight:bold; color:{st.session_state.theme_color}">{csym}{p:,.2f}</div>
                    <div style="font-size:18px; color:{pclr}; font-weight:bold;">%{pc:.2f} (24s)</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # GRAFİK
            df = get_chart_data(d_id, curr, 7) # 7 Günlük detaylı grafik
            st.plotly_chart(create_chart(df, pc, csym, 400), use_container_width=True)
            
            # İSTATİSTİK GRID
            st.markdown("### 📊 PİYASA İSTATİSTİKLERİ")
            s1, s2, s3, s4 = st.columns(4)
            
            md = detail_data['market_data']
            
            with s1:
                st.markdown(f"<div class='stat-box'><div class='stat-label'>Market Değeri</div><div class='stat-val'>{csym}{md['market_cap'][curr]:,.0f}</div></div>", unsafe_allow_html=True)
            with s2:
                st.markdown(f"<div class='stat-box'><div class='stat-label'>24s Hacim</div><div class='stat-val'>{csym}{md['total_volume'][curr]:,.0f}</div></div>", unsafe_allow_html=True)
            with s3:
                st.markdown(f"<div class='stat-box'><div class='stat-label'>Dolaşan Arz</div><div class='stat-val'>{md['circulating_supply']:,.0f}</div></div>", unsafe_allow_html=True)
            with s4:
                st.markdown(f"<div class='stat-box'><div class='stat-label'>Tüm Zamanlar En Yüksek</div><div class='stat-val'>{csym}{md['ath'][curr]:,.2f}</div></div>", unsafe_allow_html=True)
                
            # HAKKINDA (İNGİLİZCE GELİR API'DEN, TR İÇİN ÇEVİRİ YOK AMA GÖSTERELİM)
            st.markdown("---")
            st.markdown("### ℹ️ HAKKINDA")
            desc = detail_data['description']['en'][:500] + "..." if detail_data['description']['en'] else "Açıklama bulunamadı."
            st.info(desc)

        except:
            st.error("Detay verisi çekilemedi veya API limiti.")
            if st.button("Tekrar Dene"): st.rerun()

if col_right:
    with col_right:
        st.caption("Ekstra")
        st.info("NEXUS v12.0 Pro")
