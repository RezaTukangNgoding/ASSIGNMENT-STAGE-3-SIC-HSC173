import streamlit as st
import cv2
import numpy as np
import requests
from datetime import datetime
import os

# Setup
UBIDOTS_TOKEN = "BBUS-ZYMsrjRHYXbLRigG1JqWtRBmjhpLls"
DEVICE_LABEL = "phaethon"
SAVE_DIR = "absensi_foto"
ESP32_CAM_URL = "http://192.168.49.236:81/stream"

# Deteksi wajah menggunakan Haar Cascade
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

st.title("Smart Phaethon Classroom - Absensi Deteksi Wajah")

# Inisialisasi session state untuk kontrol tombol
if "stop_detection" not in st.session_state:
    st.session_state.stop_detection = False

# Fungsi untuk mengirim data absen
def kirim_absen():
    url = f"http://industrial.api.ubidots.com/api/v1.6/devices/{DEVICE_LABEL}/"
    payload = {"absensi": 1}
    headers = {
        "X-Auth-Token": UBIDOTS_TOKEN,
        "Content-Type": "application/json"
    }
    r = requests.post(url, json=payload, headers=headers)
    st.success("✅ Absen berhasil dikirim ke Ubidots")

# Fungsi untuk mulai deteksi wajah
def start_detection():
    stframe = st.empty()
    cap = cv2.VideoCapture(ESP32_CAM_URL)

    sudah_absen = False

    # Tombol stop untuk menghentikan deteksi
    if st.button("⛔ Stop Absensi", key="stop_btn"):
        st.session_state.stop_detection = True

    while not st.session_state.stop_detection:
        ret, frame = cap.read()
        if not ret:
            st.error("Gagal membaca kamera.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            if not sudah_absen:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(SAVE_DIR, f"absen_{timestamp}.jpg")
                cv2.imwrite(filename, frame)
                kirim_absen()
                sudah_absen = True

        stframe.image(frame, channels="BGR")

    cap.release()
    st.session_state.stop_detection = False  # Reset deteksi setelah berhenti

# Tombol untuk memulai deteksi wajah
if st.button("📷 Mulai Absensi (Face Detection)"):
    start_detection()
