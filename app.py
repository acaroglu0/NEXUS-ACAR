import streamlit as st
import requests
import xml.etree.ElementTree as ET
import json

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="NEXUS TERMINAL", 
    page_icon="🦁", 
    layout="wide"
)

# --- BAŞLIK ---
st.markdown("<h1 style='text-align: center; color: #00d2ff;'>🦁 NEXUS INTELLIGENCE</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: grey;'>Canlı Kripto Veri & Yapay Zeka Analiz Üssü</h3>", unsafe_allow_html=True)
st.divider()

# --- API KEY KONTROLÜ ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception as e:
    st.error("🚨 API Key Hatası! Lütfen Secrets ayarlarını kontrol et.")
    st.stop()

# --- YENİ NESİL: DİREKT API BAĞLANTISI (Kütüphanesiz) ---
def ask_gemini_directly(prompt):
    """
    Bu fonksiyon aracı kütüphaneyi kullanmaz. 
    Direkt olarak Google sunucularına bağlanır.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            # Başarılı cevap geldiyse içinden metni çıkar
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            # Hata varsa (404, 400 vs) detayını göster
            error_msg = response.text
            return f"⚠️ Google Sunucu Hatası ({response.status_code}): {error_msg}"
            
    except Exception as e:
        return f"⚠️ Bağlantı Hatası: {str(e)}"

# --- VERİ ÇEKME FONKSİYONLARI ---
@st.cache_data(ttl=120, show_spinner=False)
def get_coin_data(query):
    headers = {"User-Agent": "Mozilla/5.0"}
    query = query.strip().lower()
    try:
        r = requests.get(f"https://api.coingecko.com/api/v3/search?query={query}", headers=headers)
        data = r.json()
        if not data.get("coins"): return None
        coin = data["coins"][0]
        
        r_price = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin['id']}&vs_currencies=usd&include_24hr_change=true", headers=headers)
        p_data = r_price.json()
        
        if coin['id'] in p_data:
            return {
                "name": coin["name"], 
                "symbol": coin["symbol"].upper(), 
                "price": p_data[coin['id']]["usd"], 
                "change": p_data[coin['id']]["usd_24h_change"]
            }
        return None
    except:
        return None

@st.cache_data(ttl=300, show_spinner=False)
def get_news():
    try:
        r = requests.get("https://cointelegraph.com/rss", headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(r.content)
        return "\n".join([f"- [{i.find('title').text}]({i.find('link').text})" for i in root.findall(".//item")[:5]])
    except:
        return "Haber kaynağına ulaşılamadı."

# --- YAN MENÜ ---
with st.sidebar:
    st.header("⚙️ Kontrol Paneli")
    with st.form(key='search_form'):
        coin_input = st.text_input("🪙 Coin Ara (Örn: btc, eth):", "BTC")
        submit_button = st.form_submit_button(label='Verileri Getir')
    
    mode = st.selectbox("Analiz Tipi:", ["Genel Bakış", "Fiyat Tahmini", "Risk Analizi"])
    st.info("Sistem 'Direkt Bağlantı Modu' ile çalışıyor.")

# --- ANA EKRAN ---
col1, col2 = st.columns([1, 2])

coin_data = None
if coin_input:
    coin_data = get_coin_data(coin_input)

with col1:
    st.subheader("📡 Piyasa Durumu")
    if coin_data:
        st.metric(f"{coin_data['name']} ({coin_data['symbol']})", f"${coin_data['price']:,.2f}", f"%{coin_data['change']:.2f}")
    elif submit_button:
        st.warning("Veri bekleniyor... (CoinGecko yanıt vermezse 30sn bekleyin)")
    
    st.write("---")
    
    if st.button("ANALİZİ BAŞLAT 🚀", type="primary", use_container_width=True):
        if coin_data:
            with st.spinner("NEXUS, Google sunucularına bağlanıyor..."):
                news = get_news()
                prompt = f"""
                Sen NEXUS. Kripto uzmanısın.
                COIN: {coin_data['name']}
                FİYAT: ${coin_data['price']}
                DEĞİŞİM: %{coin_data['change']:.2f}
                HABERLER: {news}
                İSTEK: {mode}.
                Yatırım tavsiyesi verme. Samimi ve teknik konuş.
                """
                
                # --- YENİ FONKSİYONU ÇAĞIRIYORUZ ---
                result_text = ask_gemini_directly(prompt)
                st.session_state['res'] = result_text

        else:
            st.error("Önce geçerli bir coin verisi lazım.")

with col2:
    st.subheader("📝 Rapor")
    box = st.container(border=True)
    if 'res' in st.session_state:
        # Hata mesajı mı yoksa gerçek cevap mı kontrol et
        if "⚠️" in st.session_state['res']:
            st.error(st.session_state['res'])
        else:
            box.markdown(st.session_state['res'])
    else:
        box.info("Analiz bekleniyor...")
