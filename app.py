import streamlit as st
import google.generativeai as genai

# Sayfa Ayarları
st.set_page_config(page_title="NEXUS INTELLIGENCE", page_icon="🦁", layout="wide")

# Başlık ve Logo
st.markdown("<h1 style='text-align: center; color: #00d2ff;'>🦁 NEXUS INTELLIGENCE</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: grey;'>Yapay Zeka Destekli Kripto Analiz Terminali</h3>", unsafe_allow_html=True)
st.divider()

# API Key Kontrolü
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("🚨 HATA: API Anahtarı bulunamadı! Lütfen Secrets ayarlarını kontrol edin.")
    st.stop()

# Model Ayarları
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}
model = genai.GenerativeModel(
    model_name="gemini-1.5-flasht",
    generation_config=generation_config,
)

# Yan Menü
with st.sidebar:
    st.header("⚙️ Kontrol Paneli")
    coin_name = st.text_input("Kripto Para Adı:", "Bitcoin (BTC)")
    analysis_type = st.selectbox("Analiz Türü:", ["Genel Piyasa Yorumu", "Fiyat Tahmini", "Risk Analizi", "Haber Özeti"])
    st.info("NEXUS, en güncel piyasa verilerini ve haber akışlarını yapay zeka ile yorumlar.")

# Ana Ekran
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📊 Hızlı Bakış")
    if st.button("ANALİZİ BAŞLAT 🚀", use_container_width=True):
        with st.spinner("NEXUS verileri tarıyor..."):
            try:
                # Yapay Zeka İstemi
                prompt = f"""
                Sen uzman bir kripto para analistisin. Adın NEXUS.
                Şu an '{coin_name}' coini için '{analysis_type}' yapmanı istiyorum.
                
                Lütfen şu formatta yanıt ver:
                1. **Piyasa Durumu:** Kısa bir özet.
                2. **Teknik Göstergeler:** Önemli noktalar.
                3. **NEXUS Görüşü:** Yatırımcı dostu, samimi bir tavsiye (Asla kesin 'al/sat' deme).
                
                Yanıtın Türkçe, profesyonel ama anlaşılır olsun. Emojiler kullan.
                """
                response = model.generate_content(prompt)
                st.session_state['result'] = response.text
                st.success("Analiz Tamamlandı!")
            except Exception as e:
                st.error(f"Bir hata oluştu: {e}")

with col2:
    st.subheader("📝 NEXUS Raporu")
    if 'result' in st.session_state:
        st.markdown(st.session_state['result'])
    else:
        st.info("Analiz sonucunu görmek için sol taraftan butona basınız.")

# Alt Bilgi
st.divider()
st.caption("⚠️ Yasal Uyarı: Bu bir yatırım tavsiyesi değildir. Yapay zeka çıktıları hata içerebilir.")


