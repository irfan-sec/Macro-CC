import cv2
import numpy as np
import pyautogui
import pytesseract
from PIL import Image
import os

class ScreenUtils:
    """Utility class for screen image recognition and OCR."""

    @staticmethod
    def find_image_on_screen(template_path: str, threshold: float = 0.8) -> tuple[int, int] | None:
        """
        Locates an image template on the screen.
        Returns the (x, y) center coordinates of the match, or None if not found.
        """
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Image template not found: {template_path}")

        # Take a screenshot
        screenshot = pyautogui.screenshot()
        screen_np = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_np, cv2.COLOR_RGB2GRAY)

        # Load template
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            raise ValueError(f"Could not load template image: {template_path}")

        w, h = template.shape[::-1]

        # Template matching
        res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        if max_val >= threshold:
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return center_x, center_y

        return None

    @staticmethod
    def extract_text_from_screen(region: tuple[int, int, int, int] = None) -> str:
        """
        Extracts text from the screen (or a specific region) using Tesseract OCR.
        region: (x, y, width, height)
        """
        # Take a screenshot
        screenshot = pyautogui.screenshot(region=region)
        
        # We assume pytesseract is in the PATH or installed system-wide.
        # On Windows, you might need to set pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        # but we'll try the default first.
        try:
            text = pytesseract.image_to_string(screenshot)
            return text.strip()
        except Exception as e:
            print(f"[ScreenUtils] OCR Error: {e}")
            return ""

    @staticmethod
    def find_text_on_screen(target_text: str, region: tuple[int, int, int, int] = None) -> bool:
        """
        Checks if specific text exists currently on the screen.
        """
        extracted = ScreenUtils.extract_text_from_screen(region)
        return target_text.lower() in extracted.lower()
