"""Gera um ícone placeholder em resources/icon.ico para o Electron."""
import os
from PIL import Image, ImageDraw, ImageFont

os.makedirs("resources", exist_ok=True)

sizes = [256, 128, 64, 32, 16]
images = []

for size in sizes:
    img = Image.new('RGBA', (size, size), (45, 127, 249, 255))
    draw = ImageDraw.Draw(img)

    try:
        font_size = max(size // 3, 10)
        font = ImageFont.truetype("arial.ttf", font_size)
    except (OSError, IOError):
        font = ImageFont.load_default()

    draw.text(
        (size // 2, size // 2),
        "ZP",
        fill="white",
        anchor="mm",
        font=font
    )
    images.append(img)

images[0].save(
    "resources/icon.ico",
    format="ICO",
    sizes=[(s, s) for s in sizes]
)
print("Ícone criado em resources/icon.ico")
