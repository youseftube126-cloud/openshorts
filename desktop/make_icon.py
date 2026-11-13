"""Draw the Vexxo Clip logo and write desktop/vexxo.ico (+ vexxo.png).

Run during the Windows build (before Inno Setup) so no binary file has to live
in the repository:  python desktop/make_icon.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SIZE = 1024  # drawn large, then downscaled for smooth edges


def _gradient(size, c1, c2):
    """Diagonal gradient from the top-left (c1) to the bottom-right (c2)."""
    grad = Image.new("RGB", (size, size))
    px = grad.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            px[x, y] = tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))
    return grad


def draw(size=SIZE):
    scale = size / 32.0
    tile = _gradient(size, (0x9A, 0x8C, 0xFF), (0x3B, 0x82, 0xF6)).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=9 * scale, fill=255)
    tile.putalpha(mask)

    stroke = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(stroke)
    w = round(3.4 * scale)

    def line(p, q, alpha):
        d.line([p[0] * scale, p[1] * scale, q[0] * scale, q[1] * scale], fill=(255, 255, 255, alpha), width=w)
        for x, y in (p, q):                       # round caps
            r = w / 2
            d.ellipse([x * scale - r, y * scale - r, x * scale + r, y * scale + r], fill=(255, 255, 255, alpha))

    line((8.5, 9.5), (14.6, 22.3), 255)
    line((17.4, 22.3), (23.5, 9.5), 184)          # right stroke at 72% like the in-app logo
    tile.alpha_composite(stroke)
    return tile


def main():
    img = draw()
    sizes = [16, 24, 32, 48, 64, 128, 256]
    img.resize((256, 256), Image.LANCZOS).save(HERE / "vexxo.png")
    img.save(HERE / "vexxo.ico", sizes=[(s, s) for s in sizes])
    print("wrote", HERE / "vexxo.ico")


if __name__ == "__main__":
    main()
