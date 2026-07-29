#!/usr/bin/env python3
"""Frame a native macOS window screenshot (from screencapture -l, RGBA with
transparent rounded corners) onto a light 16:9 canvas with a soft drop shadow.

Usage: frame-native-screenshot.py <input.png> <output.jpg> [bg_hex]

Never crops or shrinks the source image - the canvas expands to whichever
16:9 size fully contains it (plus a small margin), so this works for any
native window resolution/aspect ratio.
"""
import os
import sys
from PIL import Image, ImageFilter, ImageChops, ImageDraw

BG_DEFAULT = "#e9eaed"
MARGIN_RATIO = 0.06       # breathing room around the screenshot, as a fraction of its larger dimension
SHADOW_BLUR = 40          # gaussian blur radius for the soft shadow
SHADOW_OFFSET_Y = 18      # px the shadow is nudged down
SHADOW_OPACITY = 0.38     # 0-1

CLICK_MARKER_RATIO = 0.05   # circle diameter as a fraction of the screenshot's larger dimension
CLICK_MARKER_MIN = 50
CLICK_MARKER_MAX = 140
CLICK_MARKER_COLOR = (255, 0, 0, 128)  # 50% transparent red


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    in_path, out_path = sys.argv[1], sys.argv[2]
    bg_hex = sys.argv[3] if len(sys.argv) > 3 else BG_DEFAULT
    bg_rgb = hex_to_rgb(bg_hex)

    shot = Image.open(in_path).convert("RGBA")
    w, h = shot.size

    margin = int(round(max(w, h) * MARGIN_RATIO))
    padded_w, padded_h = w + margin * 2, h + margin * 2

    # Expand to the smallest 16:9 box that fully contains the padded image - never crop/shrink.
    if padded_w / padded_h > 16 / 9:
        canvas_w = padded_w
        canvas_h = round(canvas_w * 9 / 16)
    else:
        canvas_h = padded_h
        canvas_w = round(canvas_h * 16 / 9)

    canvas = Image.new("RGB", (canvas_w, canvas_h), bg_rgb)

    paste_x = (canvas_w - w) // 2
    paste_y = (canvas_h - h) // 2

    # Soft shadow, shaped from the screenshot's own alpha (so it follows the
    # real rounded-corner silhouette instead of a plain rectangle).
    shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    alpha_mask = shot.split()[3]
    black_shape = Image.new("RGBA", (w, h), (0, 0, 0, int(255 * SHADOW_OPACITY)))
    black_shape.putalpha(ImageChops.multiply(black_shape.split()[3], alpha_mask))
    shadow.paste(black_shape, (paste_x, paste_y + SHADOW_OFFSET_Y), black_shape)
    shadow = shadow.filter(ImageFilter.GaussianBlur(SHADOW_BLUR))

    composed = Image.new("RGBA", (canvas_w, canvas_h), bg_rgb + (255,))
    composed.paste(shadow, (0, 0), shadow)
    composed.paste(shot, (paste_x, paste_y), shot)

    # Click-position marker: a sibling <input>.pos.txt (written by snapshot.sh
    # from a real, recent mouse click - never guessed) containing "px,py" in
    # the screenshot's own pixel space. Absent file = no marker, on purpose.
    pos_path = os.path.splitext(in_path)[0] + ".pos.txt"
    if os.path.exists(pos_path):
        with open(pos_path) as f:
            px, py = (int(v) for v in f.read().strip().split(","))
        diameter = max(CLICK_MARKER_MIN, min(CLICK_MARKER_MAX, round(max(w, h) * CLICK_MARKER_RATIO)))
        r = diameter // 2
        overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        cx, cy = paste_x + px, paste_y + py
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=CLICK_MARKER_COLOR)
        composed = Image.alpha_composite(composed, overlay)

    composed.convert("RGB").save(out_path, "JPEG", quality=92)
    print(f"{out_path}: {canvas_w}x{canvas_h}")


if __name__ == "__main__":
    main()
