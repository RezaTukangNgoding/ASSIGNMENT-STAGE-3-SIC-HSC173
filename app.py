import streamlit as st
from transformers import pipeline
import os
import requests
import cv2
from PIL import Image
from datetime import datetime
import time
import warnings
import json

# Suppress warnings
warnings.filterwarnings("ignore")

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
action = st.sidebar.radio("Choose Action", ["Absen", "Analisis Kelas", "Monitoring"])

# Load Chatbot model with caching
@st.cache_resource
def load_analysis_model():
    return pipeline("text-generation", model="mistralai/Mistral-7B-Instruct-v0.1")

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

def get_ubidots_data():
    """Fetch latest data from Ubidots."""
    url = f"https://industrial.api.ubidots.com/api/v1.6/devices/{DEVICE_LABEL}/_/values"
    headers = {"X-Auth-Token": UBIDOTS_TOKEN}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Extract latest values
        result = {}
        for item in data['results']:
            variable = item['variable']['label']
            value = item['last_value']['value']
            result[variable] = value
        
        return result
    except Exception as e:
        st.error(f"Gagal mengambil data: {str(e)}")
        return None

def analyze_classroom(data):
    """Generate classroom analysis using AI."""
    analysis_model = load_analysis_model()
    
    prompt = f"""
    Anda adalah ahli analisis kondisi kelas. Berikan analisis dan saran berdasarkan data berikut:
    
    Data Sensor:
    - Suhu: {data.get('temperature', 'N/A')}°C
    - Kelembaban: {data.get('humidity', 'N/A')}%
    - Kebisingan: {data.get('noise', 'N/A')}dB
    - Jumlah siswa hadir: {data.get('absensi', 'N/A')}
    
    Berikan:
    1. Analisis kondisi kelas saat ini
    2. Saran perbaikan jika diperlukan
    3. Prediksi masalah yang mungkin timbul
    4. Rekomendasi untuk guru
    """
    
    response = analysis_model(
        prompt,
        max_length=1000,
        temperature=0.7,
        do_sample=True
    )
    
    return response[0]['generated_text']

def start_camera(nama_siswa, kelas):
    """Starts the ESP32-CAM stream and detects faces."""
    cap = cv2.VideoCapture(ESP32_CAM_URL)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
        st.error("🚫 Could not open camera stream. Check the URL and connection.")
        return

    stframe = st.empty()
    foto_terambil = None
    sudah_absen = False

    with st.spinner("🔄 Mengakses kamera..."):
        while cap.isOpened() and not sudah_absen:
            ret, frame = cap.read()
            if not ret:
                st.error("🚫 Failed to fetch frame from the camera.")
                time.sleep(2)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

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
            time.sleep(0.1)

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

# Analysis Page
elif action == "Analisis Kelas":
    st.header("📊 Analisis Kondisi Kelas")
    
    if st.button("Analisis Sekarang", type="primary", help="Klik untuk menganalisis data terbaru dari sensor"):
        with st.spinner("🔄 Mengambil dan menganalisis data..."):
            sensor_data = get_ubidots_data()
            
            if sensor_data:
                st.subheader("📈 Data Sensor Terkini")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Suhu", f"{sensor_data.get('temperature', 'N/A')}°C")
                
                with col2:
                    st.metric("Kelembaban", f"{sensor_data.get('humidity', 'N/A')}%")
                
                with col3:
                    st.metric("Kebisingan", f"{sensor_data.get('noise', 'N/A')}dB")
                
                st.divider()
                st.subheader("🧠 Analisis AI")
                
                analysis = analyze_classroom(sensor_data)
                st.write(analysis)
            else:
                st.error("Tidak dapat memperoleh data sensor")

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
        except Exception as e:
            st.error(f"🚫 Gagal mengirim data: {str(e)}")

# Add footer
st.markdown("---")
st.markdown("© 2023 Smart Classroom Management System")
