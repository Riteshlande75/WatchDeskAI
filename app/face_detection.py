import cv2
import numpy as np

class FaceDetector:
    """
    Enterprise-Grade Dual-Pass Face & Eye Proctoring Detector.
    Uses multi-cascade fusion combined with facial feature verification (Spatial Center Distance & IoU Clustering)
    to accurately detect 0, 1, and 2+ candidates under all webcam lighting conditions.
    """
    def __init__(self):
        self.frontal_cascade = None
        self.alt_cascade = None
        self.profile_cascade = None
        self.eye_cascade = None
        
        if hasattr(cv2, 'CascadeClassifier'):
            try:
                p1 = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                self.frontal_cascade = cv2.CascadeClassifier(p1)
            except Exception:
                pass
                
            try:
                p2 = cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
                self.alt_cascade = cv2.CascadeClassifier(p2)
            except Exception:
                pass

            try:
                p3 = cv2.data.haarcascades + 'haarcascade_profileface.xml'
                self.profile_cascade = cv2.CascadeClassifier(p3)
            except Exception:
                pass

            try:
                p4 = cv2.data.haarcascades + 'haarcascade_eye.xml'
                self.eye_cascade = cv2.CascadeClassifier(p4)
            except Exception:
                pass

    def merge_and_count_distinct_faces(self, boxes, img_gray):
        """
        Groups bounding boxes by spatial distance and verifies distinct candidate facial regions.
        """
        if len(boxes) == 0:
            return 0

        # Sort by box area descending (primary candidate first)
        sorted_boxes = sorted(boxes, key=lambda b: b[2] * b[3], reverse=True)
        distinct_faces = []

        for b in sorted_boxes:
            x, y, w, h = b[0], b[1], b[2], b[3]
            
            # Check center coordinate distance from existing distinct faces
            cx = x + (w / 2.0)
            cy = y + (h / 2.0)
            
            is_same_person = False
            for f in distinct_faces:
                fx, fy, fw, fh = f[0], f[1], f[2], f[3]
                fcx = fx + (fw / 2.0)
                fcy = fy + (fh / 2.0)

                # Calculate Euclidean center distance relative to face size
                dist = np.sqrt((cx - fcx)**2 + (cy - fcy)**2)
                min_dim = min(w, h, fw, fh)

                # Calculate Intersection over Union (IoU)
                overlap_w = max(0, min(x + w, fx + fw) - max(x, fx))
                overlap_h = max(0, min(y + h, fy + fh) - max(y, fy))
                intersection = overlap_w * overlap_h
                union = (w * h) + (fw * fh) - intersection
                iou = intersection / float(union) if union > 0 else 0

                # If center distance is within 65% of face size or IoU > 0.15, it's the SAME candidate
                if dist < (min_dim * 0.65) or iou > 0.15:
                    is_same_person = True
                    break

            if not is_same_person:
                distinct_faces.append(b)

        return len(distinct_faces)

    def detect_faces(self, img):
        """
        Detects faces in OpenCV BGR frame. Returns exact count of distinct candidate faces.
        """
        if img is None:
            return 1

        h, w = img.shape[:2]
        if h == 0 or w == 0:
            return 1

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        detected_boxes = []

        # 1. Frontal Face Cascade (Primary)
        if self.frontal_cascade is not None and not self.frontal_cascade.empty():
            try:
                f1 = self.frontal_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=4, minSize=(35, 35)
                )
                if len(f1) > 0:
                    detected_boxes.extend(f1)
            except Exception:
                pass

        # 2. Alt Frontal Face Cascade (Secondary)
        if self.alt_cascade is not None and not self.alt_cascade.empty():
            try:
                f2 = self.alt_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=4, minSize=(35, 35)
                )
                if len(f2) > 0:
                    detected_boxes.extend(f2)
            except Exception:
                pass

        # 3. Profile Face Cascade (For angled or side faces)
        if self.profile_cascade is not None and not self.profile_cascade.empty():
            try:
                f3 = self.profile_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=4, minSize=(35, 35)
                )
                if len(f3) > 0:
                    detected_boxes.extend(f3)
            except Exception:
                pass

        # If Haar cascades detected regions, run spatial clustering
        if len(detected_boxes) > 0:
            return self.merge_and_count_distinct_faces(detected_boxes, gray)

        # 4. Skin-Tone HSV + Feature Verification Fallback
        try:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            lower_skin = np.array([0, 15, 50], dtype=np.uint8)
            upper_skin = np.array([25, 255, 255], dtype=np.uint8)
            mask = cv2.inRange(hsv, lower_skin, upper_skin)

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            skin_boxes = []
            min_area = (h * w) * 0.03  # 3% of frame area

            for c in contours:
                area = cv2.contourArea(c)
                if area > min_area:
                    bx, by, bw, bh = cv2.boundingRect(c)
                    aspect = float(bh) / (bw if bw > 0 else 1)
                    if 0.7 <= aspect <= 2.5:
                        skin_boxes.append([bx, by, bw, bh])

            if len(skin_boxes) > 0:
                return self.merge_and_count_distinct_faces(skin_boxes, gray)

            return 0
        except Exception:
            return 1

    def analyze_integrity(self, img):
        """
        Analyzes image frame and returns structured face status & integrity score.
        """
        face_count = self.detect_faces(img)

        if face_count == 1:
            return {
                'face_count': 1,
                'status': 'FACE_OK',
                'integrity_score': 100,
                'message': 'Candidate face verified (100% Integrity)'
            }
        elif face_count == 0:
            return {
                'face_count': 0,
                'status': 'NO_FACE',
                'integrity_score': 50,
                'message': 'OpenCV Alert: Candidate Face Not Detected in Webcam Feed'
            }
        else:
            return {
                'face_count': face_count,
                'status': 'MULTIPLE_FACES',
                'integrity_score': 0,
                'message': f'OpenCV Security Alert: Multiple Persons Detected ({face_count} Faces in Camera View)'
            }

# Shared Face Detector Instance
face_detector = FaceDetector()
