import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import plotly.graph_objects as go

# --- 1. AYARLAR ---
st.set_page_config(layout="wide", page_title="NEXUS AI", page_icon="🦁", initial_sidebar_state="collapsed")

# DEFAULT AYARLAR
if 'theme_color' not in st.session_state: st.session_state.theme_color = '#F7931A'
if 'currency' not in st.session_state: st.session_state.currency = 'usd'
if 'language' not in st.session_state: st.session_state.language = 'TR'
if 'app_mode' not in st.session_state: st.session_state.app_mode = 'TERMINAL'

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
        font-size: 12px;
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

# --- AKILLI ARAMA & VERİ ÇEKME ---

@st.cache_data(ttl=86400) # Aramayı önbelleğe al
def search_coin_id(query):
    # Kullanıcı "sol" yazarsa bunu API'de arayıp "solana" id'sini döndüren fonksiyon
    try:
        url = f"https://api.coingecko.com/api/v3/search?query={query}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
        if r.get('coins'):
            # En alakalı ilk sonucu al
            return r['coins'][0]['id']
    except: return None
    return None

@st.cache_data(ttl=60)
def get_coin_data(coin_id, currency):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={currency}&include_24hr_change=true"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
        if coin_id in r:
            return r[coin_id]
    except: return None
    return None

@st.cache_data(ttl=300)
def get_global_data():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        return requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()['data']
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

# --- GRAFİK ---
def create_mini_chart(df, price_change, currency_symbol, height=350):
    if price_change < 0:
        main_color = '#ea3943' 
        fill_color = 'rgba(234, 57, 67, 0.2)' 
    else:
        main_color = '#16c784' 
        fill_color = 'rgba(22, 199, 132, 0.2)' 

    min_p = df['price'].min()
    max_p = df['price'].max()
    padding = (max_p - min_p) * 0.05
    
    fig = go.Figure()
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

# --- EKRAN DÜZENİ ---
col_left, col_mid, col_right = st.columns([1, 4, 1])

# SOL PANEL
with col_left:
    with st.container(border=True):
        st.markdown(f"<h1 style='color: {st.session_state.theme_color}; text-align: center; margin:0; font-size: 24px;'>🦁 NEXUS</h1>", unsafe_allow_html=True)
        st.markdown("---")
        
        st.caption("🔍 **KRİPTO SEÇ**")
        coin_input = st.text_input("Coin Ara:", "ethereum", label_visibility="collapsed")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("🧠 **ANALİZ TÜRÜ**")
        analysis_type = st.selectbox("Seçiniz:", ["Genel Bakış", "Fiyat Tahmini 🎯", "Risk Analizi ⚠️"], label_visibility="collapsed")
        analyze_btn = st.button("ANALİZİ BAŞLAT", type="primary")
        
        st.markdown("---")
        if st.session_state.app_mode == "TERMINAL":
            st.caption("⏳ **SÜRE**")
            day_opt = st.radio("Süre:", ["24 Saat", "7 Gün"], horizontal=True, label_visibility="collapsed")
            days_api = "1" if day_opt == "24 Saat" else "7"
            st.markdown("<br>", unsafe_allow_html=True)
        
        st.caption("🌐 **MOD SEÇİMİ**")
        mode_select = st.radio("Mod:", ["TERMINAL", "PORTAL"], horizontal=True, label_visibility="collapsed")
        st.session_state.app_mode = mode_select
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("🌍 **DİL**")
        lng = st.radio("Dil:", ["TR", "EN"], horizontal=True, label_visibility="collapsed")
        st.session_state.language = lng

# ORTA EKRAN
with col_mid:
    if st.session_state.app_mode == "TERMINAL":
        
        # 1. GİRDİ İŞLEME VE AKILLI ARAMA
        raw_input = coin_input.lower().strip()
        btc_id = "bitcoin"
        curr = st.session_state.currency
        curr_sym = "$" if curr == 'usd' else "₺" if curr == 'try' else "€"
        
        # Arama Başlıyor...
        user_coin_id = raw_input
        user_data = get_coin_data(user_coin_id, curr)
        
        # Eğer direkt bulamazsa (örn: "sol"), akıllı arama devreye girer
        if not user_data:
            found_id = search_coin_id(raw_input)
            if found_id:
                user_coin_id = found_id
                user_data = get_coin_data(user_coin_id, curr)

        btc_data = get_coin_data(btc_id, curr)
        
        if user_data and btc_data:
            c_chart1, c_chart2 = st.columns(2)
            
            # SOL ÜST GRAFİK (KULLANICI SEÇİMİ)
            with c_chart1:
                u_change = user_data.get(f'{curr}_24h_change', 0)
                u_color = "#ea3943" if u_change < 0 else "#16c784"
                cl1, cl2 = st.columns([1, 1])
                cl1.markdown(f"<h2 style='margin:0;'>{user_coin_id.upper()}</h2>", unsafe_allow_html=True)
                cl2.markdown(f"<h3 style='text-align:right; color:{u_color}; margin:0;'>{curr_sym}{user_data[curr]:,.2f} (%{u_change:.2f})</h3>", unsafe_allow_html=True)
                
                u_df = get_chart_data(user_coin_id, curr, days_api)
                if not u_df.empty:
                    st.plotly_chart(create_mini_chart(u_df, u_change, curr_sym), use_container_width=True, config={'displayModeBar': False})

            # SAĞ ÜST GRAFİK (BITCOIN - SABİT)
            with c_chart2:
                b_change = btc_data.get(f'{curr}_24h_change', 0)
                b_color = "#ea3943" if b_change < 0 else "#16c784"
                cr1, cr2 = st.columns([1, 1])
                cr1.markdown(f"<h2 style='margin:0;'>BITCOIN</h2>", unsafe_allow_html=True)
                cr2.markdown(f"<h3 style='text-align:right; color:{b_color}; margin:0;'>{curr_sym}{btc_data[curr]:,.2f} (%{b_change:.2f})</h3>", unsafe_allow_html=True)
                
                b_df = get_chart_data(btc_id, curr, days_api)
                if not b_df.empty:
                    st.plotly_chart(create_mini_chart(b_df, b_change, curr_sym), use_container_width=True, config={'displayModeBar': False})

            # ALT KISIM (3 KUTU)
            c_bot1, c_bot2, c_bot3 = st.columns(3)
            with c_bot1:
                with st.container(border=True):
                    st.caption(f"🤖 **NEXUS AI SOR**")
                    user_q = st.text_input("Soru:", placeholder="Analiz nedir?", label_visibility="collapsed")
                    if st.button("GÖNDER", key="ai_ask"):
                         if not st.secrets.get("GEMINI_API_KEY"): st.error("API Key Yok")
                         else:
                             with st.spinner(".."):
                                 try:
                                     m = get_model()
                                     r = m.generate_content(f"Coin: {user_coin_id}. Soru: {user_q}. Kısa cevapla.")
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
                    else: st.caption("Veri yükleniyor...")
            
            if analyze_btn:
                 st.markdown("---")
                 st.subheader(f"🧠 NEXUS Analiz: {analysis_type}")
                 if not st.secrets.get("GEMINI_API_KEY"): st.error("API Key Yok")
                 else:
                     with st.spinner("Piyasa taranıyor..."):
                         try:
                             model = get_model()
                             prompt = f"Coin: {user_coin_id}. Fiyat: {user_data[curr]}. Mod: {analysis_type}. Dil: {st.session_state.language}. Analiz et."
                             res = model.generate_content(prompt)
                             st.markdown(res.text)
                         except: st.error("Bağlantı hatası.")
        else:
            # BULUNAMAZSA UYARI
            st.warning(f"⚠️ '{raw_input}' bulunamadı. Lütfen tam adını yazın (Örn: solana, avalanche).")

    else:
        st.title("🌍 NEXUS GLOBAL PORTAL")
        st.info("Küresel veriler yakında burada.")

# SAĞ PANEL
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
