import cv2

class Preprocessor:

    def __init__(self, face_size=(160, 160), gaussian_kernel=(5, 5), clahe_clip=2.0, clahe_grid=(8, 8)):
        self.face_size = face_size
        self.gaussian_kernel = gaussian_kernel
        self.clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=clahe_grid)

    def preprocess(self, face_img):
        if face_img is None or face_img.size == 0:
            return None
        processed = self.resize(face_img)
        processed = self.denoise(processed)
        processed = self.light_balance(processed)
        return processed

    def enhance(self, image):
        """Denoise and balance lighting without changing frame dimensions."""
        if image is None or image.size == 0:
            return None
        return self.light_balance(self.denoise(image))

    def resize(self, image):
        return cv2.resize(image, self.face_size, interpolation=cv2.INTER_AREA)

    def denoise(self, image):
        return cv2.GaussianBlur(image, self.gaussian_kernel, 0)

    def light_balance(self, image):
        if len(image.shape) == 2:
            return self.clahe.apply(image)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        channels = list(cv2.split(lab))
        channels[0] = self.clahe.apply(channels[0])
        lab = cv2.merge(channels)
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

