import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import plotly.graph_objects as go
import time

# --- 1. AYARLAR VE TEMA MOTORU ---
st.set_page_config(layout="wide", page_title="NEXUS AI", page_icon="🦁")

if 'page' not in st.session_state: st.session_state.page = 'Terminal'
if 'theme_color' not in st.session_state: st.session_state.theme_color = '#00d2ff' # Neon Mavi
if 'currency' not in st.session_state: st.session_state.currency = 'usd'
if 'language' not in st.session_state: st.session_state.language = 'TR'

THEMES = {
    "Neon Mavi 🔵": "#00d2ff",
    "Bitcoin Turuncusu 🟠": "#F7931A",
    "Matrix Yeşili 🟢": "#00FF41",
    "Siber Mor 🟣": "#BC13FE",
    "Alarm Kırmızısı 🔴": "#FF0033"
}

# --- 2. API VE VERİ FONKSİYONLARI ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("API Key Hatası!")
    st.stop()

@st.cache_resource
def get_model():
    try:
        # Önce çalışan modeli bulmaya çalış
        models_to_try = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models_to_try.append(m.name)
        
        # Öncelik sırası
        priority = ["models/gemini-1.5-flash", "models/gemini-1.5-pro", "models/gemini-pro"]
        for p in priority:
            if p in models_to_try: return genai.GenerativeModel(p)
        
        # Hiçbiri yoksa listeden ilkini al
        if models_to_try: return genai.GenerativeModel(models_to_try[0])
        
        return genai.GenerativeModel("gemini-1.5-flash") # Son çare
    except:
        return genai.GenerativeModel("gemini-1.5-flash") # Hata olursa

@st.cache_data(ttl=120)
def get_coin_data(coin_id, currency):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={currency}&include_24hr_change=true&include_24hr_vol=true"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()
        if coin_id in data: return data[coin_id]
        return None
    except: return None

@st.cache_data(ttl=300)
def get_chart_data(coin_id, currency, days):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency={currency}&days={days}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()
        df = pd.DataFrame(data['prices'], columns=['time', 'price'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def get_news(query=None):
    if query: rss_url = f"https://news.google.com/rss/search?q={query}+crypto&hl=tr&gl=TR&ceid=TR:tr"
    else: rss_url = "https://cointelegraph.com/rss"
    try:
        import xml.etree.ElementTree as ET
        r = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(r.content)
        news_items = []
        for item in root.findall(".//item")[:5]: # 5 haber yeterli
            news_items.append({"title": item.find("title").text, "link": item.find("link").text})
        return news_items
    except: return []

@st.cache_data(ttl=600)
def get_top_coins(currency):
    url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency={currency}&order=market_cap_desc&per_page=10&page=1&sparkline=false"
    try: return requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
    except: return []

# --- 3. GRAFİK OLUŞTURUCULAR ---
def create_gauge_chart(score, theme_color):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = score, title = {'text': "AI Güven Endeksi"},
        gauge = {
            'axis': {'range': [0, 100]}, 'bar': {'color': theme_color},
            'steps': [{'range': [0, 30], 'color': "#ff0033"}, {'range': [30, 70], 'color': "#ffd700"}, {'range': [70, 100], 'color': "#00ff41"}],
            'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': score}
        }
    ))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
    return fig

def create_price_chart(df, theme_color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['time'], y=df['price'], mode='lines', line=dict(color=theme_color, width=2),
        fill='tozeroy', fillcolor=f"rgba{tuple(int(theme_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (0.1,)}"
    ))
    # DÜZELTME: Y-ekseni otomatik zoom yapsın (autorange=True)
    fig.update_layout(
        height=300, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, visible=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)', autorange=True), # <-- KRİTİK DÜZELTME
        font={'color': "white"}
    )
    return fig

# --- 4. SAYFA TASARIMLARI ---
def render_sidebar():
    with st.sidebar:
        st.markdown(f"<h1 style='color: {st.session_state.theme_color}; text-align: center;'>🦁 NEXUS</h1>", unsafe_allow_html=True)
        col_nav1, col_nav2 = st.columns(2)
        if col_nav1.button("📡 TERMINAL", use_container_width=True): st.session_state.page = 'Terminal'
        if col_nav2.button("🌐 PORTAL", use_container_width=True): st.session_state.page = 'Portal'
        st.markdown("---")
        
        # SADELEŞEN SOL MENÜ
        if st.session_state.page == 'Terminal':
            st.subheader("🔎 Analiz Kokpiti")
            with st.form("search_form"):
                coin_input = st.text_input("Kripto Para Ara:", "bitcoin")
                # 30 GÜN SEÇENEĞİ KALDIRILDI
                days_select = st.selectbox("Grafik:", ["1", "7"], index=1)
                submit = st.form_submit_button("ANALİZ ET 🚀")
        return coin_input if 'coin_input' in locals() else "bitcoin", days_select if 'days_select' in locals() else "7", submit if 'submit' in locals() else False

def render_portal():
    st.markdown(f"<h2 style='text-align: center;'>🌍 KÜRESEL PİYASA ÖZETİ</h2>", unsafe_allow_html=True)
    st.divider()
    top_coins = get_top_coins(st.session_state.currency)
    col1, col2, col3 = st.columns(3)
    if top_coins and len(top_coins) >= 3:
        curr_sym = "₺" if st.session_state.currency == 'try' else "$"
        col1.metric("👑 " + top_coins[0]['name'], f"{curr_sym}{top_coins[0]['current_price']:,.2f}", f"%{top_coins[0]['price_change_percentage_24h']:.2f}")
        col2.metric("💎 " + top_coins[1]['name'], f"{curr_sym}{top_coins[1]['current_price']:,.2f}", f"%{top_coins[1]['price_change_percentage_24h']:.2f}")
        col3.metric("🔥 " + top_coins[2]['name'], f"{curr_sym}{top_coins[2]['current_price']:,.2f}", f"%{top_coins[2]['price_change_percentage_24h']:.2f}")
    st.divider()
    c_table, c_news = st.columns([2, 1])
    with c_table:
        st.subheader("🏆 Top 10 Piyasa Değeri")
        if top_coins:
            df = pd.DataFrame(top_coins)[['market_cap_rank', 'name', 'current_price', 'price_change_percentage_24h']]
            df.columns = ['Sıra', 'Coin', 'Fiyat', '24s Değişim %']
            st.dataframe(df, hide_index=True, use_container_width=True)
    with c_news:
        st.subheader("📰 Son Dakika")
        for n in get_news(): st.markdown(f"👉 [{n['title']}]({n['link']})")

def render_terminal(coin_query, days, trigger_analyze):
    coin_id = coin_query.lower().strip()
    if len(coin_id) < 4:
        try:
            s = requests.get(f"https://api.coingecko.com/api/v3/search?query={coin_id}").json()
            if s.get('coins'): coin_id = s['coins'][0]['id']
        except: pass

    # DÜZEN DEĞİŞTİ: Eşit sütunlar ([1, 1])
    col_main, col_side = st.columns([1, 1]) 
    curr_sym = "₺" if st.session_state.currency == 'try' else "$"
    
    # --- SOL PANEL (ANA ANALİZ) ---
    with col_main:
        price_data = get_coin_data(coin_id, st.session_state.currency)
        chart_df = get_chart_data(coin_id, st.session_state.currency, days)
        if price_data:
            st.markdown(f"<h1 style='color: {st.session_state.theme_color};'>{coin_id.upper()} TERMINAL</h1>", unsafe_allow_html=True)
            p_now = price_data[st.session_state.currency]
            p_change = price_data['usd_24h_change']
            st.metric("Canlı Fiyat", f"{curr_sym}{p_now:,.2f}", f"%{p_change:.2f}")
            if not chart_df.empty: st.plotly_chart(create_price_chart(chart_df, st.session_state.theme_color), use_container_width=True)
            if trigger_analyze:
                with st.spinner("NEXUS Yapay Zekası hesaplıyor..."):
                    risk_score = 50 + p_change
                    if risk_score > 95: risk_score = 95
                    if risk_score < 5: risk_score = 5
                    st.plotly_chart(create_gauge_chart(risk_score, st.session_state.theme_color), use_container_width=True)
                    model = get_model()
                    news_text = "\n".join([n['title'] for n in get_news(coin_id)])
                    lang_instruction = "Türkçe yaz." if st.session_state.language == 'TR' else "Write in English."
                    prompt = f"""
                    Sen NEXUS. Profesyonel kripto analistisin. Coin: {coin_id}, Fiyat: {p_now} {st.session_state.currency}, 24s Değişim: %{p_change}. Haberler: {news_text}. Görevin: {lang_instruction}. 1. Kısa vadeli teknik yorum. 2. Boğa ve Ayı senaryoları (maddeler halinde). 3. Risk değerlendirmesi. Yasal uyarı ekle.
                    """
                    response = model.generate_content(prompt)
                    st.markdown("### 📝 Yapay Zeka Raporu")
                    st.write(response.text)
        else: st.warning("Veri bekleniyor veya coin bulunamadı.")

    # --- SAĞ PANEL (AYARLAR & LİSTE & HABER) ---
    with col_side:
        # 1. HIZLI İZLEME LİSTESİ (Buraya taşındı)
        st.subheader("⭐ İzleme Listesi")
        c_w1, c_w2, c_w3 = st.columns(3)
        if c_w1.button("BTC", use_container_width=True): coin_query = "bitcoin"
        if c_w2.button("ETH", use_container_width=True): coin_query = "ethereum"
        if c_w3.button("SOL", use_container_width=True): coin_query = "solana"
        
        st.markdown("---")
        
        # 2. HIZLI AYARLAR (Buraya taşındı)
        st.subheader("⚙️ Hızlı Ayarlar")
        with st.container(border=True):
            selected_theme = st.selectbox("🎨 Tema Rengi", list(THEMES.keys()))
            st.session_state.theme_color = THEMES[selected_theme]
            selected_curr = st.selectbox("💱 Para Birimi", ["USD", "TRY", "EUR"])
            st.session_state.currency = selected_curr.lower()
            selected_lang = st.radio("🌍 Dil / Language", ["TR", "EN"], horizontal=True)
            st.session_state.language = selected_lang

        st.markdown("---")
        
        # 3. HABER BAŞLIKLARI (Azaltıldı)
        st.subheader("📰 İlgili Başlıklar")
        if coin_id:
            news = get_news(coin_id)
            if news:
                for n in news[:3]: # Sadece ilk 3 haber
                    st.markdown(f"🔹 [{n['title']}]({n['link']})")
            else: st.write("Güncel haber yok.")

# --- 5. MAIN ---
coin_input_sb, days_select_sb, submit_btn_sb = render_sidebar()
# İzleme listesinden gelen inputu önceliklendir
final_coin_input = coin_query if 'coin_query' in locals() else coin_input_sb

if st.session_state.page == 'Portal': render_portal()
elif st.session_state.page == 'Terminal': render_terminal(final_coin_input, days_select_sb, submit_btn_sb)
