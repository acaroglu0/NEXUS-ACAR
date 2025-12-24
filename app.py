import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

# --- 2. CSS (DÜZEN VE BUG DÜZELTMELERİ) ---
st.markdown(f"""
<style>
    [data-testid="stSidebar"] {{display: none;}}
    
    /* EKRANI TAM KAPLA VE BOŞLUKLARI SİL */
    .block-container {{
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }}
    
    /* PANELLER */
    .nexus-panel {{
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #333;
        margin-bottom: 10px;
    }}
    
    /* BUTONLAR */
    div.stButton > button {{
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s;
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
        df_price = pd.DataFrame(data['prices'], columns=['time', 'price'])
        df_price['time'] = pd.to_datetime(df_price['time'], unit='ms')
        df_vol = pd.DataFrame(data['total_volumes'], columns=['time', 'volume'])
        df_vol['time'] = pd.to_datetime(df_vol['time'], unit='ms')
        return df_price, df_vol
    except: return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=600)
def get_news(coin_name):
    try:
        import xml.etree.ElementTree as ET
        rss_url = f"https://news.google.com/rss/search?q={coin_name}+crypto&hl=tr&gl=TR&ceid=TR:tr"
        r = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(r.content)
        return [{"title": i.find("title").text, "link": i.find("link").text} for i in root.findall(".//item")[:5]]
    except: return []

# --- 3. PRO GRAFİK MOTORU (CMC STİLİ - DÜZELTİLMİŞ) ---
def create_professional_chart(df_price, df_vol, price_change):
    # Renk Belirleme (CMC Standartları)
    # Düşüşteyse Kırmızı (#ea3943), Yükselişteyse Yeşil (#16c784)
    if price_change < 0:
        main_color = '#ea3943' # Kırmızı
        fill_color = 'rgba(234, 57, 67, 0.2)' # Şeffaf Kırmızı
    else:
        main_color = '#16c784' # Yeşil
        fill_color = 'rgba(22, 199, 132, 0.2)' # Şeffaf Yeşil

    # İki eksenli grafik oluştur (Fiyat ve Hacim)
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. HACİM (Volume) - En Altta Silik
    fig.add_trace(go.Bar(
        x=df_vol['time'], 
        y=df_vol['volume'],
        marker_color=main_color,
        opacity=0.3, # Çok silik olsun ki fiyatı kapatmasın
        name='Hacim',
        showlegend=False
    ), secondary_y=True)

    # 2. FİYAT (Price) - Üstte Parlak
    fig.add_trace(go.Scatter(
        x=df_price['time'], 
        y=df_price['price'],
        mode='lines',
        name='Fiyat',
        line=dict(color=main_color, width=2),
        fill='tozeroy', # Altını doldur
        fillcolor=fill_color,
        showlegend=False
    ), secondary_y=False)

    # 3. GRAFİK AYARLARI
    
    # Hacim barlarını aşağı bastırmak için Hacim Ekseninin (Y2) aralığını genişletiyoruz.
    # Böylece barlar sadece grafiğin alt %20'sine sıkışıyor.
    max_vol = df_vol['volume'].max()
    fig.update_yaxes(range=[0, max_vol * 5], visible=False, secondary_y=True) # Hacim ekseni gizli

    # Fiyat Ekseni (Sağda)
    fig.update_yaxes(
        side='right', 
        visible=True, 
        showgrid=True, 
        gridcolor='rgba(128,128,128,0.1)', 
        color='white',
        tickprefix=st.session_state.currency.upper() + " ", # Para birimi sembolü
        secondary_y=False
    )

    # X Ekseni (Zaman)
    fig.update_xaxes(
        showgrid=False, 
        color='gray',
        gridcolor='rgba(128,128,128,0.1)'
    )

    # Genel Düzen
    fig.update_layout(
        height=600,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified', # İmleç takibi
        dragmode='pan' # Kaydırma modu
    )

    return fig

# --- EKRAN DÜZENİ ---
col_left, col_mid, col_right = st.columns([1, 4, 1])

# --- SOL PANEL ---
with col_left:
    with st.container(border=True):
        st.markdown(f"<h1 style='color: {st.session_state.theme_color}; text-align: center; margin:0; font-size: 24px;'>🦁 NEXUS</h1>", unsafe_allow_html=True)
        st.markdown("---")
        
        st.caption("🔍 **KRİPTO ARAMA**")
        coin_input = st.text_input("Coin Ara:", "bitcoin", label_visibility="collapsed")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("🧠 **ANALİZ TÜRÜ**")
        analysis_type = st.selectbox("Seçiniz:", ["Genel Bakış", "Fiyat Tahmini 🎯", "Risk Analizi ⚠️"], label_visibility="collapsed")
        
        analyze_btn = st.button("ANALİZİ BAŞLAT 🚀", type="primary")
        
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

# --- ORTA EKRAN ---
with col_mid:
    if st.session_state.app_mode == "TERMINAL":
        coin_id = coin_input.lower().strip()
        data = get_coin_data(coin_id, st.session_state.currency)
        
        if data:
            curr_sym = "₺" if st.session_state.currency == 'try' else "$" if st.session_state.currency == 'usd' else "€"
            
            # Fiyat Değişimine Göre Renk (Kırmızı veya Yeşil)
            p_change = data.get('usd_24h_change', 0)
            trend_color = "#ea3943" if p_change < 0 else "#16c784"
            
            # Başlık Bloğu
            h1, h2 = st.columns([1, 1])
            with h1:
                st.markdown(f"<h1 style='font-size: 40px; margin:0;'>{coin_id.upper()}</h1>", unsafe_allow_html=True)
            with h2:
                st.markdown(f"""
                <div style='text-align:right;'>
                    <h1 style='margin:0; font-size: 40px;'>{curr_sym}{data[st.session_state.currency]:,.2f}</h1>
                    <h3 style='color: {trend_color}; margin:0;'>%{p_change:.2f}</h3>
                </div>
                """, unsafe_allow_html=True)
            
            # GRAFİK ÇİZİMİ
            df_price, df_vol = get_chart_data(coin_id, st.session_state.currency, days_api)
            if not df_price.empty:
                # Fiyat değişimini parametre olarak gönderiyoruz ki renk ona göre olsun
                fig = create_professional_chart(df_price, df_vol, p_change)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})
            
            if analyze_btn:
                st.markdown("---")
                st.subheader(f"🤖 NEXUS AI: {analysis_type}")
                with st.spinner("Yapay zeka analiz ediyor..."):
                    model = get_model()
                    base_prompt = f"Coin: {coin_id}. Fiyat: {data[st.session_state.currency]}. Durum: Son {day_opt} grafiği."
                    lang_prompt = "Türkçe ve profesyonel bir dille yanıtla." if st.session_state.language == 'TR' else "Answer in professional English."
                    full_prompt = f"{base_prompt} {lang_prompt} {analysis_type} yap. (Önemli seviyeleri belirt)"
                    try:
                        res = model.generate_content(full_prompt)
                        st.info(res.text)
                    except: st.error("Servis meşgul.")
        else:
            st.warning("Veri bekleniyor... (Doğru coin ismini girdiğinizden emin olun)")
    else:
        st.title("🌍 NEXUS PORTAL")
        st.info("Küresel veriler yükleniyor...")

# --- SAĞ PANEL ---
with col_right:
    with st.container(border=True):
        st.markdown("#### ⚙️ Ayarlar")
        curr = st.selectbox("Para Birimi", ["TRY", "USD", "EUR"], label_visibility="collapsed")
        st.session_state.currency = curr.lower()
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 🎨 Tema")
        thm = st.selectbox("Tema", list(THEMES.keys()), label_visibility="collapsed")
        st.session_state.theme_color = THEMES[thm]
        
        st.markdown("---")
        target = coin_id if 'coin_id' in locals() else 'bitcoin'
        st.markdown(f"#### 📰 Haberler")
        news = get_news(target)
        if news:
            for n in news:
                st.markdown(f"<div style='background-color: #262730; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 13px;'><a href='{n['link']}' style='color: white; text-decoration: none;'>{n['title']}</a></div>", unsafe_allow_html=True)
