import os
import sqlite3
import json
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, 'database')
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, 'exam_monitoring.db')


def get_db_connection():
    """
    Establishes and returns a connection to the SQLite database.
    Sets row_factory to sqlite3.Row so query results can be accessed like dictionaries.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initializes SQLite database schema on application startup.
    Creates users, exams, questions, submissions, submission_answers, and proctor_logs tables.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users table (enhanced with Personal, Academic, and Registration Details)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            photo_path TEXT,
            phone TEXT,
            dob TEXT,
            gender TEXT,
            address TEXT,
            student_id TEXT,
            institution TEXT,
            department TEXT,
            semester TEXT,
            cgpa TEXT,
            registration_no TEXT UNIQUE,
            status TEXT DEFAULT 'Verified',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Safe Schema Migrations for existing user table columns
    columns_to_add = [
        ("phone", "TEXT"),
        ("dob", "TEXT"),
        ("gender", "TEXT"),
        ("address", "TEXT"),
        ("student_id", "TEXT"),
        ("institution", "TEXT"),
        ("department", "TEXT"),
        ("semester", "TEXT"),
        ("cgpa", "TEXT"),
        ("registration_no", "TEXT"),
        ("status", "TEXT DEFAULT 'Verified'")
    ]
    cursor.execute("PRAGMA table_info(users)")
    existing_cols = [col['name'] for col in cursor.fetchall()]
    for col_name, col_type in columns_to_add:
        if col_name not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            except Exception as err:
                print(f"Migration column notice ({col_name}): {err}")

    # 2. Exams table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            total_marks INTEGER NOT NULL,
            pass_percentage INTEGER DEFAULT 60,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. Questions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            question_type TEXT DEFAULT 'single',
            options_json TEXT NOT NULL,
            correct_option INTEGER NOT NULL,
            marks INTEGER DEFAULT 1,
            FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE
        )
    ''')

    # 4. Submissions table (exam attempts)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exam_id INTEGER NOT NULL,
            score INTEGER DEFAULT 0,
            total_marks INTEGER DEFAULT 0,
            percentage REAL DEFAULT 0.0,
            status TEXT DEFAULT 'in_progress', -- 'in_progress', 'completed'
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            submitted_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (exam_id) REFERENCES exams (id)
        )
    ''')

    # 5. Submission Answers table (draft answers & flags)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS submission_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_option INTEGER,
            is_flagged INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (submission_id) REFERENCES submissions (id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES questions (id)
        )
    ''')

    # 6. Proctor Logs table (Browser activity logging & OpenCV face detection violations)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proctor_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            violation_type TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (submission_id) REFERENCES submissions (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()

    # Seed sample exams if empty
    cursor.execute("SELECT COUNT(*) FROM exams")
    if cursor.fetchone()[0] == 0:
        seed_sample_exams(conn)

    conn.close()


def seed_sample_exams(conn):
    """Seeds rich sample exams and questions for testing candidate workflow."""
    cursor = conn.cursor()

    # Exam 1: Python & AI Fundamentals
    cursor.execute('''
        INSERT INTO exams (title, description, category, duration_minutes, total_marks, pass_percentage)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        "Python & Artificial Intelligence Basics",
        "Test your foundational knowledge in Python syntax, core data structures, and essential AI/ML concepts.",
        "Computer Science",
        15,
        5,
        60
    ))
    exam1_id = cursor.lastrowid

    q1_options = json.dumps(["dict", "list", "tuple", "set"])
    cursor.execute('''
        INSERT INTO questions (exam_id, question_text, question_type, options_json, correct_option, marks)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (exam1_id, "Which Python data structure is immutable?", "single", q1_options, 2, 1))

    q2_options = json.dumps(["def", "function", "create", "lambda"])
    cursor.execute('''
        INSERT INTO questions (exam_id, question_text, question_type, options_json, correct_option, marks)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (exam1_id, "Which keyword is used to define an anonymous function in Python?", "single", q2_options, 3, 1))

    q3_options = json.dumps(["Supervised Learning", "Unsupervised Learning", "Reinforcement Learning", "Heuristic Search"])
    cursor.execute('''
        INSERT INTO questions (exam_id, question_text, question_type, options_json, correct_option, marks)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (exam1_id, "Which ML paradigm uses labeled datasets to train models?", "single", q3_options, 0, 1))

    q4_options = json.dumps(["NumPy", "Pandas", "Matplotlib", "Scikit-Learn"])
    cursor.execute('''
        INSERT INTO questions (exam_id, question_text, question_type, options_json, correct_option, marks)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (exam1_id, "Which Python library is primarily used for fast N-dimensional array manipulations?", "single", q4_options, 0, 1))

    q5_options = json.dumps(["Activation Function", "Loss Function", "Optimizer", "Hyperparameter"])
    cursor.execute('''
        INSERT INTO questions (exam_id, question_text, question_type, options_json, correct_option, marks)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (exam1_id, "What component in a Neural Network introduces non-linearity to the output?", "single", q5_options, 0, 1))

    # Exam 2: Data Structures & Algorithms
    cursor.execute('''
        INSERT INTO exams (title, description, category, duration_minutes, total_marks, pass_percentage)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        "Data Structures & Algorithms Evaluation",
        "Assessment covering arrays, linked lists, trees, search algorithms, and computational complexity.",
        "Computer Science",
        20,
        4,
        75
    ))
    exam2_id = cursor.lastrowid

    q2_1 = json.dumps(["O(1)", "O(log n)", "O(n)", "O(n^2)"])
    cursor.execute('''
        INSERT INTO questions (exam_id, question_text, question_type, options_json, correct_option, marks)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (exam2_id, "What is the average time complexity of Binary Search on a sorted array of size n?", "single", q2_1, 1, 1))

    q2_2 = json.dumps(["Queue", "Stack", "Heap", "Graph"])
    cursor.execute('''
        INSERT INTO questions (exam_id, question_text, question_type, options_json, correct_option, marks)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (exam2_id, "Which data structure follows the LIFO (Last In First Out) principle?", "single", q2_2, 1, 1))

    q2_3 = json.dumps(["Breadth-First Search (BFS)", "Depth-First Search (DFS)", "Dijkstra's Algorithm", "Kruskal's Algorithm"])
    cursor.execute('''
        INSERT INTO questions (exam_id, question_text, question_type, options_json, correct_option, marks)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (exam2_id, "Which graph traversal technique uses a Queue data structure?", "single", q2_3, 0, 1))

    q2_4 = json.dumps(["Merge Sort", "Quick Sort", "Bubble Sort", "Insertion Sort"])
    cursor.execute('''
        INSERT INTO questions (exam_id, question_text, question_type, options_json, correct_option, marks)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (exam2_id, "Which sorting algorithm guarantees O(n log n) worst-case time complexity?", "single", q2_4, 0, 1))

    # Exam 3: Web Security & Cyber Hygiene
    cursor.execute('''
        INSERT INTO exams (title, description, category, duration_minutes, total_marks, pass_percentage)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        "Web Security Essentials",
        "Covers OWASP Top 10 vulnerabilities, authentication security, HTTPS, and safe proctoring protocols.",
        "Cybersecurity",
        10,
        3,
        66
    ))
    exam3_id = cursor.lastrowid

    q3_1 = json.dumps(["Cross-Site Scripting (XSS)", "SQL Injection (SQLi)", "CSRF", "DDoS"])
    cursor.execute('''
        INSERT INTO questions (exam_id, question_text, question_type, options_json, correct_option, marks)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (exam3_id, "Which vulnerability occurs when unsanitized user input is directly executed in database queries?", "single", q3_1, 1, 1))

    q3_2 = json.dumps(["HTTP", "HTTPS / SSL", "FTP", "TELNET"])
    cursor.execute('''
        INSERT INTO questions (exam_id, question_text, question_type, options_json, correct_option, marks)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (exam3_id, "Which protocol encrypts web communication between browser and server using TLS/SSL?", "single", q3_2, 1, 1))

    q3_3 = json.dumps(["PBKDF2 / bcrypt", "MD5", "Plaintext", "Base64"])
    cursor.execute('''
        INSERT INTO questions (exam_id, question_text, question_type, options_json, correct_option, marks)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (exam3_id, "Which hashing algorithm family is secure for storing user passwords?", "single", q3_3, 0, 1))

    conn.commit()


class User:
    """User Model class responsible for user authentication and candidate registration."""

    @staticmethod
    def create(full_name, email, password, photo_path=None, phone=None, dob=None, gender=None,
               student_id=None, institution=None, department=None, semester=None, cgpa=None, registration_no=None):
        conn = get_db_connection()
        cursor = conn.cursor()
        password_hash = generate_password_hash(password)

        cursor.execute('''
            INSERT INTO users (full_name, email, password_hash, photo_path, phone, dob, gender, 
                               student_id, institution, department, semester, cgpa, registration_no)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (full_name, email, password_hash, photo_path, phone, dob, gender,
              student_id, institution, department, semester, cgpa, registration_no))

        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id

    @staticmethod
    def get_by_email(email):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None

    @staticmethod
    def get_by_id(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None

    @staticmethod
    def verify_password(user, password):
        return check_password_hash(user['password_hash'], password)

    @staticmethod
    def update_profile(user_id, full_name=None, email=None, phone=None, dob=None, gender=None, student_id=None,
                       institution=None, department=None, semester=None, cgpa=None):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Fetch existing user to preserve values if not provided
        existing = User.get_by_id(user_id)
        if not existing:
            conn.close()
            return

        name_to_use = full_name if full_name else existing['full_name']
        email_to_use = email if email else existing['email']

        cursor.execute('''
            UPDATE users
            SET full_name = ?, email = ?, phone = ?, dob = ?, gender = ?, student_id = ?, 
                institution = ?, department = ?, semester = ?, cgpa = ?
            WHERE id = ?
        ''', (name_to_use, email_to_use, phone, dob, gender, student_id, institution, department, semester, cgpa, user_id))
        conn.commit()
        conn.close()

    @staticmethod
    def get_all_users():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]


class Exam:
    """Exam Model class responsible for fetching exam details and associated questions."""

    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM exams ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_by_id(exam_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM exams WHERE id = ?", (exam_id,))
        exam = cursor.fetchone()
        conn.close()
        return dict(exam) if exam else None

    @staticmethod
    def get_questions_by_exam(exam_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM questions WHERE exam_id = ? ORDER BY id ASC", (exam_id,))
        rows = cursor.fetchall()
        conn.close()

        questions = []
        for r in rows:
            q_dict = dict(r)
            q_dict['options'] = json.loads(q_dict['options_json'])
            questions.append(q_dict)
        return questions


class Submission:
    """Submission Model class for managing candidate exam attempts and answers."""

    @staticmethod
    def create_or_get_in_progress(user_id, exam_id):
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM submissions 
            WHERE user_id = ? AND exam_id = ? AND status = 'in_progress'
            ORDER BY id DESC LIMIT 1
        ''', (user_id, exam_id))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            return dict(existing)

        cursor.execute("SELECT total_marks FROM exams WHERE id = ?", (exam_id,))
        exam_row = cursor.fetchone()
        total_marks = exam_row['total_marks'] if exam_row else 0

        cursor.execute('''
            INSERT INTO submissions (user_id, exam_id, total_marks, status, started_at)
            VALUES (?, ?, ?, 'in_progress', CURRENT_TIMESTAMP)
        ''', (user_id, exam_id, total_marks))
        conn.commit()

        submission_id = cursor.lastrowid
        cursor.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,))
        new_sub = cursor.fetchone()
        conn.close()
        return dict(new_sub)

    @staticmethod
    def get_by_id(submission_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,))
        sub = cursor.fetchone()
        conn.close()
        return dict(sub) if sub else None

    @staticmethod
    def get_user_submissions(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.*, e.title as exam_title, e.category as exam_category, 
                   e.duration_minutes, e.pass_percentage
            FROM submissions s
            JOIN exams e ON s.exam_id = e.id
            WHERE s.user_id = ?
            ORDER BY s.id DESC
        ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_all_submissions():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.*, e.title as exam_title, e.category as exam_category, 
                   e.duration_minutes, e.pass_percentage
            FROM submissions s
            JOIN exams e ON s.exam_id = e.id
            ORDER BY s.id DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def save_draft_answer(submission_id, question_id, selected_option, is_flagged=None):
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM submission_answers 
            WHERE submission_id = ? AND question_id = ?
        ''', (submission_id, question_id))
        existing = cursor.fetchone()

        if existing:
            if is_flagged is not None and selected_option is not None:
                cursor.execute('''
                    UPDATE submission_answers 
                    SET selected_option = ?, is_flagged = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE submission_id = ? AND question_id = ?
                ''', (selected_option, is_flagged, submission_id, question_id))
            elif selected_option is not None:
                cursor.execute('''
                    UPDATE submission_answers 
                    SET selected_option = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE submission_id = ? AND question_id = ?
                ''', (selected_option, submission_id, question_id))
            elif is_flagged is not None:
                cursor.execute('''
                    UPDATE submission_answers 
                    SET is_flagged = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE submission_id = ? AND question_id = ?
                ''', (is_flagged, submission_id, question_id))
        else:
            opt = selected_option if selected_option is not None else -1
            flag = is_flagged if is_flagged is not None else 0
            cursor.execute('''
                INSERT INTO submission_answers (submission_id, question_id, selected_option, is_flagged)
                VALUES (?, ?, ?, ?)
            ''', (submission_id, question_id, opt, flag))

        conn.commit()
        conn.close()

    @staticmethod
    def get_submission_answers(submission_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT question_id, selected_option, is_flagged
            FROM submission_answers
            WHERE submission_id = ?
        ''', (submission_id,))
        rows = cursor.fetchall()
        conn.close()

        answers = {}
        for r in rows:
            answers[r['question_id']] = {
                'selected_option': r['selected_option'],
                'is_flagged': bool(r['is_flagged'])
            }
        return answers

    @staticmethod
    def log_violation(submission_id, user_id, violation_type, details=None):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO proctor_logs (submission_id, user_id, violation_type, details)
            VALUES (?, ?, ?, ?)
        ''', (submission_id, user_id, violation_type, details))
        conn.commit()
        conn.close()

    @staticmethod
    def get_violation_count(submission_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM proctor_logs WHERE submission_id = ?", (submission_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    @staticmethod
    def get_proctor_logs(submission_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM proctor_logs 
            WHERE submission_id = ? 
            ORDER BY id ASC
        ''', (submission_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
