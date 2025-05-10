import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import subprocess
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# ------------------- DATABASE & ATTENDANCE LOG ------------------- #
def extract_name_from_qr(qr_text):
    """Extracts name from QR data formatted as 'Name - RollNo'."""
    parts = qr_text.split(" - ")
    if len(parts) == 2:
        return parts[0]  # Return only the Name part
    return qr_text  # Return the whole QR data if format is unexpected

def load_attendance_data():
    conn = sqlite3.connect("qrcodes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT qr_data, roll_no, scan_time, status FROM scan_logs ORDER BY scan_time DESC")
    records = cursor.fetchall()
    conn.close()

    tree.delete(*tree.get_children())
    for record in records:
        # Extract the name from qr_data (Assuming format "Name - RollNo")
        name = extract_name_from_qr(record[0])  # record[0] is the QR data (which contains Name - RollNo)
        tree.insert("", tk.END, values=(name, record[1], record[2], record[3]))  # Insert name instead of QR data

def clear_attendance_data():
    confirm = messagebox.askyesno("Confirm", "Are you sure you want to clear all attendance records?")
    if confirm:
        conn = sqlite3.connect("qrcodes.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scan_logs")
        conn.commit()
        conn.close()
        load_attendance_data()
        messagebox.showinfo("Success", "Attendance records cleared successfully.")

def export_attendance_to_excel():
    try:
        conn = sqlite3.connect("qrcodes.db")
        query = "SELECT qr_data, roll_no, scan_time, status FROM scan_logs"
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            messagebox.showinfo("No Data", "No attendance records found to export.")
            return

        df = df.sort_values(by="roll_no", ascending=True)
        file_path = "Attendance_Report.xlsx"
        df.to_excel(file_path, index=False)
        messagebox.showinfo("Export Successful", f"Data exported successfully to '{file_path}'")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to export data.\nError: {e}")

def show_attendance_trends():
    conn = sqlite3.connect("qrcodes.db")
    df = pd.read_sql_query("SELECT * FROM scan_logs", conn)
    conn.close()

    df['scan_time'] = pd.to_datetime(df['scan_time'])
    df['day'] = df['scan_time'].dt.date
    attendance_by_day = df[df["status"] == "Present"].groupby("day").size()

    plt.figure(figsize=(10, 5))
    attendance_by_day.plot(kind="bar", color="#4CAF50")
    plt.title("Attendance Over Days")
    plt.xlabel("Date")
    plt.ylabel("Number of Present Entries")
    plt.tight_layout()
    plt.show()

# ------------------- QR SCANNER FUNCTION ------------------- #
def scan_qr():
    threading.Thread(target=lambda: subprocess.run(["python", "qr_scanner.py"]), daemon=True).start()

# ------------------- GUI DESIGN ------------------- #
root = tk.Tk()
root.title("E-Attendance System")
root.geometry("1150x750")
root.configure(bg="#FAE3B4")

container = tk.Frame(root, bg="#2C2F33", bd=2, relief="ridge")
container.place(x=20, y=20, width=1100, height=700)

header = tk.Label(container, text="E-Attendance System", font=("Arial", 24, "bold"), bg="#2C2F33", fg="white")
header.pack(pady=10)

body_frame = tk.Frame(container, bg="#FAE3B4")
body_frame.pack(fill="both", expand=True, padx=10, pady=10)

# LEFT PANEL
left_panel = tk.Frame(body_frame, width=300, bg="#FAE3B4")
left_panel.pack(side="left", fill="y")

qr_image = Image.open("img/qr_code.png").resize((250, 250), Image.LANCZOS)
qr_photo = ImageTk.PhotoImage(qr_image)
tk.Label(left_panel, image=qr_photo, bg="#FAE3B4").pack(pady=10)

scan_btn = tk.Button(left_panel, text="Scan ID-Card", font=("Arial", 14, "bold"), bg="#2C2F33", fg="white", command=scan_qr)
scan_btn.pack(pady=5, fill="x", padx=20)

refresh_btn = tk.Button(left_panel, text="Refresh", font=("Arial", 14, "bold"), bg="#2C2F33", fg="white", command=load_attendance_data)
refresh_btn.pack(pady=5, fill="x", padx=20)

clear_btn = tk.Button(left_panel, text="Clear Table", font=("Arial", 14, "bold"), bg="#2C2F33", fg="white", command=clear_attendance_data)
clear_btn.pack(pady=5, fill="x", padx=20)

export_btn = tk.Button(left_panel, text="Export to Excel", font=("Arial", 14, "bold"), bg="#2C2F33", fg="white", command=export_attendance_to_excel)
export_btn.pack(pady=5, fill="x", padx=20)

analytics_btn = tk.Button(left_panel, text="Show Analytics", font=("Arial", 14, "bold"), bg="#2C2F33", fg="white", command=show_attendance_trends)
analytics_btn.pack(pady=5, fill="x", padx=20)

# TABLE PANEL
right_panel = tk.Frame(body_frame, bg="#FAE3B4")
right_panel.pack(side="right", fill="both", expand=True)

table_title = tk.Label(right_panel, text="Attendance Records", font=("Arial", 20, "bold"), bg="#FAE3B4", fg="#2C2F33")
table_title.pack(pady=5)

columns = ("QR Data", "Roll No", "Scan Time", "Status")
tree = ttk.Treeview(right_panel, columns=columns, show="headings", height=25)
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, anchor="center")
tree.pack(fill="both", expand=True)

style = ttk.Style()
style.configure("Treeview.Heading", font=("Arial", 12, "bold"), background="#2C2F33", foreground="#2C2F33")
style.configure("Treeview", font=("Arial", 15), rowheight=25)

load_attendance_data()
root.mainloop()
