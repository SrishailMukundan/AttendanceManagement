import math
import time
from luma.core.render import canvas
from PIL import Image, ImageDraw, ImageFont

class UIManager:
    def __init__(self, device):
        self.device = device
        self.font_small = ImageFont.load_default()
        self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        # Load your images here (rfid_img, finger_img, etc.)

    def draw_loading_bar(self, draw, progress):
        x, y, width, height = 14, 40, 100, 8
        draw.rectangle((x, y, x + width, y + height), outline=255, fill=0)
        fill_width = int((progress / 100) * (width - 2))
        if fill_width > 0:
            draw.rectangle((x + 1, y + 1, x + fill_width, y + height - 1), outline=0, fill=255)

    def render_home(self, menu_index):
        with canvas(self.device) as draw:
            draw.text((0, 2), "SPB Front Office", fill=255, font=self.font_large)
            # Add the rest of your rectangle/text logic for HOME state...
