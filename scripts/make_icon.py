"""Generate assets/icon.ico programmatically using PIL."""

from PIL import Image, ImageDraw
import os

os.makedirs("assets", exist_ok=True)

img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Dark background circle
draw.ellipse([8, 8, 248, 248], fill="#1a1a2e")

# Accent inner circle
draw.ellipse([40, 40, 216, 216], fill="#e94560")

# White mouse cursor arrow
draw.polygon(
    [(90, 70), (90, 186), (120, 160), (145, 210), (162, 202), (137, 148), (172, 148)],
    fill="white",
)

img.save(
    "assets/icon.ico",
    format="ICO",
    sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)],
)
print("Icon saved.")
