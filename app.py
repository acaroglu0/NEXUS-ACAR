import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import plotly.graph_objects as go

# --- 1. AYARLAR ---
# Native Sidebar'ı "collapsed" (kapalı) başlatıyoruz ki bizimkiler öne çıksın
st.set_page_config(layout="wide", page_title="NEXUS AI", page_icon="🦁", initial_sidebar_state="collapsed")

# Session State
if 'theme_color' not in st.session_state: st.session_state.theme_color = '#F7931A'
if 'currency' not in st.session_state: st.session_state.currency = 'try'
if 'language' not in st.session_state: st.session_state.language = 'TR'

THEMES = {
    "Neon Mavi 🔵": "#00d2ff",
    "Bitcoin Turuncusu 🟠": "#F7931A",
    "Matrix Yeşili 🟢": "#00FF41",
    "Siber Mor 🟣": "#BC13FE",
    "Alarm Kırmızısı 🔴": "#FF0033"
}

# --- 2. CSS İLE PANEL GÖRÜNÜMÜ ---
# Sol ve Sağ sütunların arka planını "Sidebar Grisi" (#262730) yapıyoruz
st.markdown("""
<style>
    /* Sol menü çubuğunu tamamen gizle */
    [data-testid="stSidebar"] {display: none;}
    
    /* Panel Kutuları (Sol ve Sağ için) */
    .nexus-panel {
        background-color: #262730;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #444;
        height: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- API ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("API Key Hatası!")
    st.stop()

@st.cache_resource
def get_model():
    try: return genai.GenerativeModel("gemini-1.5-flash")
    except: return genai.GenerativeModel("gemini-pro")

@st.cache_data(ttl=60)
def get_coin_data(coin_id, currency):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={currency}&include_24hr_change=true"
        return requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()[coin_id]
    except: return None

@st.cache_data(ttl=300)
def get_chart_data(coin_id, currency, days):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency={currency}&days={days}"
        data = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
        df = pd.DataFrame(data['prices'], columns=['time', 'price'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def get_news(coin_name):
    try:
        import xml.etree.ElementTree as ET
        rss_url = f"https://news.google.com/rss/search?q={coin_name}+crypto&hl=tr&gl=TR&ceid=TR:tr"
        r = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(r.content)
        return [{"title": i.find("title").text, "link": i.find("link").text} for i in root.findall(".//item")[:4]]
    except: return []

def create_price_chart(df, theme_color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['time'], y=df['price'], mode='lines', line=dict(color=theme_color, width=2),
        fill='tozeroy', fillcolor=f"rgba{tuple(int(theme_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (0.1,)}"
    ))
    fig.update_layout(
        height=500, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, visible=True, showticklabels=True, color='grey'),
        yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.1)', autorange=True, side='right'),
        font={'color': "white"}
    )
    return fig

# --- ANA EKRAN DÜZENİ (3 SÜTUNLU DASHBOARD) ---

# Sütun Oranları: [1 Sol] - [3.5 Orta] - [1 Sağ]
col_left, col_mid, col_right = st.columns([1, 3.5, 1])

# --- 1. SOL SÜTUN (KONTROL PANELİ) ---
with col_left:
    # Kendi Panelimizi Oluşturuyoruz
    with st.container(border=True): # border=True ile gri kutu içine alıyoruz
        st.markdown(f"<h2 style='color: {st.session_state.theme_color}; text-align: center;'>🦁 NEXUS</h2>", unsafe_allow_html=True)
        st.markdown("---")
        
        st.caption("ANALİZ KOKPİTİ")
        coin_input = st.text_input("Kripto Ara:", "bitcoin")
        days_select = st.selectbox("Zaman Aralığı:", ["1", "7", "30", "90"], index=1)
        analyze_btn = st.button("ANALİZİ BAŞLAT 🚀", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.info("💡 **İpucu:** Sol menü ile sağ menü artık simetriktir.")


# --- 2. ORTA SÜTUN (GRAFİK VE ANALİZ) ---
with col_mid:
    # Veri İşlemleri
    coin_id = st.session_state.get('selected_coin', coin_input.lower().strip())
    data = get_coin_data(coin_id, st.session_state.currency)
    
    if data:
        curr_sym = "₺" if st.session_state.currency == 'try' else "$" if st.session_state.currency == 'usd' else "€"
        
        # Başlıklar
        h_c1, h_c2 = st.columns([3, 1])
        h_c1.markdown(f"<h1 style='color: {st.session_state.theme_color}; margin:0;'>{coin_id.upper()}</h1>", unsafe_allow_html=True)
        h_c2.markdown(f"<h2 style='margin:0; text-align:right;'>{curr_sym}{data[st.session_state.currency]:,.2f}</h2>", unsafe_allow_html=True)

        # Grafik
        chart_df = get_chart_data(coin_id, st.session_state.currency, days_select)
        if not chart_df.empty:
            st.plotly_chart(create_price_chart(chart_df, st.session_state.theme_color), use_container_width=True, config={'displayModeBar': False})
        
        # Analiz Sonucu
        if analyze_btn:
            with st.spinner("NEXUS Hesaplıyor..."):
                model = get_model()
                prompt = f"Coin: {coin_id}. Fiyat: {data[st.session_state.currency]}. Yorumla."
                try:
                    res = model.generate_content(prompt)
                    st.info(res.text)
                except: st.error("Servis meşgul.")
    else:
        st.warning("Veri bekleniyor...")

# --- 3. SAĞ SÜTUN (SOLUN KOPYASI) ---
with col_right:
    # Aynı 'container(border=True)' kullanarak Sol ile BİREBİR aynı görünümü veriyoruz
    with st.container(border=True):
        st.markdown("#### ⭐ Favoriler")
        
        def set_coin(c): st.session_state.selected_coin = c
        
        c_f1, c_f2 = st.columns(2)
        if c_f1.button("BTC", use_container_width=True): set_coin("bitcoin")
        if c_f2.button("ETH", use_container_width=True): set_coin("ethereum")
        
        c_f3, c_f4 = st.columns(2)
        if c_f3.button("SOL", use_container_width=True): set_coin("solana")
        if c_f4.button("AVAX", use_container_width=True): set_coin("avalanche-2")
        
        if st.button("DOGE", use_container_width=True): set_coin("dogecoin")
        
        st.markdown("---")
        st.markdown("#### ⚙️ Ayarlar")
        
        curr = st.selectbox("Para Birimi", ["TRY", "USD", "EUR"], label_visibility="collapsed")
        st.session_state.currency = curr.lower()
        
        thm = st.selectbox("Tema", list(THEMES.keys()), label_visibility="collapsed")
        st.session_state.theme_color = THEMES[thm]
        
        lng = st.radio("Dil", ["TR", "EN"], horizontal=True, label_visibility="collapsed")
        st.session_state.language = lng
        
        st.markdown("---")
        target = st.session_state.get('selected_coin', 'bitcoin')
        st.markdown(f"#### 📰 Haberler")
        
        news = get_news(target)
        if news:
            for n in news:
                st.markdown(f"<div style='font-size:12px; margin-bottom:5px;'><a href='{n['link']}' style='color:grey; text-decoration:none;'>• {n['title']}</a></div>", unsafe_allow_html=True)
