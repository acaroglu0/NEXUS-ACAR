import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import plotly.graph_objects as go

# --- 1. AYARLAR ---
st.set_page_config(layout="wide", page_title="NEXUS AI", page_icon="🦁", initial_sidebar_state="collapsed")

# Session State
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

# --- 2. CSS (ÖLÜ ALANLARI YOK ETME VE YAYILMA) ---
st.markdown(f"""
<style>
    /* Native Sidebar'ı Gizle */
    [data-testid="stSidebar"] {{display: none;}}
    
    /* EN ÖNEMLİ KISIM: EKRANIN KENARLARINA YAPIŞTIRMA */
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 5rem;
        padding-left: 1rem;  /* Sol boşluğu azalttık */
        padding-right: 1rem; /* Sağ boşluğu azalttık */
        max-width: 100%;     /* Ekranın %100'ünü kullan */
    }}
    
    /* Panel Kutuları */
    .nexus-panel {{
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #333;
        margin-bottom: 15px;
    }}
    
    /* Butonlar */
    div.stButton > button {{
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s;
    }}
    
    /* Analiz Butonu */
    div.stButton > button[kind="primary"] {{
        background-color: {st.session_state.theme_color};
        color: black;
        border: none;
        margin-top: 5px;
        margin-bottom: 15px;
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
        return [{"title": i.find("title").text, "link": i.find("link").text} for i in root.findall(".//item")[:5]]
    except: return []

def create_price_chart(df, theme_color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['time'], y=df['price'], mode='lines', line=dict(color=theme_color, width=2),
        fill='tozeroy', fillcolor=f"rgba{tuple(int(theme_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (0.1,)}"
    ))
    fig.update_layout(
        height=600, margin=dict(l=0, r=0, t=30, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, visible=True, showticklabels=True, color='grey'),
        yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.1)', autorange=True, side='right'),
        font={'color': "white"}
    )
    return fig

# --- EKRAN DÜZENİ ---
# BURASI ÖNEMLİ: [1, 3, 1] yaparak panellere biraz hacim verdik ama CSS ile kenarlara ittik.
col_left, col_mid, col_right = st.columns([1, 3, 1])

# --- 1. SOL PANEL ---
with col_left:
    with st.container(border=True):
        st.markdown(f"<h1 style='color: {st.session_state.theme_color}; text-align: center; margin:0; font-size: 28px;'>🦁 NEXUS</h1>", unsafe_allow_html=True)
        st.markdown("---")
        
        st.caption("🔍 **KRİPTO ARAMA**")
        coin_input = st.text_input("Coin Ara:", "bitcoin", label_visibility="collapsed")
        
        st.markdown("<br>", unsafe_allow_html=True)

        st.caption("🧠 **ANALİZ TÜRÜ**")
        analysis_type = st.selectbox("Seçiniz:", 
                                   ["Genel Bakış", "Fiyat Tahmini 🎯", "Risk Analizi ⚠️"],
                                   label_visibility="collapsed")
        
        # BUTON (HEMEN ALTINDA)
        analyze_btn = st.button("ANALİZİ BAŞLAT 🚀", type="primary")
        
        st.markdown("---")

        st.caption("🌐 **PORTAL / MOD**")
        mode_select = st.radio("Mod:", ["TERMINAL", "PORTAL"], horizontal=True, label_visibility="collapsed")
        st.session_state.app_mode = mode_select
        
        st.markdown("---")
        
        if st.session_state.app_mode == "TERMINAL":
            st.caption("⏳ **GRAFİK SÜRESİ**")
            day_opt = st.radio("Süre:", ["24 Saat", "7 Gün"], horizontal=True, label_visibility="collapsed")
            days_api = "1" if day_opt == "24 Saat" else "7"
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # DİL SEÇENEĞİ (EN ALTTA)
            st.caption("🌍 **DİL / LANGUAGE**")
            lng = st.radio("Dil:", ["TR", "EN"], horizontal=True, label_visibility="collapsed")
            st.session_state.language = lng

# --- 2. ORTA EKRAN ---
with col_mid:
    if st.session_state.app_mode == "TERMINAL":
        coin_id = coin_input.lower().strip()
        data = get_coin_data(coin_id, st.session_state.currency)
        
        if data:
            curr_sym = "₺" if st.session_state.currency == 'try' else "$" if st.session_state.currency == 'usd' else "€"
            
            h1, h2 = st.columns([2, 1])
            h1.markdown(f"<h1 style='font-size: 56px; margin:0;'>{coin_id.upper()}</h1>", unsafe_allow_html=True)
            h2.markdown(f"<h1 style='text-align:right; color: {st.session_state.theme_color}; margin:0; font-size: 56px;'>{curr_sym}{data[st.session_state.currency]:,.2f}</h1>", unsafe_allow_html=True)
            
            chart_df = get_chart_data(coin_id, st.session_state.currency, days_api)
            if not chart_df.empty:
                st.plotly_chart(create_price_chart(chart_df, st.session_state.theme_color), use_container_width=True, config={'displayModeBar': False})
            
            if analyze_btn:
                st.markdown("---")
                st.subheader(f"🤖 NEXUS AI: {analysis_type}")
                
                with st.spinner("Yapay zeka verileri işliyor..."):
                    model = get_model()
                    
                    base_prompt = f"Coin: {coin_id}. Fiyat: {data[st.session_state.currency]}. Durum: Son {day_opt} grafiği."
                    lang_prompt = "Türkçe ve profesyonel bir dille yanıtla." if st.session_state.language == 'TR' else "Answer in professional English."
                    
                    if "Risk" in analysis_type:
                        specific_prompt = "Bu coinin risk seviyesini 0-100 arası puanla. Destek ve direnç noktalarını belirt. Volatilite durumunu analiz et. Yatırımcı neye dikkat etmeli?"
                    elif "Fiyat" in analysis_type:
                        specific_prompt = "Kısa vadeli (haftalık) ve orta vadeli fiyat tahmin senaryoları oluştur. Boğa (yükseliş) ve Ayı (düşüş) durumunda hedefler ne olabilir? Maddeler halinde yaz."
                    else: 
                        specific_prompt = "Coine genel bir bakış at. Piyasadaki son durumu, temel analizi ve teknik göstergeleri özetle."
                    
                    full_prompt = f"{base_prompt} {lang_prompt} {specific_prompt}"
                    
                    try:
                        res = model.generate_content(full_prompt)
                        st.info(res.text)
                    except:
                        st.error("Yapay zeka servisi şu an yanıt veremiyor.")
        else:
            st.warning("Veri bekleniyor... (Doğru coin ismini girdiğinizden emin olun)")
            
    else:
        st.title("🌍 NEXUS PORTAL")
        st.info("Burası yakında küresel piyasa verileriyle dolacak.")

# --- 3. SAĞ PANEL ---
with col_right:
    with st.container(border=True):
        st.markdown("#### ⚙️ Ayarlar")
        
        st.caption("Para Birimi")
        curr = st.selectbox("Para Birimi", ["TRY", "USD", "EUR"], label_visibility="collapsed")
        st.session_state.currency = curr.lower()
        
        st.caption("Tema Rengi")
        thm = st.selectbox("Tema", list(THEMES.keys()), label_visibility="collapsed")
        st.session_state.theme_color = THEMES[thm]
        
        st.markdown("---")
        
        target = coin_input.lower().strip() if 'coin_input' in locals() else 'bitcoin'
        st.markdown(f"#### 📰 {target.upper()} Haber")
        
        news = get_news(target)
        if news:
            for n in news:
                st.markdown(f"""
                <div style='background-color: #262730; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 13px;'>
                    <a href='{n['link']}' style='color: white; text-decoration: none;'>
                        {n['title']}
                    </a>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("Güncel haber bulunamadı.")
