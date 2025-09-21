import os

class Config:
    SECRET_KEY = 'your-secret-key-here'  # Change in production
    UPLOAD_FOLDER = 'uploads'
    DATA_FOLDER = 'data'
    KNOWN_FACES_FOLDER = 'known_faces'
    ATTENDANCE_DATA_FOLDER = 'attendance_data'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    MATCH_THRESHOLD = 0.6
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB