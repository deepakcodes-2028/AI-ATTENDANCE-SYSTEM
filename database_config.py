import os
import mysql.connector
from mysql.connector import Error
import sqlite3

# Redundant definition removed below to avoid conflicts

class SQLiteCursorWrapper:
    def __init__(self, conn, dictionary=False):
        self.conn = conn
        self.cursor = conn.cursor()
        self.dictionary = dictionary
        
    def execute(self, query, params=None):
        
        query = query.replace('%s', '?')

        if 'ON DUPLICATE KEY UPDATE face_encoding' in query:
            query = "INSERT OR REPLACE INTO Face_Data (student_id, face_encoding) VALUES (?, ?)"
            if params and len(params) == 3:
                params = (params[0], params[1])
                
        if params is None:
            self.cursor.execute(query)
        else:
            self.cursor.execute(query, params)
            
    def fetchone(self):
        row = self.cursor.fetchone()
        if not row: return None
        if self.dictionary: return dict(row)
        return row
        
    def fetchall(self):
        rows = self.cursor.fetchall()
        if self.dictionary: return [dict(r) for r in rows]
        return rows
        
    @property
    def lastrowid(self):
        return self.cursor.lastrowid
        
    def close(self):
        self.cursor.close()

class SQLiteConnWrapper:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
    def is_connected(self):
        return True
        
    def cursor(self, dictionary=False):
        return SQLiteCursorWrapper(self.conn, dictionary)
        
    def commit(self):
        self.conn.commit()
        
    def rollback(self):
        self.conn.rollback()
        
    def close(self):
        self.conn.close()

def setup_sqlite_schema(conn):
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS Faculty (
                faculty_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Student (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                student_id TEXT UNIQUE NOT NULL,
                email TEXT,
                phone TEXT,
                course TEXT,
                face_image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # Ensure Class_Session and Enrollment tables are created
    c.execute('''CREATE TABLE IF NOT EXISTS Course (
                course_id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_name TEXT NOT NULL,
                faculty_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Class_Session (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER,
                date TEXT NOT NULL,
                time_slot TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Enrollment (
                student_id TEXT NOT NULL,
                course_id INTEGER,
                PRIMARY KEY (student_id, course_id))''')
    
    # Simple Subject-wise Attendance table
    c.execute('''CREATE TABLE IF NOT EXISTS Attendance (
                attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                course_id INTEGER NOT NULL,
                date DATE NOT NULL,
                time TEXT,
                status TEXT DEFAULT 'Present',
                UNIQUE(student_id, course_id, date))''')

    # Migration: Check if session_id exists in Attendance, if not add it
    c.execute("PRAGMA table_info(Attendance)")
    columns = [col[1] for col in c.fetchall()]
    if columns and 'session_id' not in columns:
        print("Migrating Attendance table: Adding session_id column")
        try:
            c.execute("ALTER TABLE Attendance ADD COLUMN session_id INTEGER")
        except:
            pass

    c.execute('''CREATE TABLE IF NOT EXISTS Face_Data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL UNIQUE,
                face_encoding TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    c.execute("SELECT * FROM Faculty WHERE email='admin@school.edu'")
    if not c.fetchone():
        c.execute("INSERT INTO Faculty (name, email, password) VALUES ('Admin Faculty', 'admin@school.edu', 'admin123')")
    
    conn.commit()

USE_SQLITE_FALLBACK = True # Set to True to ensure app runs even if MySQL is not started

def setup_mysql_tables(cursor):
    """Initializes MySQL tables if they don't exist"""
    cursor.execute('''CREATE TABLE IF NOT EXISTS Faculty (
                faculty_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS Student (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                student_id VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100),
                phone VARCHAR(20),
                course VARCHAR(100),
                face_image_path VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Course (
                course_id INT AUTO_INCREMENT PRIMARY KEY,
                course_name VARCHAR(100) NOT NULL,
                faculty_id INT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Attendance (
                attendance_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(50) NOT NULL,
                course_id INT NOT NULL,
                date DATE NOT NULL,
                time TIME,
                status VARCHAR(20) DEFAULT 'Present',
                UNIQUE KEY unique_att (student_id, course_id, date))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Face_Data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(50) NOT NULL UNIQUE,
                face_encoding LONGTEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Enrollment (
                student_id VARCHAR(50) NOT NULL,
                course_id INT NOT NULL,
                PRIMARY KEY (student_id, course_id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Class_Session (
                session_id INT AUTO_INCREMENT PRIMARY KEY,
                course_id INT,
                date DATE NOT NULL,
                time_slot VARCHAR(50) NOT NULL)''')

    # Create default admin if not exists
    cursor.execute("SELECT * FROM Faculty WHERE email='admin@school.edu'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO Faculty (name, email, password) VALUES ('Admin Faculty', 'admin@school.edu', 'admin123')")

def get_db_connection():
    # 1. Try MySQL first
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='Admin@1234',  # <-- IMPORTANT: Change this to your MySQL password!
            auth_plugin='mysql_native_password'
        )
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS ai_attendance_db")
            cursor.execute("USE ai_attendance_db")
            setup_mysql_tables(cursor)
            connection.commit()
            cursor.close()
            return connection
    except Error as e:
        print(f"MySQL Connection failed: {e}")
        print("TIP: Ensure MySQL Server is running and password 'Admin@1234' is correct.")

    # 2. Fallback to SQLite if MySQL fails (Guaranteeing 100% Uptime)
    if USE_SQLITE_FALLBACK:
        print("Using SQLite Fallback...")
        db_path = os.path.join(os.path.dirname(__file__), 'database', 'ai_attendance.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = SQLiteConnWrapper(db_path)
        setup_sqlite_schema(conn)
        return conn
        
    return None