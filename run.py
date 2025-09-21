#!/usr/bin/env python3
"""
Smart Attendance System - Startup Script
"""
import os
from app import app

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    os.makedirs('known_faces', exist_ok=True)
    os.makedirs('attendance_data', exist_ok=True)
    
    print("=" * 50)
    print("Starting Smart Attendance System...")
    print("=" * 50)
    print("Open http://localhost:5000 in your browser")
    print("=" * 50)
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)