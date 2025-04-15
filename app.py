import streamlit as st
import requests
import cv2
from PIL import Image
from datetime import datetime
import os
import time
from transformers import pipeline

# Konfigurasi
ESP32_CAM_URL = "http://192.168.1.10:81/stream"
UBIDOTS_TOKEN = "BBUS-ZYMsrjRHYXbLRigG1JqWtRBmjhpLls"
DEVICE_LABEL = "phaethon"
SAVE_DIR = "absensi_foto"
os.makedirs(SAVE_DIR, exist_ok=True)

# Setup Streamlit
st.set_page_config(page_title="Manajemen Kelas Pintar", layout="wide")
st.title("🏫 Manajemen Kelas Pintar")

# Sidebar Menu
action = st.sidebar.radio("Menu", ["Absensi", "Deskripsi Sensor", "Monitoring"])

# Model AI Generatif
@st.cache_resource
def load_generator():
    return pipeline("text-generation", model="gpt2")

# Fungsi Ubidots
def kirim_ke_ubidots(nama_variabel, nilai):
    """Mengirim data ke Ubidots"""
    url = f"https://industrial.api.ubidots.com/api/v1.6/devices/{DEVICE_LABEL}"
    headers = {
        "X-Auth-Token": UBIDOTS_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {nama_variabel: {"value": nilai}}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        return True
    except:
        return False

def ambil_data_sensor():
    """Mengambil data sensor terbaru dari Ubidots"""
    url = f"https://industrial.api.ubidots.com/api/v1.6/devices/{DEVICE_LABEL}"
    headers = {"X-Auth-Token": UBIDOTS_TOKEN}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        return {
            "suhu": data.get("temperature", {}).get("last_value", {}).get("value"),
            "kelembaban": data.get("humidity", {}).get("last_value", {}).get("value"),
            "kebisingan": data.get("noise", {}).get("last_value", {}).get("value")
        }
    except:
        return None

# Fungsi Generatif AI
def buat_deskripsi(pembacaan_sensor):
    """Membuat deskripsi alami dari data sensor dalam Bahasa Indonesia"""
    generator = load_generator()
    
    prompt = f"""Data sensor:
- Suhu: {pembacaan_sensor['suhu']}°C
- Kelembaban: {pembacaan_sensor['kelembaban']}%
- Kebisingan: {pembacaan_sensor['kebisingan']}dB

Deskripsi kondisi kelas dalam Bahasa Indonesia:"""
    
    output = generator(
        prompt,
        max_length=150,
        num_return_sequences=1,
        temperature=0.7
    )
    
    return output[0]['generated_text'].split("Deskripsi kondisi kelas dalam Bahasa Indonesia:")[-1].strip()

# Fungsi Absensi
def ambil_absen(nama_siswa, kelas):
    """Mengambil absen menggunakan ESP32-CAM"""
    cap = cv2.VideoCapture(ESP32_CAM_URL)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
        st.error("Gagal terhubung ke kamera")
        return

    st_frame = st.empty()
    sudah_absen = False

    while cap.isOpened() and not sudah_absen:
        ret, frame = cap.read()
        if not ret:
            st.warning("Gagal mengambil frame")
            time.sleep(1)
            continue

        # Deteksi wajah
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            if not sudah_absen:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(SAVE_DIR, f"{nama_siswa}_{kelas}_{timestamp}.jpg")
                cv2.imwrite(filename, frame)
                if kirim_ke_ubidots("absensi", 1):
                    st.success(f"✅ Absen {nama_siswa} berhasil!")
                    st.image(filename, caption=f"Absen {nama_siswa} ({kelas})", use_container_width=True)
                    sudah_absen = True

        st_frame.image(frame, channels="BGR", use_container_width=True)
        time.sleep(0.1)

    cap.release()

# Halaman Absensi
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
            ambil_absen(nama_siswa, kelas)
        else:
            st.warning("Harap isi Nama Siswa dan pilih Kelas!")

# Halaman Deskripsi Sensor
elif action == "Deskripsi Sensor":
    st.header("📝 Deskripsi Kondisi Kelas")
    
    if st.button("Buat Deskripsi Otomatis", type="primary"):
        with st.spinner("Menganalisis data sensor..."):
            data_sensor = ambil_data_sensor()
            
            if data_sensor:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 Data Sensor")
                    st.metric("Suhu", f"{data_sensor['suhu']}°C")
                    st.metric("Kelembaban", f"{data_sensor['kelembaban']}%")
                    st.metric("Kebisingan", f"{data_sensor['kebisingan']}dB")
                
                with col2:
                    st.subheader("🖋️ Deskripsi AI")
                    deskripsi = buat_deskripsi(data_sensor)
                    st.write(deskripsi)
            else:
                st.error("Gagal mengambil data sensor")

# Halaman Monitoring
elif action == "Monitoring":
    st.header("📊 Monitoring Kelas")
    
    cols = st.columns(3)
    kebisingan = cols[0].number_input("Kebisingan (dB):", 0, 100, 50)
    suhu = cols[1].number_input("Suhu (°C):", 0, 50, 25)
    kelembaban = cols[2].number_input("Kelembaban (%):", 0, 100, 60)

    if st.button("Kirim Data", type="primary"):
        if all(kirim_ke_ubidots(var, val) for var, val in zip(
            ["noise", "temperature", "humidity"], 
            [kebisingan, suhu, kelembaban]
        )):
            st.success("Data berhasil dikirim!")
        else:
            st.error("Gagal mengirim beberapa data")

# Footer
st.markdown("---")
st.markdown("© 2023 Sistem Manajemen Kelas Pintar")
