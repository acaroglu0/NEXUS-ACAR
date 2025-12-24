import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import plotly.graph_objects as go

# --- 1. AYARLAR ---
st.set_page_config(layout="wide", page_title="NEXUS AI", page_icon="🦁")

# Session State (Hafıza)
if 'page' not in st.session_state: st.session_state.page = 'Terminal'
if 'theme_color' not in st.session_state: st.session_state.theme_color = '#00d2ff' # Neon Mavi
if 'currency' not in st.session_state: st.session_state.currency = 'try'
if 'language' not in st.session_state: st.session_state.language = 'TR'
if 'show_right_panel' not in st.session_state: st.session_state.show_right_panel = True # Sağ panel açık mı?

THEMES = {
    "Neon Mavi 🔵": "#00d2ff",
    "Bitcoin Turuncusu 🟠": "#F7931A",
    "Matrix Yeşili 🟢": "#00FF41",
    "Siber Mor 🟣": "#BC13FE",
    "Alarm Kırmızısı 🔴": "#FF0033"
}

# --- 2. ÖZEL CSS (SAĞ TARAFIN RENGİNİ SOLA BENZETMEK İÇİN) ---
# Bu kod sağdaki sütuna gri arka plan verir
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background-color: #262730;
    }
    .right-panel {
        background-color: #262730;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #444;
    }
</style>
""", unsafe_allow_html=True)

# --- API FONKSİYONLARI ---
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

# --- GRAFİK MOTORU ---
def create_price_chart(df, theme_color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['time'], y=df['price'], mode='lines', line=dict(color=theme_color, width=2),
        fill='tozeroy', fillcolor=f"rgba{tuple(int(theme_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (0.1,)}"
    ))
    fig.update_layout(
        height=500, margin=dict(l=0, r=0, t=20, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, visible=True, showticklabels=True, color='grey'),
        yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.1)', autorange=True, side='right'),
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

# --- SOL MENÜ (NATIVE) ---
with st.sidebar:
    st.markdown(f"<h2 style='color: {st.session_state.theme_color}; text-align: center;'>🦁 NEXUS</h2>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("📡 TERMINAL", use_container_width=True): st.session_state.page = 'Terminal'
    if c2.button("🌐 PORTAL", use_container_width=True): st.session_state.page = 'Portal'
    st.markdown("---")
    if st.session_state.page == 'Terminal':
        st.caption("🔎 **ANALİZ KOKPİTİ**")
        coin_input_sb = st.text_input("Kripto Ara:", "bitcoin")
        days_select = st.selectbox("Zaman Aralığı:", ["1", "7", "30", "90"], index=1)
        analyze_btn = st.button("ANALİZİ BAŞLAT 🚀", type="primary", use_container_width=True)
    else:
        coin_input_sb = "bitcoin"
        days_select = "7"
        analyze_btn = False

# --- ANA EKRAN DÜZENİ ---

# Aç/Kapat Butonu için fonksiyon
def toggle_panel():
    st.session_state.show_right_panel = not st.session_state.show_right_panel

# Ekranı Bölme Mantığı
if st.session_state.show_right_panel:
    # Panel Açıksa: [3 birim Grafik, 1 birim Panel]
    col_main, col_right = st.columns([3, 1])
else:
    # Panel Kapalıysa: [Tek parça Grafik]
    col_main = st.container()
    col_right = None

# --- ORTA KISIM (GRAFİK) ---
with col_main:
    # Sağ üst köşeye minik panel butonu
    h_col1, h_col2 = st.columns([10, 1])
    h_col2.button("◫", on_click=toggle_panel, help="Sağ Paneli Aç/Kapat")

    if st.session_state.page == 'Terminal':
        coin_id = coin_input_sb.lower().strip()
        # İZLEME LİSTESİNDEN GELEN SEÇİMİ KONTROL ET
        if 'selected_coin' in st.session_state:
            coin_id = st.session_state.selected_coin
            # Tek kullanımlık olduğu için silebiliriz ama kalması daha iyi user experience sağlar
            
        data = get_coin_data(coin_id, st.session_state.currency)
        
        if data:
            curr_sym = "₺" if st.session_state.currency == 'try' else "$" if st.session_state.currency == 'usd' else "€"
            h_col1.markdown(f"<h1 style='color: {st.session_state.theme_color}; margin:0; padding:0;'>{coin_id.upper()}</h1>", unsafe_allow_html=True)
            h_col1.metric("Canlı Fiyat", f"{curr_sym}{data[st.session_state.currency]:,.2f}", f"%{data.get('usd_24h_change', 0):.2f}")
            
            chart_df = get_chart_data(coin_id, st.session_state.currency, days_select)
            if not chart_df.empty:
                st.plotly_chart(create_price_chart(chart_df, st.session_state.theme_color), use_container_width=True, config={'displayModeBar': False})
            
            if analyze_btn:
                ar1, ar2 = st.columns([1, 2])
                with ar1:
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
        st.subheader("🌍 Küresel Piyasa (Top 10)")
        top10 = get_top_coins(st.session_state.currency)
        if top10:
            df = pd.DataFrame(top10)[['market_cap_rank', 'name', 'current_price', 'price_change_percentage_24h']]
            df.columns = ['Sıra', 'Coin', 'Fiyat', 'Değişim %']
            st.dataframe(df, hide_index=True, use_container_width=True)

# --- SAĞ PANEL (SADECE AÇIKSA GÖSTER) ---
if st.session_state.show_right_panel and col_right:
    with col_right:
        # Görünümü Sidebar'a benzetmek için özel kutu içine alıyoruz
        with st.container(border=True): # border=True gri çerçeve ve arka plan hissi verir
            
            # 1. FAVORİLER
            st.info("⭐ **Favoriler**")
            
            # Favori butonlarına basınca coini değiştirme mantığı
            def set_coin(c): st.session_state.selected_coin = c

            cf1, cf2 = st.columns(2)
            if cf1.button("BTC", use_container_width=True): set_coin("bitcoin")
            if cf2.button("ETH", use_container_width=True): set_coin("ethereum")
            
            cf3, cf4 = st.columns(2)
            if cf3.button("SOL", use_container_width=True): set_coin("solana")
            if cf4.button("AVAX", use_container_width=True): set_coin("avalanche-2")
            
            if st.button("DOGE", use_container_width=True): set_coin("dogecoin")
            
            st.markdown("---")

            # 2. PARA BİRİMİ
            st.caption("💱 **Para Birimi**")
            curr_opt = st.selectbox("Para Birimi Seç:", ["TRY", "USD", "EUR"], label_visibility="collapsed")
            st.session_state.currency = curr_opt.lower()

            st.markdown("---")

            # 3. HABERLER
            # Burada 'coin_id' tanımlıysa onu, değilse 'bitcoin' haberlerini göster
            target_coin = coin_id if 'coin_id' in locals() else "bitcoin"
            st.caption(f"📰 **{target_coin.upper()} Haberleri**")
            news_data = get_news(target_coin)
            if news_data:
                for n in news_data:
                    st.markdown(f"<small>• <a href='{n['link']}'>{n['title']}</a></small>", unsafe_allow_html=True)
            else:
                st.caption("Haber yok.")

            st.markdown("---")

            # 4. TEMA RENGİ
            st.caption("🎨 **Tema Rengi**")
            th_opt = st.selectbox("Tema:", list(THEMES.keys()), label_visibility="collapsed")
            st.session_state.theme_color = THEMES[th_opt]

            st.markdown("---")

            # 5. DİL
            st.caption("🌍 **Dil**")
            lang_opt = st.radio("Dil:", ["TR", "EN"], horizontal=True, label_visibility="collapsed")
            st.session_state.language = lang_opt
