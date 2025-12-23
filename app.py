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
st.markdown("<h3 style='text-align: center; color: grey;'>Canlı Piyasa & Yapay Zeka Analizi</h3>", unsafe_allow_html=True)
st.divider()

# --- API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("🚨 HATA: API Anahtarı bulunamadı!")
    st.stop()

genai.configure(api_key=api_key)

# --- MODEL SEÇİCİ ---
def get_model():
    # Model isimlerini sırayla dene
    models = ["models/gemini-1.5-flash", "models/gemini-pro"]
    for m in models:
        try:
            return genai.GenerativeModel(m)
        except:
            continue
    return genai.GenerativeModel("gemini-1.5-flash")

# --- GÜÇLENDİRİLMİŞ VERİ ÇEKME (HEADERS EKLENDİ) ---
def get_coin_data(query):
    """CoinGecko'dan veri çekerken tarayıcı gibi davranır"""
    # Bu başlıklar sayesinde robot sanılmayacağız
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        # 1. ARAMA YAP (eth -> ethereum bul)
        search_url = f"https://api.coingecko.com/api/v3/search?query={query}"
        r = requests.get(search_url, headers=headers)
        data = r.json()
        
        if not data.get("coins"):
            return None
            
        # İlk eşleşen coini al
        coin = data["coins"][0]
        coin_id = coin["id"]
        symbol = coin["symbol"].upper()
        name = coin["name"]
        
        # 2. FİYAT ÇEK
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
        
    except Exception as e:
        # Hata olursa sessizce None dön
        return None

def get_news():
    """Haberleri çeker"""
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
    coin_input = st.text_input("🪙 Coin Ara (Örn: eth, avax):", "BTC")
    mode = st.selectbox("Analiz Tipi:", ["Genel Bakış", "Fiyat Tahmini", "Risk Analizi"])
    
    st.info("💡 İpucu: Kısaltma yazabilirsin (btc, eth, sol...)")

# --- ANA EKRAN ---
col1, col2 = st.columns([1, 2])

# Veriyi Çek
coin_data = None
if coin_input:
    coin_data = get_coin_data(coin_input)

with col1:
    st.subheader("📡 Piyasa Durumu")
    
    if coin_data:
        p = coin_data['price']
        c = coin_data['change']
        color = "normal"
        if c > 0: color = "normal" # Streamlit metric rengi otomatik ayarlar
        
        st.metric(
            label=f"{coin_data['name']} ({coin_data['symbol']})", 
            value=f"${p:,.2f}", 
            delta=f"%{c:.2f}"
        )
    else:
        st.warning(f"'{coin_input}' bulunamadı. Tam ismini deneyin.")

    st.write("---")
    
    if st.button("ANALİZİ BAŞLAT 🚀", type="primary", use_container_width=True):
        if coin_data:
            with st.spinner("NEXUS verileri işliyor..."):
                try:
                    news = get_news()
                    model = get_model()
                    
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
                    st.error(f"Hata: {e}")
        else:
            st.error("Önce geçerli bir coin bulunmalı.")

with col2:
    st.subheader("📝 NEXUS Raporu")
    box = st.container(border=True)
    if 'res' in st.session_state:
        box.markdown(st.session_state['res'])
    else:
        box.info("Sol taraftan analizi başlatın.")

st.markdown("---")
st.caption("⚠️ **Yasal Uyarı:** Veriler CoinGecko ve Cointelegraph'tan sağlanır. Yatırım tavsiyesi değildir.")
