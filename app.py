import streamlit as st
import requests
import cv2
from PIL import Image
from datetime import datetime
import os
import time
from transformers import pipeline

# Configuration
ESP32_CAM_URL = "http://192.168.1.10:81/stream"
UBIDOTS_TOKEN = "BBUS-ZYMsrjRHYXbLRigG1JqWtRBmjhpLls"
DEVICE_LABEL = "phaethon"
SAVE_DIR = "absensi_foto"
os.makedirs(SAVE_DIR, exist_ok=True)

# Streamlit App Setup
st.set_page_config(page_title="Smart Classroom Management", layout="wide")
st.title("🏫 Smart Classroom Management")

# Sidebar Menu
action = st.sidebar.radio("Menu", ["Absensi", "Analisis & Chatbot", "Monitoring"])

# Load AI Models
@st.cache_resource
def load_chatbot():
    return pipeline("text-generation", model="microsoft/DialoGPT-medium")

# Ubidots Functions
def send_to_ubidots(variable_name, value):
    """Send data to Ubidots"""
    url = f"https://industrial.api.ubidots.com/api/v1.6/devices/{DEVICE_LABEL}"
    headers = {
        "X-Auth-Token": UBIDOTS_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {variable_name: {"value": value}}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Gagal mengirim data: {str(e)}")
        return False

def get_ubidots_data():
    """Get latest data from Ubidots"""
    url = f"https://industrial.api.ubidots.com/api/v1.6/devices/{DEVICE_LABEL}"
    headers = {"X-Auth-Token": UBIDOTS_TOKEN}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Extract the last values
        result = {}
        for var_name, var_data in data.items():
            if isinstance(var_data, dict) and 'last_value' in var_data:
                result[var_name] = var_data['last_value']['value']
        return result
    except Exception as e:
        st.error(f"Gagal mengambil data: {str(e)}")
        return None

# Analysis Functions
def analyze_classroom(data):
    """Simple classroom analysis"""
    analysis = []
    
    temp = data.get('temperature')
    if temp:
        if temp > 28: analysis.append("🔥 Suhu terlalu panas (>28°C)")
        elif temp < 22: analysis.append("❄️ Suhu terlalu dingin (<22°C)")
        else: analysis.append("🌡 Suhu normal")
    
    humidity = data.get('humidity')
    if humidity:
        if humidity > 70: analysis.append("💦 Kelembaban tinggi (>70%)")
        elif humidity < 40: analysis.append("🏜 Kelembaban rendah (<40%)")
        else: analysis.append("💧 Kelembaban normal")
    
    noise = data.get('noise')
    if noise:
        if noise > 65: analysis.append("🔊 Kebisingan tinggi (>65dB)")
        else: analysis.append("🔉 Kebisingan normal")
    
    return "\n".join(analysis) if analysis else "Tidak ada data sensor"

def ai_chatbot_response(user_input, sensor_data=None):
    """Generate AI response with context"""
    chatbot = load_chatbot()
    
    prompt = f"Pertanyaan: {user_input}\n"
    if sensor_data:
        prompt += f"Data sensor: Suhu {sensor_data.get('temperature')}°C, Kelembaban {sensor_data.get('humidity')}%, Kebisingan {sensor_data.get('noise')}dB\n"
    prompt += "Jawaban:"
    
    response = chatbot(
        prompt,
        max_length=300,
        pad_token_id=chatbot.tokenizer.eos_token_id
    )
    return response[0]['generated_text'].split("Jawaban:")[-1]

# Attendance Function
def capture_attendance(nama_siswa, kelas):
    """Capture attendance using ESP32-CAM"""
    cap = cv2.VideoCapture(ESP32_CAM_URL)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
        st.error("Gagal terhubung ke kamera")
        return

    st_frame = st.empty()
    captured = False

    while cap.isOpened() and not captured:
        ret, frame = cap.read()
        if not ret:
            st.warning("Gagal mengambil frame")
            time.sleep(1)
            continue

        # Display the frame
        st_frame.image(frame, channels="BGR", use_container_width=True)
        
        # Simple face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        if len(faces) > 0:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(SAVE_DIR, f"{nama_siswa}_{kelas}_{timestamp}.jpg")
            cv2.imwrite(filename, frame)
            if send_to_ubidots("absensi", 1):
                st.success(f"✅ Absen {nama_siswa} berhasil!")
                st.image(filename, caption=f"Absen {nama_siswa} ({kelas})", use_container_width=True)
                captured = True

    cap.release()

# Absensi Page
if action == "Absensi":
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
            capture_attendance(nama_siswa, kelas)
        else:
            st.warning("Harap isi Nama Siswa dan pilih Kelas!")

# Analysis & Chatbot Page
elif action == "Analisis & Chatbot":
    st.header("🤖 Analisis & Asisten Kelas")
    
    tab1, tab2 = st.tabs(["Analisis Sensor", "Chatbot AI"])
    
    with tab1:
        if st.button("Ambil Data Sensor"):
            sensor_data = get_ubidots_data()
            if sensor_data:
                cols = st.columns(3)
                cols[0].metric("Suhu", f"{sensor_data.get('temperature', 'N/A')}°C")
                cols[1].metric("Kelembaban", f"{sensor_data.get('humidity', 'N/A')}%")
                cols[2].metric("Kebisingan", f"{sensor_data.get('noise', 'N/A')}dB")
                st.write("### Analisis Kondisi")
                st.write(analyze_classroom(sensor_data))
    
    with tab2:
        user_input = st.text_area("Tanyakan tentang kondisi kelas:")
        if st.button("Kirim Pertanyaan"):
            if user_input.strip():
                sensor_data = get_ubidots_data()
                with st.spinner("AI sedang memproses..."):
                    response = ai_chatbot_response(user_input, sensor_data)
                    st.write("### 💬 Jawaban AI")
                    st.write(response)
            else:
                st.warning("Silakan tulis pertanyaan terlebih dahulu")

# Monitoring Page
elif action == "Monitoring":
    st.header("📊 Monitoring Kondisi Kelas")
    
    cols = st.columns(3)
    noise = cols[0].number_input("Kebisingan (dB):", 0, 100, 50)
    temp = cols[1].number_input("Suhu (°C):", 0, 50, 25)
    humidity = cols[2].number_input("Kelembaban (%):", 0, 100, 60)

    if st.button("Kirim Data Sensor", type="primary"):
        if all(send_to_ubidots(var, val) for var, val in zip(
            ["noise", "temperature", "humidity"], 
            [noise, temp, humidity]
        )):
            st.success("Data berhasil dikirim!")
        else:
            st.error("Gagal mengirim beberapa data")

# Footer
st.markdown("---")
st.markdown("© 2023 Smart Classroom Management System")
