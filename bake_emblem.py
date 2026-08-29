"""Bakes the applied gold emblem to a transparent PNG for use as a Connect IQ
bitmap resource. Everything else on the dial is drawn with primitives on device;
only this needs real gradients."""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import render_v2 as R

# DialRenderer.drawEmblem blits the asset at this top-left on a 416 dial, at
# this size. Changing the emblem geometry moves the crop; if these stop
# matching, the Monkey C constant has to follow.
EXPECTED_ORIGIN = (103, 103)
EXPECTED_SIZE = (214, 214)
DEST = R.HERE / "resources" / "drawables" / "emblem.png"

SS = R.SS
W = R.W
C = R.C

canvas = Image.new("RGBA", (W, W), (0, 0, 0, 0))


def applied_rgba(img, pts, normal, lut, drop=2.4, boost=1.0):
    sh = Image.new("L", img.size, 0)
    ImageDraw.Draw(sh).polygon([(p[0] + drop * SS, p[1] + drop * SS) for p in pts],
                               fill=120)
    sh = sh.filter(ImageFilter.GaussianBlur(1.8 * SS))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow.putalpha(sh)
    img.alpha_composite(shadow)

    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    bbox = mask.getbbox()
    if bbox is None:
        return
    x0, y0, x1, y1 = bbox
    ys, xs = np.mgrid[y0:y1, x0:x1]
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    nx, ny = normal
    half = max(abs((p[0] - cx) * nx + (p[1] - cy) * ny) for p in pts) or 1.0
    t = np.clip((((xs - cx) * nx + (ys - cy) * ny) / half + 1.0) / 2.0, 0, 1)
    rgb = (lut[(t * 255).astype(int)] * boost).clip(0, 255).astype(np.uint8)
    patch = Image.fromarray(rgb, "RGB").convert("RGBA")
    canvas.paste(patch, (x0, y0), mask.crop(bbox))


for p1, p2, w1, w2 in [(R.VERTEX, R.ARM_L, 19, 19), (R.VERTEX, R.ARM_R, 19, 19)]:
    q, n = R.band(p1, p2, w1, w2)
    applied_rgba(canvas, q, n, R.GOLD, boost=0.88)

for p1, p2, w1, w2 in [(R.HINGE, R.TIP_L, 17, 11), (R.HINGE, R.TIP_R, 17, 11)]:
    q, n = R.band(p1, p2, w1, w2)
    applied_rgba(canvas, q, n, R.GOLD)

for tip in (R.TIP_L, R.TIP_R):
    dx, dy = tip[0] - R.HINGE[0], tip[1] - R.HINGE[1]
    ln = math.hypot(dx, dy)
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy, ux
    tri = [R.P(tip[0] + nx * 9, tip[1] + ny * 9),
           R.P(tip[0] + ux * 24, tip[1] + uy * 24),
           R.P(tip[0] - nx * 9, tip[1] - ny * 9)]
    applied_rgba(canvas, tri, (nx, ny), R.GOLD)

d = ImageDraw.Draw(canvas)
hx, hy = R.P(*R.HINGE)
d.ellipse([hx - 14 * SS, hy - 14 * SS, hx + 14 * SS, hy + 14 * SS],
          fill=(120, 94, 44, 255), outline=(248, 226, 170, 255), width=int(2 * SS))
d.ellipse([hx - 5 * SS, hy - 5 * SS, hx + 5 * SS, hy + 5 * SS], fill=(0, 0, 0, 0))

small = canvas.resize((416, 416), Image.LANCZOS)
bbox = small.getbbox()
crop = small.crop(bbox)
print("emblem bbox on the 416 dial:", bbox, "size:", crop.size)

alpha = crop.split()[3]
flat = crop.convert("RGB").quantize(colors=64, method=Image.MEDIANCUT)
flat = flat.convert("RGBA")
flat.putalpha(alpha)

dest = Path(sys.argv[1]) if len(sys.argv) > 1 else DEST
flat.save(dest, optimize=True)
print("wrote", dest, "-", dest.stat().st_size, "bytes")

if bbox[:2] != EXPECTED_ORIGIN or crop.size != EXPECTED_SIZE:
    print()
    print("!! geometry moved: DialRenderer.drawEmblem still blits at",
          EXPECTED_ORIGIN, "expecting", EXPECTED_SIZE)
    print("!! update the (103, 103) offset in source/DialRenderer.mc to",
          bbox[:2], "and EXPECTED_* above.")
