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

# --- TASARIM BAŞLIKLARI ---
st.markdown("<h1 style='text-align: center; color: #00d2ff;'>🦁 NEXUS INTELLIGENCE</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: grey;'>Canlı Kripto Veri & Yapay Zeka Analiz Üssü</h3>", unsafe_allow_html=True)
st.divider()

# --- API KEY KONTROLÜ ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("🚨 HATA: API Anahtarı bulunamadı! Lütfen Streamlit 'Secrets' ayarlarını kontrol edin.")
    st.stop()

genai.configure(api_key=api_key)

# --- FONKSİYONLAR (GERÇEK VERİ ÇEKME) ---

def get_coin_price(coin_name):
    """
    CoinGecko'dan canlı fiyat çeker.
    Önce coinin ID'sini arar, sonra fiyatını bulur.
    """
    try:
        # 1. Arama Yap (Kullanıcı 'BTC' yazsa bile 'bitcoin' id'sini bulalım)
        search_url = f"https://api.coingecko.com/api/v3/search?query={coin_name}"
        search_response = requests.get(search_url).json()
        
        if not search_response.get("coins"):
            return None, None, None

        # En iyi eşleşen coini al
        coin_id = search_response["coins"][0]["id"]
        coin_symbol = search_response["coins"][0]["symbol"].upper()
        
        # 2. Fiyatı Çek
        price_url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
        price_data = requests.get(price_url).json()
        
        if coin_id in price_data:
            current_price = price_data[coin_id]["usd"]
            change_24h = price_data[coin_id]["usd_24h_change"]
            return current_price, change_24h, coin_symbol
        else:
            return None, None, None
            
    except Exception as e:
        st.error(f"Fiyat verisi alınamadı: {e}")
        return None, None, None

def get_crypto_news():
    """
    Cointelegraph RSS beslemesinden son haberleri çeker.
    """
    try:
        rss_url = "https://cointelegraph.com/rss"
        response = requests.get(rss_url)
        root = ET.fromstring(response.content)
        
        news_items = []
        # İlk 5 haberi al
        for item in root.findall(".//item")[:5]:
            title = item.find("title").text
            link = item.find("link").text
            news_items.append(f"- [{title}]({link})")
            
        return "\n".join(news_items)
    except Exception as e:
        return "Haber kaynağına ulaşılamadı."

# --- YAN MENÜ ---
with st.sidebar:
    st.header("⚙️ Kontrol Paneli")
    coin_input = st.text_input("🪙 Coin Ara:", "Bitcoin")
    analysis_type = st.selectbox("🔍 Analiz Modu:", 
        ["Genel Piyasa Yorumu", "Fiyat Tahmini", "Risk Analizi"]
    )
    st.info("💡 NEXUS artık canlı fiyatları ve haberleri okuyup ona göre yorum yapıyor.")

# --- ANA EKRAN ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📡 Canlı Veriler")
    
    # Butona basılmasa bile fiyatı gösterelim (Eğer geçerli bir coin ise)
    if coin_input:
        price, change, symbol = get_coin_price(coin_input)
        if price:
            st.metric(label=f"{symbol} Fiyatı", value=f"${price:,.2f}", delta=f"%{change:.2f}")
        else:
            st.warning("Coin bulunamadı, doğru yazdığınızdan emin olun.")

    st.write("---")
    
    if st.button("NEXUS'U ÇALIŞTIR 🚀", type="primary", use_container_width=True):
        if not price:
            st.error("Önce geçerli bir coin bulunmalı.")
        else:
            with st.spinner("Haberler taranıyor, fiyatlar inceleniyor..."):
                try:
                    # 1. Haberleri Çek
                    latest_news = get_crypto_news()
                    
                    # 2. Modeli Seç (Akıllı Seçim)
                    model = genai.GenerativeModel("gemini-1.5-flash") # En hızlısı
                    
                    # 3. Prompt Hazırla (Canlı verileri de ekleyerek)
                    prompt = f"""
                    Sen NEXUS adında usta bir kripto analistisin.
                    Şu anki gerçek veriler şunlar:
                    
                    VARLIK: {symbol}
                    GÜNCEL FİYAT: ${price}
                    24S DEĞİŞİM: %{change:.2f}
                    
                    SON DAKİKA HABER BAŞLIKLARI:
                    {latest_news}
                    
                    Kullanıcı isteği: {analysis_type}
                    
                    Bu verileri kullanarak, yatırımcıya kısa, net ve veriye dayalı bir analiz yap.
                    Haberlerin fiyata etkisini yorumla.
                    Yasal uyarıyı unutma.
                    """
                    
                    response = model.generate_content(prompt)
                    st.session_state['result'] = response.text
                    
                except Exception as e:
                    st.error(f"Yapay zeka hatası: {e}")

with col2:
    st.subheader("📝 Akıllı Analiz Raporu")
    container = st.container(border=True)
    if 'result' in st.session_state:
        container.markdown(st.session_state['result'])
    else:
        container.info("Sol taraftan 'NEXUS'U ÇALIŞTIR' butonuna basınız.")

# --- ALT BİLGİ ---
st.markdown("---")
st.caption("⚠️ **Yasal Uyarı:** Veriler CoinGecko ve Cointelegraph üzerinden sağlanmaktadır. Yatırım tavsiyesi değildir.")info("Analiz bekleniyor...")

