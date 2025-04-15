import streamlit as st
from transformers import pipeline
import os
import requests
import cv2
from PIL import Image
from datetime import datetime
import warnings

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Configuration
ESP32_CAM_URL = "http://192.168.1.10:81/stream"  # Replace with your ESP32-CAM URL
UBIDOTS_TOKEN = "BBUS-ZYMsrjRHYXbLRigG1JqWtRBmjhpLls"
DEVICE_LABEL = "phaethon"
SAVE_DIR = "absensi_foto"

# Create save directory if not exists
os.makedirs(SAVE_DIR, exist_ok=True)

# Initialize Streamlit app
st.set_page_config(page_title="Smart Classroom Management", layout="wide")
st.title("🏫 Smart Classroom Management")

# Streamlit Sidebar
st.sidebar.title("📋 Menu")
action = st.sidebar.radio("Choose Action", ["Absen", "Chatbot", "Monitoring"])

# Load Chatbot model with caching
@st.cache_resource
def load_chatbot():
    return pipeline("text-generation", model="microsoft/DialoGPT-medium")

# Functions
def kirim_absen(nama_siswa, kelas):
    """Send attendance data to Ubidots."""
    url = f"https://industrial.api.ubidots.com/api/v1.6/devices/{DEVICE_LABEL}/"
    payload = {
        "absensi": 1,
        "nama_siswa": nama_siswa,
        "kelas": kelas
    }
    headers = {
        "X-Auth-Token": UBIDOTS_TOKEN,
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"🚫 Error sending to Ubidots: {str(e)}")
        return False

def ai_chatbot(prompt):
    """Interacts with Hugging Face's DialoGPT for classroom analysis."""
    try:
        chatbot = load_chatbot()
        responses = chatbot(prompt, max_length=1000, pad_token_id=chatbot.tokenizer.eos_token_id)
        return responses[0]["generated_text"]
    except Exception as e:
        return f"Error in chatbot: {str(e)}"

def capture_frame(cap):
    """Capture frame from camera with error handling."""
    try:
        ret, frame = cap.read()
        if not ret:
            st.error("🚫 Failed to fetch frame from the camera.")
            return None
        return frame
    except Exception as e:
        st.error(f"Camera error: {str(e)}")
        return None

def start_camera(nama_siswa, kelas):
    """Starts the ESP32-CAM stream and detects faces."""
    cap = cv2.VideoCapture(ESP32_CAM_URL)
    if not cap.isOpened():
        st.error("🚫 Could not open camera stream. Check the URL and connection.")
        return

    stframe = st.empty()
    foto_terambil = None
    sudah_absen = False

    with st.spinner("🔄 Mengakses kamera..."):
        while cap.isOpened() and not sudah_absen:
            frame = capture_frame(cap)
            if frame is None:
                break

            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

            # Draw rectangles around faces
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                if not sudah_absen:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = os.path.join(SAVE_DIR, f"{nama_siswa}_{kelas}_{timestamp}.jpg")
                    cv2.imwrite(filename, frame)
                    foto_terambil = Image.open(filename)
                    if kirim_absen(nama_siswa, kelas):
                        sudah_absen = True

            stframe.image(frame, channels="BGR", use_container_width=True)

    cap.release()
    if foto_terambil:
        st.success(f"✅ Absen {nama_siswa} berhasil direkam!")
        st.image(foto_terambil, caption=f"Absen {nama_siswa} - {kelas}", use_container_width=True)

# Absen Page
if action == "Absen":
    st.header("📸 Sistem Absensi Siswa")
    col1, col2 = st.columns(2)
    
    with col1:
        nama_siswa = st.text_input("Nama Lengkap Siswa:")
        kelas = st.selectbox("Pilih Kelas:", ["Kelas 1", "Kelas 2", "Kelas 3", "Kelas 4"])
        
    with col2:
        st.markdown("### Petunjuk:")
        st.markdown("1. Isi nama lengkap siswa")
        st.markdown("2. Pilih kelas")
        st.markdown("3. Klik tombol 'Ambil Absen'")
        st.markdown("4. Hadapkan wajah ke kamera")

    if st.button("Ambil Absen", type="primary"):
        if nama_siswa.strip() and kelas:
            start_camera(nama_siswa, kelas)
        else:
            st.warning("⚠️ Harap isi Nama Siswa dan pilih Kelas terlebih dahulu!")

# Chatbot Page
elif action == "Chatbot":
    st.header("🤖 Asisten Virtual Kelas")
    st.markdown("Tanyakan apapun tentang manajemen kelas:")
    
    prompt = st.text_area("Pertanyaan Anda:", height=100)
    
    if st.button("Kirim Pertanyaan", type="primary"):
        if prompt.strip():
            with st.spinner("🤖 Sedang memproses..."):
                response = ai_chatbot(prompt)
                st.markdown("### 💬 Jawaban AI:")
                st.write(response)
        else:
            st.warning("⚠️ Harap tulis pertanyaan terlebih dahulu!")

# Monitoring Page
elif action == "Monitoring":
    st.header("📊 Monitoring Kondisi Kelas")
    st.markdown("Masukkan data sensor untuk dikirim ke Ubidots:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        ky038_value = st.number_input("Tingkat Kebisingan (dB):", min_value=0, max_value=100, value=50)
    
    with col2:
        dht11_temp = st.number_input("Suhu Ruangan (°C):", min_value=0, max_value=50, value=25)
    
    with col3:
        dht11_hum = st.number_input("Kelembaban (%):", min_value=0, max_value=100, value=60)

    if st.button("Kirim Data Sensor", type="primary"):
        payload = {
            "noise": ky038_value,
            "temperature": dht11_temp,
            "humidity": dht11_hum,
        }
        try:
            url = f"https://industrial.api.ubidots.com/api/v1.6/devices/{DEVICE_LABEL}/"
            headers = {
                "X-Auth-Token": UBIDOTS_TOKEN,
                "Content-Type": "application/json"
            }
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            st.success("✅ Data berhasil dikirim ke Ubidots!")
            st.json(response.json())
        except Exception as e:
            st.error(f"🚫 Gagal mengirim data: {str(e)}")

# Add footer
st.markdown("---")
st.markdown("© 2023 Smart Classroom Management System")
