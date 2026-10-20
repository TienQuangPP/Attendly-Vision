import os
import re
import shutil
import threading
import cv2
import numpy as np
from insightface.app import FaceAnalysis
from config import MODELS_DIR
_insight_app = None

def get_insight_app(det_size=(320, 320)):  # Giảm 640→320: nhanh hơn ~4x trên CPU
    global _insight_app
    if _insight_app is None:
        root = os.path.join(MODELS_DIR, 'insightface')
        _insight_app = FaceAnalysis(name='buffalo_sc', root=root, providers=['CPUExecutionProvider'])
        _insight_app.prepare(ctx_id=0, det_size=det_size)
    return _insight_app

class FaceRecognizer:

    def __init__(self, dataset_dir, threshold=0.6, min_margin=0.08):
        self.dataset_dir = dataset_dir
        self.threshold = threshold
        self.min_margin = min_margin
        self.embeddings_db = {}
        self._normed_db = {}   # Cache đã normalize sẵn — tính 1 lần, dùng mãi mãi!
        self._db_lock = threading.RLock()
        os.makedirs(dataset_dir, exist_ok=True)
        self._app = get_insight_app()
        self._load_all_embeddings()
        print(f'[INFO] ArcFace Recognizer initialized. {len(self.embeddings_db)} students loaded.')

    def recognize(self, frame, face_raw):
        try:
            if hasattr(face_raw, 'embedding') and face_raw.embedding is not None:
                embedding = face_raw.embedding.reshape(1, -1)
            else:
                faces = self._app.get(frame)
                if not faces:
                    return {'matched': False, 'score': 0.0}
                embedding = faces[0].embedding.reshape(1, -1)
            return self.recognize_embedding(embedding)
        except Exception as e:
            print(f'[ERROR] ArcFace recognize: {e}')
            return {'matched': False, 'score': 0.0}

    def recognize_embedding(self, embedding):
        if not self.embeddings_db:
            return {'matched': False, 'score': 0.0}
        best_match, best_score = (None, -1.0)
        second_score = -1.0
        # Normalize vector đầu vào (query)
        emb_norm = embedding / (np.linalg.norm(embedding) + 1e-06)
        with self._db_lock:
            # Dùng _normed_db đã tính sẵn — KHÔNG tính norm lại nữa! Nhanh hơn nhiều!
            normed_snapshot = list(self._normed_db.items())
        for folder, stored_norm in normed_snapshot:
            if stored_norm.shape[1] != embedding.shape[1]:
                continue
            # Chỉ còn phép nhân ma trận thuần túy — cực nhanh!
            scores = stored_norm @ emb_norm.T
            score = float(scores.max())
            if score > best_score:
                second_score = best_score
                best_score = score
                best_match = folder
            elif score > second_score:
                second_score = score
        margin = best_score - second_score if second_score > -1 else 1.0
        if best_match and best_score >= self.threshold and margin >= self.min_margin:
            parts = best_match.split('_', 2)
            return {'class_name': parts[0] if len(parts) > 0 else 'Unknown', 'student_id': parts[1] if len(parts) > 1 else 'Unknown', 'student_name': parts[2].replace('_', ' ') if len(parts) > 2 else 'Unknown', 'score': round(best_score, 4), 'matched': True, 'folder': best_match}
        return {
            'matched': False,
            'score': round(best_score, 4) if best_score > -1 else 0.0,
            'ambiguous': best_score >= self.threshold and margin < self.min_margin,
        }

    def enroll_student(self, class_name, student_id, student_name, aligned_faces, face_crops=None):
        class_name = self._safe_component(class_name)
        student_id = self._safe_component(student_id.upper())
        safe_name = self._safe_component(student_name, spaces_to_underscores=True)
        folder = f'{class_name}_{student_id}_{safe_name}'
        student_dir = os.path.join(self.dataset_dir, folder)
        with self._db_lock:
            if os.path.exists(student_dir) or any(
                s['id'].casefold() == student_id.casefold() for s in self.get_all_students()
            ):
                return False
            embeddings = self._extract_embeddings(aligned_faces)
            if not embeddings:
                return False
            emb_array = np.vstack(embeddings)
            duplicate = self.recognize_embedding(emb_array.mean(axis=0, keepdims=True))
            if duplicate['matched'] or duplicate['score'] >= self.threshold:
                return False
            os.makedirs(student_dir)
            try:
                np.save(os.path.join(student_dir, 'embeddings.npy'), emb_array)
                for i, img_or_emb in enumerate(aligned_faces):
                    save_img = (face_crops[i] if face_crops and i < len(face_crops)
                                else img_or_emb if img_or_emb.ndim == 3
                                else np.zeros((112, 112, 3), dtype=np.uint8))
                    if not cv2.imwrite(os.path.join(student_dir, f'img_{i + 1:02d}.jpg'), save_img):
                        raise OSError('Cannot save enrollment image')
                self.embeddings_db[folder] = emb_array
            except Exception:
                shutil.rmtree(student_dir, ignore_errors=True)
                raise
        # Rebuild normed cache sau khi enroll (ngoài try-except)
        self._update_normed_db()
        print(f'[INFO] Enrolled: {class_name} - {student_id} - {student_name} ({len(embeddings)} images)')
        return True

    def _extract_embeddings(self, samples):
        embeddings = []
        for sample in samples:
            if isinstance(sample, np.ndarray) and sample.ndim == 1:
                emb = sample
            else:
                faces = self._app.get(sample)
                emb = faces[0].embedding if len(faces) == 1 else None
            if emb is not None and np.isfinite(emb).all() and np.linalg.norm(emb) > 0:
                embeddings.append(np.asarray(emb).flatten())
        return embeddings

    @staticmethod
    def _safe_component(value, spaces_to_underscores=False):
        value = str(value).strip()
        if spaces_to_underscores:
            value = re.sub(r'\s+', '_', value)
        if not value or value in {'.', '..'} or re.search(r'[\\/:*?"<>|]', value):
            raise ValueError('Invalid class, student ID, or student name')
        return value

    def get_all_students(self):
        students = []
        if not os.path.exists(self.dataset_dir):
            return students
        for folder in sorted(os.listdir(self.dataset_dir)):
            fp = os.path.join(self.dataset_dir, folder)
            if not os.path.isdir(fp) or folder.startswith('.'):
                continue
            parts = folder.split('_', 2)
            students.append({'class': parts[0] if len(parts) > 0 else 'Unknown', 'id': parts[1] if len(parts) > 1 else folder, 'name': parts[2].replace('_', ' ') if len(parts) > 2 else '', 'folder': folder, 'photo_count': len([f for f in os.listdir(fp) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])})
        return students

    def remove_student(self, folder_name):
        import shutil
        path = os.path.join(self.dataset_dir, folder_name)
        if os.path.exists(path):
            shutil.rmtree(path)
            self.embeddings_db.pop(folder_name, None)
            self._normed_db.pop(folder_name, None)  # Xóa luôn khỏi cache
            print(f'[INFO] Removed student: {folder_name}')
            return True
        return False

    def edit_student(self, old_folder, new_class, new_id, new_name):
        new_class = self._safe_component(new_class)
        new_id = self._safe_component(new_id.upper())
        safe = self._safe_component(new_name, spaces_to_underscores=True)
        new_folder = f'{new_class}_{new_id}_{safe}'
        old_dir = os.path.join(self.dataset_dir, old_folder)
        new_dir = os.path.join(self.dataset_dir, new_folder)
        if not os.path.exists(old_dir) or (new_dir != old_dir and os.path.exists(new_dir)):
            return False
        os.rename(old_dir, new_dir)
        if old_folder in self.embeddings_db:
            self.embeddings_db[new_folder] = self.embeddings_db.pop(old_folder)
        print(f'[INFO] Edited student: {old_folder} -> {new_folder}')
        return True

    def _update_normed_db(self):
        """Tính sẵn normalized embeddings cho toàn bộ DB.
        Gọi mỗi khi DB thay đổi (load, enroll, remove)."""
        normed = {}
        for folder, stored in self.embeddings_db.items():
            norms = np.linalg.norm(stored, axis=1, keepdims=True) + 1e-06
            normed[folder] = stored / norms
        self._normed_db = normed

    def _load_all_embeddings(self):
        if not os.path.exists(self.dataset_dir):
            return
        for folder in os.listdir(self.dataset_dir):
            fp = os.path.join(self.dataset_dir, folder)
            if os.path.isdir(fp) and (not folder.startswith('.')):
                emb_file = os.path.join(fp, 'embeddings.npy')
                if os.path.exists(emb_file):
                    try:
                        self.embeddings_db[folder] = np.load(emb_file)
                    except Exception as e:
                        print(f'[WARNING] Failed to load embeddings for {folder}: {e}')
        # Tính sẵn normalized DB sau khi load xong
        self._update_normed_db()
