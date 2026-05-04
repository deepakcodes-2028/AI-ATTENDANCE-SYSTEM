import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import date, datetime
from database_config import get_db_connection
from modules.camera_module import process_frame_for_recognition, capture_face_from_base64
from modules.face_recognition_module import register_face_encoding

app = Flask(__name__)
app.secret_key = 'ai_attendance_secret_key_2024'

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'faculty_id' in session:
        return redirect(url_for('dashboard'))
    
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM Faculty WHERE email=%s AND password=%s", (email, password))
            faculty = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if faculty:
                session['faculty_id'] = faculty['faculty_id']
                session['faculty_name'] = faculty['name']
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid email or password.'
        else:
            error = 'Database connection failed.'
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'faculty_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    stats = {'students': 0, 'courses': 0, 'today_attendance': 0, 'registered_faces': 0}
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Student")
        stats['students'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Course")
        stats['courses'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Attendance WHERE date=%s", (date.today(),))
        stats['today_attendance'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Face_Data")
        stats['registered_faces'] = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
    
    return render_template('dashboard.html', stats=stats, faculty_name=session.get('faculty_name'))

@app.route('/students')
@login_required
def students():
    conn = get_db_connection()
    students_list = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.*, 
                CASE WHEN fd.student_id IS NOT NULL THEN 1 ELSE 0 END AS has_face
            FROM Student s
            LEFT JOIN Face_Data fd ON s.student_id = fd.student_id
            ORDER BY s.id DESC
        """)
        students_list = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template('students.html', students=students_list, faculty_name=session.get('faculty_name'))

@app.route('/students/add', methods=['POST'])
@login_required
def add_student():
    data = request.json or request.form
    name = data.get('name', '').strip()
    student_id = data.get('student_id', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    course = data.get('course', '').strip()
    image_data = data.get('image_data', '')
    
    if not all([name, student_id, email, phone, course, image_data]):
        return jsonify({'success': False, 'message': 'All fields and face photo are required.'})

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'DB error.'})
        
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Student WHERE student_id=%s", (student_id,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Student ID already exists!'})

    import os, base64
    image_dir = os.path.join(app.root_path, 'static', 'images', 'students')
    os.makedirs(image_dir, exist_ok=True)
    filename = f"{student_id}.jpg"
    filepath = os.path.join(image_dir, filename)
    
    try:
        header, encoded = image_data.split(',', 1)
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(encoded))
    except Exception as e:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Failed to save image.'})
        
    relative_path = f"images/students/{filename}"
    
    try:
        cursor.execute(
            "INSERT INTO Student (name, student_id, email, phone, course, face_image_path) VALUES (%s, %s, %s, %s, %s, %s)",
            (name, student_id, email, phone, course, relative_path)
        )
        conn.commit()
    except Exception as e:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': str(e)})

    from modules.face_recognition_module import register_face_encoding
    from modules.camera_module import capture_face_from_base64
    
    frame = capture_face_from_base64(image_data)
    if frame is not None:
        
        success, msg = register_face_encoding(student_id, frame)
        if not success:
            
            cursor.execute("DELETE FROM Student WHERE student_id=%s", (student_id,))
            conn.commit()
            cursor.close()
            conn.close()
            try: os.remove(filepath) 
            except: pass
            return jsonify({'success': False, 'message': f'Face Error: {msg}'})
            
    cursor.close()
    conn.close()
    return jsonify({'success': True, 'message': f'Student "{name}" added and face trained.'})

@app.route('/students/delete/<string:sid>', methods=['POST'])
@login_required
def delete_student(sid):
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False})
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM Face_Data WHERE student_id=%s", (sid,))
    cursor.execute("DELETE FROM Student WHERE student_id=%s", (sid,))
    conn.commit()
    cursor.close()
    conn.close()

    import os
    try:
        path = os.path.join(app.root_path, 'static', 'images', 'students', f"{sid}.jpg")
        if os.path.exists(path):
            os.remove(path)
    except:
        pass
        
    return jsonify({'success': True})

@app.route('/register-face', methods=['POST'])
@login_required
def register_face():
    data = request.json
    student_id = data.get('student_id')
    image_data = data.get('image')
    
    if not student_id or not image_data:
        return jsonify({'success': False, 'message': 'Missing data.'})
    
    frame = capture_face_from_base64(image_data)
    if frame is None:
        return jsonify({'success': False, 'message': 'Failed to decode image.'})
    
    success, message = register_face_encoding(student_id, frame)
    return jsonify({'success': success, 'message': message})

@app.route('/attendance')
@login_required
def attendance():
    conn = get_db_connection()
    courses = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Course")
        courses = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template('attendance.html', courses=courses, faculty_name=session.get('faculty_name'))

@app.route('/attendance/recognize', methods=['POST'])
@login_required
def recognize():
    data = request.json
    image_data = data.get('image')
    course_id = data.get('course_id')
    
    if not image_data:
        return jsonify({'success': False, 'message': 'No image provided.'})
    
    recognized_ids, face_locations = process_frame_for_recognition(image_data)
    
    if not recognized_ids:
        return jsonify({'success': True, 'recognized': [], 'face_count': len(face_locations)})
    
    marked = []
    conn = get_db_connection()
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        today = date.today()
        now = datetime.now().strftime('%H:%M:%S')
        
        for sid in set(recognized_ids):
            # Check if attendance already marked FOR THIS SPECIFIC COURSE TODAY
            cursor.execute(
                "SELECT attendance_id FROM Attendance WHERE student_id=%s AND course_id=%s AND date=%s",
                (sid, course_id, today)
            )
            existing = cursor.fetchone()
            
            if not existing:
                cursor.execute(
                    "INSERT INTO Attendance (student_id, course_id, date, time, status) VALUES (%s, %s, %s, %s, 'Present')",
                    (sid, course_id, today, now)
                )
                conn.commit()

            cursor.execute("SELECT name FROM Student WHERE student_id=%s", (sid,))
            student = cursor.fetchone()
            if student:
                marked.append({'student_id': sid, 'name': student['name'], 'already_marked': bool(existing)})
        
        cursor.close()
        conn.close()
    
    return jsonify({'success': True, 'recognized': marked, 'face_count': len(face_locations)})

@app.route('/reports')
@login_required
def reports():
    conn = get_db_connection()
    courses = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Course")
        courses = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template('reports.html', courses=courses, faculty_name=session.get('faculty_name'))

@app.route('/reports/data')
@login_required
def reports_data():
    filter_date = request.args.get('date', '')
    course_id = request.args.get('course_id', '')
    student_name = request.args.get('student_name', '')
    
    conn = get_db_connection()
    if not conn:
        return jsonify([])
    
    query = """
        SELECT a.attendance_id, s.student_id, s.name AS student_name,
               s.course, s.email, c.course_name,
               a.date, a.time, a.status
        FROM Attendance a
        JOIN Student s ON a.student_id = s.student_id
        LEFT JOIN Course c ON a.course_id = c.course_id
        WHERE 1=1
    """
    params = []
    
    if filter_date:
        query += " AND a.date = %s"
        params.append(filter_date)
    if course_id:
        query += " AND a.course_id = %s"
        params.append(course_id)
    if student_name:
        query += " AND s.name LIKE %s"
        params.append(f"%{student_name}%")
    
    query += " ORDER BY a.date DESC, a.time DESC"
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    for row in rows:
        row['date'] = str(row['date'])
        row['time'] = str(row['time'])
    
    return jsonify(rows)

@app.route('/api/students')
@login_required
def api_students():
    conn = get_db_connection()
    if not conn:
        return jsonify([])
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT student_id, name, course FROM Student ORDER BY name")
    students = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(students)

@app.route('/courses')
@login_required
def courses():
    conn = get_db_connection()
    course_list = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Course ORDER BY course_id DESC")
        course_list = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template('courses.html', courses=course_list, faculty_name=session.get('faculty_name'))

@app.route('/courses/add', methods=['POST'])
@login_required
def add_course():
    name = request.form.get('course_name', '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Course name is required.'})
    
    conn = get_db_connection()
    if not conn: return jsonify({'success': False, 'message': 'DB Error'})
    
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Course (course_name) VALUES (%s)", (name,))
        conn.commit()
        cursor.close()
        return jsonify({'success': True, 'message': 'Course added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/courses/edit', methods=['POST'])
@login_required
def edit_course():
    cid = request.form.get('course_id')
    name = request.form.get('course_name', '').strip()
    
    if not cid or not name:
        return jsonify({'success': False, 'message': 'Invalid data.'})
    
    conn = get_db_connection()
    if not conn: return jsonify({'success': False, 'message': 'DB Error'})
    
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Course SET course_name = %s WHERE course_id = %s", (name, cid))
        conn.commit()
        cursor.close()
        return jsonify({'success': True, 'message': 'Course updated!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/courses/delete/<int:cid>', methods=['POST'])
@login_required
def delete_course(cid):
    conn = get_db_connection()
    if not conn: return jsonify({'success': False, 'message': 'DB Error'})
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Attendance WHERE course_id = %s", (cid,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Cannot delete: This course is used in attendance records.'})
            
        cursor.execute("DELETE FROM Course WHERE course_id = %s", (cid,))
        conn.commit()
        cursor.close()
        return jsonify({'success': True, 'message': 'Course deleted.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(debug=True, port=5000)
    