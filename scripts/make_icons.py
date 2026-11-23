#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 PWA / APK 需要的 PNG 图标（192 / 512），造型与 assets/img/icon.svg 一致。
需要 Pillow：pip install pillow
    python scripts/make_icons.py
"""
import os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "img")
BG = (15, 157, 118, 255)
WHITE = (255, 255, 255, 255)

BOLT = [(262, 214), (206, 282), (240, 282), (224, 330), (286, 256), (248, 256)]


def draw_icon(size: int) -> Image.Image:
    ss = 4
    W = size * ss
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = W / 512.0

    def s(v):
        return v * k

    d.rounded_rectangle([0, 0, W - 1, W - 1], radius=s(96), fill=BG)
    d.rounded_rectangle([s(150), s(198), s(346), s(314)], radius=s(20), fill=WHITE)
    d.rounded_rectangle([s(346), s(232), s(372), s(280)], radius=s(10), fill=WHITE)
    d.polygon([(s(x), s(y)) for x, y in BOLT], fill=BG)
    return img.resize((size, size), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    for size in (192, 512):
        path = os.path.join(OUT, f"icon-{size}.png")
        draw_icon(size).save(path, "PNG", optimize=True)
        print(f"[icons] {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
