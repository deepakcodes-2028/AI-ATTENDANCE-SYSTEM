# AI-ATTENDANCE-SYSTEM
This project is an AI-Based Smart Attendance Management System that uses DeepFace for face recognition to automatically mark student attendance. It supports subject-wise attendance tracking, prevents duplicate entries, and stores data securely in a MySQL database. The system is built using Flask for backend and HTML/CSS/JavaScript for frontend.
# AI-Based Smart Attendance Management System 🚀

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![DeepFace](https://img.shields.io/badge/DeepFace-AI-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)

A modern, high-performance attendance management system that leverages **Deep Learning** and **Computer Vision** to automate student attendance through real-time face recognition.

## ✨ Key Features

- 👤 **Face Recognition Attendance:** Automated attendance marking using state-of-the-art face embeddings via **DeepFace**.
- 📊 **Real-time Dashboard:** Track total students, courses, daily attendance, and registered face models at a glance.
- 🎓 **Student Management:** Comprehensive CRUD operations for student profiles, including instant face registration and training.
- 📚 **Course Management:** Subject-wise attendance tracking with easy course administration.
- 📈 **Detailed Reporting:** Filterable attendance reports (by date, course, or name) with real-time data fetching.
- 🔐 **Secure Authentication:** Faculty-only access with session-based security.
- 🎨 **Modern UI/UX:** Sleek, responsive interface built with clean CSS and dynamic JavaScript.

## 🛠️ Technology Stack

| Component | Technology Used |
| :--- | :--- |
| **Backend** | Python, Flask |
| **Database** | MySQL |
| **AI/ML** | DeepFace (VGG-Face, Facenet, etc.), OpenCV |
| **Frontend** | HTML5, CSS3, JavaScript (Fetch API) |
| **Data Processing** | NumPy, Base64 |

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- MySQL Server installed and running
- Webcam (for face registration and recognition)

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/ai-attendance-system.git
cd ai-attendance-system
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
source venv/bin/activate  # On macOS/Linux
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Configuration
1. Open your MySQL client (Workbench or Shell).
2. Execute the schema provided in `database/database.sql`:
   ```sql
   SOURCE database/database.sql;
   ```
3. Update `database_config.py` with your MySQL credentials:
   ```python
   # Example config
   host="localhost",
   user="root",
   password="your_password",
   database="ai_attendance_db"
   ```

### 5. Run the Application
```bash
python app.py
```
Visit `http://127.0.0.1:5000` in your browser.

## 📂 Project Structure

```text
AI Attendence system/
├── app.py                  # Main Flask application
├── database_config.py      # MySQL connection logic
├── modules/                # Core AI modules
│   ├── camera_module.py    # Frame processing & recognition
│   └── face_recognition_module.py # Face registration & embeddings
├── static/                 # CSS, JS, and Student Images
├── templates/              # HTML Templates (Dashboard, Students, etc.)
├── database/               # SQL scripts and backup
└── requirements.txt        # Python dependencies
```

## 📸 Screenshots

*(Add your screenshots here to make your README look more professional!)*
> **Tip:** You can use tools like `Snip & Sketch` to capture the dashboard and recognition screens.

## 💡 How it Works

1. **Registration:** During student registration, the system captures a frame from the webcam, detects the face using OpenCV, and generates a unique **128-d / 512-d embedding** using DeepFace.
2. **Storage:** The embedding is converted to a string format and stored in the `Face_Data` table in MySQL.
3. **Recognition:** When the camera starts for attendance, it scans the live feed, extracts face embeddings from the frames, and compares them against the stored database using **Cosine Similarity**.
4. **Marking:** If a match is found with high confidence (low distance), the student is marked "Present" for that specific course and date.

---

## 🤝 Contributing
Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.

---
**Made with ❤️ by [Your Name]**
