import os
import cv2
import json
import numpy as np
import pandas as pd
from deepface import DeepFace
from database_config import get_db_connection

# Directory where student images are stored
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, 'static', 'images', 'students')

def recognize_face(frame):
    """
    Recognizes faces in the given frame using DeepFace.find.
    Returns a list of recognized student_ids and their face locations.
    """
    recognized_ids = []
    face_locations = []

    try:
        # 1. Save the current frame temporarily for DeepFace to process
        temp_path = "temp_capture.jpg"
        cv2.imwrite(temp_path, frame)
        
        # 2. Use DeepFace.find to search for matches in the dataset directory
        results = DeepFace.find(
            img_path=temp_path, 
            db_path=DATASET_DIR, 
            model_name="Facenet", 
            enforce_detection=False,
            distance_metric="cosine"
        )

        # 3. Process results
        for df in results:
            if not df.empty:
                best_match_path = df.iloc[0]['identity']
                distance = df.iloc[0]['distance']
                
                if distance < 0.40:
                    filename = os.path.basename(best_match_path)
                    student_id = os.path.splitext(filename)[0]
                    recognized_ids.append(student_id)

        # 4. Get face locations for UI boxes
        faces = DeepFace.extract_faces(img_path=temp_path, enforce_detection=False)
        for face in faces:
            area = face["facial_area"]
            top = area["y"]
            right = area["x"] + area["w"]
            bottom = area["y"] + area["h"]
            left = area["x"]
            face_locations.append((top, right, bottom, left))

        if os.path.exists(temp_path):
            os.remove(temp_path)

    except Exception as e:
        print(f"ERROR in recognition: {str(e)}")

    return recognized_ids, face_locations

def register_face_encoding(student_id, frame):
    """
    Verifies face and SAVES encoding to database to enable the 'Trained Active' status.
    """
    try:
        # 1. Verify face exists and get embedding
        objs = DeepFace.represent(img_path=frame, model_name="Facenet", enforce_detection=True)
        
        if len(objs) == 0:
            return False, "No face detected. Please look directly at the camera."
        if len(objs) > 1:
            return False, "Multiple faces detected. Please ensure only one person is in view."
        
        # Get the embedding (the AI Profile)
        encoding = objs[0]["embedding"]
        encoding_json = json.dumps(encoding)

        # 2. Save to Database (This fixes the 'Missing AI Profile' issue)
        conn = get_db_connection()
        if not conn:
            return False, "Database connection failed."
        
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Face_Data (student_id, face_encoding) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE face_encoding = %s",
            (student_id, encoding_json, encoding_json)
        )
        conn.commit()
        cursor.close()
        conn.close()

        # 3. Cleanup DeepFace cache to force refresh for DeepFace.find
        if os.path.exists(DATASET_DIR):
            for f in os.listdir(DATASET_DIR):
                if f.endswith(".pkl"):
                    os.remove(os.path.join(DATASET_DIR, f))
            
        return True, "Face profile created and activated successfully."
        
    except Exception as e:
        return False, f"Face processing error: {str(e)}"