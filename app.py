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
st.markdown("<h3 style='text-align: center; color: grey;'>Canlı Kripto Veri & Yapay Zeka Analiz Üssü</h3>", unsafe_allow_html=True)
st.divider()

# --- API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("🚨 HATA: API Anahtarı bulunamadı!")
    st.stop()

genai.configure(api_key=api_key)

# --- AKILLI MODEL SEÇİCİ (TANK MODU) ---
@st.cache_resource(show_spinner="Uygun yapay zeka motoru aranıyor...")
def find_working_model():
    """
    Google'ın tüm olası model isimlerini dener.
    Gerçekten cevap vereni bulana kadar durmaz.
    """
    # Denenecekler listesi (En hızlıdan en eskiye)
    models_to_test = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-001",
        "gemini-1.5-pro",
        "gemini-1.5-pro-latest",
        "gemini-1.5-pro-001",
        "gemini-pro",
        "gemini-1.0-pro"
    ]
    
    logs = []
    
    for model_name in models_to_test:
        try:
            model = genai.GenerativeModel(model_name)
            # GERÇEK TEST: Modele 'Merhaba' de, cevap veriyor mu bak.
            response = model.generate_content("test")
            if response:
                return model_name, logs # Çalışanı bulduk!
        except Exception as e:
            logs.append(f"❌ {model_name} başarısız oldu.")
            continue
            
    # Hiçbiri çalışmazsa (Çok düşük ihtimal)
    return None, logs

# En başta modeli bul
active_model_name, debug_logs = find_working_model()

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
    st.header("⚙️ Sistem Durumu")
    
    if active_model_name:
        st.success(f"✅ Bağlı Motor: **{active_model_name}**")
    else:
        st.error("🚨 Hiçbir model çalışmadı!")
        with st.expander("Hata Günlüğü"):
            for log in debug_logs:
                st.write(log)
    
    st.markdown("---")
    with st.form(key='search_form'):
        coin_input = st.text_input("🪙 Coin Ara:", "BTC")
        submit_button = st.form_submit_button(label='Verileri Getir')
    mode = st.selectbox("Analiz Tipi:", ["Genel Bakış", "Fiyat Tahmini", "Risk Analizi"])

# --- ANA EKRAN ---
col1, col2 = st.columns([1, 2])
coin_data = None
if coin_input: coin_data = get_coin_data(coin_input)

with col1:
    st.subheader("📡 Piyasa Durumu")
    if coin_data:
        st.metric(f"{coin_data['name']} ({coin_data['symbol']})", f"${coin_data['price']:,.2f}", f"%{coin_data['change']:.2f}")
    elif submit_button:
        st.warning("Veri bekleniyor...")
    
    st.write("---")
    
    if st.button("ANALİZİ BAŞLAT 🚀", type="primary", use_container_width=True):
        if not active_model_name:
            st.error("Sistem çalışır durumda bir yapay zeka motoru bulamadı.")
        elif coin_data:
            with st.spinner(f"NEXUS ({active_model_name}) analiz yapıyor..."):
                try:
                    model = genai.GenerativeModel(active_model_name)
                    news = get_news()
                    prompt = f"""
                    Sen NEXUS. Kripto uzmanısın.
                    COIN: {coin_data['name']} ({coin_data['symbol']})
                    FİYAT: ${coin_data['price']}
                    DEĞİŞİM: %{coin_data['change']:.2f}
                    HABERLER: {news}
                    İSTEK: {mode}.
                    Yatırım tavsiyesi olmadan, samimi ve teknik bir yorum yap. Türkçe olsun.
                    """
                    res = model.generate_content(prompt)
                    st.session_state['res'] = res.text
                except Exception as e:
                    st.error(f"Motor Hatası: {e}")
        else:
            st.error("Önce geçerli bir coin verisi çekin.")

with col2:
    st.subheader("📝 Rapor")
    box = st.container(border=True)
    if 'res' in st.session_state:
        box.markdown(st.session_state['res'])
    else:
        box.info("Analiz bekleniyor...")
