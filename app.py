import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import plotly.graph_objects as go

# --- 1. AYARLAR ---
st.set_page_config(layout="wide", page_title="NEXUS AI", page_icon="🦁")

# Session State
if 'page' not in st.session_state: st.session_state.page = 'Terminal'
if 'theme_color' not in st.session_state: st.session_state.theme_color = '#F7931A' # Default Bitcoin Turuncusu
if 'currency' not in st.session_state: st.session_state.currency = 'try'
if 'language' not in st.session_state: st.session_state.language = 'TR'
if 'show_right_panel' not in st.session_state: st.session_state.show_right_panel = True

THEMES = {
    "Neon Mavi 🔵": "#00d2ff",
    "Bitcoin Turuncusu 🟠": "#F7931A",
    "Matrix Yeşili 🟢": "#00FF41",
    "Siber Mor 🟣": "#BC13FE",
    "Alarm Kırmızısı 🔴": "#FF0033"
}

# --- 2. CSS İLE İKİZ GÖRÜNÜM (SOL VE SAĞI EŞİTLEME) ---
st.markdown(f"""
<style>
    /* 1. Sol Menü Rengi (Koyu Gri) */
    [data-testid="stSidebar"] {{
        background-color: #262730;
        border-right: 1px solid #444;
    }}
    
    /* 2. Sağ Panel İçin Özel Stil (Solun Aynısı Olsun Diye) */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: #262730; /* Sol menü ile aynı renk */
        border: 1px solid #444;
        border-radius: 5px;
        padding: 1rem;
    }}

    /* 3. Metin Renklerini Eşitle */
    h1, h2, h3, p, span {{
        color: white !important;
    }}
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

@st.cache_data(ttl=600)
def get_top_coins(currency):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency={currency}&order=market_cap_desc&per_page=10&page=1&sparkline=false"
        return requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
    except: return []

# --- GRAFİK ---
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

# --- SOL MENÜ (NATIVE SIDEBAR) ---
with st.sidebar:
    st.markdown(f"<h2 style='color: {st.session_state.theme_color}; text-align: center;'>🦁 NEXUS</h2>", unsafe_allow_html=True)
    
    # Butonlar
    c1, c2 = st.columns(2)
    if c1.button("📡 TERMINAL", use_container_width=True): st.session_state.page = 'Terminal'
    if c2.button("🌐 PORTAL", use_container_width=True): st.session_state.page = 'Portal'
    st.markdown("---")
    
    # İçerik
    if st.session_state.page == 'Terminal':
        st.caption("ANALİZ KOKPİTİ")
        coin_input_sb = st.text_input("Kripto Ara:", "bitcoin")
        days_select = st.selectbox("Zaman Aralığı:", ["1", "7", "30", "90"], index=1)
        analyze_btn = st.button("ANALİZİ BAŞLAT 🚀", type="primary", use_container_width=True)
    else:
        coin_input_sb = "bitcoin"
        days_select = "7"
        analyze_btn = False

# --- EKRAN DÜZENİ (SİMETRİ) ---
def toggle_panel(): st.session_state.show_right_panel = not st.session_state.show_right_panel

# ORAN AYARI: Sol menü genelde %20'dir. Biz de sağa %20 verelim.
# [4, 1] oranı genelde sidebar genişliğine çok yakındır.
if st.session_state.show_right_panel:
    col_main, col_right = st.columns([4, 1]) 
else:
    col_main = st.container()
    col_right = None

# --- ORTA (GRAFİK) ---
with col_main:
    # Toggle Butonu (Sağ üst)
    h_c1, h_c2 = st.columns([20, 1])
    h_c2.button("◫", on_click=toggle_panel, help="Paneli Aç/Kapat")

    if st.session_state.page == 'Terminal':
        # COIN MANTIĞI
        coin_id = st.session_state.get('selected_coin', coin_input_sb.lower().strip())
        
        data = get_coin_data(coin_id, st.session_state.currency)
        if data:
            curr_sym = "₺" if st.session_state.currency == 'try' else "$" if st.session_state.currency == 'usd' else "€"
            
            # Başlık
            h_c1.markdown(f"<h1 style='color: {st.session_state.theme_color}; margin:0;'>{coin_id.upper()}</h1>", unsafe_allow_html=True)
            h_c1.markdown(f"<h2 style='margin:0;'>{curr_sym}{data[st.session_state.currency]:,.2f}</h2>", unsafe_allow_html=True)

            # Grafik
            chart_df = get_chart_data(coin_id, st.session_state.currency, days_select)
            if not chart_df.empty:
                st.plotly_chart(create_price_chart(chart_df, st.session_state.theme_color), use_container_width=True, config={'displayModeBar': False})
            
            # Analiz
            if analyze_btn:
                with st.spinner("NEXUS Analiz Ediyor..."):
                    model = get_model()
                    prompt = f"Coin: {coin_id}. Fiyat: {data[st.session_state.currency]}. Yorumla."
                    try:
                        res = model.generate_content(prompt)
                        st.info(res.text)
                    except: st.error("Analiz servisi meşgul.")
        else:
            st.warning("Veri bekleniyor...")

    elif st.session_state.page == 'Portal':
        st.title("Küresel Piyasa")
        top10 = get_top_coins(st.session_state.currency)
        if top10:
            df = pd.DataFrame(top10)[['market_cap_rank', 'name', 'current_price', 'price_change_percentage_24h']]
            st.dataframe(df, use_container_width=True)

# --- SAĞ PANEL (SOLUN İKİZİ) ---
if st.session_state.show_right_panel and col_right:
    with col_right:
        # border=True kullanarak ve CSS ile rengini değiştirerek sol menünün aynısını yapıyoruz
        with st.container(border=True):
            
            # 1. FAVORİLER
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

            # 2. AYARLAR
            st.markdown("#### ⚙️ Ayarlar")
            
            st.caption("Para Birimi")
            curr = st.selectbox("Para Birimi", ["TRY", "USD", "EUR"], label_visibility="collapsed")
            st.session_state.currency = curr.lower()
            
            st.caption("Tema Rengi")
            thm = st.selectbox("Tema", list(THEMES.keys()), label_visibility="collapsed")
            st.session_state.theme_color = THEMES[thm]
            
            st.caption("Dil")
            lng = st.radio("Dil", ["TR", "EN"], horizontal=True, label_visibility="collapsed")
            st.session_state.language = lng

            st.markdown("---")

            # 3. HABERLER
            target = st.session_state.get('selected_coin', 'bitcoin')
            st.markdown(f"#### 📰 {target.upper()} Haber")
            news = get_news(target)
            if news:
                for n in news:
                    st.markdown(f"• [{n['title']}]({n['link']})")
