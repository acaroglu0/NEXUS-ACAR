import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import plotly.graph_objects as go

# --- 1. AYARLAR ---
st.set_page_config(layout="wide", page_title="NEXUS AI", page_icon="🦁", initial_sidebar_state="collapsed")

if 'theme_color' not in st.session_state: st.session_state.theme_color = '#F7931A'
if 'currency' not in st.session_state: st.session_state.currency = 'try'
if 'language' not in st.session_state: st.session_state.language = 'TR'
if 'app_mode' not in st.session_state: st.session_state.app_mode = 'TERMINAL'

THEMES = {
    "Neon Mavi 🔵": "#00d2ff",
    "Bitcoin Turuncusu 🟠": "#F7931A",
    "Matrix Yeşili 🟢": "#00FF41",
    "Siber Mor 🟣": "#BC13FE",
    "Alarm Kırmızısı 🔴": "#FF0033"
}

# --- 2. CSS (KOKPİT DÜZENİ) ---
st.markdown(f"""
<style>
    [data-testid="stSidebar"] {{display: none;}}
    
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }}
    
    .nexus-panel {{
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #333;
        margin-bottom: 10px;
    }}

    /* KUTU İÇERİKLERİNİ ORTALAMA VE YÜKSEKLİK AYARI */
    .box-content {{
        height: 180px; /* AI Kutusunun ortalama yüksekliğine eşitledik */
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
    }}
    
    /* REKLAM ALANI STİLİ */
    .ad-placeholder {{
        width: 100%;
        height: 100%;
        border: 2px dashed #333;
        border-radius: 8px;
        color: #555;
        display: flex;
        justify-content: center;
        align-items: center;
        font-weight: bold;
        letter-spacing: 1px;
    }}
    
    div.stButton > button {{
        width: 100%;
        border-radius: 8px;
        font-weight: 900 !important;
        font-size: 16px;
        transition: all 0.3s;
        text-transform: uppercase;
    }}
    
    div.stButton > button[kind="primary"] {{
        background-color: {st.session_state.theme_color};
        color: black;
        border: none;
        margin-top: 5px;
        margin-bottom: 15px;
    }}
</style>
""", unsafe_allow_html=True)

# --- API AYARLARI ---
try:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if api_key:
        genai.configure(api_key=api_key)
except: pass

@st.cache_resource
def get_model():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name:
                    return genai.GenerativeModel(m.name)
    except: pass
    return genai.GenerativeModel("gemini-pro")

@st.cache_data(ttl=60)
def get_coin_data(coin_id, currency):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={currency}&include_24hr_change=true&include_market_cap=true"
        return requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()[coin_id]
    except: return None

@st.cache_data(ttl=300)
def get_chart_data(coin_id, currency, days):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency={currency}&days={days}"
        data = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
        df_price = pd.DataFrame(data['prices'], columns=['time', 'price'])
        df_price['time'] = pd.to_datetime(df_price['time'], unit='ms')
        return df_price
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def get_news(coin_name):
    try:
        import xml.etree.ElementTree as ET
        rss_url = f"https://news.google.com/rss/search?q={coin_name}+crypto&hl=tr&gl=TR&ceid=TR:tr"
        r = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(r.content)
        return [{"title": i.find("title").text, "link": i.find("link").text} for i in root.findall(".//item")[:5]]
    except: return []

# --- GRAFİK MOTORU ---
def create_mountain_chart(df_price, price_change):
    if price_change < 0:
        main_color = '#ea3943' 
        fill_color = 'rgba(234, 57, 67, 0.2)' 
    else:
        main_color = '#16c784' 
        fill_color = 'rgba(22, 199, 132, 0.2)' 

    min_price = df_price['price'].min()
    max_price = df_price['price'].max()
    padding = (max_price - min_price) * 0.05 
    y_min = min_price - padding
    y_max = max_price + padding

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_price['time'], y=df_price['price'],
        mode='lines', name='Fiyat',
        line=dict(color=main_color, width=3), 
        fill='tozeroy', fillcolor=fill_color, 
        showlegend=False
    ))
    fig.update_layout(
        height=400, # İnce Uzun
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified', dragmode='pan',
        xaxis=dict(showgrid=False, color='gray', gridcolor='rgba(128,128,128,0.1)'),
        yaxis=dict(side='right', visible=True, showgrid=True, gridcolor='rgba(128,128,128,0.1)', color='white', range=[y_min, y_max], tickprefix=st.session_state.currency.upper() + " ")
    )
    return fig

# --- EKRAN DÜZENİ ---
col_left, col_mid, col_right = st.columns([1, 4, 1])

# SOL PANEL
with col_left:
    with st.container(border=True):
        st.markdown(f"<h1 style='color: {st.session_state.theme_color}; text-align: center; margin:0; font-size: 24px;'>🦁 NEXUS</h1>", unsafe_allow_html=True)
        st.markdown("---")
        st.caption("🔍 **KRİPTO ARAMA**")
        coin_input = st.text_input("Coin Ara:", "bitcoin", label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("🧠 **ANALİZ TÜRÜ**")
        analysis_type = st.selectbox("Seçiniz:", ["Genel Bakış", "Fiyat Tahmini 🎯", "Risk Analizi ⚠️"], label_visibility="collapsed")
        analyze_btn = st.button("ANALİZİ BAŞLAT", type="primary")
        st.markdown("---")
        st.caption("🌐 **PORTAL / MOD**")
        mode_select = st.radio("Mod:", ["TERMINAL", "PORTAL"], horizontal=True, label_visibility="collapsed")
        st.session_state.app_mode = mode_select
        st.markdown("---")
        if st.session_state.app_mode == "TERMINAL":
            st.caption("⏳ **SÜRE**")
            day_opt = st.radio("Süre:", ["24 Saat", "7 Gün"], horizontal=True, label_visibility="collapsed")
            days_api = "1" if day_opt == "24 Saat" else "7"
            st.markdown("<br>", unsafe_allow_html=True)
            st.caption("🌍 **DİL**")
            lng = st.radio("Dil:", ["TR", "EN"], horizontal=True, label_visibility="collapsed")
            st.session_state.language = lng

# ORTA EKRAN
with col_mid:
    if st.session_state.app_mode == "TERMINAL":
        coin_id = coin_input.lower().strip()
        data = get_coin_data(coin_id, st.session_state.currency)
        
        if data:
            curr_sym = "₺" if st.session_state.currency == 'try' else "$" if st.session_state.currency == 'usd' else "€"
            p_change = data.get('usd_24h_change', 0)
            m_cap = data.get(f'{st.session_state.currency}_market_cap', 0)
            trend_color = "#ea3943" if p_change < 0 else "#16c784"
            
            # ÜST: BAŞLIK VE FİYAT
            h1, h2 = st.columns([1, 1])
            with h1: st.markdown(f"<h1 style='font-size: 40px; margin:0;'>{coin_id.upper()}</h1>", unsafe_allow_html=True)
            with h2: st.markdown(f"<div style='text-align:right;'><h1 style='margin:0; font-size: 40px;'>{curr_sym}{data[st.session_state.currency]:,.2f}</h1><h3 style='color: {trend_color}; margin:0;'>%{p_change:.2f}</h3></div>", unsafe_allow_html=True)
            
            # ORTA: GRAFİK
            df_price = get_chart_data(coin_id, st.session_state.currency, days_api)
            if not df_price.empty:
                fig = create_mountain_chart(df_price, p_change)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})
            
            # --- ALT KOKPİT (3 EŞİT KUTUCUK) ---
            # Hepsi st.container(border=True) kullanıyor = AYNI GÖRÜNÜM
            c_bot1, c_bot2, c_bot3 = st.columns(3)
            
            # 1. KUTU: AI CHAT
            with c_bot1:
                with st.container(border=True):
                    # İçeriği ortalamak için CSS sınıfı kullanıyoruz
                    st.caption(f"🤖 **NEXUS ASİSTAN**")
                    user_q = st.text_input("Soru sor:", key="chat", placeholder="Direnç neresi?", label_visibility="collapsed")
                    if st.button("SOR", key="ask_btn"):
                        if not st.secrets.get("GEMINI_API_KEY"): st.error("API Key Yok")
                        else:
                            with st.spinner("."):
                                try:
                                    m = get_model()
                                    r = m.generate_content(f"Coin: {coin_id}. Soru: {user_q}. Çok kısa cevapla.")
                                    st.info(r.text)
                                except: pass

            # 2. KUTU: REKLAM ALANI
            with c_bot2:
                with st.container(border=True):
                    # Yüksekliği eşitlemek için box-content div'i
                    st.markdown("""
                    <div class="box-content">
                        <div class="ad-placeholder">REKLAM ALANI</div>
                    </div>
                    """, unsafe_allow_html=True)

            # 3. KUTU: MARKET CAP
            with c_bot3:
                with st.container(border=True):
                    # Market Cap Formatı
                    if m_cap > 1_000_000_000_000: cap_fmt = f"{m_cap/1_000_000_000_000:.2f} T"
                    elif m_cap > 1_000_000_000: cap_fmt = f"{m_cap/1_000_000_000:.2f} B"
                    else: cap_fmt = f"{m_cap:,.0f}"
                    
                    st.markdown(f"""
                    <div class="box-content">
                        <h3 style="color: gray; margin: 0; font-size: 14px;">MARKET CAP</h3>
                        <h1 style="color: white; margin: 10px 0; font-size: 32px;">{curr_sym}{cap_fmt}</h1>
                        <p style="color: {st.session_state.theme_color}; margin:0; font-size: 11px;">Toplam Değer</p>
                    </div>
                    """, unsafe_allow_html=True)

            # ANA ANALİZ ÇIKTISI
            if analyze_btn:
                st.markdown("---")
                st.subheader(f"🤖 NEXUS AI: {analysis_type}")
                if not st.secrets.get("GEMINI_API_KEY"):
                    st.error("⚠️ API Anahtarı Eksik!")
                else:
                    with st.spinner("Analiz ediliyor..."):
                        try:
                            model = get_model()
                            base_prompt = f"Coin: {coin_id}. Fiyat: {data[st.session_state.currency]}. Market Cap: {m_cap}. Durum: Son {day_opt}."
                            lang_prompt = "Türkçe yanıtla." if st.session_state.language == 'TR' else "Answer in English."
                            full_prompt = f"{base_prompt} {lang_prompt} {analysis_type} yap."
                            res = model.generate_content(full_prompt)
                            st.info(res.text)
                        except Exception as e:
                            st.error(f"Hata: {str(e)}")
        else:
            st.warning("Veri bekleniyor...")
    else:
        st.title("🌍 NEXUS PORTAL")
        st.info("Yükleniyor...")

# SAĞ PANEL
with col_right:
    with st.container(border=True):
        st.markdown("#### ⚙️ Ayarlar")
        curr = st.selectbox("Para Birimi", ["TRY", "USD", "EUR"], label_visibility="collapsed")
        st.session_state.currency = curr.lower()
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Tema Rengi")
        thm = st.selectbox("Tema", list(THEMES.keys()), label_visibility="collapsed")
        st.session_state.theme_color = THEMES[thm]
        st.markdown("---")
        target = coin_id if 'coin_id' in locals() else 'bitcoin'
        st.markdown(f"#### 📰 Haberler")
        news = get_news(target)
        if news:
            for n in news:
                st.markdown(f"<div style='background-color: #262730; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 13px;'><a href='{n['link']}' style='color: white; text-decoration: none;'>{n['title']}</a></div>", unsafe_allow_html=True)
