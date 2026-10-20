import os
import pandas as pd
import numpy as np
import cv2
from datetime import datetime

class BiometricsLogger:

    @staticmethod
    def draw_face_features(frame, det, box_color):
        raw = det.get('raw')
        if raw is None:
            return
        x, y, w, h = det['box']
        kps = None
        if hasattr(raw, 'kps') and raw.kps is not None:
            kps = raw.kps.astype(int)
        det_score = float(raw.det_score) if hasattr(raw, 'det_score') and raw.det_score is not None else 0.0
        emb_norm = 0.0
        if hasattr(raw, 'embedding') and raw.embedding is not None:
            emb_norm = float(np.linalg.norm(raw.embedding))
        eye_dist = 0.0
        symmetry = 0.0
        yaw_est = 0.0
        if kps is not None and len(kps) >= 5:
            le, re, nose, lm, rm = (kps[0], kps[1], kps[2], kps[3], kps[4])
            eye_dist = float(np.linalg.norm(re - le))
            eye_mid = (le + re) / 2
            face_cx = x + w / 2
            d_nose = abs(nose[0] - face_cx)
            sym_raw = 1.0 - min(d_nose / (w / 2 + 1), 1.0)
            symmetry = sym_raw
            dx = float(nose[0] - eye_mid[0])
            yaw_est = dx / (eye_dist / 2 + 1) * 45
        aspect = round(w / (h + 1), 2)
        panel_x = x + w + 6
        panel_y = y
        lines = [(f'Det  {det_score:.2f}', (180, 255, 180)), (f'Norm {emb_norm:.1f}', (180, 220, 255)), (f'EyeD {eye_dist:.0f}px', (255, 220, 100)), (f'Asp  {aspect:.2f}', (200, 200, 200)), (f'Sym  {symmetry:.2f}', (200, 180, 255)), (f'Yaw  {yaw_est:+.0f}°', (255, 180, 120))]
        line_h = 18
        panel_w = 105
        panel_h = len(lines) * line_h + 8
        fh, fw = frame.shape[:2]
        if panel_x + panel_w > fw:
            panel_x = x - panel_w - 6
        if panel_y + panel_h > fh:
            panel_y = fh - panel_h - 2
        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (15, 15, 30), -1)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
        cv2.rectangle(frame, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), box_color, 1)
        for li, (txt, col) in enumerate(lines):
            ty = panel_y + 14 + li * line_h
            cv2.putText(frame, txt, (panel_x + 5, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.42, col, 1, cv2.LINE_AA)

    @staticmethod
    def _extract_features(raw, box, base_emb=None):
        features = {}
        x, y, w, h = box
        features['Det Score'] = float(raw.det_score) if hasattr(raw, 'det_score') else 0.0
        emb = raw.embedding.flatten() if hasattr(raw, 'embedding') else np.zeros(512)
        features['Norm (Vector Length)'] = float(np.linalg.norm(emb))
        cos_sim = 1.0
        if base_emb is not None:
            norm1 = np.linalg.norm(emb)
            norm2 = np.linalg.norm(base_emb)
            if norm1 > 0 and norm2 > 0:
                cos_sim = float(np.dot(emb, base_emb) / (norm1 * norm2))
        features['Cosine Similarity w/ Gốc'] = round(cos_sim, 4)
        kps = raw.kps.astype(int) if hasattr(raw, 'kps') and raw.kps is not None else None
        features['Eye Dist (px)'] = 0.0
        features['Symmetry'] = 0.0
        features['Yaw Est (deg)'] = 0.0
        features['Aspect Ratio'] = round(w / (h + 1e-06), 2)
        if kps is not None and len(kps) >= 5:
            le, re, nose, lm, rm = (kps[0], kps[1], kps[2], kps[3], kps[4])
            eye_dist = float(np.linalg.norm(re - le))
            features['Eye Dist (px)'] = round(eye_dist, 2)
            eye_mid = (le + re) / 2
            face_cx = x + w / 2
            d_nose = abs(nose[0] - face_cx)
            sym = 1.0 - min(d_nose / (w / 2 + 1), 1.0)
            features['Symmetry'] = round(sym, 3)
            dx = float(nose[0] - eye_mid[0])
            yaw = dx / (eye_dist / 2 + 1) * 45
            features['Yaw Est (deg)'] = round(yaw, 2)
        for i in range(512):
            val = float(emb[i]) if i < len(emb) else 0.0
            features[f'Emb_{i + 1:03d}'] = val
        return features

    @staticmethod
    def create_enroll_log(student_dir, raw, box):
        features = BiometricsLogger._extract_features(raw, box)
        df = pd.DataFrame({'Metric': list(features.keys()), 'Ảnh Gốc (Enroll)': list(features.values())})
        excel_path = os.path.join(student_dir, 'biometrics.xlsx')
        df.to_excel(excel_path, index=False)
        print(f'[INFO] Saved biometrics log to {excel_path}')

    @staticmethod
    def log_attendance(student_dir, raw, box):
        excel_path = os.path.join(student_dir, 'biometrics.xlsx')
        if not os.path.exists(excel_path):
            print(f'[WARNING] Biometrics log not found for student at {student_dir}')
            return
        try:
            df = pd.read_excel(excel_path)
            try:
                emb_rows = df[df['Metric'].str.startswith('Emb_')]
                base_emb = emb_rows['Ảnh Gốc (Enroll)'].values.astype(float)
            except Exception:
                base_emb = None
            features = BiometricsLogger._extract_features(raw, box, base_emb=base_emb)
            col_name = datetime.now().strftime('Check_In_%Y%m%d_%H%M%S')
            new_col_values = []
            for metric in df['Metric']:
                new_col_values.append(features.get(metric, 0.0))
            df[col_name] = new_col_values
            df.to_excel(excel_path, index=False)
        except Exception as e:
            print(f'[ERROR] Failed to update biometrics log: {e}')

    @staticmethod
    def add_student_to_master_sheet(class_dir, student_id, student_name):
        import pandas as pd
        excel_path = os.path.join(class_dir, 'attendance.xlsx')
        try:
            if os.path.exists(excel_path):
                df = pd.read_excel(excel_path)
                df['Student ID'] = df['Student ID'].astype(str)
                if str(student_id) not in df['Student ID'].values:
                    new_row = {'Student ID': str(student_id), 'Student Name': student_name}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_excel(excel_path, index=False)
            else:
                df = pd.DataFrame([{'Student ID': str(student_id), 'Student Name': student_name}])
                df.to_excel(excel_path, index=False)
        except Exception as e:
            print(f'[ERROR] Cannot update master attendance sheet: {e}')

    @staticmethod
    def mark_attendance_in_master_sheet(class_dir, student_id, session_col_name):
        import pandas as pd
        excel_path = os.path.join(class_dir, 'attendance.xlsx')
        now_time = datetime.now().strftime('%H:%M:%S')
        try:
            if not os.path.exists(excel_path):
                df = pd.DataFrame(columns=['Student ID', 'Student Name'])
            else:
                df = pd.read_excel(excel_path)
            df['Student ID'] = df['Student ID'].astype(str)
            if session_col_name not in df.columns:
                df[session_col_name] = ''
            df.loc[df['Student ID'] == str(student_id), session_col_name] = f'Present ({now_time})'
            df.to_excel(excel_path, index=False)
        except Exception as e:
            print(f'[ERROR] Cannot mark attendance in master sheet: {e}')