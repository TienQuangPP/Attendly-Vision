import os
import cv2
import numpy as np
_MODEL_NAME = 'anti_spoof_minifas.onnx'
_INPUT_W = 80
_INPUT_H = 80

class AntiSpoof:

    def __init__(self, models_dir: str, threshold: float=0.8):
        self.threshold = threshold
        self._session = None
        self._input_name = None
        model_path = os.path.join(models_dir, _MODEL_NAME)
        if os.path.exists(model_path):
            try:
                import onnxruntime as ort
                self._session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
                self._input_name = self._session.get_inputs()[0].name
                print('[INFO] Anti-Spoof: MiniFASNet ONNX loaded.')
            except Exception as e:
                print(f'[WARNING] Anti-Spoof ONNX failed ({e}), falling back to CV analysis.')
        else:
            print('[INFO] Anti-Spoof: MiniFASNet model not found, using CV texture analysis.')

    @property
    def enabled(self) -> bool:
        return True

    def predict(self, frame: np.ndarray, bbox) -> dict:
        try:
            x, y, w, h = bbox
            pad_x = int(w * 0.2)
            pad_y = int(h * 0.2)
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(frame.shape[1], x + w + pad_x)
            y2 = min(frame.shape[0], y + h + pad_y)
            roi = frame[y1:y2, x1:x2]
            if roi.size == 0:
                return {'is_real': True, 'live_score': 1.0, 'label': 'LIVE'}
            if self._session is not None:
                return self._predict_onnx(roi)
            else:
                return self._predict_cv(roi)
        except Exception as e:
            print(f'[ERROR] AntiSpoof.predict: {e}')
            return {'is_real': True, 'live_score': 1.0, 'label': 'LIVE'}

    def _predict_onnx(self, roi):
        face_resized = cv2.resize(roi, (_INPUT_W, _INPUT_H))
        face_rgb = cv2.cvtColor(face_resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        blob = ((face_rgb - 0.5) / 0.5).transpose(2, 0, 1)[np.newaxis]
        outputs = self._session.run(None, {self._input_name: blob})
        probs = self._softmax(outputs[0][0])
        live_score = float(probs[1])
        is_real = live_score >= self.threshold
        return {'is_real': is_real, 'live_score': round(live_score, 4), 'label': 'LIVE' if is_real else 'FAKE'}

    def _predict_cv(self, roi):
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        scores = []
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(lap_var / 800.0, 1.0)
        scores.append(('sharpness', sharpness_score, 0.3))
        lbp = self._compute_lbp(gray)
        hist, _ = np.histogram(lbp, bins=32, range=(0, 256))
        hist = hist.astype(float)
        hist /= hist.sum() + 1e-07
        entropy = -np.sum(hist * np.log2(hist + 1e-07))
        lbp_score = min(entropy / 4.5, 1.0)
        scores.append(('lbp', lbp_score, 0.3))
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV).astype(float)
        sat_var = hsv[:, :, 1].var()
        val_var = hsv[:, :, 2].var()
        colour_score = min((sat_var + val_var * 0.5) / 1500.0, 1.0)
        scores.append(('colour', colour_score, 0.2))
        fft = np.fft.fft2(gray.astype(float))
        fft_s = np.fft.fftshift(fft)
        mag = np.abs(fft_s)
        cy, cx = (gray.shape[0] // 2, gray.shape[1] // 2)
        r_low = min(cy, cx) // 4
        low_e = mag[cy - r_low:cy + r_low, cx - r_low:cx + r_low].sum()
        total_e = mag.sum() + 1e-07
        hf_ratio = 1.0 - low_e / total_e
        fft_score = 1.0 - min(hf_ratio * 5.0, 1.0)
        scores.append(('fft', fft_score, 0.2))
        live_score = sum((s * w for _, s, w in scores))
        live_score = float(np.clip(live_score, 0.0, 1.0))
        is_real = live_score >= self.threshold
        detail = ' | '.join((f'{n}={s:.2f}' for n, s, _ in scores))
        print(f"[SPOOF] live={live_score:.3f} (thr={self.threshold}) [{detail}] → {('LIVE' if is_real else 'FAKE')}")
        return {'is_real': is_real, 'live_score': round(live_score, 4), 'label': 'LIVE' if is_real else 'FAKE'}

    @staticmethod
    def _compute_lbp(gray, radius=1, n_points=8):
        h, w = gray.shape
        result = np.zeros_like(gray)
        angles = [2 * np.pi * i / n_points for i in range(n_points)]
        for i, angle in enumerate(angles):
            ox = int(round(radius * np.cos(angle)))
            oy = int(round(radius * np.sin(angle)))
            x1, x2 = (max(0, ox), w + min(0, ox))
            y1, y2 = (max(0, oy), h + min(0, oy))
            shifted = gray[max(0, -oy):h - max(0, oy), max(0, -ox):w - max(0, ox)]
            base = gray[y1:y2, x1:x2]
            if shifted.shape == base.shape:
                result[y1:y2, x1:x2] += (shifted >= base).astype(np.uint8) << i
        return result

    @staticmethod
    def _softmax(x):
        e = np.exp(x - np.max(x))
        return e / e.sum()