import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import plotly.graph_objects as go

# --- 1. AYARLAR VE BAŞLANGIÇ ---
st.set_page_config(layout="wide", page_title="NEXUS AI", page_icon="🦁")

if 'page' not in st.session_state: st.session_state.page = 'Terminal'
if 'theme_color' not in st.session_state: st.session_state.theme_color = '#00d2ff' # Neon Mavi
if 'currency' not in st.session_state: st.session_state.currency = 'try' # Default TL olsun dedin
if 'language' not in st.session_state: st.session_state.language = 'TR'

THEMES = {
    "Neon Mavi 🔵": "#00d2ff",
    "Bitcoin Turuncusu 🟠": "#F7931A",
    "Matrix Yeşili 🟢": "#00FF41",
    "Siber Mor 🟣": "#BC13FE",
    "Alarm Kırmızısı 🔴": "#FF0033"
}

# --- 2. API FONKSİYONLARI ---
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
    # Haberleri biraz daha genel çekelim ki her zaman dolu görünsün
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

# --- 3. GRAFİK MOTORU (PREMIUM) ---
def create_price_chart(df, theme_color):
    fig = go.Figure()
    # Çizgi yerine 'Area' (Alan) grafiği yapıyoruz, altı dolu ve daha şık
    fig.add_trace(go.Scatter(
        x=df['time'], y=df['price'],
        mode='lines',
        line=dict(color=theme_color, width=2),
        fill='tozeroy', # Altını doldur
        # Renk geçişi efekti için hex kodunu rgba'ya çevirip şeffaflık veriyoruz
        fillcolor=f"rgba{tuple(int(theme_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (0.1,)}"
    ))
    
    # BOŞLUKLARI YOK ETME VE YENİ DÜZEN
    fig.update_layout(
        height=400, # Sabit yükseklik
        margin=dict(l=0, r=0, t=20, b=0), # Kenar boşluklarını sıfırla
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, visible=True, showticklabels=True, color='grey'), # Alt tarihleri göster
        yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.1)', autorange=True, side='right'), # Fiyatı sağa al
        font={'color': "white"}
    )
    return fig

def create_gauge_chart(score, theme_color):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = score,
        gauge = {
            'axis': {'range': [0, 100]}, 'bar': {'color': theme_color},
            'steps': [{'range': [0, 30], 'color': "#ff0033"}, {'range': [30, 70], 'color': "#ffd700"}, {'range': [70, 100], 'color': "#00ff41"}],
            'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': score}
        }
    ))
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
    return fig

# --- 4. SAYFA YAPISI ---

# 4.1 SOL MENÜ (NATIVE SIDEBAR)
with st.sidebar:
    st.markdown(f"<h2 style='color: {st.session_state.theme_color}; text-align: center;'>🦁 NEXUS</h2>", unsafe_allow_html=True)
    
    # Navigasyon
    c1, c2 = st.columns(2)
    if c1.button("📡 TERMINAL", use_container_width=True): st.session_state.page = 'Terminal'
    if c2.button("🌐 PORTAL", use_container_width=True): st.session_state.page = 'Portal'
    
    st.markdown("---")
    
    # Arama Kutusu (Terminaldeyse)
    if st.session_state.page == 'Terminal':
        st.caption("🔎 **ANALİZ KOKPİTİ**")
        coin_input = st.text_input("Kripto Ara:", "bitcoin")
        days_select = st.selectbox("Zaman Aralığı:", ["1", "7", "30", "90"], index=1)
        analyze_btn = st.button("ANALİZİ BAŞLAT 🚀", type="primary", use_container_width=True)
    else:
        coin_input = "bitcoin" # Dummy
        days_select = "7"
        analyze_btn = False

# 4.2 ANA İÇERİK (ORTA VE SAĞ SÜTUN)
# Simetriyi sağlamak için ekranı [3, 1] oranında bölüyoruz. 
# 3 birim orta (grafik), 1 birim sağ (panel).
col_main, col_right = st.columns([3, 1.2]) 

# --- SAĞ SÜTUN (KONTROL PANELİ) ---
# Burayı senin istediğin sıraya göre diziyoruz
with col_right:
    # 1. FAVORİLER (5 COIN)
    st.info("⭐ **Favoriler**")
    cf1, cf2 = st.columns(2) # Butonları yan yana dizelim
    cf3, cf4 = st.columns(2)
    if cf1.button("BTC", use_container_width=True): coin_input = "bitcoin"
    if cf2.button("ETH", use_container_width=True): coin_input = "ethereum"
    if cf3.button("SOL", use_container_width=True): coin_input = "solana"
    if cf4.button("AVAX", use_container_width=True): coin_input = "avalanche-2"
    if st.button("DOGE", use_container_width=True): coin_input = "dogecoin"
    
    st.markdown("---")

    # 2. PARA BİRİMİ
    st.caption("💱 **Para Birimi**")
    curr_opt = st.selectbox("Seçiniz:", ["TRY", "USD", "EUR"], label_visibility="collapsed")
    st.session_state.currency = curr_opt.lower()

    st.markdown("---")

    # 3. HABERLER (Coin seçiliyse)
    st.caption(f"📰 **{coin_input.upper()} Haberleri**")
    news_data = get_news(coin_input)
    if news_data:
        with st.container(height=150): # Kaydırılabilir kutu
            for n in news_data:
                st.markdown(f"• [{n['title']}]({n['link']})")
    else:
        st.caption("Haber yok.")

    st.markdown("---")

    # 4. TEMA RENGİ
    st.caption("🎨 **Tema Rengi**")
    th_opt = st.selectbox("Tema:", list(THEMES.keys()), label_visibility="collapsed")
    st.session_state.theme_color = THEMES[th_opt]

    st.markdown("---")

    # 5. DİL (EN ALTTA)
    st.caption("🌍 **Dil / Language**")
    lang_opt = st.radio("Dil:", ["TR", "EN"], horizontal=True, label_visibility="collapsed")
    st.session_state.language = lang_opt

# --- ORTA SÜTUN (GRAFİK VE ANALİZ) ---
with col_main:
    if st.session_state.page == 'Terminal':
        # COIN VERİSİ
        coin_id = coin_input.lower().strip()
        data = get_coin_data(coin_id, st.session_state.currency)
        
        if data:
            curr_sym = "₺" if st.session_state.currency == 'try' else "$" if st.session_state.currency == 'usd' else "€"
            
            # BAŞLIK VE FİYAT (YAN YANA)
            h1, h2 = st.columns([2, 1])
            h1.markdown(f"<h1 style='color: {st.session_state.theme_color}; margin:0; padding:0;'>{coin_id.upper()}</h1>", unsafe_allow_html=True)
            h2.metric("Canlı Fiyat", f"{curr_sym}{data[st.session_state.currency]:,.2f}", f"%{data[usd_24h_change]:.2f}" if 'usd_24h_change' in data else "")
            
            # GRAFİK (BOŞLUKSUZ)
            chart_df = get_chart_data(coin_id, st.session_state.currency, days_select)
            if not chart_df.empty:
                st.plotly_chart(create_price_chart(chart_df, st.session_state.theme_color), use_container_width=True, config={'displayModeBar': False})
            
            # ANALİZ BÖLÜMÜ
            if analyze_btn:
                # Yapay Zeka + Risk İbresi
                ar1, ar2 = st.columns([1, 2])
                
                with ar1:
                    # Risk İbresi (Basit Simülasyon)
                    st.plotly_chart(create_gauge_chart(50 + (data.get('usd_24h_change', 0)*2), st.session_state.theme_color), use_container_width=True)
                
                with ar2:
                    with st.spinner("NEXUS Analiz Yapıyor..."):
                        model = get_model()
                        lang_prompt = "Türkçe yanıtla." if st.session_state.language == 'TR' else "Answer in English."
                        prompt = f"Coin: {coin_id}. Fiyat: {data[st.session_state.currency]}. {lang_prompt}. Teknik analiz ve gelecek tahmini yap. Kısa olsun."
                        res = model.generate_content(prompt)
                        st.info(res.text)
        else:
            st.warning("Veri bekleniyor... (Coin ismini doğru yazdığınızdan emin olun)")

    elif st.session_state.page == 'Portal':
        # PORTAL SAYFASI (TOP 10)
        st.subheader("🌍 Küresel Piyasa (Top 10)")
        top10 = get_top_coins(st.session_state.currency)
        if top10:
            df = pd.DataFrame(top10)[['market_cap_rank', 'name', 'current_price', 'price_change_percentage_24h']]
            df.columns = ['Sıra', 'Coin', 'Fiyat', 'Değişim %']
            st.dataframe(df, hide_index=True, use_container_width=True)
