import os
RTSP_URL = 'rtsp://username:password@192.168.1.1:554/stream'
WEBCAM_INDEX = 0
ENABLE_PREPROCESSING = False
BASE_DIR = os.path.abspath(os.path.expanduser(os.environ.get(
    'ATTENDLY_DATA_DIR', os.path.join(
        os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'AttendlyVision'
    )
)))
DATASET_DIR = os.path.join(BASE_DIR, 'dataset')
FRAMES_DIR = os.path.join(BASE_DIR, 'frames')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
DB_PATH = os.path.join(BASE_DIR, 'attendance.db')
for _d in [DATASET_DIR, FRAMES_DIR, MODELS_DIR]:
    os.makedirs(_d, exist_ok=True)
DETECTION_SCORE_THRESHOLD = 0.5
RECOGNITION_COSINE_THRESHOLD = 0.6
RECOGNITION_MIN_MARGIN = 0.08
RECOGNITION_INTERVAL = 0.8      # Giảm từ 1.5s → 0.8s: nhận diện nhanh gấp đôi
RECOGNITION_RESULT_TTL = 8.0    # Tăng từ 5s → 8s: giữ kết quả lâu hơn, ít bị Unknown
RECOGNITION_BOX_IOU_THRESHOLD = 0.35  # Nới lỏng IOU: không mất kết quả khi đầu hơi nghiêng
# A distant bystander's face may be ignored only when it is both tiny in the
# whole frame and much smaller than the primary face.
INCIDENTAL_FACE_MAX_FRAME_RATIO = 0.012
INCIDENTAL_FACE_MAX_PRIMARY_RATIO = 0.22
ANTISPOOF_ENABLED = False
ANTISPOOF_THRESHOLD = 0.4
FACE_SIZE = (160, 160)
GAUSSIAN_KERNEL = (5, 5)
CLAHE_CLIP = 2.0
CLAHE_GRID = (8, 8)
APP_TITLE = 'Attendly Vision — Điểm danh thông minh'
APP_MIN_WIDTH = 1100
APP_MIN_HEIGHT = 650
COLOR_PRIMARY = '#6C63FF'
COLOR_PRIMARY_HOVER = '#5A52E0'
COLOR_SUCCESS = '#00D26A'
COLOR_WARNING = '#F9A825'
COLOR_DANGER = '#FF5252'
COLOR_BG_DARK = '#0F0F1A'
COLOR_BG_CARD = '#1A1A2E'
COLOR_TEXT = '#E8E8F0'
COLOR_TEXT_DIM = '#7A7A9E'
COLOR_BORDER = '#2A2A4A'
COLOR_ACCENT_BLUE = '#00B4D8'
FONT_FAMILY = 'Segoe UI'
SESSIONS_FILE = os.path.join(BASE_DIR, 'sessions.json')
