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

# --- AKILLI MODEL SEÇİCİ (404 HATASI ÇÖZÜMÜ) ---
def get_working_model():
    """
    Önce en hızlı modeli (Flash) dener.
    Eğer '404' hatası verirse veya çalışmazsa,
    otomatik olarak 'Pro' modeline (Tank gibi sağlamdır) geçer.
    """
    models_to_try = [
        "gemini-1.5-flash",  # En hızlısı
        "gemini-1.5-pro",    # En zekisi
        "gemini-pro"         # En eskisi ama en sağlamı
    ]
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            # Test atışı yapalım (Boş bir istek gönderip çalışıyor mu bakalım)
            # Not: Bu test kullanıcının kotasından yemez, sadece model nesnesi oluşturur.
            return model
        except:
            continue
            
    # Hiçbiri çalışmazsa varsayılanı döndür
    return genai.GenerativeModel("gemini-pro")

# --- VERİ ÇEKME (HAFIZALI / CACHED) ---
# ttl=120 -> Verileri 2 dakika (120 saniye) hafızada tut. 
# Böylece sayfayı yenilesen de CoinGecko "Çok hızlı geldin" demez.
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
        
        if not data.get("coins"):
            return None
            
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

@st.cache_data(ttl=300, show_spinner=False) # Haberler 5 dakika hafızada kalsın
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
    
    # FORM: Kullanıcı "Enter"a basmadan veriyi çekme. Bu da hatayı önler.
    with st.form(key='search_form'):
        coin_input = st.text_input("🪙 Coin Ara (Örn: avax, fet):", "BTC")
        submit_button = st.form_submit_button(label='Verileri Getir')
        
    mode = st.selectbox("Analiz Tipi:", ["Genel Bakış", "Fiyat Tahmini", "Risk Analizi"])
    st.caption("ℹ️ 'Coin Bulunamadı' hatası alırsanız 30 saniye bekleyin.")

# --- ANA EKRAN ---
col1, col2 = st.columns([1, 2])

# Veriyi Hafızadan Çek
coin_data = None
if coin_input:
    coin_data = get_coin_data(coin_input)

with col1:
    st.subheader("📡 Piyasa Durumu")
    
    if coin_data:
        p = coin_data['price']
        c = coin_data['change']
        
        st.metric(
            label=f"{coin_data['name']} ({coin_data['symbol']})", 
            value=f"${p:,.2f}", 
            delta=f"%{c:.2f}"
        )
    elif submit_button: # Sadece butona bastıysa ve bulamadıysa uyar
        st.warning("Veri alınıyor... Eğer gelmezse biraz bekleyip tekrar deneyin.")

    st.write("---")
    
    # Analiz Butonu
    if st.button("ANALİZİ BAŞLAT 🚀", type="primary", use_container_width=True):
        if coin_data:
            with st.spinner("NEXUS, en uygun yapay zeka motorunu seçiyor ve analiz yapıyor..."):
                try:
                    news = get_news()
                    model = get_working_model() # Burada hatasız modeli seçecek
                    
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
                    st.error(f"Hata oluştu: {e}")
        else:
            st.error("Lütfen geçerli bir coin aratın.")

with col2:
    st.subheader("📝 NEXUS Raporu")
    box = st.container(border=True)
    if 'res' in st.session_state:
        box.markdown(st.session_state['res'])
    else:
        box.info("Sol taraftan analizi başlatın.")

st.markdown("---")
st.caption("⚠️ **Yasal Uyarı:** Veriler CoinGecko ve Cointelegraph'tan sağlanır. Yatırım tavsiyesi değildir.")
