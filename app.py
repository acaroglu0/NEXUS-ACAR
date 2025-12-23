import streamlit as st
import google.generativeai as genai

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="NEXUS TERMINAL", 
    page_icon="🦁", 
    layout="wide"
)

# --- BAŞLIK ---
st.markdown("<h1 style='text-align: center; color: #00d2ff;'>🦁 NEXUS INTELLIGENCE</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: grey;'>Otomatik Model Algılayıcı Sistem</h3>", unsafe_allow_html=True)
st.divider()

# --- API KEY KONTROLÜ ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("🚨 HATA: API Anahtarı bulunamadı! Lütfen Streamlit 'Secrets' ayarlarını kontrol edin.")
    st.stop()

genai.configure(api_key=api_key)

# --- AKILLI MODEL SEÇİCİ (BU KISIM YENİ) ---
# Modelleri tek tek deneyeceğiz, hangisi çalışırsa onu kapacağız.
def get_working_model():
    available_models = []
    try:
        # Google'a sor: Hangi modellerin var?
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
    except Exception as e:
        return None, f"Bağlantı Hatası: {str(e)}"

    # Tercih sıramız: Önce Flash, olmazsa Pro, o da olmazsa herhangi biri.
    priority_models = [
        "models/gemini-1.5-flash", 
        "models/gemini-1.5-pro", 
        "models/gemini-pro"
    ]
    
    # Listeden eşleşen ilkini bul
    for priority in priority_models:
        if priority in available_models:
            return priority, None
            
    # Eğer öncelikliler yoksa, çalışan ilk modeli ver
    if available_models:
        return available_models[0], None
        
    return None, "Hiçbir uygun model bulunamadı."

# Modeli Belirle
model_name, error_msg = get_working_model()

if error_msg:
    st.error(f"🚨 SİSTEM HATASI: {error_msg}")
    st.warning("İpucu: API Key'iniz geçerli mi? Google AI Studio'dan yeni bir key almayı deneyin.")
    st.stop()
else:
    # Model Başarıyla Seçildi
    try:
        model = genai.GenerativeModel(model_name)
        st.success(f"✅ Sistem Bağlandı! Aktif Motor: **{model_name}**")
    except Exception as e:
        st.error(f"Model yüklenirken hata: {e}")

# --- YAN MENÜ ---
with st.sidebar:
    st.header("⚙️ Kontrol Paneli")
    coin_name = st.text_input("🪙 Kripto Para:", "Bitcoin (BTC)")
    analysis_type = st.selectbox("🔍 Analiz Modu:", 
        ["Genel Piyasa Yorumu", "Fiyat Tahmini", "Risk Analizi"]
    )

# --- ANA EKRAN ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📡 Sinyal Gönder")
    if st.button("ANALİZİ BAŞLAT 🚀", type="primary", use_container_width=True):
        with st.spinner(f"{model_name} motoru çalışıyor..."):
            try:
                prompt = f"""
                Sen uzman bir kripto analistisin.
                Coin: {coin_name}
                Konu: {analysis_type}
                Lütfen kısa, net ve yatırımcı dostu bir yorum yap.
                """
                response = model.generate_content(prompt)
                st.session_state['result'] = response.text
            except Exception as e:
                st.error(f"Bir hata oluştu: {e}")

with col2:
    st.subheader("📝 Rapor")
    if 'result' in st.session_state:
        st.markdown(st.session_state['result'])
    else:
        st.info("Analiz bekleniyor...")
