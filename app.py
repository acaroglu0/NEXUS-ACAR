import streamlit as st
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="NEXUS TERMINAL", 
    page_icon="🦁", 
    layout="wide"
)

# --- TASARIM VE BAŞLIK ---
st.markdown("<h1 style='text-align: center; color: #00d2ff;'>🦁 NEXUS INTELLIGENCE</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: grey;'>Canlı Kripto Veri & Yapay Zeka Analiz Üssü</h3>", unsafe_allow_html=True)
st.divider()

# --- API KEY KONTROLÜ ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("🚨 HATA: API Anahtarı bulunamadı! Lütfen Streamlit 'Secrets' ayarlarını kontrol edin.")
    st.stop()

genai.configure(api_key=api_key)

# --- AKILLI MODEL SEÇİCİ ---
def get_working_model():
    # Öncelikli olarak Flash modelini dene (Hız için)
    priority_models = ["models/gemini-1.5-flash", "models/gemini-pro"]
    for model_name in priority_models:
        try:
            return genai.GenerativeModel(model_name)
        except:
            continue
    # Hiçbiri olmazsa varsayılanı döndür
    return genai.GenerativeModel("gemini-1.5-flash")

# --- VERİ ÇEKME FONKSİYONLARI ---
def get_coin_price(coin_name):
    """CoinGecko'dan canlı fiyat çeker"""
    try:
        search_url = f"https://api.coingecko.com/api/v3/search?query={coin_name}"
        search_response = requests.get(search_url).json()
        
        if not search_response.get("coins"):
            return None, None, None

        coin_id = search_response["coins"][0]["id"]
        coin_symbol = search_response["coins"][0]["symbol"].upper()
        
        price_url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
        price_data = requests.get(price_url).json()
        
        if coin_id in price_data:
            return price_data[coin_id]["usd"], price_data[coin_id]["usd_24h_change"], coin_symbol
        return None, None, None
    except:
        return None, None, None

def get_crypto_news():
    """Cointelegraph'tan haber başlıklarını çeker"""
    try:
        response = requests.get("https://cointelegraph.com/rss")
        root = ET.fromstring(response.content)
        news = [f"- [{item.find('title').text}]({item.find('link').text})" for item in root.findall(".//item")[:5]]
        return "\n".join(news)
    except:
        return "Haber kaynağına ulaşılamadı."

# --- YAN MENÜ ---
with st.sidebar:
    st.header("⚙️ Kontrol Paneli")
    coin_input = st.text_input("🪙 Coin Ara:", "Bitcoin")
    analysis_type = st.selectbox("🔍 Analiz Modu:", ["Genel Piyasa Yorumu", "Fiyat Tahmini", "Risk Analizi"])
    st.info("💡 NEXUS canlı verilerle çalışır.")

# --- ANA EKRAN ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📡 Canlı Veriler")
    price, change, symbol = get_coin_price(coin_input)
    
    if price:
        color = "green" if change > 0 else "red"
        st.metric(label=f"{symbol} Fiyatı", value=f"${price:,.2f}", delta=f"%{change:.2f}")
    else:
        st.warning("Coin bulunamadı.")

    st.write("---")
    
    if st.button("ANALİZİ BAŞLAT 🚀", type="primary", use_container_width=True):
        if price:
            with st.spinner("NEXUS piyasayı tarıyor..."):
                try:
                    news_text = get_crypto_news()
                    model = get_working_model()
                    
                    prompt = f"""
                    Sen NEXUS, usta bir kripto analistisin.
                    
                    CANLI VERİLER:
                    - Coin: {symbol}
                    - Fiyat: ${price}
                    - Değişim (24s): %{change:.2f}
                    
                    HABERLER:
                    {news_text}
                    
                    İSTEK: {analysis_type} yap.
                    Yatırımcıya kısa, net ve samimi bir analiz sun.
                    """
                    
                    response = model.generate_content(prompt)
                    st.session_state['result'] = response.text
                except Exception as e:
                    st.error(f"Hata: {e}")
        else:
            st.error("Lütfen geçerli bir coin girin.")

with col2:
    st.subheader("📝 NEXUS Raporu")
    container = st.container(border=True)
    if 'result' in st.session_state:
        container.markdown(st.session_state['result'])
    else:
        container.info("Analiz bekleniyor... Sol taraftan başlatın.")

# --- ALT BİLGİ ---
st.markdown("---")
st.caption("⚠️ **Yasal Uyarı:** Veriler CoinGecko ve Cointelegraph üzerinden sağlanmaktadır. Yatırım tavsiyesi değildir.")
