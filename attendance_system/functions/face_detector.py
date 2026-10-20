import cv2

class FaceDetector:

    def __init__(self, score_threshold=0.5):
        from functions.face_recognizer import get_insight_app
        self._app = get_insight_app(det_size=(640, 640))
        self.score_threshold = score_threshold
        print('[INFO] SCRFD Face Detector initialized.')

    def detect_faces(self, frame):
        if frame is None:
            return []
        faces = self._app.get(frame)
        if not faces:
            return []
        height, width = frame.shape[:2]
        results = []
        for face in faces:
            if face.det_score < self.score_threshold:
                continue
            x1, y1, x2, y2 = face.bbox.astype(int)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(width, x2), min(height, y2)
            if x2 <= x1 or y2 <= y1:
                continue
            x, y, w, h = x1, y1, x2 - x1, y2 - y1
            landmarks = {}
            if face.kps is not None and len(face.kps) >= 5:
                kp = face.kps.astype(int)
                landmarks = {'right_eye': tuple(kp[0]), 'left_eye': tuple(kp[1]), 'nose': tuple(kp[2]), 'mouth_right': tuple(kp[3]), 'mouth_left': tuple(kp[4])}
            results.append({'box': (x, y, w, h), 'confidence': float(face.det_score), 'landmarks': landmarks, 'raw': face})
        return sorted(results, key=lambda item: (item['box'][0], item['box'][1]))

    @staticmethod
    def select_primary_face(detections, frame_shape,
                            max_frame_ratio=0.012, max_primary_ratio=0.22):
        """Return (primary, blockers, incidental) using conservative size rules."""
        if not detections:
            return None, [], []
        frame_area = max(1, frame_shape[0] * frame_shape[1])
        ordered = sorted(
            detections,
            key=lambda det: det['box'][2] * det['box'][3],
            reverse=True,
        )
        primary = ordered[0]
        primary_area = primary['box'][2] * primary['box'][3]
        blockers, incidental = [], []
        for det in ordered[1:]:
            area = det['box'][2] * det['box'][3]
            is_incidental = (
                area / frame_area <= max_frame_ratio and
                area / max(1, primary_area) <= max_primary_ratio
            )
            (incidental if is_incidental else blockers).append(det)
        return primary, blockers, incidental

    def draw_detections(self, frame, detections, names=None):
        result = frame.copy()
        for i, det in enumerate(detections):
            x, y, w, h = det['box']
            conf = det['confidence']
            if names and i < len(names) and names[i]:
                label = names[i]
                color = (0, 210, 106)
            else:
                label = f'Unknown ({conf:.0%})'
                color = (82, 82, 255)
            cv2.rectangle(result, (x, y), (x + w, y + h), color, 2)
            cl = min(20, w // 4, h // 4)
            for pt1, pt2 in [((x, y), (x + cl, y)), ((x, y), (x, y + cl)), ((x + w, y), (x + w - cl, y)), ((x + w, y), (x + w, y + cl)), ((x, y + h), (x + cl, y + h)), ((x, y + h), (x, y + h - cl)), ((x + w, y + h), (x + w - cl, y + h)), ((x + w, y + h), (x + w, y + h - cl))]:
                cv2.line(result, pt1, pt2, color, 3)
            for pt in det['landmarks'].values():
                cv2.circle(result, pt, 2, (0, 255, 255), -1)
            font, fs, th = (cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            (tw, th_), _ = cv2.getTextSize(label, font, fs, th)
            cv2.rectangle(result, (x, y - th_ - 12), (x + tw + 10, y), color, -1)
            cv2.putText(result, label, (x + 5, y - 6), font, fs, (255, 255, 255), th)
        return result

    def crop_face(self, frame, box, padding=20):
        h_img, w_img = frame.shape[:2]
        x, y, w, h = box
        return frame[max(0, y - padding):min(h_img, y + h + padding), max(0, x - padding):min(w_img, x + w + padding)]
