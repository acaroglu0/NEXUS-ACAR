import streamlit as st
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
import time

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="NEXUS TERMINAL", 
    page_icon="🦁", 
    layout="wide"
)

# --- TASARIM ---
st.markdown("<h1 style='text-align: center; color: #00d2ff;'>🦁 NEXUS INTELLIGENCE</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: grey;'>Canlı Piyasa & Yapay Zeka Analiz Üssü</h3>", unsafe_allow_html=True)
st.divider()

# --- API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("🚨 HATA: API Anahtarı bulunamadı!")
    st.stop()

genai.configure(api_key=api_key)

# --- AKILLI MODEL SEÇİCİ (TEST SÜRÜŞLÜ) ---
# cache_resource: Bu işlemi bir kere yap, çalışan modeli hafızada tut.
@st.cache_resource(show_spinner="Yapay zeka motorları test ediliyor...")
def get_working_model():
    """
    Modelleri sırayla dener. Sadece ismine bakmaz, 
    gerçekten cevap veriyor mu diye test eder.
    """
    models_to_try = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            # GİZLİ TEST: Modele boş bir sinyal gönder
            model.generate_content("test")
            # Hata vermediyse bu model çalışıyor demektir!
            return model_name 
        except:
            # Hata verdiyse sonrakine geç
            continue
            
    # Hiçbiri çalışmazsa en eskisini döndür (Son çare)
    return "gemini-pro"

# Çalışan modeli hafızadan çağır
active_model_name = get_working_model()
model = genai.GenerativeModel(active_model_name)

# --- VERİ ÇEKME (HAFIZALI / CACHED) ---
@st.cache_data(ttl=120, show_spinner=False)
def get_coin_data(query):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    query = query.strip().lower()
    try:
        # 1. ARAMA
        search_url = f"https://api.coingecko.com/api/v3/search?query={query}"
        r = requests.get(search_url, headers=headers)
        data = r.json()
        if not data.get("coins"): return None
            
        coin = data["coins"][0]
        coin_id = coin["id"]
        symbol = coin["symbol"].upper()
        name = coin["name"]
        
        # 2. FİYAT
        price_url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
        r_price = requests.get(price_url, headers=headers)
        p_data = r_price.json()
        
        if coin_id in p_data:
            return {
                "name": name, 
                "symbol": symbol, 
                "price": p_data[coin_id]["usd"], 
                "change": p_data[coin_id]["usd_24h_change"]
            }
        return None
    except:
        return None

@st.cache_data(ttl=300, show_spinner=False)
def get_news():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get("https://cointelegraph.com/rss", headers=headers)
        root = ET.fromstring(r.content)
        news = []
        for item in root.findall(".//item")[:5]:
            title = item.find("title").text
            link = item.find("link").text
            news.append(f"- [{title}]({link})")
        return "\n".join(news)
    except:
        return "Haberler şu an alınamıyor."

# --- ARAYÜZ ---
with st.sidebar:
    st.header("⚙️ Kontrol Paneli")
    
    # Kullanıcıya aktif modeli gösterelim ki için rahat olsun
    st.success(f"✅ Aktif Motor: {active_model_name}")
    
    with st.form(key='search_form'):
        coin_input = st.text_input("🪙 Coin Ara (Örn: sol, avax):", "BTC")
        submit_button = st.form_submit_button(label='Verileri Getir')
        
    mode = st.selectbox("Analiz Tipi:", ["Genel Bakış", "Fiyat Tahmini", "Risk Analizi"])
    st.caption("ℹ️ Veriler önbelleğe alınır, sistem hızlı çalışır.")

# --- ANA EKRAN ---
col1, col2 = st.columns([1, 2])

coin_data = None
if coin_input:
    coin_data = get_coin_data(coin_input)

with col1:
    st.subheader("📡 Piyasa Durumu")
    
    if coin_data:
        p = coin_data['price']
        c = coin_data['change']
        st.metric(label=f"{coin_data['name']} ({coin_data['symbol']})", value=f"${p:,.2f}", delta=f"%{c:.2f}")
    elif submit_button:
        st.warning("Veri bulunamadı, lütfen tekrar deneyin.")

    st.write("---")
    
    if st.button("ANALİZİ BAŞLAT 🚀", type="primary", use_container_width=True):
        if coin_data:
            with st.spinner("NEXUS analiz yapıyor..."):
                try:
                    news = get_news()
                    # Modeli yukarıda zaten seçtik ve test ettik, direkt kullanıyoruz.
                    
                    prompt = f"""
                    Sen NEXUS. Kripto uzmanısın.
                    
                    ANALİZ EDİLECEK COIN: {coin_data['name']} ({coin_data['symbol']})
                    FİYAT: ${coin_data['price']}
                    DEĞİŞİM (24s): %{coin_data['change']:.2f}
                    
                    SON HABERLER:
                    {news}
                    
                    KULLANICI İSTEĞİ: {mode}
                    
                    Yatırımcıya samimi, net ve veriye dayalı bir analiz yap.
                    Başlıklar kullan, emojiler ekle. Yasal uyarıyı unutma.
                    """
                    
                    res = model.generate_content(prompt)
                    st.session_state['res'] = res.text
                except Exception as e:
                    st.error(f"Beklenmedik bir hata: {e}")
        else:
            st.error("Lütfen geçerli bir coin verisi çekin.")

with col2:
    st.subheader("📝 NEXUS Raporu")
    box = st.container(border=True)
    if 'res' in st.session_state:
        box.markdown(st.session_state['res'])
    else:
        box.info("Analiz bekleniyor...")

st.markdown("---")
st.caption("⚠️ **Yasal Uyarı:** Veriler CoinGecko ve Cointelegraph'tan sağlanır. Yatırım tavsiyesi değildir.")
