import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import plotly.graph_objects as go
import time

# --- 1. AYARLAR VE TEMA MOTORU ---
st.set_page_config(layout="wide", page_title="NEXUS AI", page_icon="🦁")

# Session State (Hafıza) Başlangıç Ayarları
if 'page' not in st.session_state: st.session_state.page = 'Terminal' # İlk açılış Terminal olsun (Ters Köşe)
if 'theme_color' not in st.session_state: st.session_state.theme_color = '#00d2ff' # Neon Mavi (Default)
if 'currency' not in st.session_state: st.session_state.currency = 'usd'
if 'language' not in st.session_state: st.session_state.language = 'TR'

# Renk Paletleri (Kullanıcının Seçebileceği Temalar)
THEMES = {
    "Neon Mavi 🔵": "#00d2ff",
    "Bitcoin Turuncusu 🟠": "#F7931A",
    "Matrix Yeşili 🟢": "#00FF41",
    "Siber Mor 🟣": "#BC13FE",
    "Alarm Kırmızısı 🔴": "#FF0033"
}

# --- 2. API VE VERİ FONKSİYONLARI ---

# API Key Kontrolü
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("API Key Hatası!")
    st.stop()

# Otomatik Model Seçici (Google ile konuşan kısım)
@st.cache_resource
def get_model():
    models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
    for m in models:
        try:
            model = genai.GenerativeModel(m)
            model.generate_content("test") # Gizli test
            return model
        except: continue
    return genai.GenerativeModel("gemini-1.5-flash")

# Canlı Veri Çekme (CoinGecko)
@st.cache_data(ttl=120)
def get_coin_data(coin_id, currency):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={currency}&include_24hr_change=true&include_24hr_vol=true&include_last_updated_at=true"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()
        if coin_id in data:
            return data[coin_id]
        return None
    except: return None

# Grafik İçin Geçmiş Veri (Sparkline)
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

# Haberler (RSS)
@st.cache_data(ttl=300)
def get_news(query=None):
    # Eğer özel bir coin aranıyorsa Google News RSS, yoksa Cointelegraph
    if query:
        rss_url = f"https://news.google.com/rss/search?q={query}+crypto&hl=tr&gl=TR&ceid=TR:tr"
    else:
        rss_url = "https://cointelegraph.com/rss"
        
    try:
        import xml.etree.ElementTree as ET
        r = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(r.content)
        news_items = []
        for item in root.findall(".//item")[:6]:
            news_items.append({
                "title": item.find("title").text,
                "link": item.find("link").text
            })
        return news_items
    except: return []

# Top 10 Listesi (Portal İçin)
@st.cache_data(ttl=600)
def get_top_coins(currency):
    url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency={currency}&order=market_cap_desc&per_page=10&page=1&sparkline=false"
    try:
        return requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
    except: return []

# --- 3. GRAFİK OLUŞTURUCULAR (PLOTLY) ---

def create_gauge_chart(score, theme_color):
    """Risk/Güven İbresi"""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        title = {'text': "Yapay Zeka Güven Endeksi"},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': theme_color}, # İbre rengi tema rengi olsun
            'steps': [
                {'range': [0, 30], 'color': "#ff0033"},   # Kırmızı (Risk/Korku)
                {'range': [30, 70], 'color': "#ffd700"},  # Sarı (Nötr)
                {'range': [70, 100], 'color': "#00ff41"}  # Yeşil (Güven/Boğa)
            ],
            'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': score}
        }
    ))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
    return fig

def create_price_chart(df, theme_color):
    """Çizgi Fiyat Grafiği"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['time'], y=df['price'],
        mode='lines',
        line=dict(color=theme_color, width=2),
        fill='tozeroy', # Altını doldur
        fillcolor=f"rgba{tuple(int(theme_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (0.1,)}" # Tema renginin şeffaf hali
    ))
    fig.update_layout(
        height=300, 
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, visible=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
        font={'color': "white"}
    )
    return fig

# --- 4. SAYFA TASARIMLARI ---

def render_sidebar():
    """Sol Menü ve Ayarlar"""
    with st.sidebar:
        # Logo ve Başlık
        st.markdown(f"<h1 style='color: {st.session_state.theme_color}; text-align: center;'>🦁 NEXUS</h1>", unsafe_allow_html=True)
        
        # NAVIGASYON (GEÇİŞ) BUTONLARI
        col_nav1, col_nav2 = st.columns(2)
        if col_nav1.button("📡 TERMINAL", use_container_width=True): st.session_state.page = 'Terminal'
        if col_nav2.button("🌐 PORTAL", use_container_width=True): st.session_state.page = 'Portal'
        
        st.markdown("---")
        
        # TERMİNAL KONTROLLERİ (Sadece Terminaldeyse göster)
        if st.session_state.page == 'Terminal':
            st.subheader("🔎 Analiz Kokpiti")
            with st.form("search_form"):
                coin_input = st.text_input("Kripto Para Ara:", "bitcoin")
                col_b1, col_b2 = st.columns(2)
                days_select = col_b1.selectbox("Grafik:", ["1", "7", "30"], index=1)
                submit = st.form_submit_button("ANALİZ ET 🚀")
            
            st.markdown("---")
            st.caption("⭐ **Hızlı İzleme Listesi**")
            col_w1, col_w2, col_w3 = st.columns(3)
            if col_w1.button("BTC"): coin_input = "bitcoin"
            if col_w2.button("ETH"): coin_input = "ethereum"
            if col_w3.button("SOL"): coin_input = "solana"

        # AYARLAR (Her yerde görünür)
        with st.expander("⚙️ Sistem Ayarları"):
            selected_theme = st.selectbox("🎨 Tema Rengi", list(THEMES.keys()))
            st.session_state.theme_color = THEMES[selected_theme]
            
            selected_curr = st.selectbox("💱 Para Birimi", ["USD", "TRY", "EUR"])
            st.session_state.currency = selected_curr.lower()
            
            selected_lang = st.selectbox("🌍 Dil / Language", ["TR", "EN"])
            st.session_state.language = selected_lang

        return coin_input if 'coin_input' in locals() else "bitcoin", days_select if 'days_select' in locals() else "7", submit if 'submit' in locals() else False

def render_portal():
    """Portal (Ana Sayfa) Görünümü"""
    st.markdown(f"<h2 style='text-align: center;'>🌍 KÜRESEL PİYASA ÖZETİ</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: grey;'>Piyasanın nabzı burada atıyor. Detaylı analiz için Terminal'e geçin.</p>", unsafe_allow_html=True)
    st.divider()
    
    # Canlı Verileri Çek
    top_coins = get_top_coins(st.session_state.currency)
    
    # 3'lü Gündem Kartları
    col1, col2, col3 = st.columns(3)
    if top_coins:
        btc = top_coins[0]
        eth = top_coins[1]
        dom = top_coins[2] # 3. coin genelde USDT veya BNB olur
        
        curr_sym = "₺" if st.session_state.currency == 'try' else "$"
        
        col1.metric("👑 " + btc['name'], f"{curr_sym}{btc['current_price']:,.2f}", f"%{btc['price_change_percentage_24h']:.2f}")
        col2.metric("💎 " + eth['name'], f"{curr_sym}{eth['current_price']:,.2f}", f"%{eth['price_change_percentage_24h']:.2f}")
        col3.metric("🔥 " + dom['name'], f"{curr_sym}{dom['current_price']:,.2f}", f"%{dom['price_change_percentage_24h']:.2f}")
    
    st.divider()
    
    # İKİ SÜTUN: Tablo ve Haberler
    c_table, c_news = st.columns([2, 1])
    
    with c_table:
        st.subheader("🏆 Top 10 Piyasa Değeri")
        if top_coins:
            df = pd.DataFrame(top_coins)
            df = df[['market_cap_rank', 'name', 'current_price', 'price_change_percentage_24h']]
            df.columns = ['Sıra', 'Coin', 'Fiyat', '24s Değişim %']
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.warning("Veriler yükleniyor...")
            
    with c_news:
        st.subheader("📰 Son Dakika")
        news = get_news() # Genel haberler
        for n in news:
            st.markdown(f"👉 [{n['title']}]({n['link']})")
        
        st.info("💡 **İpucu:** Detaylı analiz için sol üstten **TERMINAL** butonuna basın.")

def render_terminal(coin_query, days, trigger_analyze):
    """Terminal (Analiz) Görünümü"""
    # 1. Coin ID Bulma (Arama)
    # CoinGecko'da doğru ID'yi bulmak için basit arama yapıyoruz
    coin_id = coin_query.lower().strip() 
    
    # Eğer butona basıldıysa veya sayfa yeni açıldıysa verileri çek
    if True: # Her zaman çalışsın şimdilik, dinamik olsun
        col_main, col_side = st.columns([3, 1])
        
        curr_sym = "₺" if st.session_state.currency == 'try' else "$"
        
        # --- ANA PANEL (SOL %75) ---
        with col_main:
            # Coin ID'yi doğrula (Basit bir map veya direkt API denemesi)
            # Burada 'bitcoin' gibi tam isim lazım, kullanıcı 'btc' yazarsa diye basit düzeltme:
            if len(coin_id) < 4: 
                # Basit bir eşleştirme (Geliştirilebilir)
                search_r = requests.get(f"https://api.coingecko.com/api/v3/search?query={coin_id}").json()
                if search_r.get('coins'): coin_id = search_r['coins'][0]['id']
            
            # Fiyat ve Grafik Verisi
            price_data = get_coin_data(coin_id, st.session_state.currency)
            chart_df = get_chart_data(coin_id, st.session_state.currency, days)
            
            if price_data:
                # BAŞLIK
                st.markdown(f"<h1 style='color: {st.session_state.theme_color};'>{coin_id.upper()} TERMINAL</h1>", unsafe_allow_html=True)
                
                # FİYAT METRİĞİ
                p_now = price_data[st.session_state.currency]
                p_change = price_data['usd_24h_change']
                st.metric("Canlı Fiyat", f"{curr_sym}{p_now:,.2f}", f"%{p_change:.2f}")
                
                # GRAFİK
                if not chart_df.empty:
                    st.plotly_chart(create_price_chart(chart_df, st.session_state.theme_color), use_container_width=True)
                
                # YAPAY ZEKA RAPORU & İBRE
                if trigger_analyze:
                    with st.spinner("NEXUS Yapay Zekası hesaplıyor..."):
                        # İbre Puanı (Simüle edilmiş veya AI'dan çekilmiş)
                        # Gerçek bir AI puanı için prompt'tan JSON istemek lazım, şimdilik fiyata göre basit mantık
                        risk_score = 50 + p_change # Basit mantık: Fiyat artıyorsa güven artar
                        if risk_score > 100: risk_score = 95
                        if risk_score < 0: risk_score = 5
                        
                        st.plotly_chart(create_gauge_chart(risk_score, st.session_state.theme_color), use_container_width=True)
                        
                        # AI Analizi
                        model = get_model()
                        news_text = "\n".join([n['title'] for n in get_news(coin_id)])
                        
                        lang_instruction = "Türkçe yaz." if st.session_state.language == 'TR' else "Write in English."
                        
                        prompt = f"""
                        Sen NEXUS. Profesyonel kripto analistisin.
                        Coin: {coin_id}
                        Fiyat: {p_now} {st.session_state.currency}
                        24s Değişim: %{p_change}
                        Son Haberler: {news_text}
                        
                        Görevin: {lang_instruction}
                        1. Kısa vadeli teknik yorum yap.
                        2. Boğa (Yükseliş) ve Ayı (Düşüş) senaryolarını maddeler halinde yaz.
                        3. Risk durumunu değerlendir.
                        
                        Yasal uyarı yapmayı unutma.
                        """
                        response = model.generate_content(prompt)
                        st.markdown("### 📝 Yapay Zeka Raporu")
                        st.write(response.text)
                        
            else:
                st.warning("Veri bekleniyor veya coin bulunamadı. Tam ismini yazmayı deneyin (örn: bitcoin).")

        # --- YAN PANEL (SAĞ %25) ---
        with col_side:
            st.subheader("📰 İlgili Haberler")
            if coin_id:
                news = get_news(coin_id)
                if news:
                    for n in news:
                        st.markdown(f"🔹 [{n['title']}]({n['link']})")
                else:
                    st.write("Bu coin için güncel haber bulunamadı.")
            
            st.markdown("---")
            # REKLAM ALANI (PLACEHOLDER)
            st.markdown(f"""
            <div style="
                border: 2px dashed {st.session_state.theme_color};
                padding: 20px;
                text-align: center;
                border-radius: 10px;
                color: grey;
            ">
                📢 REKLAM ALANI<br>
                (Sponsorun Logosu Buraya)
            </div>
            """, unsafe_allow_html=True)

# --- 5. MAIN (ANA ÇALIŞTIRICI) ---

coin_input, days_select, submit_btn = render_sidebar()

if st.session_state.page == 'Portal':
    render_portal()
elif st.session_state.page == 'Terminal':
    render_terminal(coin_input, days_select, submit_btn)
