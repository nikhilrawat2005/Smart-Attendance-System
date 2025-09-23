import csv
import os
from datetime import date, timedelta

CSV_FILE = "attendance_data/overall_attendance.csv"

def ensure_csv_exists():
    """Make sure CSV exists with header"""
    os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "class_name", "total_students", "present"])

def log_attendance(class_name, total_students, present):
    """Add/Update today's record for a class"""
    ensure_csv_exists()
    today = date.today().isoformat()
    rows = []
    updated = False
    
    # read old data
    with open(CSV_FILE, "r") as f:
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
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date","class_name","total_students","present"])
        writer.writeheader()
        writer.writerows(rows)

def get_today_summary():
    """Return total present/total students + missing classes"""
    ensure_csv_exists()
    today = date.today().isoformat()
    total_students, total_present = 0, 0
    
    with open(CSV_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["date"] == today:
                total_students += int(row["total_students"])
                if row["present"] != "":
                    total_present += int(row["present"])
    
    return total_present, total_students

def get_performance():
    """Compare today's vs yesterday's attendance %"""
    ensure_csv_exists()
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    
    def calc_percentage(day):
        total_s, total_p = 0, 0
        with open(CSV_FILE, "r") as f:
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