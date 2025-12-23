import streamlit as st
import google.generativeai as genai

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="NEXUS TERMINAL", 
    page_icon="🦁", 
    layout="wide"
)

# --- TASARIM VE BAŞLIK ---
st.markdown("<h1 style='text-align: center; color: #00d2ff;'>🦁 NEXUS INTELLIGENCE</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: grey;'>Yapay Zeka Destekli Kripto Analiz Üssü</h3>", unsafe_allow_html=True)
st.divider()

# --- API KEY KONTROLÜ ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("🚨 HATA: API Anahtarı bulunamadı! Lütfen Streamlit 'Secrets' ayarlarını kontrol edin.")
    st.stop()

# --- MODEL AYARLARI (Flash Modeli - En Hızlısı) ---
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}

try:
    # Google ismini güncelledi, en güvenli güncel isim bu:
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )
except Exception as e:
    st.error(f"Model yüklenirken hata: {e}")

# --- YAN MENÜ ---
with st.sidebar:
    st.title("⚙️ Kontrol Paneli")
    st.markdown("---")
    coin_name = st.text_input("🪙 Kripto Para:", "Bitcoin (BTC)")
    analysis_type = st.selectbox("🔍 Analiz Modu:", 
        ["Genel Piyasa Yorumu", "Fiyat Tahmini (Senaryolu)", "Risk Analizi", "Son Dakika Haber Özeti", "Yatırımcı Psikolojisi"]
    )
    st.markdown("---")
    st.info("💡 **NEXUS**, Gemini 1.5 Flash motorunu kullanarak piyasayı saniyeler içinde tarar.")

# --- ANA EKRAN ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📡 Sinyal Gönder")
    st.write(f"**Hedef:** {coin_name}")
    st.write(f"**Mod:** {analysis_type}")
    
    if st.button("ANALİZİ BAŞLAT 🚀", type="primary", use_container_width=True):
        with st.spinner("NEXUS verileri işliyor, yapay zeka düşünüyor..."):
            try:
                # Prompt (Yapay Zeka İstemi)
                prompt = f"""
                Sen NEXUS adında, dünya çapında ünlü, zeki ve hafif esprili bir kripto para uzmanısın.
                Kullanıcı senden şu konuda analiz istedi:
                Coin: {coin_name}
                Konu: {analysis_type}

                Lütfen cevabını şu başlıklarla, Markdown formatında düzenle:
                1. 🌍 **Piyasa Nabzı:** Durum ne? Boğa mı Ayı mı?
                2. 📊 **Teknik Veriler:** Kritik destek/direnç noktaları neler olabilir? (Tahmini)
                3. 🧠 **NEXUS Görüşü:** Yatırımcıya dostane, samimi ve net tavsiyeler ver. (Asla kesin 'al-sat' emri verme, yön göster).
                
                Bol emoji kullan, sıkıcı olma. Türkçe konuş.
                """
                
                response = model.generate_content(prompt)
                st.session_state['result'] = response.text
                st.balloons() # Başarılı olunca balonlar çıksın!
                st.success("Analiz Başarıyla Tamamlandı!")
                
            except Exception as e:
                st.error(f"Bir hata oluştu: {e}")

with col2:
    st.subheader("📝 Analiz Raporu")
    container = st.container(border=True)
    if 'result' in st.session_state:
        container.markdown(st.session_state['result'])
    else:
        container.info("Analiz sonuçları burada görüntülenecek. Sol taraftan başlatın.")

# --- ALT BİLGİ ---
st.markdown("---")
st.caption("⚠️ **Yasal Uyarı:** Bu uygulama yapay zeka destekli eğitim ve bilgi amaçlıdır. Kesin yatırım tavsiyesi değildir.")
