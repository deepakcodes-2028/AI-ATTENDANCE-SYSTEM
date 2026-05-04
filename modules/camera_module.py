import cv2
import numpy as np
import base64
from modules.face_recognition_module import recognize_face

def decode_base64_image(data_url):

    header, encoded = data_url.split(',', 1)
    img_bytes = base64.b64decode(encoded)
    nparr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return frame

def process_frame_for_recognition(data_url):

    frame = decode_base64_image(data_url)
    if frame is None:
        return [], []
    recognized_ids, face_locations = recognize_face(frame)
    return recognized_ids, face_locations

def draw_face_boxes(frame, face_locations, labels=None):

    for i, (top, right, bottom, left) in enumerate(face_locations):
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 100), 2)
        label = labels[i] if labels and i < len(labels) else "Unknown"
        cv2.putText(frame, label, (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 100), 2)
    return frame

def capture_face_from_base64(data_url):

    frame = decode_base64_image(data_url)
    return frame
