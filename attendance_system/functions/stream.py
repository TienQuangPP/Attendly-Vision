import cv2
import threading
import time

class CameraStream:

    def __init__(self, source=0):
        self.source = source
        self.cap = None
        self.frame = None
        self.is_running = False
        self.thread = None
        self.lock = threading.Lock()
        self.fps = 0
        self._frame_count = 0
        self._fps_timer = time.time()
        self.last_error = None

    def _open_capture(self):
        backend = cv2.CAP_FFMPEG if isinstance(self.source, str) else cv2.CAP_ANY
        cap = cv2.VideoCapture(self.source, backend)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            return cap
        cap.release()
        return None

    def start(self):
        if self.is_running:
            return True
        self.cap = self._open_capture()
        if self.cap is None:
            self.last_error = 'Cannot open camera source'
            print('[ERROR] Cannot open camera source.')
            return False
        self.is_running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        print('[INFO] Camera stream started.')
        return True

    def _update_loop(self):
        while self.is_running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame
                self._frame_count += 1
                elapsed = time.time() - self._fps_timer
                if elapsed >= 1.0:
                    self.fps = self._frame_count / elapsed
                    self._frame_count = 0
                    self._fps_timer = time.time()
            else:
                self.last_error = 'Stream interrupted; reconnecting'
                time.sleep(0.5)
                old_cap = self.cap
                replacement = self._open_capture()
                if replacement is not None:
                    if not self.is_running:
                        replacement.release()
                        break
                    with self.lock:
                        self.cap = replacement
                    if old_cap is not None:
                        old_cap.release()
                    self.last_error = None

    def get_frame(self):
        with self.lock:
            if self.frame is not None:
                return self.frame.copy()
        return None

    def stop(self):
        self.is_running = False
        if self.thread is not None:
            self.thread.join(timeout=2)
        if self.cap is not None:
            self.cap.release()
        self.frame = None
        self.cap = None
        print('[INFO] Camera stream stopped.')

    def __del__(self):
        self.stop()
