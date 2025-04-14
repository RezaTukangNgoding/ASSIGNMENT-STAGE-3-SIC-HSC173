import streamlit as st
import cv2
import numpy as np
import requests
from datetime import datetime
import os

# Setup
UBIDOTS_TOKEN = "BBFF-UBIDOTS_TOKEN_KAMU"
DEVICE_LABEL = "smart_classroom"
SAVE_DIR = "absensi_foto"
ESP32_CAM_URL = 0  # Ganti dengan 0 untuk webcam lokal, atau URL ESP32-CAM

# Deteksi wajah menggunakan Haar Cascade
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

st.title("Smart Phaethon Classroom - Absensi Deteksi Wajah")

def kirim_absen():
    url = f"http://industrial.api.ubidots.com/api/v1.6/devices/{DEVICE_LABEL}/"
    payload = {"absensi": 1}
    headers = {
        "X-Auth-Token": UBIDOTS_TOKEN,
        "Content-Type": "application/json"
    }
    r = requests.post(url, json=payload, headers=headers)
    st.success("✅ Absen berhasil dikirim ke Ubidots")

def start_detection():
    stframe = st.empty()
    cap = cv2.VideoCapture(ESP32_CAM_URL)

    sudah_absen = False

    while True:
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

        # Tombol stop
        if st.button("⛔ Stop"):
            break

    cap.release()

if st.button("📷 Mulai Absensi (Face Detection)"):
    start_detection()
