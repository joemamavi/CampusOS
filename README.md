# 🎓 CampusOS

**The Operating System for Your Academic Life.**

CampusOS is a smart, Flask-based student productivity dashboard designed to go beyond simple to-do lists. It actively manages your attendance risk, optimizes your schedule, prioritizes tasks using the Eisenhower Matrix, and helps you track career achievements—all in one PWA-ready application.

## 🚀 Key Features

### 🧠 Smart Attendance & Forecasting
* **Real-time Tracking:** Visual progress bars for student vs. teacher syllabus coverage.
* **"Safe to Bunk" Calculator:** Tells you exactly how many classes you can miss while maintaining 75% attendance, or warns you when you are in the "Danger Zone".
* **✈️ Holiday Forecaster:** A simulation algorithm that accepts date ranges for planned leaves and predicts which specific subjects will drop below the attendance threshold.

### ⚡ Productivity Tools
* **Prioritization Matrix:** An interactive **Eisenhower Matrix** (Drag & Drop) to categorize tasks into *Do First, Schedule, Delegate,* and *Delete*.
* **Bottleneck Alerts:** Automatically detects "High Pressure" days (3+ deadlines) and displays a warning banner on the dashboard.
* **Gap Finder:** Scans your daily timetable to identify free time slots, suggesting when to fit in productivity tasks.

### 📅 Scheduling & Career
* **Interactive Timetable:** A visual weekly schedule supporting both Theory and Lab slots.
* **Calendar Integration:** A unified view of academic events and assignment deadlines.
* **💼 Career Vault:** A dedicated log for hackathons, projects, and internships to keep your resume data organized.

## 🛠️ Tech Stack

* **Backend:** Python, Flask, SQLAlchemy.
* **Database:** SQLite (Local storage for privacy).
* **Frontend:** HTML5, CSS3 (Bootstrap 5, Custom "Mint Leaf" Theme), JavaScript.
* **PWA:** Service Workers & Manifest for app-like installation.

## ⚙️ Installation & Setup

Follow these steps to run CampusOS locally:

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/yourusername/campusos.git](https://github.com/yourusername/campusos.git)
    cd campusos
    ```

2.  **Create a Virtual Environment (Optional)**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Application**
    ```bash
    python app.py
    ```

5.  **Access the App**
    Open your browser and navigate to: `http://127.0.0.1:5000`

