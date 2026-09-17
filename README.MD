# 🛡️ WatchDesk — Online Exam Monitoring & Proctoring System

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.org/)
[![OpenCV](https://img.shields.io/badge/Computer_Vision-OpenCV-5C3EE8?style=flat-square&logo=opencv&logoColor=white)](https://opencv.org/)
[![Pandas](https://img.shields.io/badge/Data_Analytics-Pandas-150458?style=flat-square&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Bootstrap](https://img.shields.io/badge/UI-Bootstrap_5-7952B3?style=flat-square&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)

**WatchDesk** is an enterprise-grade, web-based online assessment and automated proctoring platform built using **Python (Flask)**, **OpenCV**, **Pandas**, and **SQLite**. It features live webcam computer vision monitoring, browser security event logging, real-time draft answer autosaving, weighted integrity risk scoring, and interactive candidate performance analytics.

---

## 🌟 Key Features

### 📷 1. OpenCV Live AI Proctoring Engine
- **Webcam Frame Analysis**: Periodically captures and processes webcam frames in memory using base64 decoding and OpenCV Haar Cascade Classifiers (`haarcascade_frontalface_default.xml`).
- **Real-Time Violation Triggers**:
  - `NO_FACE`: Detects when the candidate is absent or looking away from the camera.
  - `MULTIPLE_FACES`: Detects unauthorized secondary persons in the camera frame.
- **Auto-Submission**: Automatically terminates and submits the assessment if a candidate reaches **5 proctoring violations**.

### 🛡️ 2. Browser Security & Anti-Cheating System
- **Tab Switching Detection**: Listens to HTML5 `visibilitychange` events (`document.hidden`).
- **Application Switching Detection**: Traps `window.blur` events (e.g., `Alt + Tab`, split screening, opening external apps).
- **Prohibited Shortcut Blocking**: Disables right-click context menu, text copying/pasting (`copy`, `cut`, `paste`), and developer shortcuts (`F12`, `Ctrl+C`, `Ctrl+V`, `Ctrl+Shift+I`).

### 📊 3. Pandas-Powered Integrity Scoring Engine
- Aggregates session log data into a **Pandas DataFrame** pipeline.
- Calculates weighted security penalties per violation type:
  - 🚨 `MULTIPLE_FACES`: **-30.0 points**
  - ⚠️ `NO_FACE`: **-18.0 points**
  - 🔄 `TAB_SWITCH`: **-12.0 points**
  - 🔲 `FOCUS_LOST`: **-8.0 points**
- Computes **Face Presence Ratio (%)** and classifies session integrity into risk tiers:
  - 🟢 **LOW_RISK** (Score ≥ 85%) — High Academic Integrity
  - 🟡 **MEDIUM_RISK** (Score 60% – 84%) — Moderate Security Alert
  - 🔴 **HIGH_RISK** (Score < 60%) — Flagged for Review

### ⚙️ 4. System Permissions Setup
- Pre-exam hardware and permission check interface before entering the exam room.
- Verifies **Desktop Device Check**, **Webcam Camera Access**, and **Screen & Fullscreen Access**.
- Features a floating live webcam video preview with a real-time status indicator.

### ⏱️ 5. Live Exam Attempt Room & Real-Time Auto-Save
- Countdown exam timer with status warnings.
- Interactive question palette for quick navigation.
- Asynchronous draft answer autosaving via AJAX (`/exam/api/save-draft`).
- Instant automated evaluation and percentage score calculation upon submission.

### 📈 6. Candidate Dashboard & Performance Analytics
- **Overview KPIs**: Total Exams Available, Completed Attempts, Pass Rate %, and Average Score.
- **My Exams Catalog**: Filterable list of available online assessments.
- **Exam History**: Historical scorecard table with **CSV Export** functionality (`/exam/export-history`).
- **Performance Analytics**: Dynamic **Chart.js v4** line charts (Score Trends) and doughnut charts (Category Mastery).

### 📜 7. Assessment Certificate Generator
- Generates downloadable, print-friendly verification certificates for candidates who pass assessments (`/exam/submission/<id>/certificate`).

### 🎨 8. 3-Mode Adaptive Theme System
- Native support for **System**, **Light**, and **Dark** theme modes powered by CSS custom properties and persistent browser `localStorage`.

---

## 🛠️ Technology Stack

| Component | Technology Used |
|---|---|
| **Backend Framework** | Python 3.14, Flask Web Framework, Jinja2 Templates |
| **Computer Vision / AI** | OpenCV (`cv2`) with Haar Cascade Frontal Face Classifier |
| **Data Analytics** | Pandas DataFrames & NumPy |
| **Database** | SQLite3 (`database/exam_monitoring.db`) |
| **Frontend UI** | HTML5, Custom CSS3 Design System, JavaScript (ES6+), Bootstrap 5 |
| **Data Visualization** | Chart.js v4 |
| **Iconography & Fonts** | FontAwesome 6 Pro, Plus Jakarta Sans |

---

## 📁 Project Directory Structure

```
Exam Monitoring/
├── app.py                      # Application server entry point & runner
├── requirements.txt            # Python package dependencies
├── README.MD                   # Project documentation
├── .gitignore                  # Git exclusion rules
├── .vscode/
│   └── settings.json           # VS Code & Pylance diagnostic configuration
├── database/
│   └── exam_monitoring.db      # SQLite relational database
└── app/
    ├── __init__.py             # Flask App Factory, Blueprint registration & Error Handlers
    ├── models.py               # Database ORM model queries (Users, Exams, Submissions, Logs)
    ├── face_detection.py       # OpenCV webcam frame analysis & face count engine
    ├── integrity_scoring.py    # Pandas-Powered Integrity Risk Scoring Engine
    ├── scoring.py              # Automated exam grading & percentage evaluation logic
    ├── routes/
    │   ├── __init__.py
    │   ├── auth.py             # Auth routes (Login, Register, Profile, Student Directory)
    │   ├── exam.py             # Dashboard, System Check, Exam Room, Results & Certificates
    │   └── events.py           # Real-time AJAX APIs (Webcam frames, violations, draft saves)
    ├── static/
    │   ├── css/
    │   │   ├── style.css       # Global design system & theme variables
    │   │   ├── dashboard.css   # Dashboard layout & performance card styling
    │   │   ├── exam.css        # Live exam room interface styling
    │   │   └── system_check.css# System setup & permission check styling
    │   └── js/
    │       ├── main.js         # Theme switcher & global utilities
    │       ├── exam_engine.js  # Timer, autosave, palette & security violation listeners
    │       └── system_check.js # Pre-exam camera, fullscreen & screen check engine
    └── templates/
        ├── base.html           # Master layout template (Navbar, Theme Switcher, Flash Alerts)
        ├── login.html          # Candidate login page
        ├── register.html       # Candidate registration page
        ├── profile.html        # Candidate profile management
        ├── students.html       # Registered student directory
        ├── errors/
        │   ├── 404.html        # Page Not Found error template
        │   ├── 403.html        # Forbidden Access error template
        │   └── 500.html        # Server Error template
        ├── dashboard/
        │   └── dashboard.html  # Candidate Dashboard (Overview, My Exams, History, Results)
        └── exam/
            ├── system_check.html # Pre-exam System Permissions Setup page
            ├── exam_room.html    # Live exam room interface
            ├── result.html       # Scorecard, Integrity Score & Violation audit log
            └── certificate.html  # Assessment completion certificate
```

---

## 💾 Database Schema (`database/exam_monitoring.db`)

1. **`users`**: Candidate user profiles (`id`, `full_name`, `email`, `password_hash`, `photo_path`, `role`, `created_at`).
2. **`exams`**: Assessment catalog (`id`, `title`, `category`, `duration_minutes`, `total_marks`, `pass_percentage`).
3. **`questions`**: Exam question bank (`id`, `exam_id`, `question_text`, `option1`, `option2`, `option3`, `option4`, `correct_option`, `marks`).
4. **`submissions`**: Assessment attempt records (`id`, `user_id`, `exam_id`, `started_at`, `submitted_at`, `score`, `total_marks`, `percentage`, `status`).
5. **`submission_answers`**: Candidate responses per question (`id`, `submission_id`, `question_id`, `selected_option`, `is_flagged`).
6. **`proctor_logs`**: Security violation audit log (`id`, `submission_id`, `user_id`, `violation_type`, `details`, `timestamp`).

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.10 or higher installed.

### 1. Clone the Repository
```bash
git clone https://github.com/Riteshlande75/WatchDeskAI.git
cd "Exam Monitoring"
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python app.py
```

### 4. Access WatchDesk in Browser
Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

---

## 🔒 Security & Violation Policy

| Violation Type | Trigger Condition | Score Penalty | Action |
|---|---|---|---|
| **`MULTIPLE_FACES`** | More than 1 face detected by OpenCV | **-30.0 pts** | Log Incident & Warning Modal |
| **`NO_FACE`** | No face detected in camera stream | **-18.0 pts** | Log Incident & Warning Modal |
| **`TAB_SWITCH`** | Candidate switches tab or minimizes window | **-12.0 pts** | Log Incident & Warning Modal |
| **`FOCUS_LOST`** | Window focus lost (`Alt + Tab` / App switch) | **-8.0 pts** | Log Incident & Warning Modal |
| **`MAX_VIOLATIONS`** | Total violations reach **5 incidents** | **Auto-Submit** | Terminate Exam & Redirect to Result |

---

## 📜 License
This project is licensed under the MIT License.
