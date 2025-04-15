import streamlit as st
from transformers import pipeline
import os
import requests
import cv2
from PIL import Image
from datetime import datetime

# Configuration
ESP32_CAM_URL = "http://192.168.1.10:81/stream"  # Replace with your ESP32-CAM URL
UBIDOTS_TOKEN = "BBUS-ZYMsrjRHYXbLRigG1JqWtRBmjhpLls"
DEVICE_LABEL = "phaethon"
SAVE_DIR = "absensi_foto"

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# Initialize Streamlit app
st.title("Smart Classroom Management")

# Streamlit Sidebar
st.sidebar.title("Classroom Features")
action = st.sidebar.radio("Choose Action", ["Absen", "Chatbot", "Monitoring"])

# Load Hugging Face's DialoGPT for Chatbot
chatbot = pipeline("text-generation", model="microsoft/DialoGPT-medium")

# Functions
def kirim_absen():
    """Send attendance data to Ubidots."""
    url = f"http://industrial.api.ubidots.com/api/v1.6/devices/{DEVICE_LABEL}/"
    payload = {"absensi": 1}
    headers = {
        "X-Auth-Token": UBIDOTS_TOKEN,
        "Content-Type": "application/json"
    }
    requests.post(url, json=payload, headers=headers)
    st.success("✅ Absen berhasil dikirim ke Ubidots")

def ai_chatbot(prompt):
    """Interacts with Hugging Face's DialoGPT for classroom analysis."""
    responses = chatbot(prompt, max_length=1000, num_return_sequences=1)
    return responses[0]["generated_text"]

def start_camera():
    """Starts the ESP32-CAM stream and detects faces."""
    cap = cv2.VideoCapture(ESP32_CAM_URL)
    if not cap.isOpened():
        st.error("🚫 Could not open camera stream.")
        return

    stframe = st.empty()
    foto_terambil = None
    sudah_absen = False

    while cap.isOpened() and not sudah_absen:
        ret, frame = cap.read()
        if not ret:
            st.error("🚫 Failed to fetch frame from the camera.")
            break

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
                kirim_absen()
                sudah_absen = True

        stframe.image(frame, channels="BGR", use_container_width=True)

    cap.release()
    if foto_terambil:
        st.image(foto_terambil, caption=f"Absen {nama_siswa} di {kelas}", use_container_width=True)

# Absen Page
if action == "Absen":
    st.header("📸 Absen Siswa")
    nama_siswa = st.text_input("Nama Siswa:")
    kelas = st.selectbox("Pilih Kelas:", ["Kelas 1", "Kelas 2", "Kelas 3", "Kelas 4"])

    if st.button("Ambil Absen"):
        if nama_siswa and kelas:
            start_camera()
        else:
            st.warning("⚠️ Harap isi Nama Siswa dan pilih Kelas terlebih dahulu!")

# Chatbot Page
elif action == "Chatbot":
    st.header("🤖 AI Chatbot")
    prompt = st.text_area("Tulis pertanyaan Anda tentang kondisi kelas:")
    if st.button("Kirim ke Chatbot"):
        if prompt:
            response = ai_chatbot(prompt)
            st.write("### 💬 Balasan AI:")
            st.write(response)
        else:
            st.warning("⚠️ Harap tulis pertanyaan terlebih dahulu!")

# Monitoring Page
elif action == "Monitoring":
    st.header("📊 Monitoring Kondisi Kelas")
    ky038_value = st.number_input("Masukkan nilai kebisingan dari KY038:", min_value=0, max_value=100, value=50)
    dht11_temp = st.number_input("Masukkan suhu dari DHT11 (°C):", min_value=0, max_value=50, value=25)
    dht11_hum = st.number_input("Masukkan kelembaban dari DHT11 (%):", min_value=0, max_value=100, value=60)

    if st.button("Update Monitoring"):
        payload = {
            "noise": ky038_value,
            "temperature": dht11_temp,
            "humidity": dht11_hum,
        }
        url = f"http://industrial.api.ubidots.com/api/v1.6/devices/{DEVICE_LABEL}/"
        headers = {
            "X-Auth-Token": UBIDOTS_TOKEN,
            "Content-Type": "application/json"
        }
        r = requests.post(url, json=payload, headers=headers)
        if r.status_code == 200:
            st.success("✅ Data berhasil dikirim ke Ubidots")
        else:
            st.error("🚫 Gagal mengirim data ke Ubidots.")
