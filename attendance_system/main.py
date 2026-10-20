import sys
import os
import traceback
from config import BASE_DIR

# Windowed executables have no console; model download progress still needs streams.
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

def global_exception_handler(exc_type, exc_value, exc_traceback):
    with open(os.path.join(BASE_DIR, 'error_log.txt'), 'a', encoding='utf-8') as f:
        f.write('Uncaught exception:\n')
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    if sys.stderr is not None:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
sys.excepthook = global_exception_handler
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget
from config import (APP_MIN_HEIGHT, APP_MIN_WIDTH, APP_TITLE,
                    COLOR_BG_CARD, COLOR_BG_DARK, COLOR_BORDER, COLOR_TEXT,
                    COLOR_TEXT_DIM, DATASET_DIR, DB_PATH,
                    RECOGNITION_COSINE_THRESHOLD, RECOGNITION_MIN_MARGIN)
from functions.database import Database
from functions.face_recognizer import FaceRecognizer
from ui.screens import SetupScreen, AttendanceApp
from ui.styles import GLOBAL_STYLE

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(APP_MIN_WIDTH, APP_MIN_HEIGHT)
        self.setStyleSheet(f'\n            QMainWindow {{ background-color: {COLOR_BG_DARK}; }}\n            QPushButton {{\n                background-color: {COLOR_BG_CARD}; color: {COLOR_TEXT};\n                border: 1px solid {COLOR_BORDER}; border-radius: 6px; font-weight: bold;\n            }}\n            QPushButton:hover {{ background-color: {COLOR_BORDER}; }}\n            QLineEdit, QComboBox {{\n                background-color: {COLOR_BG_CARD}; color: {COLOR_TEXT};\n                border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 5px;\n            }}\n            QTableWidget {{\n                background-color: {COLOR_BG_CARD}; color: {COLOR_TEXT};\n                gridline-color: {COLOR_BORDER}; border: none;\n            }}\n            QHeaderView::section {{\n                background-color: {COLOR_BG_DARK}; color: {COLOR_TEXT_DIM}; border: none; font-weight: bold;\n            }}\n            QScrollBar:vertical {{\n                background-color: {COLOR_BG_DARK}; width: 14px;\n            }}\n            QScrollBar::handle:vertical {{\n                background-color: {COLOR_BORDER}; border-radius: 7px;\n            }}\n        ')
        self.db = Database(DB_PATH)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.setup_screen = SetupScreen(self)
        self.stack.addWidget(self.setup_screen)

    def start_session(self, class_name, subject, slot_number=1, slot_minutes=15,
                      camera_source=0):
        class_dataset_dir = os.path.join(DATASET_DIR, class_name)
        from PyQt5.QtWidgets import QMessageBox
        from PyQt5.QtCore import Qt
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.face_recognizer = FaceRecognizer(
                class_dataset_dir,
                threshold=RECOGNITION_COSINE_THRESHOLD,
                min_margin=RECOGNITION_MIN_MARGIN,
            )
        except Exception as exc:
            QMessageBox.warning(self, 'Không thể tải mô hình',
                'Lần đầu cần Internet để tải mô hình nhận diện. '
                'Kiểm tra kết nối rồi thử lại.\n\n' + str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.app_screen = AttendanceApp(
            self, class_name, subject, self.face_recognizer, self.db,
            slot_number, slot_minutes, camera_source
        )
        self.stack.addWidget(self.app_screen)
        self.stack.setCurrentIndex(1)

    def show_setup(self):
        self.stack.setCurrentIndex(0)
        if hasattr(self, 'app_screen'):
            self.stack.removeWidget(self.app_screen)
            self.app_screen.deleteLater()
            del self.app_screen
        self.setup_screen.refresh_sessions()

    def closeEvent(self, event):
        if hasattr(self, 'app_screen'):
            self.app_screen._finalize_attendance_sheet()
        event.accept()
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLE)
    os.makedirs(DATASET_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    window = MainWindow()
    if '--self-test' in sys.argv:
        import json
        import numpy as np
        from functions.face_recognizer import get_insight_app
        result = {'title': window.windowTitle(), 'gui': True,
                  'database': isinstance(window.db.get_today_count(), int)}
        if '--check-models' in sys.argv:
            engine = get_insight_app()
            assert 'detection' in engine.models and 'recognition' in engine.models
            assert not engine.get(np.zeros((480, 640, 3), dtype=np.uint8))
            result['model_inference'] = True
        with open(os.path.join(BASE_DIR, 'self-test.json'), 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        window.close()
        sys.exit(0)
    window.show()
    sys.exit(app.exec_())
