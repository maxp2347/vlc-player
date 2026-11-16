import math
import os
import struct
from io import BytesIO

from PIL import Image, ImageDraw

SIZES = {
    "1280x720": (1280, 720),
    "1920x1080": (1920, 1080),
    "2560x1440": (2560, 1440),
    "3840x2160": (3840, 2160),
    "720x576": (720, 576),
    "640x360": (640, 360),
}

STATIC_MIRE_TYPES = [
    "Barres SMPTE",
    "Grille",
    "Échelle de gris",
    "Focus",
    "Rouge",
    "Vert",
    "Bleu",
    "Blanc",
    "Noir",
]

DYNAMIC_MIRE_TYPES = [
    "Barre défilante",
    "Damier clignotant",
    "Cercle rotatif",
]

FPS_CHOICES = [25, 30, 50, 60]


def generate_static(kind, size, folder):
    width, height = SIZES.get(size, SIZES["1920x1080"])
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    if kind == "Barres SMPTE":
        _draw_smpte(draw, width, height)
    elif kind == "Grille":
        _draw_grid(draw, width, height)
    elif kind == "Échelle de gris":
        _draw_gray(draw, width, height)
    elif kind == "Focus":
        _draw_focus(draw, width, height)
    else:
        colors = {
            "Rouge": (255, 0, 0), "Vert": (0, 255, 0), "Bleu": (0, 0, 255),
            "Blanc": (255, 255, 255), "Noir": (0, 0, 0),
        }
        draw.rectangle([0, 0, width, height], fill=colors[kind])
    name = f"mire_{_slug(kind)}_{width}x{height}.png"
    path = os.path.join(folder, name)
    os.makedirs(folder, exist_ok=True)
    image.save(path)
    return path


def generate_dynamic(kind, size, fps, duration_s, rate_hz, folder):
    width, height = SIZES.get(size, SIZES["1920x1080"])
    fps = int(fps)
    frames = max(1, int(fps * duration_s))
    rate_hz = float(rate_hz) if rate_hz else 1.0
    name = f"mire_{_slug(kind)}_{width}x{height}_{fps}fps_{rate_hz:g}Hz.avi"
    path = os.path.join(folder, name)
    os.makedirs(folder, exist_ok=True)
    writer = _MjpegAviWriter(path, width, height, fps)
    for i in range(frames):
        image = Image.new("RGB", (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        if kind == "Barre défilante":
            _draw_moving_bar(draw, width, height, i, frames)
        elif kind == "Damier clignotant":
            _draw_blinking_checker(draw, width, height, i, fps, rate_hz)
        elif kind == "Cercle rotatif":
            _draw_rotating_circle(draw, width, height, i, frames)
        writer.write(image)
    writer.close()
    return path


def _slug(text):
    for a, b in (("é", "e"), ("è", "e"), ("ê", "e"), ("à", "a"), ("ç", "c"), (" ", "_")):
        text = text.replace(a, b)
    return "".join(c if c.isalnum() or c == "_" else "" for c in text.lower())


def _draw_smpte(draw, w, h):
    bars = [(255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0),
            (255, 0, 255), (255, 0, 0), (0, 0, 255)]
    top = int(h * 0.67)
    bar_w = w / len(bars)
    for i, color in enumerate(bars):
        draw.rectangle([int(i * bar_w), 0, int((i + 1) * bar_w) - 1, top], fill=color)
    bottom_bars = [(0, 0, 255), (19, 19, 19), (255, 0, 255), (19, 19, 19),
                   (0, 255, 255), (19, 19, 19), (255, 255, 255)]
    mid = int(h * 0.08)
    for i, color in enumerate(bottom_bars):
        draw.rectangle([int(i * bar_w), top, int((i + 1) * bar_w) - 1, top + mid], fill=color)
    steps = [int(255 * i / 5) for i in range(6)]
    y0 = top + mid
    seg = w / 6
    for i, v in enumerate(steps):
        draw.rectangle([int(i * seg), y0, int((i + 1) * seg) - 1, h], fill=(v, v, v))


def _draw_grid(draw, w, h):
    draw.rectangle([0, 0, w, h], fill=(0, 0, 0))
    step_x, step_y = w / 12, h / 8
    for i in range(13):
        x = int(i * step_x)
        draw.line([(x, 0), (x, h)], fill=(255, 255, 255), width=1 if i % 3 else 3)
    for j in range(9):
        y = int(j * step_y)
        draw.line([(0, y), (w, y)], fill=(255, 255, 255), width=1 if j % 2 else 3)
    draw.line([(w // 2 - 20, h // 2), (w // 2 + 20, h // 2)], fill=(255, 0, 0), width=3)
    draw.line([(w // 2, h // 2 - 20), (w // 2, h // 2 + 20)], fill=(255, 0, 0), width=3)


def _draw_gray(draw, w, h):
    steps = 11
    seg = w / steps
    for i in range(steps):
        v = int(255 * i / (steps - 1))
        draw.rectangle([int(i * seg), 0, int((i + 1) * seg) - 1, h], fill=(v, v, v))


def _draw_focus(draw, w, h):
    draw.rectangle([0, 0, w, h], fill=(0, 0, 0))
    cx, cy = w // 2, h // 2
    radius = min(w, h) // 2 - 10
    ring = max(4, radius // 12)
    for r in range(radius, 0, -ring):
        color = (255, 255, 255) if (r // ring) % 2 else (0, 0, 0)
        draw.ellipse([cx - r, cy - r // 2, cx + r, cy + r // 2], outline=color, width=2)
    for x in range(0, w, 24):
        draw.line([(x, 0), (x, h)], fill=(60, 60, 60), width=1)
    for y in range(0, h, 24):
        draw.line([(0, y), (w, y)], fill=(60, 60, 60), width=1)
    draw.line([(cx - 40, cy), (cx + 40, cy)], fill=(255, 0, 0), width=3)
    draw.line([(cx, cy - 40), (cx, cy + 40)], fill=(255, 0, 0), width=3)


def _draw_moving_bar(draw, w, h, i, frames):
    bar_w = max(8, w // 20)
    x = int(i * (w + bar_w) / frames) - bar_w
    draw.rectangle([x, 0, x + bar_w, h], fill=(255, 255, 255))


def _draw_blinking_checker(draw, w, h, i, fps, rate_hz):
    phase = int((i * rate_hz / fps) % 2)
    cells_x, cells_y = 8, 5
    cw, ch = w / cells_x, h / cells_y
    for cx in range(cells_x):
        for cy in range(cells_y):
            if (cx + cy + phase) % 2 == 0:
                draw.rectangle(
                    [int(cx * cw), int(cy * ch), int((cx + 1) * cw) - 1, int((cy + 1) * ch) - 1],
                    fill=(255, 255, 255),
                )


def _draw_rotating_circle(draw, w, h, i, frames):
    cx, cy = w // 2, h // 2
    r = min(w, h) // 3
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255), width=3)
    angle = 2 * math.pi * i / frames
    draw.line(
        [(cx, cy), (cx + int(r * math.cos(angle)), cy + int(r * math.sin(angle)))],
        fill=(255, 255, 0), width=4,
    )


class _MjpegAviWriter:
    def __init__(self, path, width, height, fps):
        self.path = path
        self.width = width
        self.height = height
        self.fps = fps
        self.frames = 0
        self.bytes_written = 0
        self._index = []
        self.f = open(path, "wb")
        self._write_header()

    def _write_header(self):
        f = self.f
        f.write(b"RIFF" + struct.pack("<I", 0) + b"AVI ")
        f.write(b"LIST" + struct.pack("<I", 192) + b"hdrl")
        f.write(b"avih" + struct.pack("<I", 56) + struct.pack(
            "<14I",
            int(1_000_000 / self.fps), 0, 0, 0x10, 0, 0, 1, 0,
            self.width, self.height, 0, 0, 0, 0,
        ))
        f.write(b"LIST" + struct.pack("<I", 116) + b"strl")
        f.write(b"strh" + struct.pack("<I", 56) + b"vidsMJPG" + struct.pack(
            "<IHHIIIIIIII4h",
            0, 0, 0, 0, 1, self.fps, 0, 0, 0, 10000, 0, 0, 0,
            self.width, self.height,
        ))
        f.write(b"strf" + struct.pack("<I", 40) + struct.pack(
            "<IiiHHIIiiII", 40, self.width, self.height, 1, 24, 0x47504A4D,
            self.width * self.height * 3, 0, 0, 0, 0,
        ))
        f.write(b"LIST" + struct.pack("<I", 0) + b"movi")

    def write(self, image):
        buf = BytesIO()
        image.save(buf, "JPEG", quality=90)
        data = buf.getvalue()
        if len(data) % 2:
            data += b"\x00"
        offset = self.f.tell() - 220
        self.f.write(b"00dc" + struct.pack("<I", len(data)) + data)
        self._index.append((b"00dc", 0x10, offset, len(data)))
        self.frames += 1
        self.bytes_written += len(data) + 8

    def close(self):
        f = self.f
        f.write(b"idx1" + struct.pack("<I", 16 * len(self._index)))
        for fourcc, flags, offset, size in self._index:
            f.write(fourcc + struct.pack("<III", flags, offset, size))
        file_size = f.tell()
        movi_size = 4 + self.bytes_written
        f.seek(4)
        f.write(struct.pack("<I", file_size - 8))
        f.seek(216)
        f.write(struct.pack("<I", movi_size))
        f.seek(32 + 16)
        f.write(struct.pack("<I", self.frames))
        f.seek(108 + 32)
        f.write(struct.pack("<i", self.frames))
        f.close()
