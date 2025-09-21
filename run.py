#!/usr/bin/env python3
"""
Smart Attendance System - Startup Script
"""
import os
from app import app
import urllib.request

# --------------------------
# 1) Ensure necessary folders
# --------------------------
os.makedirs('uploads', exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('known_faces', exist_ok=True)
os.makedirs('attendance_data', exist_ok=True)
os.makedirs('models', exist_ok=True)

# --------------------------
# 2) Download model if missing
# --------------------------
MODEL_URL = "https://github.com/davisking/dlib-models/raw/master/shape_predictor_68_face_landmarks.dat.bz2"
MODEL_PATH = "models/shape_predictor_68_face_landmarks.dat.bz2"

if not os.path.exists(MODEL_PATH):
    print("Model not found, downloading...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
else:
    print("Model already exists, skipping download.")

# --------------------------
# 3) Start the Flask app
# --------------------------
print("=" * 50)
print("Starting Smart Attendance System...")
print("=" * 50)
print("Open http://localhost:5000 in your browser")
print("=" * 50)

app.run(debug=True, host='0.0.0.0', port=5000)
