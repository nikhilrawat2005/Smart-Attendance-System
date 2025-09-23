import os
import io
import json
import csv
import base64
import logging
from datetime import datetime, timedelta
from flask import Flask, request, render_template, redirect, send_from_directory, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
import face_recognition
from config import Config


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change in production

# Configuration
UPLOAD_FOLDER = 'uploads'
DATA_FOLDER = 'data'
KNOWN_FACES_FOLDER = 'known_faces'
ATTENDANCE_DATA_FOLDER = 'attendance_data'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MATCH_THRESHOLD = 0.6
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(KNOWN_FACES_FOLDER, exist_ok=True)
os.makedirs(ATTENDANCE_DATA_FOLDER, exist_ok=True)

# Helper Functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_safe_name(name):
    return "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_')

# Attendance Summary Functions (NEW)
def ensure_attendance_csv_exists():
    """Make sure CSV exists with header"""
    os.makedirs(os.path.dirname("attendance_data/overall_attendance.csv"), exist_ok=True)
    csv_file = "attendance_data/overall_attendance.csv"
    if not os.path.exists(csv_file):
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "class_name", "total_students", "present"])

def log_attendance(class_name, total_students, present):
    """Add/Update today's record for a class"""
    ensure_attendance_csv_exists()
    today = datetime.now().date().isoformat()
    csv_file = "attendance_data/overall_attendance.csv"
    rows = []
    updated = False
    
    # read old data
    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["date"] == today and row["class_name"] == class_name:
                row["total_students"] = str(total_students)
                row["present"] = str(present)
                updated = True
            rows.append(row)
    
    # if not updated, add new row
    if not updated:
        rows.append({
            "date": today,
            "class_name": class_name,
            "total_students": total_students,
            "present": present
        })
    
    # rewrite file
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date","class_name","total_students","present"])
        writer.writeheader()
        writer.writerows(rows)

def get_today_summary():
    """Return total present/total students"""
    ensure_attendance_csv_exists()
    today = datetime.now().date().isoformat()
    csv_file = "attendance_data/overall_attendance.csv"
    total_students, total_present = 0, 0
    
    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["date"] == today:
                total_students += int(row["total_students"])
                if row["present"] != "":
                    total_present += int(row["present"])
    
    return total_present, total_students

def get_performance():
    """Compare today's vs yesterday's attendance %"""
    ensure_attendance_csv_exists()
    today = datetime.now().date().isoformat()
    yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
    csv_file = "attendance_data/overall_attendance.csv"
    
    def calc_percentage(day):
        total_s, total_p = 0, 0
        with open(csv_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["date"] == day and row["present"] != "":
                    total_s += int(row["total_students"])
                    total_p += int(row["present"])
        return (total_p/total_s*100) if total_s > 0 else 0
    
    today_perc = calc_percentage(today)
    yest_perc = calc_percentage(yesterday)
    
    change = today_perc - yest_perc
    status = "Improved" if change > 0 else "Declined"
    return today_perc, status, round(abs(change), 1)

# Class Management
def get_all_classes():
    classes = []
    if os.path.exists(DATA_FOLDER):
        for filename in os.listdir(DATA_FOLDER):
            if filename.endswith('.json'):
                class_name = filename[:-5]  # Remove .json extension
                classes.append(class_name)
    return sorted(classes)

def create_class(class_name, total_students=0):
    safe_class_name = get_safe_name(class_name)
    filepath = os.path.join(DATA_FOLDER, f"{safe_class_name}.json")
    
    if os.path.exists(filepath):
        return False, f"Class '{class_name}' already exists"
    
    # Create class directories
    class_faces_dir = os.path.join(KNOWN_FACES_FOLDER, safe_class_name)
    os.makedirs(class_faces_dir, exist_ok=True)
    
    class_attendance_dir = os.path.join(ATTENDANCE_DATA_FOLDER, safe_class_name)
    os.makedirs(class_attendance_dir, exist_ok=True)
    
    # Create class data structure
    class_data = {
        'name': class_name,
        'safe_name': safe_class_name,
        'total_students': total_students,
        'students': [],
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
    
    with open(filepath, 'w') as f:
        json.dump(class_data, f, indent=2)
    
    return True, f"Class '{class_name}' created successfully"

def get_class(class_name):
    safe_class_name = get_safe_name(class_name)
    filepath = os.path.join(DATA_FOLDER, f"{safe_class_name}.json")
    
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r') as f:
        return json.load(f)

def save_class(class_data):
    safe_class_name = class_data['safe_name']
    filepath = os.path.join(DATA_FOLDER, f"{safe_class_name}.json")
    
    with open(filepath, 'w') as f:
        json.dump(class_data, f, indent=2)
    
    return True

def delete_class(class_name):
    safe_class_name = get_safe_name(class_name)
    
    # Delete class data file
    filepath = os.path.join(DATA_FOLDER, f"{safe_class_name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
    
    # Delete class faces directory
    class_faces_dir = os.path.join(KNOWN_FACES_FOLDER, safe_class_name)
    if os.path.exists(class_faces_dir):
        import shutil
        shutil.rmtree(class_faces_dir)
    
    # Delete class attendance directory
    class_attendance_dir = os.path.join(ATTENDANCE_DATA_FOLDER, safe_class_name)
    if os.path.exists(class_attendance_dir):
        import shutil
        shutil.rmtree(class_attendance_dir)
    
    return True, f"Class '{class_name}' deleted successfully"

# Student Management
def add_students(class_name, students_data):
    class_data = get_class(class_name)
    if not class_data:
        return False, "Class not found"
    
    # Update existing students or add new ones
    for new_student in students_data:
        existing = False
        for i, student in enumerate(class_data['students']):
            if student['student_id'] == new_student['student_id']:
                class_data['students'][i]['name'] = new_student['name']
                existing = True
                break
        
        if not existing:
            class_data['students'].append({
                'student_id': new_student['student_id'],
                'name': new_student['name'],
                'photos': [],
                'encodings': []
            })
    
    # Update timestamp
    class_data['updated_at'] = datetime.now().isoformat()
    
    # Save updated class data
    save_class(class_data)
    
    return True, f"Added/updated {len(students_data)} students in class '{class_name}'"

def add_student_photo(class_name, student_id, photo_files):
    """Add one or multiple photos for a student."""
    class_data = get_class(class_name)
    if not class_data:
        return False, "Class not found"
    
    # Find the student
    student = next((s for s in class_data['students'] if s['student_id'] == student_id), None)
    if not student:
        return False, "Student not found"
    
    # Ensure photo_files is a list
    if not isinstance(photo_files, list):
        photo_files = [photo_files]

    safe_class_name = class_data['safe_name']
    added = 0

    for photo_file in photo_files:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{student_id}_{timestamp}_{secure_filename(photo_file.filename)}"
        filepath = os.path.join(KNOWN_FACES_FOLDER, safe_class_name, filename)

        photo_file.save(filepath)

        try:
            image = face_recognition.load_image_file(filepath)
            face_locations = face_recognition.face_locations(image)
            if not face_locations:
                os.remove(filepath)
                continue

            face_encodings = face_recognition.face_encodings(image, face_locations)
            if not face_encodings:
                os.remove(filepath)
                continue

            student['photos'].append(filename)
            student['encodings'].append(face_encodings[0].tolist())
            added += 1
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            logger.warning(f"Error processing {filepath}: {e}")

    if added > 0:
        # Keep only the first photo for encodings
        if student['photos']:
            # Sort photos by filename and keep only the first one for encoding
            sorted_photos = sorted(student['photos'])
            first_photo = sorted_photos[0]
            
            # Find the encoding corresponding to the first photo
            first_photo_index = student['photos'].index(first_photo)
            first_encoding = student['encodings'][first_photo_index]
            
            # Keep only the first photo and encoding
            student['photos'] = [first_photo]
            student['encodings'] = [first_encoding]
        
        class_data['updated_at'] = datetime.now().isoformat()
        save_class(class_data)
        return True, f"✅ {added} photo(s) added successfully. Only first photo used for encoding."
    else:
        return False, "❌ No valid face detected in uploaded photo(s)"

# Function to delete a student
def delete_student(class_name, student_id):
    """Delete a student from JSON, photos, and encodings (not CSV)."""
    class_data = get_class(class_name)
    if not class_data:
        return False, "Class not found"

    safe_class_name = class_data['safe_name']
    students = class_data['students']

    # find student
    student = None
    for s in students:
        if s['student_id'] == student_id:
            student = s
            break

    if not student:
        return False, f"Student {student_id} not found"

    # 1. remove photos from known_faces folder
    class_faces_dir = os.path.join(KNOWN_FACES_FOLDER, safe_class_name)
    if os.path.exists(class_faces_dir):
        for photo in student.get("photos", []):
            photo_path = os.path.join(class_faces_dir, photo)
            try:
                if os.path.exists(photo_path):
                    os.remove(photo_path)
            except Exception as e:
                logger.warning(f"Could not delete {photo_path}: {e}")

    # 2. remove student from JSON
    class_data['students'] = [s for s in students if s['student_id'] != student_id]
    class_data['updated_at'] = datetime.now().isoformat()
    save_class(class_data)

    return True, f"🗑️ Student {student_id} deleted from {class_name}"

# Function to generate encodings for all photos in a class
def generate_class_encodings(class_name):
    class_data = get_class(class_name)
    if not class_data:
        return False, "Class not found"
    
    safe_class_name = class_data['safe_name']
    class_faces_dir = os.path.join(KNOWN_FACES_FOLDER, safe_class_name)
    
    if not os.path.exists(class_faces_dir):
        return False, "Class faces directory not found"
    
    # Process each student
    for student in class_data['students']:
        # Clear existing encodings
        student['encodings'] = []
        
        # Use only the first photo (sorted by filename)
        if student['photos']:
            # Sort photos by filename and take the first one
            sorted_photos = sorted(student['photos'])
            first_photo = sorted_photos[0]
            photo_path = os.path.join(class_faces_dir, first_photo)
            
            if not os.path.exists(photo_path):
                continue
                
            try:
                # Load the image
                image = face_recognition.load_image_file(photo_path)
                
                # Find face locations
                face_locations = face_recognition.face_locations(image)
                
                if not face_locations:
                    continue
                
                # Get face encodings
                face_encodings = face_recognition.face_encodings(image, face_locations)
                
                if face_encodings:
                    # Add only the first encoding to student data
                    student['encodings'] = [face_encodings[0].tolist()]
                    
            except Exception as e:
                print(f"Error processing {photo_path}: {e}")
                continue
    
    # Save updated class data
    class_data['updated_at'] = datetime.now().isoformat()
    save_class(class_data)
    
    return True, f"🔧 Encodings generated for class '{class_name}' (using first photo only)"

# Attendance Management
def recognize_faces_in_image(class_name, image_path, tolerance=0.5, margin=0.02):
    """
    Recognize faces in a group image and mark attendance.

    Args:
        class_name (str): Class identifier
        image_path (str): Path to uploaded group image
        tolerance (float): Distance threshold for recognition (lower = stricter)
        margin (float): Difference required between best and second-best match
    """
    class_data = get_class(class_name)
    if not class_data:
        return {"error": "Class not found"}

    # load all students encodings
    students_encodings = {}
    for student in class_data['students']:
        encs = [np.array(e) for e in student.get("encodings", [])]
        if encs:
            students_encodings[student['student_id']] = {
                "name": student['name'],
                "encodings": encs
            }

    # load group image
    try:
        group_image = face_recognition.load_image_file(image_path)
    except Exception as e:
        return {"error": f"Error loading image: {e}"}

    face_locations = face_recognition.face_locations(group_image)
    face_encodings = face_recognition.face_encodings(group_image, face_locations)

    recognized_faces, unknown_faces = [], []

    for i, face_encoding in enumerate(face_encodings):
        results = []

        # compare with each student
        for sid, data in students_encodings.items():
            dists = face_recognition.face_distance(data["encodings"], face_encoding)
            if len(dists) > 0:
                min_d = float(np.min(dists))
                results.append((sid, data["name"], min_d))

        if results:
            results.sort(key=lambda x: x[2])  # sort by distance (lower is better)
            best_sid, best_name, best_dist = results[0]
            second_dist = results[1][2] if len(results) > 1 else 1.0

            # ✅ margin + tolerance check
            if best_dist <= tolerance and (second_dist - best_dist) >= margin:
                confidence = max(0, (1 - best_dist / 0.6) * 100)
                recognized_faces.append({
                    "location": face_locations[i],
                    "student_id": best_sid,
                    "name": best_name,
                    "distance": round(best_dist, 3),
                    "confidence": round(confidence, 1)
                })
            else:
                unknown_faces.append({"location": face_locations[i]})
        else:
            unknown_faces.append({"location": face_locations[i]})

    # annotated image banani
    pil_image = Image.fromarray(group_image)
    draw = ImageDraw.Draw(pil_image)

    # recognized (green box + name)
    for face in recognized_faces:
        top, right, bottom, left = face['location']
        draw.rectangle(((left, top), (right, bottom)), outline=(0, 255, 0), width=3)
        label = f"{face['name']} ({face['confidence']}%)"
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except IOError:
            font = ImageFont.load_default()
        try:
            bbox = draw.textbbox((0, 0), label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            tw, th = draw.textsize(label, font=font)
        draw.rectangle(((left, bottom - th - 10), (left + tw + 10, bottom)), fill=(0, 255, 0))
        draw.text((left + 5, bottom - th - 5), label, fill=(0, 0, 0), font=font)

    # unknown (red box)
    for face in unknown_faces:
        top, right, bottom, left = face['location']
        draw.rectangle(((left, top), (right, bottom)), outline=(255, 0, 0), width=3)

    # save annotated image
    annotated_dir = os.path.join("static", "annotated")
    os.makedirs(annotated_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    annotated_filename = f"{class_name}_{ts}.jpg"
    annotated_path = os.path.join(annotated_dir, annotated_filename)
    pil_image.save(annotated_path)

    # attendance status
    student_status = []
    for student in class_data['students']:
        status = "absent"
        for rf in recognized_faces:
            if rf["student_id"] == student["student_id"]:
                status = "present"
                break
        student_status.append({
            "student_id": student["student_id"],
            "name": student["name"],
            "status": status
        })

    # Calculate recognition rate
    recognition_rate = (len(recognized_faces) / len(class_data['students'])) * 100 if class_data['students'] else 0

    return {
        "class_name": class_name,
        "total_students": len(class_data["students"]),
        "recognized_count": len(recognized_faces),
        "unknown_count": len(unknown_faces),
        "student_status": student_status,
        "annotated_image": f"annotated/{annotated_filename}",
        "recognition_rate": recognition_rate
    }

@app.route('/class/<class_name>/delete', methods=['POST'])
def delete_class_route(class_name):
    success, message = delete_class(class_name)
    if success:
        flash(f"🗑️ {message}", "success")
    else:
        flash(f"❌ {message}", "error")
    return redirect(url_for("add_data"))

def save_attendance(class_name, attendance_data, timestamp, present_count):
    class_data = get_class(class_name)
    if not class_data:
        return False, "Class not found"
    
    safe_class_name = class_data['safe_name']
    attendance_dir = os.path.join(ATTENDANCE_DATA_FOLDER, safe_class_name)
    os.makedirs(attendance_dir, exist_ok=True)
    
    # Create filename with timestamp
    date_str = timestamp.strftime("%Y%m%d")
    time_str = timestamp.strftime("%H%M%S")
    filename = f"attendance_{safe_class_name}_{date_str}_{time_str}.csv"
    filepath = os.path.join(attendance_dir, filename)
    
    # Prepare CSV data
    csv_data = []
    total_students = len(class_data['students'])
    absent_count = total_students - present_count
    
    # Header
    csv_data.append(["Class Attendance Report"])
    csv_data.append([f"Class: {class_name}"])
    csv_data.append([f"Date: {timestamp.strftime('%Y-%m-%d')}"])
    csv_data.append([f"Time: {timestamp.strftime('%H:%M:%S')}"])
    csv_data.append([f"Total Students: {total_students}"])
    csv_data.append([f"Present: {present_count}"])
    csv_data.append([f"Absent: {absent_count}"])
    csv_data.append([])
    csv_data.append(["Student ID", "Name", "Status"])
    
    # Add student attendance
    for student in class_data['students']:
        status = "absent"
        for att in attendance_data:
            if att['student_id'] == student['student_id']:
                status = att['status']
                break
        
        csv_data.append([student['student_id'], student['name'], status])
    
    # Write CSV file
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(csv_data)
    
    return True, f"✅ Attendance saved successfully for {class_name}"

def get_attendance_history(class_name):
    class_data = get_class(class_name)
    if not class_data:
        return []
    
    safe_class_name = class_data['safe_name']
    attendance_dir = os.path.join(ATTENDANCE_DATA_FOLDER, safe_class_name)
    
    if not os.path.exists(attendance_dir):
        return []
    
    attendance_files = []
    for filename in os.listdir(attendance_dir):
        if filename.startswith('attendance_') and filename.endswith('.csv'):
            # Extract date and time from filename
            parts = filename.split('_')
            if len(parts) >= 4:
                date_str = parts[2]
                time_str = parts[3].split('.')[0]
                
                try:
                    date = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
                    time = datetime.strptime(time_str, "%H%M%S").strftime("%H:%M:%S")
                    
                    attendance_files.append({
                        'filename': filename,
                        'date': date,
                        'time': time,
                        'class_name': class_name
                    })
                except ValueError:
                    continue
    
    # Sort by date and time (newest first)
    attendance_files.sort(key=lambda x: (x['date'], x['time']), reverse=True)
    return attendance_files

# NEW API ROUTES
@app.route('/api/attendance-stats/<class_name>')
def attendance_stats(class_name):
    """API endpoint for chart data"""
    attendance_files = get_attendance_history(class_name)
    
    # Sample data - replace with actual calculation
    data = {
        'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
        'datasets': [{
            'label': 'Attendance Rate',
            'data': [85, 82, 88, 92],
            'borderColor': '#10b981',
            'backgroundColor': 'rgba(16, 185, 129, 0.1)'
        }]
    }
    
    return jsonify(data)

@app.route('/api/class-overview')
def class_overview():
    """API endpoint for dashboard overview"""
    classes = get_all_classes()
    
    # Calculate actual statistics
    total_students = 0
    for class_name in classes:
        class_data = get_class(class_name)
        if class_data:
            total_students += len(class_data.get('students', []))
    
    overview = {
        'total_classes': len(classes),
        'total_students': total_students,
        'attendance_rate': 89  # Calculate actual rate
    }
    
    return jsonify(overview)

# Flask Routes - UPDATED INDEX ROUTE
@app.route('/')
def index():
    # NEW: Calculate dynamic stats
    classes = get_all_classes()
    active_classes = len(classes)
    
    # Calculate total students across all classes
    total_students_all = 0
    for class_name in classes:
        class_data = get_class(class_name)
        if class_data:
            total_students_all += len(class_data.get('students', []))
    
    # Get today's attendance summary
    try:
        today_present, today_total = get_today_summary()
        # Calculate attendance rate
        attendance_rate = round((today_present / today_total * 100), 1) if today_total > 0 else 0
    except:
        today_present, today_total = 0, 0
        attendance_rate = 0
    
    # Get performance data
    try:
        today_perc, performance_status, performance_change = get_performance()
    except:
        performance_status = "Improved"
        performance_change = 0
    
    # Prepare stats for template
    stats = {
        'active_classes': active_classes,
        'total_students': total_students_all,
        'today_present': today_present,
        'today_total': today_total,
        'attendance_rate': attendance_rate,
        'performance_status': performance_status,
        'performance_change': performance_change
    }
    
    return render_template('index.html', stats=stats)

@app.route('/add_data')
def add_data():
    classes = get_all_classes()
    return render_template('add_class.html', classes=classes)

@app.route('/create_class', methods=['POST'])
def create_class_route():
    class_name = request.form.get('class_name')
    total_students = request.form.get('total_students', 0, type=int)
    
    if not class_name:
        flash('🎯 Class name is required to get started', 'warning')
        return redirect(url_for('add_data'))
    
    success, message = create_class(class_name, total_students)
    
    if success:
        flash(f'🎉 {message}', 'success')
        return redirect(url_for('class_detail', class_name=class_name))
    else:
        flash(f'⚠️ {message}', 'error')
        return redirect(url_for('add_data'))

@app.route('/class/<class_name>')
def class_detail(class_name):
    class_data = get_class(class_name)
    if not class_data:
        flash('❌ Class not found', 'error')
        return redirect(url_for('add_data'))
    
    # Calculate how many empty rows to show (at least 5)
    empty_rows = max(5, 10 - len(class_data['students']))
    
    return render_template('class_detail.html', 
                         class_name=class_name, 
                         class_data=class_data,
                         empty_rows=empty_rows)

@app.route('/class/<class_name>/add_students', methods=['POST'])
def add_students_route(class_name):
    # -------------------------------
    # 1️⃣ Collect text inputs (FIXED)
    # -------------------------------
    students_data = []
    
    # Collect all form fields systematically
    for key in request.form:
        if not key.startswith('student_'):
            continue
            
        parts = key.split('_')
        if len(parts) < 3:
            continue
            
        try:
            idx = int(parts[1])
            field = parts[2]
        except (ValueError, IndexError):
            continue

        # Ensure list is large enough
        while len(students_data) <= idx:
            students_data.append({'student_id': '', 'name': ''})

        if field == 'id':
            students_data[idx]['student_id'] = request.form.get(key, '').strip()
        elif field == 'name':
            students_data[idx]['name'] = request.form.get(key, '').strip()

    logger.info(f"Collected student info: {students_data}")

    # -------------------------------
    # 2️⃣ Collect uploaded files (FIXED)
    # -------------------------------
    photo_files = {}
    for file_key in request.files:
        if not file_key.startswith('student_') or not file_key.endswith('_photos'):
            continue
            
        parts = file_key.split('_')
        if len(parts) < 3:
            continue
            
        try:
            idx = int(parts[1])
        except ValueError:
            continue

        files = request.files.getlist(file_key)
        valid_files = [f for f in files if f and f.filename and allowed_file(f.filename)]
        if valid_files:
            photo_files[idx] = valid_files
            logger.info(f"Files received for row {idx}: {[f.filename for f in valid_files]}")

    # -------------------------------
    # 3️⃣ Clean student data (FIXED)
    # -------------------------------
    cleaned_students = []
    for i, s in enumerate(students_data):
        sid = s.get('student_id', '').strip()
        sname = s.get('name', '').strip()
        
        # Only add if both fields are filled
        if sid and sname:
            cleaned_students.append({'student_id': sid, 'name': sname})
        elif sid or sname:  # Only one field filled
            flash(f"⚠️ Row {i+1}: Both Student ID and Name are required. Skipping.", 'warning')

    # -------------------------------
    # 4️⃣ Add students to JSON (FIXED)
    # -------------------------------
    if cleaned_students:
        success, message = add_students(class_name, cleaned_students)
        logger.info(f"add_students result: {success}, {message}")
        
        if not success:
            flash(f'❌ {message}', 'error')
            return redirect(url_for('class_detail', class_name=class_name))
    else:
        flash("ℹ️ No valid student data to add.", 'info')
        return redirect(url_for('class_detail', class_name=class_name))

    # -------------------------------
    # 5️⃣ Process photos for each student (FIXED)
    # -------------------------------
    photos_processed = 0
    for idx, files in photo_files.items():
        if idx < len(students_data):
            student_entry = students_data[idx]
            student_id = student_entry.get('student_id', '').strip()
            
            if not student_id:
                flash(f"⚠️ Photo provided for row {idx+1} but Student ID missing. Photo skipped.", 'warning')
                continue

            # Check if student exists in class
            class_data = get_class(class_name)
            student_exists = any(s['student_id'] == student_id for s in class_data.get('students', []))
            
            if not student_exists:
                flash(f"⚠️ Student {student_id} not found in class. Please add student first.", 'warning')
                continue

            # Process and add photos
            success_photo, msg_photo = add_student_photo(class_name, student_id, files)
            logger.info(f"add_student_photo for {student_id}: {success_photo}, {msg_photo}")

            if success_photo:
                photos_processed += 1
            else:
                flash(f"⚠️ {msg_photo} for {student_id}", 'warning')
        else:
            flash(f"⚠️ Photo provided for invalid row {idx+1}. Skipping.", 'warning')

    # -------------------------------
    # 6️⃣ Final flash and redirect
    # -------------------------------
    if photos_processed > 0:
        flash(f'✅ Students added successfully and {photos_processed} photo(s) processed!', 'success')
    else:
        flash(f'✅ Students added successfully!', 'success')

    return redirect(url_for('class_detail', class_name=class_name))


# New route to generate encodings for a class
@app.route('/class/<class_name>/generate_encodings')
def generate_encodings_route(class_name):
    success, message = generate_class_encodings(class_name)
    if success:
        flash(f'✅ {message}', 'success')
    else:
        flash(f'❌ {message}', 'error')
    
    return redirect(url_for('class_detail', class_name=class_name))

# Route to delete a student
@app.route('/class/<class_name>/delete_student/<student_id>', methods=['POST'])
def delete_student_route(class_name, student_id):
    success, message = delete_student(class_name, student_id)
    if success:
        flash(f'✅ {message}', 'success')
        # optional: regenerate encodings for class
        try:
            generate_class_encodings(class_name)
        except Exception as e:
            logger.warning(f"Re-encoding failed: {e}")
    else:
        flash(f'❌ {message}', 'error')

    return redirect(url_for('class_detail', class_name=class_name))

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if request.method == 'POST':
        class_name = request.form.get('class_name')
        if not class_name:
            flash("🎯 Please select a class", "error")
            return redirect(url_for("attendance"))

        return redirect(url_for("take_attendance", class_name=class_name))

    classes = get_all_classes()
    return render_template('attendance_upload.html', classes=classes)

@app.route('/attendance/<class_name>', methods=['GET', 'POST'])
def take_attendance(class_name):
    if request.method == 'POST':
        file = request.files.get('group_photo')
        if not file or not allowed_file(file.filename):
            flash('📸 Please upload a valid image file', 'error')
            return redirect(url_for('attendance'))

        # Generate unique filename
        import uuid
        from datetime import datetime

        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"group_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)

        # Recognize faces in the image
        result = recognize_faces_in_image(class_name, filepath)
        
        if 'error' in result:
            flash(f'❌ Error: {result["error"]}', 'error')
            return redirect(url_for('attendance'))

        # Add success metrics
        recognition_rate = result.get('recognition_rate', 0)
        
        if recognition_rate > 80:
            flash_message = f"🎯 Excellent! {recognition_rate:.1f}% recognition rate"
        elif recognition_rate > 60:
            flash_message = f"👍 Good detection! {recognition_rate:.1f}% recognized"
        else:
            flash_message = f"🔍 Low recognition. Please check photo quality"
        
        flash(flash_message, 'info')

        # Render result page
        return render_template(
            "attendance_result.html",
            class_name=class_name,
            result=result
        )
    
    # GET request - show upload page
    return render_template("attendance_upload.html", class_name=class_name)

# UPDATED SAVE ATTENDANCE ROUTE WITH STATS LOGGING
@app.route('/attendance/<class_name>/save', methods=['POST'])
def save_attendance_route(class_name):
    attendance_data = []
    present_count = 0
    
    for key in request.form:
        if key.startswith('status_'):
            student_id = key.split('_')[1]
            status = request.form.get(key)
            attendance_data.append({
                'student_id': student_id,
                'status': status
            })
            if status == 'present':
                present_count += 1
    
    # NEW: Log attendance for stats
    class_data = get_class(class_name)
    if class_data:
        total_students = len(class_data.get('students', []))
        log_attendance(class_name, total_students, present_count)
    
    # Save attendance to CSV
    timestamp = datetime.now()
    success, message = save_attendance(class_name, attendance_data, timestamp, present_count)
    
    if success:
        flash(f'✅ {message}', 'success')
        return redirect(url_for('attendance_history', class_name=class_name))
    else:
        flash(f'❌ {message}', 'error')
        return redirect(url_for('take_attendance', class_name=class_name))

@app.route('/attendance/<class_name>/history')
def attendance_history(class_name):
    attendance_files = get_attendance_history(class_name)
    return render_template('attendance_history.html', 
                         class_name=class_name,
                         attendance_files=attendance_files)

@app.route('/download_attendance/<class_name>/<filename>')
def download_attendance(class_name, filename):
    safe_class_name = get_safe_name(class_name)
    filepath = os.path.join(ATTENDANCE_DATA_FOLDER, safe_class_name, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        flash('❌ File not found', 'error')
        return redirect(url_for('attendance_history', class_name=class_name))

# New route to view attendance table
@app.route('/attendance/<class_name>/view/<filename>')
def view_attendance_table(class_name, filename):
    safe_class_name = get_safe_name(class_name)
    filepath = os.path.join(ATTENDANCE_DATA_FOLDER, safe_class_name, filename)

    table_data = []
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            table_data = list(reader)

    return render_template('attendance_history.html',
                           class_name=class_name,
                           attendance_files=get_attendance_history(class_name),
                           table_data=table_data,
                           selected_file=filename)

@app.context_processor
def utility_processor():
    def get_class_data(class_name):
        return get_class(class_name)
    return dict(get_class_data=get_class_data)

# Add this route to your app.py
@app.route('/class_report/<class_name>')
def class_report(class_name):
    # Get class data
    class_data = get_class(class_name)
    if not class_data:
        flash("❌ Class not found", "error")
        return redirect(url_for("add_data"))
    
    # Get attendance files for this class
    safe_class_name = class_data['safe_name']
    attendance_dir = os.path.join(ATTENDANCE_DATA_FOLDER, safe_class_name)
    
    if not os.path.exists(attendance_dir):
        flash("ℹ️ No attendance records found for this class.", "warning")
        return redirect(url_for("class_detail", class_name=class_name))
    
    # Initialize student summary
    students_summary = {}
    total_classes = 0
    
    # Process each attendance file
    for filename in os.listdir(attendance_dir):
        if filename.startswith('attendance_') and filename.endswith('.csv'):
            total_classes += 1
            filepath = os.path.join(attendance_dir, filename)
            
            # Extract date from filename
            parts = filename.split('_')
            if len(parts) >= 4:
                date_str = parts[2]  # Date is in YYYYMMDD format
                try:
                    date_obj = datetime.strptime(date_str, "%Y%m%d")
                    formatted_date = date_obj.strftime("%Y-%m-%d")
                except:
                    formatted_date = date_str
            else:
                formatted_date = "Unknown Date"
            
            # Read CSV file
            with open(filepath, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
                
                # Skip header rows (first 8 rows)
                if len(rows) > 8:
                    for row in rows[8:]:
                        if len(row) >= 3:
                            student_id = row[0]
                            name = row[1]
                            status = row[2].lower()
                            
                            # Initialize student if not exists
                            if student_id not in students_summary:
                                students_summary[student_id] = {
                                    'id': student_id,
                                    'name': name,
                                    'present_days': 0,
                                    'absent_days': 0,
                                    'absent_dates': []
                                }
                            
                            # Update counts
                            if status == 'present':
                                students_summary[student_id]['present_days'] += 1
                            else:
                                students_summary[student_id]['absent_days'] += 1
                                students_summary[student_id]['absent_dates'].append(formatted_date)
    
    # Calculate percentage for each student
    for student in students_summary.values():
        student['total_classes'] = total_classes
        student['attendance_percentage'] = (
            (student['present_days'] / total_classes) * 100 if total_classes > 0 else 0
        )
    
    return render_template(
        "class_report.html",
        class_name=class_name,
        students=list(students_summary.values()),  # <-- convert dict to list and name it 'students'
        total_classes=total_classes
    )

@app.route('/known_faces/<path:filename>')
def known_faces(filename):
    # Base folder where all class folders are stored
    base_dir = os.path.join(app.root_path, 'known_faces')  # change 'known_faces' if your folder is named differently

    # Safely serve the requested file
    return send_from_directory(base_dir, filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)