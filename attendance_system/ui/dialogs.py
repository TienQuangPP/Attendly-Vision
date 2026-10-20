import os
import cv2
import json
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from config import (COLOR_BG_DARK, COLOR_BG_CARD, COLOR_TEXT, COLOR_PRIMARY,
                    COLOR_BORDER, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                    FONT_FAMILY, COLOR_TEXT_DIM, SESSIONS_FILE,
                    INCIDENTAL_FACE_MAX_FRAME_RATIO,
                    INCIDENTAL_FACE_MAX_PRIMARY_RATIO, ENABLE_PREPROCESSING)
from functions.biometrics_logger import BiometricsLogger

class CreateSessionDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Khởi tạo Lớp/Môn Mới')
        self.setFixedSize(400, 250)
        self.setStyleSheet(f'background-color: {COLOR_BG_DARK}; color: {COLOR_TEXT};')
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Tên Lớp (VD: SE1501):'))
        self.class_input = QLineEdit()
        self.class_input.setStyleSheet(f'background-color: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; padding: 5px;')
        layout.addWidget(self.class_input)
        layout.addWidget(QLabel('Môn Học (VD: CPV301):'))
        self.subj_input = QLineEdit()
        self.subj_input.setStyleSheet(f'background-color: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; padding: 5px;')
        layout.addWidget(self.subj_input)
        self.err = QLabel('')
        self.err.setStyleSheet(f'color: {COLOR_DANGER};')
        layout.addWidget(self.err)
        btns = QHBoxLayout()
        save = QPushButton('💾 Khởi tạo')
        save.setStyleSheet(f'background-color: {COLOR_PRIMARY}; font-weight: bold; padding: 8px;')
        save.clicked.connect(self.save)
        btns.addWidget(save)
        cancel = QPushButton('❌ Hủy')
        cancel.setStyleSheet('padding: 8px;')
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        layout.addLayout(btns)

    def save(self):
        c = self.class_input.text().strip().upper()
        s = self.subj_input.text().strip().upper()
        if not c or not s:
            self.err.setText('Vui lòng điền đủ Lớp và Môn!')
            return
        sessions = []
        if os.path.exists(SESSIONS_FILE):
            try:
                with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                    sessions = json.load(f)
            except (OSError, json.JSONDecodeError):
                pass
        for sess in sessions:
            if sess.get('class') == c and sess.get('subject') == s:
                self.err.setText('Phiên học này đã tồn tại!')
                return
        sessions.append({'class': c, 'subject': s})
        with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(sessions, f, ensure_ascii=False, indent=4)
        self.accept()
class EnrollDialog(QDialog):

    def __init__(self, parent, camera, face_detector, face_recognizer,
                 preprocessor=None):
        super().__init__(parent)
        self.camera = camera
        self.face_detector = face_detector
        self.face_recognizer = face_recognizer
        self.preprocessor = preprocessor
        self._enrolling = False
        self._single_face_frames = 0
        self.setWindowTitle('📸 Đăng ký khuôn mặt')
        self.setFixedSize(480, 520)
        self.setStyleSheet(f'background-color: {COLOR_BG_DARK}; color: {COLOR_TEXT};')
        self._build_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_feed)
        self.timer.start(30)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setFixedSize(340, 260)
        self.video_label.setStyleSheet('background-color: #000; border-radius: 10px;')
        layout.addWidget(self.video_label, alignment=Qt.AlignCenter)
        self.quality_label = QLabel('⏳ Đang chờ phát hiện khuôn mặt...')
        self.quality_label.setAlignment(Qt.AlignCenter)
        self.quality_label.setFont(QFont(FONT_FAMILY, 10))
        self.quality_label.setStyleSheet(f'color: {COLOR_TEXT_DIM};')
        layout.addWidget(self.quality_label)
        form = QGridLayout()
        form.addWidget(QLabel('Student ID:'), 0, 0)
        self.id_entry = QLineEdit()
        self.id_entry.setStyleSheet(f'background-color: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; padding: 6px;')
        form.addWidget(self.id_entry, 0, 1)
        form.addWidget(QLabel('Full Name:'), 1, 0)
        self.name_entry = QLineEdit()
        self.name_entry.setStyleSheet(f'background-color: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; padding: 6px;')
        form.addWidget(self.name_entry, 1, 1)
        layout.addLayout(form)
        self.btn_capture = QPushButton('📸 Chụp & Đăng ký ngay')
        self.btn_capture.setFixedHeight(46)
        self.btn_capture.setFont(QFont(FONT_FAMILY, 12, QFont.Bold))
        self.btn_capture.setStyleSheet(f'background-color: {COLOR_PRIMARY};')
        self.btn_capture.clicked.connect(self._capture_and_enroll)
        layout.addWidget(self.btn_capture)
        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont(FONT_FAMILY, 10))
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    def _update_feed(self):
        frame = self.camera.get_frame()
        if frame is None:
            return
        frame = self.preprocessor.enhance(frame) if self.preprocessor and ENABLE_PREPROCESSING else frame
        self.current_frame = frame.copy()
        display = frame.copy()
        if self.face_detector:
            dets = self.face_detector.detect_faces(display)
            primary, blockers, incidental = self.face_detector.select_primary_face(
                dets, display.shape,
                INCIDENTAL_FACE_MAX_FRAME_RATIO,
                INCIDENTAL_FACE_MAX_PRIMARY_RATIO,
            )
            if dets:
                if blockers:
                    self._single_face_frames = 0
                    for det in dets:
                        x, y, w, h = det['box']
                        cv2.rectangle(display, (x, y), (x+w, y+h), (255, 165, 0), 2)
                    self.quality_label.setText("⚠️ Yêu cầu chỉ đứng 1 người!")
                    self.quality_label.setStyleSheet(f"color: {COLOR_WARNING};")
                else:
                    det = primary
                    x, y, w, h = det['box']
                    ratio = (w * h) / (display.shape[0] * display.shape[1])
                    if ratio > 0.03:
                        self._single_face_frames += 1
                        cv2.rectangle(display, (x, y), (x+w, y+h), (0, 220, 80), 2)
                        self.quality_label.setText('✅ Khuôn mặt OK – Nhìn thẳng và bấm Chụp!')
                        self.quality_label.setStyleSheet(f'color: {COLOR_SUCCESS};')
                        BiometricsLogger.draw_face_features(display, det, (0, 220, 80))
                    else:
                        self._single_face_frames = 0
                        cv2.rectangle(display, (x, y), (x+w, y+h), (255, 165, 0), 2)
                        self.quality_label.setText('⚠️ Lại gần camera hơn!')
                        self.quality_label.setStyleSheet(f'color: {COLOR_WARNING};')
                        BiometricsLogger.draw_face_features(display, det, (255, 165, 0))
            else:
                self._single_face_frames = 0
                self.quality_label.setText('⏳ Không phát hiện khuôn mặt...')
                self.quality_label.setStyleSheet(f'color: {COLOR_TEXT_DIM};')
        rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        self.video_label.setPixmap(QPixmap.fromImage(QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)).scaled(340, 260, Qt.KeepAspectRatio))

    def _capture_and_enroll(self):
        if self._enrolling:
            return
        student_id = self.id_entry.text().strip()
        student_name = self.name_entry.text().strip()
        if not student_id or not student_name:
            self._status('⚠️ Vui lòng điền đủ ID và Tên!', COLOR_DANGER)
            return
        for s in self.face_recognizer.get_all_students():
            if s['id'].upper() == student_id.upper():
                self._status(f"⚠️ ID '{student_id}' đã tồn tại!", COLOR_DANGER)
                return
        if not hasattr(self, 'current_frame') or not self.face_detector:
            self._status('❌ Camera chưa sẵn sàng!', COLOR_DANGER)
            return
        dets = self.face_detector.detect_faces(self.current_frame)
        if not dets:
            self._status('❌ Không tìm thấy khuôn mặt – thử lại!', COLOR_DANGER)
            return
            
        primary, blockers, _ = self.face_detector.select_primary_face(
            dets, self.current_frame.shape,
            INCIDENTAL_FACE_MAX_FRAME_RATIO,
            INCIDENTAL_FACE_MAX_PRIMARY_RATIO,
        )
        if blockers:
            self._status('❌ Quá nhiều người! Vui lòng chỉ đứng 1 người để đăng ký.', COLOR_DANGER)
            return
        if self._single_face_frames < 3:
            self._status('Giữ một mình trong khung hình thêm một chút rồi thử lại.', COLOR_WARNING)
            return
            
        det = primary
        raw = det['raw']
        if not (hasattr(raw, 'embedding') and raw.embedding is not None):
            self._status('❌ Không trích xuất được embedding – thử lại!', COLOR_DANGER)
            return
        emb = raw.embedding.flatten()
        match = self.face_recognizer.recognize_embedding(emb.reshape(1, -1))
        if match['matched']:
            self._status(f"⚠️ Khuôn mặt đã đăng ký: {match['student_id']} ({match['student_name']})", COLOR_DANGER)
            return
        if match['score'] >= self.face_recognizer.threshold:
            self._status('Khuôn mặt quá giống dữ liệu đã có; không thể đăng ký an toàn.', COLOR_DANGER)
            return
        x, y, w, h = det['box']
        x, y = (max(0, x), max(0, y))
        crop = self.current_frame[y:y + h, x:x + w].copy()
        class_name = getattr(self.parent(), 'class_name', 'UnknownClass')
        self._enrolling = True
        self.btn_capture.setEnabled(False)
        try:
            enrolled = self.face_recognizer.enroll_student(
                class_name, student_id, student_name, [emb], [crop]
            )
        except (OSError, ValueError) as exc:
            self._status(f'Không thể đăng ký: {exc}', COLOR_DANGER)
            self._enrolling = False
            self.btn_capture.setEnabled(True)
            return
        if not enrolled:
            self._status('Không thể đăng ký: ID hoặc khuôn mặt đã tồn tại.', COLOR_DANGER)
            self._enrolling = False
            self.btn_capture.setEnabled(True)
            return
        safe_name = student_name.replace(' ', '_')
        student_dir = os.path.join(self.face_recognizer.dataset_dir, f'{class_name}_{student_id}_{safe_name}')
        BiometricsLogger.create_enroll_log(student_dir, raw, det['box'])
        BiometricsLogger.add_student_to_master_sheet(self.face_recognizer.dataset_dir, student_id, student_name)
        self._status(f'✅ Đăng ký thành công: {student_name}!', COLOR_SUCCESS)
        QTimer.singleShot(1200, self.close)

    def _status(self, text, color):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f'color: {color};')

class ManageDialog(QDialog):

    def __init__(self, parent, face_recognizer, db):
        super().__init__(parent)
        self.face_recognizer = face_recognizer
        self.db = db
        self.setWindowTitle('⚙️ Quản lý Sinh viên')
        self.setFixedSize(620, 520)
        self.setStyleSheet(f'background-color: {COLOR_BG_DARK}; color: {COLOR_TEXT};')
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel('Quản lý Sinh viên trong Lớp')
        title.setFont(QFont(FONT_FAMILY, 16, QFont.Bold))
        layout.addWidget(title)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container.setStyleSheet('background-color: transparent;')
        self.table_layout = QVBoxLayout(container)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        self.refresh_list()
        close_btn = QPushButton('Đóng')
        close_btn.setStyleSheet(f'background-color: {COLOR_BG_CARD};')
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

    def refresh_list(self):
        while self.table_layout.count():
            item = self.table_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        students = self.face_recognizer.get_all_students()
        if not students:
            self.table_layout.addWidget(QLabel('Chưa có sinh viên nào.'))
        for s in students:
            row = QFrame()
            row.setStyleSheet(f'background-color: {COLOR_BG_CARD}; border-radius: 5px;')
            r_lay = QHBoxLayout(row)
            n_emb = self._count_embeddings(s['folder'])
            info = QLabel(f"{s['id']} – {s['name']}  <span style='color:{COLOR_TEXT_DIM}; font-size:10px'>({n_emb} emb)</span>")
            info.setTextFormat(Qt.RichText)
            r_lay.addWidget(info, stretch=1)
            edit_btn = QPushButton('✏️ Sửa')
            edit_btn.setStyleSheet(f'background-color: {COLOR_WARNING};')
            edit_btn.clicked.connect(lambda checked, st=s: self.edit_student(st))
            r_lay.addWidget(edit_btn)
            del_btn = QPushButton('🗑 Xóa')
            del_btn.setStyleSheet(f'background-color: {COLOR_DANGER};')
            del_btn.clicked.connect(lambda checked, st=s: self.delete_student(st))
            r_lay.addWidget(del_btn)
            self.table_layout.addWidget(row)
        self.table_layout.addStretch()

    def _count_embeddings(self, folder):
        try:
            emb_path = os.path.join(self.face_recognizer.dataset_dir, folder, 'embeddings.npy')
            if os.path.exists(emb_path):
                return np.load(emb_path).shape[0]
        except (OSError, ValueError):
            pass
        return 0

    def edit_student(self, student):
        dialog = EditDialog(self, student, self.face_recognizer, self.db)
        if dialog.exec_():
            self.refresh_list()
            if self.parent() and hasattr(self.parent(), '_update_dashboard'):
                self.parent()._update_dashboard()

    def delete_student(self, student):
        reply = QMessageBox.question(self, 'Xác nhận xóa', f"Xóa sinh viên {student['id']} - {student['name']}?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.face_recognizer.remove_student(student['folder'])
            self.refresh_list()
            if self.parent() and hasattr(self.parent(), '_update_dashboard'):
                self.parent()._update_dashboard()

class EditDialog(QDialog):

    def __init__(self, parent, student, face_recognizer, db):
        super().__init__(parent)
        self.student = student
        self.face_recognizer = face_recognizer
        self.db = db
        self.setWindowTitle('✏️ Sửa thông tin')
        self.setFixedSize(400, 250)
        self.setStyleSheet(f'background-color: {COLOR_BG_DARK}; color: {COLOR_TEXT};')
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Mã Sinh viên mới:'))
        self.id_input = QLineEdit(student['id'])
        layout.addWidget(self.id_input)
        layout.addWidget(QLabel('Tên Sinh viên mới:'))
        self.name_input = QLineEdit(student['name'])
        layout.addWidget(self.name_input)
        self.err = QLabel('')
        self.err.setStyleSheet(f'color: {COLOR_DANGER};')
        layout.addWidget(self.err)
        btns = QHBoxLayout()
        save = QPushButton('💾 Lưu')
        save.setStyleSheet(f'background-color: {COLOR_SUCCESS};')
        save.clicked.connect(self.save)
        btns.addWidget(save)
        cancel = QPushButton('❌ Hủy')
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        layout.addLayout(btns)

    def save(self):
        new_id = self.id_input.text().strip().upper()
        new_name = self.name_input.text().strip()
        if not new_id or not new_name:
            self.err.setText('Vui lòng điền đủ thông tin!')
            return
        if new_id != self.student['id'].upper():
            for s in self.face_recognizer.get_all_students():
                if s['id'].upper() == new_id:
                    self.err.setText(f"ID '{new_id}' đã tồn tại!")
                    return
        success = self.face_recognizer.edit_student(
            self.student['folder'], self.student['class'], new_id, new_name
        )
        if success:
            self.db.update_student_info(
                self.student['id'], self.student['class'], new_id, new_name
            )
            self.accept()
        else:
            self.err.setText('Có lỗi xảy ra!')
