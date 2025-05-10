import cv2
import numpy as np
import sqlite3
import re
from pyzbar.pyzbar import decode
from sklearn.ensemble import IsolationForest
from datetime import datetime

# ------------------- DATABASE INITIALIZATION ------------------- #
def init_db():
    conn = sqlite3.connect("qrcodes.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS qr_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_data TEXT UNIQUE,
            roll_no TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_data TEXT,
            roll_no TEXT,
            scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT
        )
    """)

    conn.commit()
    conn.close()

# ------------------- HELPER FUNCTIONS ------------------- #
def extract_name_roll(qr_text):
    """Extracts name and roll number from 'Name - RollNo' format."""
    match = re.match(r"(.+?)\s*-\s*(\d+)$", qr_text)
    if match:
        name = match.group(1).strip()
        roll_no = match.group(2).strip()
        return name, roll_no
    return qr_text, None

def verify_qr(name, roll_no):
    """Checks if the name exists in the qr_codes table and the roll_no matches."""
    conn = sqlite3.connect("qrcodes.db")
    cursor = conn.cursor()
    # Check if the name is in qr_data and roll_no matches
    cursor.execute("SELECT * FROM qr_codes WHERE qr_data = ? AND roll_no = ?", (name, roll_no))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def log_scan(qr_data, roll_no, status):
    """Logs the scan attempt into the database."""
    conn = sqlite3.connect("qrcodes.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO scan_logs (qr_data, roll_no, status) VALUES (?, ?, ?)", (qr_data, roll_no, status))
    conn.commit()
    conn.close()

def get_features(qr_data, scan_time):
    scan_dt = datetime.strptime(scan_time, "%Y-%m-%d %H:%M:%S")
    features = [
        hash(qr_data) % 10000,          # Hashed QR (scaled)
        scan_dt.hour,                   # Hour of the scan
        scan_dt.weekday(),              # Day of the week
    ]
    return features


def train_anomaly_detector():
    conn = sqlite3.connect("qrcodes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT qr_data, scan_time FROM scan_logs WHERE status = 'Present'")
    data = cursor.fetchall()
    conn.close()

    if len(data) > 5:
        feature_vectors = [get_features(qr, scan_time.split('.')[0]) for qr, scan_time in data]
        model = IsolationForest(contamination=0.1, random_state=42)
        model.fit(feature_vectors)
        return model
    return None

# ------------------- QR CODE SCANNER ------------------- #
def scan_qr():
    scanned_qrs = set()  # To keep track of already scanned QR codes
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture image.")
            break

        decoded_objects = decode(frame)
        for obj in decoded_objects:
            qr_text = obj.data.decode('utf-8')

            # Skip scanning if this QR has already been scanned
            if qr_text in scanned_qrs:
                continue  # Skip to the next QR code

            # Extract name and roll_no from qr_text
            name, roll_no = extract_name_roll(qr_text)

            # Verify if the name and roll_no are present in the database
            if verify_qr(name, roll_no):
                status = "Present"
            else:
                status = "Invalid"

            # Log the scan (either "Present" or "Invalid")
            log_scan(qr_text, roll_no, status)

            # Mark the QR code as scanned
            scanned_qrs.add(qr_text)

            # Draw bounding box with status text on the frame
            color = (0, 255, 0) if status == "Present" else (0, 0, 255)
            pts = np.array([tuple(point) for point in obj.polygon], dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], True, color, 3)

            cv2.putText(frame, f"{status}: {name} ({roll_no})", (obj.rect[0], obj.rect[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
            print(f'Scanned: {name} - Roll No: {roll_no} - Status: {status}')

        cv2.imshow("QR Code Scanner", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    init_db()
    scan_qr()
