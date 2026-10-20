import os
import cv2
import json
import time
import threading
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from config import *
from functions.face_detector import FaceDetector
from functions.anti_spoof import AntiSpoof
from functions.biometrics_logger import BiometricsLogger
from functions.stream import CameraStream
from functions.frame_extractor import FrameExtractor
from functions.preprocessor import Preprocessor
from ui.dialogs import CreateSessionDialog, EnrollDialog, ManageDialog

class SetupScreen(QWidget):

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setStyleSheet(f'background-color: {COLOR_BG_DARK}; color: {COLOR_TEXT};')
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignCenter)
        title = QLabel('📚 Quản lý Phiên Điểm Danh')
        title.setFont(QFont(FONT_FAMILY, 22, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(title)
        self.main_layout.addSpacing(20)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet('border: none;')
        scroll.setFixedSize(600, 400)
        self.container = QWidget()
        self.container.setStyleSheet('background-color: transparent;')
        self.sessions_layout = QVBoxLayout(self.container)
        self.sessions_layout.setAlignment(Qt.AlignTop)
        self.sessions_layout.setSpacing(15)
        scroll.setWidget(self.container)
        self.main_layout.addWidget(scroll, alignment=Qt.AlignCenter)
        self.main_layout.addSpacing(20)
        btn_create = QPushButton('➕ Khởi tạo Lớp / Môn mới')
        btn_create.setFixedSize(250, 45)
        btn_create.setCursor(Qt.PointingHandCursor)
        btn_create.setStyleSheet(f'QPushButton {{ background-color: {COLOR_PRIMARY}; color: white; border-radius: 5px; font-weight: bold; font-size: 14px; }}')
        btn_create.clicked.connect(self._create_session)
        self.main_layout.addWidget(btn_create, alignment=Qt.AlignCenter)
        self.refresh_sessions()

    def refresh_sessions(self):
        while self.sessions_layout.count():
            item = self.sessions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        sessions = []
        if os.path.exists(SESSIONS_FILE):
            try:
                with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                    sessions = json.load(f)
            except (OSError, json.JSONDecodeError):
                pass
        if not sessions:
            lbl = QLabel('Chưa có lớp nào được thiết lập.')
            lbl.setStyleSheet('color: #888;')
            lbl.setAlignment(Qt.AlignCenter)
            self.sessions_layout.addWidget(lbl)
            return
        for sess in sessions:
            c = sess.get('class', '')
            s = sess.get('subject', '')
            card = QFrame()
            card.setFixedHeight(70)
            c_lay = QHBoxLayout(card)
            info = QLabel(f"Lớp: <b style='color:{COLOR_ACCENT_BLUE}'>{c}</b>  -  Môn: <b style='color:{COLOR_ACCENT_BLUE}'>{s}</b>")
            info.setFont(QFont(FONT_FAMILY, 14))
            info.setStyleSheet('border: none;')
            c_lay.addWidget(info, stretch=1)
            btn_start = QPushButton('▶ Vào Điểm danh')
            btn_start.setFixedHeight(40)
            btn_start.setCursor(Qt.PointingHandCursor)
            btn_start.setStyleSheet(f'background-color: {COLOR_SUCCESS}; font-weight: bold; padding: 0 15px;')
            btn_start.clicked.connect(lambda checked, cls=c, subj=s: self._pick_slot_and_start(cls, subj))
            c_lay.addWidget(btn_start)
            btn_del = QPushButton('🗑')
            btn_del.setFixedSize(40, 40)
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setStyleSheet(f'background-color: {COLOR_DANGER};')
            btn_del.clicked.connect(lambda checked, sess_obj=sess: self._delete_session(sess_obj))
            c_lay.addWidget(btn_del)
            self.sessions_layout.addWidget(card)

    def _create_session(self):
        dlg = CreateSessionDialog(self)
        if dlg.exec_():
            self.refresh_sessions()

    def _delete_session(self, sess_obj):
        reply = QMessageBox.question(self, 'Xác nhận xóa', f'Bạn có chắc chắn muốn xóa phiên học này khỏi danh sách?\\n(Dữ liệu điểm danh cũ trong CSDL vẫn sẽ được giữ nguyên)', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if os.path.exists(SESSIONS_FILE):
                with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                    sessions = json.load(f)
                sessions = [s for s in sessions if s != sess_obj]
                with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(sessions, f, ensure_ascii=False, indent=4)
                self.refresh_sessions()

    def _pick_slot_and_start(self, class_name, subject):
        dlg = QDialog(self)
        dlg.setWindowTitle('Chọn Slot học')
        dlg.setFixedSize(440, 360)
        dlg.setStyleSheet(f'background-color: {COLOR_BG_CARD}; color: {COLOR_TEXT};')
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        lbl = QLabel(f'📚 {class_name} – {subject}')
        lbl.setFont(QFont(FONT_FAMILY, 13, QFont.Bold))
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        slot_layout = QHBoxLayout()
        slot_label = QLabel('Chọn Slot:')
        slot_label.setFont(QFont(FONT_FAMILY, 12))
        slot_layout.addWidget(slot_label)
        combo = QComboBox()
        combo.setFixedHeight(35)
        combo.setFont(QFont(FONT_FAMILY, 12))
        for i in range(1, 21):
            combo.addItem(f'Slot {i}', i)
        slot_layout.addWidget(combo)
        layout.addLayout(slot_layout)
        time_layout = QHBoxLayout()
        time_label = QLabel('Thời lượng:')
        time_label.setFont(QFont(FONT_FAMILY, 12))
        time_layout.addWidget(time_label)
        spin = QSpinBox()
        spin.setRange(0, 9999)
        spin.setValue(15)
        spin.setSuffix(' phút')
        spin.setSpecialValueText('♾ Không giới hạn')
        spin.setFixedHeight(35)
        spin.setFont(QFont(FONT_FAMILY, 12))
        time_layout.addWidget(spin)
        layout.addLayout(time_layout)
        source_label = QLabel('Nguồn camera:')
        source_label.setFont(QFont(FONT_FAMILY, 12))
        layout.addWidget(source_label)
        source_combo = QComboBox()
        source_combo.addItem('Webcam', 'webcam')
        source_combo.addItem('IP Camera (RTSP)', 'rtsp')
        layout.addWidget(source_combo)
        source_input = QLineEdit(RTSP_URL)
        source_input.setPlaceholderText('rtsp://user:password@ip:554/stream')
        source_input.setVisible(False)
        source_combo.currentIndexChanged.connect(
            lambda: source_input.setVisible(source_combo.currentData() == 'rtsp')
        )
        layout.addWidget(source_input)
        btn = QPushButton('▶  Bắt đầu Điểm danh')
        btn.setFixedHeight(40)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f'background-color: {COLOR_SUCCESS}; color: white; font-weight: bold; font-size: 13px; border-radius: 6px;')
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)
        if dlg.exec_() == QDialog.Accepted:
            slot_number = combo.currentData()
            slot_minutes = spin.value()
            camera_source = (source_input.text().strip()
                             if source_combo.currentData() == 'rtsp'
                             else WEBCAM_INDEX)
            if source_combo.currentData() == 'rtsp' and not camera_source.lower().startswith('rtsp://'):
                QMessageBox.warning(self, 'RTSP không hợp lệ', 'URL phải bắt đầu bằng rtsp://')
                return
            self.main_window.start_session(
                class_name, subject, slot_number, slot_minutes, camera_source
            )

class AttendanceApp(QWidget):

    def __init__(self, main_window, class_name, subject, face_recognizer, db,
                 slot_number=1, slot_minutes=15, camera_source=0):
        super().__init__()
        self.main_window = main_window
        self.class_name = class_name
        self.subject = subject
        self.face_recognizer = face_recognizer
        self.db = db
        self.slot_number = slot_number
        self.slot_minutes = slot_minutes
        self.slot_expired = False
        self.setStyleSheet(f'background-color: {COLOR_BG_DARK}; color: {COLOR_TEXT};')
        self.camera_source = camera_source
        self.camera = CameraStream(camera_source)
        self.frame_extractor = FrameExtractor(FRAMES_DIR)
        self.preprocessor = Preprocessor(FACE_SIZE, GAUSSIAN_KERNEL, CLAHE_CLIP, CLAHE_GRID)
        self._last_primary_crop = None
        self.face_detector = None
        self.anti_spoof = None
        self._models_loaded = False
        self.is_camera_on = False
        self.is_recognizing = False
        self.last_recognition_time = 0
        self._recognition_lock = threading.Lock()
        self._recognition_busy = False
        self._recognition_generation = 0
        self._recognition_results = []    # Multi-person: danh sách kết quả nhận diện
        self._biometrics_logged = set()
        self._frame_counter = 0
        self._cached_detections = []
        self.session_col_name = f'Slot {self.slot_number} - ' + datetime.now().strftime('%d/%m/%Y %H:%M')
        if self.slot_minutes > 0:
            self.deadline = datetime.now() + __import__('datetime').timedelta(minutes=self.slot_minutes)
        else:
            self.deadline = None
        self._build_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(30)
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._update_countdown)
        self.countdown_timer.start(1000)
        threading.Thread(target=self._load_models, daemon=True).start()

    def _update_countdown(self):
        if self.deadline is None:
            self.countdown_label.setText('♾ Không giới hạn')
            self.countdown_label.setStyleSheet(f'color: {COLOR_TEXT_DIM}; border: none; font-weight: bold;')
            return
        remaining = (self.deadline - datetime.now()).total_seconds()
        if remaining <= 0:
            self.countdown_label.setText('⏰ HẾT GIỜ!')
            self.countdown_label.setStyleSheet(f'color: {COLOR_DANGER}; border: none; font-weight: bold;')
            if not self.slot_expired:
                self.slot_expired = True
                self._finalize_attendance_sheet()
                self._set_status('⏰ Hết giờ! Đã chốt sổ điểm danh.', COLOR_DANGER)
        else:
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            self.countdown_label.setText(f'⏱ Còn lại: {mins:02d}:{secs:02d}')
            if remaining < 60:
                self.countdown_label.setStyleSheet(f'color: {COLOR_DANGER}; border: none; font-weight: bold;')
            elif remaining < 180:
                self.countdown_label.setStyleSheet(f'color: {COLOR_WARNING}; border: none; font-weight: bold;')
            else:
                self.countdown_label.setStyleSheet(f'color: {COLOR_SUCCESS}; border: none; font-weight: bold;')

    def _load_models(self):
        try:
            self.face_detector = FaceDetector(DETECTION_SCORE_THRESHOLD)
            self.anti_spoof = AntiSpoof(MODELS_DIR, threshold=ANTISPOOF_THRESHOLD)
            self._models_loaded = True
            spoof_status = '✅ Models loaded (Anti-Spoof ON)' if self.anti_spoof.enabled else '✅ Models loaded (Anti-Spoof OFF)'
            QTimer.singleShot(0, lambda: self._set_status(spoof_status, COLOR_SUCCESS))
        except Exception as e:
            QTimer.singleShot(0, lambda: self._set_status(f'❌ Model Error: {e}', COLOR_DANGER))

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        header_bar = QFrame()
        header_bar.setFixedHeight(60)
        h_layout = QHBoxLayout(header_bar)
        h_layout.setContentsMargins(15, 0, 15, 0)
        lbl_info = QLabel(f"📚 Lớp: <b style='color:{COLOR_PRIMARY}'>{self.class_name}</b> &nbsp;&nbsp;|&nbsp;&nbsp; 📝 Môn: <b style='color:{COLOR_PRIMARY}'>{self.subject}</b> &nbsp;&nbsp;|&nbsp;&nbsp; 🔢 Slot: <b style='color:{COLOR_PRIMARY}'>{self.slot_number}</b>")
        lbl_info.setFont(QFont(FONT_FAMILY, 14))
        lbl_info.setStyleSheet('border: none;')
        h_layout.addWidget(lbl_info)
        h_layout.addStretch()
        self.countdown_label = QLabel(f'⏱ Còn lại: {self.slot_minutes:02d}:00')
        self.countdown_label.setFont(QFont(FONT_FAMILY, 14, QFont.Bold))
        self.countdown_label.setStyleSheet(f'color: {COLOR_SUCCESS}; border: none; font-weight: bold;')
        h_layout.addWidget(self.countdown_label)
        h_layout.addSpacing(15)
        btn_back = QPushButton('🔙 Đóng Session')
        btn_back.setFixedHeight(35)
        btn_back.setStyleSheet(f'background-color: {COLOR_WARNING}; color: black; border-radius: 5px; font-weight: bold; padding: 0 15px;')
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.clicked.connect(self._go_back)
        h_layout.addWidget(btn_back)
        main_layout.addWidget(header_bar)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        left_col = QVBoxLayout()
        left_col.addWidget(self._build_camera_panel(), stretch=1)
        content_layout.addLayout(left_col, stretch=2)
        right_col = QVBoxLayout()
        self.dashboard_layout = QVBoxLayout()
        right_col.addLayout(self.dashboard_layout)
        right_col.addWidget(self._build_attendance_log(), stretch=1)
        content_layout.addLayout(right_col, stretch=1)
        main_layout.addLayout(content_layout)
        self._build_dashboard_ui()
        self._update_dashboard()

    def _build_camera_panel(self):
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        self.video_label = QLabel('Camera Offline')
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setFont(QFont(FONT_FAMILY, 16))
        self.video_label.setStyleSheet(f'background-color: #000000; border-radius: 8px; color: {COLOR_TEXT_DIM};')
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setMinimumSize(640, 480)
        layout.addWidget(self.video_label, stretch=1)
        btn_layout = QHBoxLayout()
        self.btn_toggle_cam = QPushButton('▶  Start Camera')
        self.btn_toggle_cam.setObjectName('btn_toggle_cam')
        self.btn_toggle_cam.setFixedHeight(42)
        self.btn_toggle_cam.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_cam.clicked.connect(self._toggle_camera)
        btn_layout.addWidget(self.btn_toggle_cam)
        self.btn_recognize = QPushButton('🔍  Auto Recognize')
        self.btn_recognize.setObjectName('btn_recognize')
        self.btn_recognize.setFixedHeight(42)
        self.btn_recognize.setCursor(Qt.PointingHandCursor)
        self.btn_recognize.setCheckable(True)
        self.btn_recognize.clicked.connect(self._toggle_recognition)
        btn_layout.addWidget(self.btn_recognize)
        self.btn_enroll = QPushButton('➕  Enroll')
        self.btn_enroll.setObjectName('btn_enroll')
        self.btn_enroll.setFixedHeight(42)
        self.btn_enroll.setCursor(Qt.PointingHandCursor)
        self.btn_enroll.clicked.connect(self._open_enroll_dialog)
        btn_layout.addWidget(self.btn_enroll)
        self.btn_capture_frame = QPushButton('📷  Capture Face (C)')
        self.btn_capture_frame.setFixedHeight(42)
        self.btn_capture_frame.setCursor(Qt.PointingHandCursor)
        self.btn_capture_frame.clicked.connect(self._capture_face_frame)
        btn_layout.addWidget(self.btn_capture_frame)
        self.btn_manage = QPushButton('⚙️  Manage')
        self.btn_manage.setObjectName('btn_export')
        self.btn_manage.setFixedHeight(42)
        self.btn_manage.setCursor(Qt.PointingHandCursor)
        self.btn_manage.clicked.connect(self._open_manage_dialog)
        btn_layout.addWidget(self.btn_manage)
        layout.addLayout(btn_layout)
        self.status_label = QLabel('System Ready.')
        self.status_label.setFont(QFont(FONT_FAMILY, 10))
        self.status_label.setStyleSheet(f'color: {COLOR_TEXT_DIM}; border: none;')
        layout.addWidget(self.status_label)
        return panel

    def _create_stat_card(self, title, value, color):
        card = QFrame()
        card.setFixedHeight(100)
        c_lay = QVBoxLayout(card)
        c_lay.setAlignment(Qt.AlignCenter)
        t_lbl = QLabel(title)
        t_lbl.setFont(QFont(FONT_FAMILY, 10, QFont.Bold))
        t_lbl.setStyleSheet(f'color: {color}; border: none;')
        t_lbl.setAlignment(Qt.AlignCenter)
        v_lbl = QLabel(value)
        v_lbl.setFont(QFont(FONT_FAMILY, 24, QFont.Bold))
        v_lbl.setStyleSheet('border: none;')
        v_lbl.setAlignment(Qt.AlignCenter)
        c_lay.addWidget(t_lbl)
        c_lay.addWidget(v_lbl)
        return (card, v_lbl)

    def _build_dashboard_ui(self):
        self.stats_layout = QHBoxLayout()
        self.card_total = self._create_stat_card('Total Enrolled', '0', '#3F51B5')
        self.card_present = self._create_stat_card('Present Today', '0', '#4CAF50')
        self.card_absent = self._create_stat_card('Absent', '0', '#F44336')
        self.stats_layout.addWidget(self.card_total[0])
        self.stats_layout.addWidget(self.card_present[0])
        self.stats_layout.addWidget(self.card_absent[0])
        self.dashboard_layout.addLayout(self.stats_layout)

    def _build_attendance_log(self):
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 12, 15, 15)
        layout.setSpacing(8)
        header = QHBoxLayout()
        title = QLabel('📋  Attendance Log')
        title.setFont(QFont(FONT_FAMILY, 14, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        self.log_table = QTableWidget(0, 4)
        self.log_table.setHorizontalHeaderLabels(['ID', 'Name', 'Time', 'Score'])
        header = self.log_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.log_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.log_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.log_table)
        return frame

    def _set_status(self, text, color):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f'color: {color}; border: none;')

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_C:
            self._capture_face_frame()
            event.accept()
            return
        super().keyPressEvent(event)

    def _capture_face_frame(self):
        if self._last_primary_crop is None:
            self._set_status('Không có khuôn mặt hợp lệ để cắt frame.', COLOR_WARNING)
            return
        path = self.frame_extractor.capture_frame(self._last_primary_crop)
        if path:
            self._set_status(f'Đã lưu face frame: {os.path.basename(path)}', COLOR_SUCCESS)

    def _go_back(self):
        if self.is_camera_on:
            self._toggle_camera()
        self._finalize_attendance_sheet()
        self.main_window.show_setup()

    def _toggle_camera(self):
        if not self.is_camera_on:
            if not self.camera.start():
                self._set_status('❌ Failed to open camera!', COLOR_DANGER)
                return
            self.is_camera_on = True
            self.btn_toggle_cam.setText('⏹  Stop Camera')
            self.btn_toggle_cam.setStyleSheet('background-color: #D32F2F; color: white;')
            self._set_status('▶ Camera started.', COLOR_PRIMARY)
        else:
            self.camera.stop()
            self.is_camera_on = False
            self.btn_toggle_cam.setText('▶  Start Camera')
            self.btn_toggle_cam.setStyleSheet('')
            self.video_label.setText('Camera Offline')
            self.is_recognizing = False
            self.btn_recognize.setChecked(False)
            self._set_status('⏹ Camera stopped.', COLOR_TEXT_DIM)

    def _toggle_recognition(self):
        if not self.is_camera_on:
            self.btn_recognize.setChecked(False)
            self._set_status('⚠️ Turn on camera first!', COLOR_WARNING)
            return
        self.is_recognizing = self.btn_recognize.isChecked()
        if self.is_recognizing:
            self._set_status('🔍 Auto-recognition active.', COLOR_PRIMARY)
        else:
            self._invalidate_recognition()
            self._set_status('🔍 Auto-recognition stopped.', COLOR_TEXT_DIM)

    @staticmethod
    def _box_iou(first, second):
        ax, ay, aw, ah = first
        bx, by, bw, bh = second
        left, top = max(ax, bx), max(ay, by)
        right, bottom = min(ax + aw, bx + bw), min(ay + ah, by + bh)
        intersection = max(0, right - left) * max(0, bottom - top)
        union = aw * ah + bw * bh - intersection
        return intersection / union if union > 0 else 0.0

    def _invalidate_recognition(self):
        with self._recognition_lock:
            self._recognition_generation += 1
            self._recognition_results = []

    def _start_recognition(self, frame, detection):
        with self._recognition_lock:
            if self._recognition_busy:
                return
            self._recognition_busy = True
            self._recognition_generation += 1
            generation = self._recognition_generation
        self.last_recognition_time = time.time()
        threading.Thread(
            target=self._recognize_face,
            args=(frame.copy(), detection, generation),
            daemon=True,
        ).start()

    def _update_frame(self):
        if not self.is_camera_on:
            return
        frame = self.camera.get_frame()
        if frame is None:
            return
        processed_frame = (self.preprocessor.enhance(frame)
                           if ENABLE_PREPROCESSING else frame)
        display_frame = processed_frame.copy()
        if self._models_loaded and self.face_detector:
            self._frame_counter += 1
            # Chỉ chạy SCRFD mỗi 3 frame → giảm tải CPU 66%
            # Frame giữa dùng lại cached detections
            if self._frame_counter % 3 == 0 or not self._cached_detections:
                detections = self.face_detector.detect_faces(processed_frame)
                self._cached_detections = detections
            else:
                detections = self._cached_detections
            primary, blockers, incidental = self.face_detector.select_primary_face(
                detections, frame.shape,
                INCIDENTAL_FACE_MAX_FRAME_RATIO,
                INCIDENTAL_FACE_MAX_PRIMARY_RATIO,
            )
            # Multi-person: gom tất cả mặt thật (primary + blockers)
            real_faces = []
            if primary:
                real_faces.append(primary)
            real_faces.extend(blockers)
            incidental_set = set(id(d) for d in incidental)

            if not real_faces:
                self._invalidate_recognition()
            elif (self.is_recognizing and
                  time.time() - self.last_recognition_time > RECOGNITION_INTERVAL):
                # Round-robin: tìm mặt chưa có cache, nhận diện mặt đó
                with self._recognition_lock:
                    cached_list = list(self._recognition_results)
                for det in real_faces:
                    has_cache = False
                    for cached in cached_list:
                        if (cached['expires_at'] >= time.time() and
                                self._box_iou(det['box'], cached['box']) >= RECOGNITION_BOX_IOU_THRESHOLD):
                            has_cache = True
                            break
                    if not has_cache:
                        self._start_recognition(processed_frame, det)
                        break  # Mỗi interval chỉ gửi 1 mặt để không quá tải CPU

            # Crop primary face (mặt to nhất) cho nút Capture
            if primary:
                self._last_primary_crop = self.face_detector.crop_face(
                    processed_frame, primary['box'], padding=12
                )
            else:
                self._last_primary_crop = None

            # Vẽ khung + tên cho TẤT CẢ khuôn mặt
            for i, det in enumerate(detections):
                if id(det) in incidental_set:
                    continue  # Bỏ qua mặt rác (quá nhỏ)
                x, y, w, h = det['box']
                name_to_draw = 'Unknown'
                color = (0, 0, 255)
                if self.is_recognizing:
                    color = (0, 140, 255)  # Cam: đang xử lý
                    with self._recognition_lock:
                        for cached in self._recognition_results:
                            if (cached['expires_at'] >= time.time() and
                                    self._box_iou(det['box'], cached['box']) >= RECOGNITION_BOX_IOU_THRESHOLD):
                                name_to_draw = f"{cached['student_id']} - {cached['name']}"
                                color = (0, 255, 100)  # Xanh: đã nhận diện
                                break
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(display_frame, name_to_draw, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                BiometricsLogger.draw_face_features(display_frame, det, color)
        self._display_frame(display_frame)

    def _recognize_face(self, frame, det, generation):
        try:
            if not self.face_recognizer or self.slot_expired:
                return
            spoof_res = {'is_real': True, 'live_score': 1.0, 'label': 'LIVE'}
            if self.anti_spoof and self.anti_spoof.enabled and ANTISPOOF_ENABLED:
                spoof_res = self.anti_spoof.predict(frame, det['box'])
            if not spoof_res['is_real']:
                QTimer.singleShot(0, lambda: self._set_status('Fake face detected.', COLOR_DANGER))
                return

            result = self.face_recognizer.recognize(frame, det['raw'])
            if not result['matched']:
                return
            with self._recognition_lock:
                valid = (generation == self._recognition_generation and
                         self.is_recognizing and not self.slot_expired)
                if valid:
                    new_entry = {
                        'name': result['student_name'],
                        'student_id': result['student_id'],
                        'box': det['box'],
                        'expires_at': time.time() + RECOGNITION_RESULT_TTL,
                    }
                    # Xóa kết quả cũ hết hạn + cùng student_id (tránh trùng)
                    now = time.time()
                    self._recognition_results = [
                        r for r in self._recognition_results
                        if r['expires_at'] >= now and r['student_id'] != result['student_id']
                    ]
                    self._recognition_results.append(new_entry)
            if not valid:
                return

            student_dir = os.path.join(self.face_recognizer.dataset_dir, result['folder'])
            if result['student_id'] not in self._biometrics_logged:
                BiometricsLogger.log_attendance(student_dir, det['raw'], det['box'])
                self._biometrics_logged.add(result['student_id'])
            BiometricsLogger.mark_attendance_in_master_sheet(
                self.face_recognizer.dataset_dir, result['student_id'], self.session_col_name
            )
            if self.db.save_attendance(
                self.class_name, self.subject, result['student_id'],
                result['student_name'], result['score'], slot=self.slot_number
            ):
                QTimer.singleShot(0, lambda n=result['student_name']:
                                  self._set_status(f'{n} checked in!', COLOR_SUCCESS))
                QTimer.singleShot(0, self._update_dashboard)
        except Exception as exc:
            print(f'[ERROR] Recognition error: {exc}')
        finally:
            with self._recognition_lock:
                self._recognition_busy = False

    def _display_frame(self, frame):
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img).scaled(self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio)
        self.video_label.setPixmap(pixmap)

    def _open_enroll_dialog(self):
        if not self._models_loaded:
            self._set_status('Models still loading, please wait...', COLOR_WARNING)
            return
        dialog = EnrollDialog(
            self, self.camera, self.face_detector, self.face_recognizer,
            self.preprocessor
        )
        dialog.exec_()
        self._update_dashboard()

    def _open_manage_dialog(self):
        if not self._models_loaded:
            self._set_status('Models still loading, please wait...', COLOR_WARNING)
            return
        dialog = ManageDialog(self, self.face_recognizer, self.db)
        dialog.exec_()
        self._update_dashboard()

    def _update_dashboard(self):
        if self.face_recognizer:
            total = len(self.face_recognizer.get_all_students())
        else:
            total = 0
        present = self.db.get_today_count(class_name=self.class_name, subject=self.subject, slot=self.slot_number)
        absent = max(0, total - present)
        self.card_total[1].setText(str(total))
        self.card_present[1].setText(str(present))
        self.card_absent[1].setText(str(absent))
        self._update_log_table()

    def _update_log_table(self):
        records = self.db.get_attendance_today(self.class_name, self.subject, slot=self.slot_number)
        self.log_table.setRowCount(0)
        for row, (c_name, subj, sid, name, ts, conf) in enumerate(records):
            self.log_table.insertRow(row)
            self.log_table.setItem(row, 0, QTableWidgetItem(sid))
            self.log_table.setItem(row, 1, QTableWidgetItem(name))
            time_only = ts.split(' ')[1] if ' ' in ts else ts
            self.log_table.setItem(row, 2, QTableWidgetItem(time_only))
            conf_str = f'{conf:.1%}' if conf else 'N/A'
            self.log_table.setItem(row, 3, QTableWidgetItem(conf_str))

    def _finalize_attendance_sheet(self):
        all_enrolled = self.face_recognizer.get_all_students() if self.face_recognizer else []
        enrolled_dict = {str(s['id']): s['name'] for s in all_enrolled}
        excel_path = os.path.join(self.face_recognizer.dataset_dir, 'attendance.xlsx')
        try:
            import pandas as pd
            if os.path.exists(excel_path):
                df = pd.read_excel(excel_path)
            else:
                df = pd.DataFrame(columns=['Student ID', 'Student Name'])
            if not df.empty:
                df['Student ID'] = df['Student ID'].astype(str)
            else:
                df['Student ID'] = pd.Series(dtype='str')
            if self.session_col_name not in df.columns:
                df[self.session_col_name] = ''
            for sid, sname in enrolled_dict.items():
                if sid not in df['Student ID'].values:
                    new_row = {'Student ID': sid, 'Student Name': sname, self.session_col_name: 'X (Absent)'}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

            def fill_absent(val):
                if pd.isna(val) or str(val).strip() == '':
                    return 'X (Absent)'
                return val
            df[self.session_col_name] = df[self.session_col_name].apply(fill_absent)
            df.to_excel(excel_path, index=False)
        except Exception as e:
            print(f'[ERROR] Cannot finalize attendance sheet: {e}')
