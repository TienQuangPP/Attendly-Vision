import cv2
import os
from datetime import datetime

class FrameExtractor:

    def __init__(self, output_dir='frames'):
        self.output_dir = output_dir
        self.frame_count = 0
        os.makedirs(output_dir, exist_ok=True)

    def capture_frame(self, frame):
        if frame is None:
            return None
        self.frame_count += 1
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'frame_{timestamp}_{self.frame_count:04d}.jpg'
        filepath = os.path.join(self.output_dir, filename)
        cv2.imwrite(filepath, frame)
        return filepath

