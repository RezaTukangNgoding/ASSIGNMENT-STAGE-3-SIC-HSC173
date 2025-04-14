import streamlit as st
import cv2
import numpy as np
import requests
from datetime import datetime
import os
from PIL import Image

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

# Fungsi untuk mulai deteksi wajah dan ambil foto
def start_detection():
    cap = cv2.VideoCapture(ESP32_CAM_URL)
    sudah_absen = False
    foto_terambil = None

    st.info("📸 Sedang Mengambil Foto...")

    while not sudah_absen:
        ret, frame = cap.read()
        if not ret:
            st.error("Gagal membaca kamera.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            if not sudah_absen:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(SAVE_DIR, f"absen_{timestamp}.jpg")
                cv2.imwrite(filename, frame)
                foto_terambil = Image.open(filename)
                kirim_absen()
                sudah_absen = True

        if foto_terambil:
            # Menyimpan foto di session_state agar tetap tampil setelah interaksi
            st.session_state.foto_absen = foto_terambil
            st.session_state.siswa_absen = st.session_state.namasiswa
            break

    cap.release()

# Daftar Kelas yang tersedia
kelas_list = ["Kelas 1", "Kelas 2", "Kelas 3", "Kelas 4"]
kelas_terpilih = st.selectbox("Pilih Kelas", kelas_list)

# Menggunakan session state untuk menyimpan nama siswa yang telah terdaftar
if "siswa" not in st.session_state:
    st.session_state.siswa = {}

# Input nama siswa
nama_siswa = st.text_input("Nama Siswa:")

# Tombol untuk menambah nama siswa
if st.button("Tambah Siswa ke Kelas"):
    if nama_siswa:
        if kelas_terpilih not in st.session_state.siswa:
            st.session_state.siswa[kelas_terpilih] = []
        if nama_siswa not in st.session_state.siswa[kelas_terpilih]:
            st.session_state.siswa[kelas_terpilih].append(nama_siswa)
            st.success(f"Nama {nama_siswa} berhasil ditambahkan ke {kelas_terpilih}")
            # Menyimpan nama siswa di session_state
            st.session_state.namasiswa = nama_siswa
            start_detection()  # Memanggil fungsi untuk mendeteksi wajah
        else:
            st.warning(f"{nama_siswa} sudah ada di kelas {kelas_terpilih}")
    else:
        st.warning("Harap masukkan nama siswa terlebih dahulu!")

# Menampilkan daftar siswa di kelas yang dipilih
if kelas_terpilih in st.session_state.siswa and len(st.session_state.siswa[kelas_terpilih]) > 0:
    st.write("Daftar Siswa di Kelas:", kelas_terpilih)
    for siswa in st.session_state.siswa[kelas_terpilih]:
        st.write(siswa)

# Menampilkan foto hasil absen yang diambil
if 'foto_absen' in st.session_state:
    st.image(st.session_state.foto_absen, caption=f"Foto Hasil Absen {st.session_state.siswa_absen}", use_column_width=True)
    st.write(f"Nama: {st.session_state.siswa_absen}")
