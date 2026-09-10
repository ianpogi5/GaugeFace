"""Bakes the applied gold emblem - square, compasses and the G - to a
transparent PNG for use as a Connect IQ bitmap resource.

Everything else on the dial is drawn with primitives on device; these are the
only elements that need real gradients, so they are baked together as one
asset. The owner's name is *not* baked in: it is a user setting, and is drawn
on device from the custom script font (see bake_font.py).
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import render_v2 as R
import render_v3 as V

# DialRenderer.drawEmblem blits the asset at this top-left on a 416 dial, at
# this size. Changing the emblem geometry moves the crop; if these stop
# matching, the Monkey C constant has to follow.
EXPECTED_ORIGIN = (98, 100)
EXPECTED_SIZE = (224, 222)
DEST = R.HERE / "resources" / "drawables" / "emblem.png"

SS, W, C = R.SS, R.W, R.C
SCALE = 1.06          # must match render_v3.emblem(scale=...)

canvas = Image.new("RGBA", (W, W), (0, 0, 0, 0))


def _shadow(pts=None, mask=None, drop=2.4, alpha=120):
    sh = Image.new("L", (W, W), 0)
    if pts is not None:
        ImageDraw.Draw(sh).polygon(
            [(p[0] + drop * SS, p[1] + drop * SS) for p in pts], fill=alpha)
    else:
        sh = mask.point(lambda v: int(v * alpha / 255))
        sh = sh.transform((W, W), Image.AFFINE,
                          (1, 0, -drop * SS, 0, 1, -drop * SS))
    sh = sh.filter(ImageFilter.GaussianBlur(1.8 * SS))
    layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    layer.putalpha(sh)
    canvas.alpha_composite(layer)


def _fill(mask, normal, lut, boost=1.0):
    bbox = mask.getbbox()
    if bbox is None:
        return
    x0, y0, x1, y1 = bbox
    ys, xs = np.mgrid[y0:y1, x0:x1]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = normal
    half = max(abs((x1 - x0) * nx), abs((y1 - y0) * ny)) / 2 or 1.0
    t = np.clip((((xs - cx) * nx + (ys - cy) * ny) / half + 1.0) / 2.0, 0, 1)
    rgb = (lut[(t * 255).astype(int)] * boost).clip(0, 255).astype(np.uint8)
    patch = Image.fromarray(rgb, "RGB").convert("RGBA")
    canvas.paste(patch, (x0, y0), mask.crop(bbox))


def applied_rgba(pts, normal, lut, drop=2.4, boost=1.0):
    _shadow(pts=pts, drop=drop)
    mask = Image.new("L", (W, W), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    # the polygon gradient runs across the limb, so measure along its own normal
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    nx, ny = normal
    half = max(abs((p[0] - cx) * nx + (p[1] - cy) * ny) for p in pts) or 1.0
    bbox = mask.getbbox()
    if bbox is None:
        return
    x0, y0, x1, y1 = bbox
    ys, xs = np.mgrid[y0:y1, x0:x1]
    t = np.clip((((xs - cx) * nx + (ys - cy) * ny) / half + 1.0) / 2.0, 0, 1)
    rgb = (lut[(t * 255).astype(int)] * boost).clip(0, 255).astype(np.uint8)
    canvas.paste(Image.fromarray(rgb, "RGB").convert("RGBA"), (x0, y0),
                 mask.crop(bbox))


def mask_rgba(mask, normal, lut, drop=2.6, boost=1.0):
    _shadow(mask=mask, drop=drop, alpha=140)
    _fill(mask, normal, lut, boost)


def build():
    def s(pt):
        return (pt[0] * SCALE, pt[1] * SCALE)

    HINGE, VERTEX = s(R.HINGE), s(R.VERTEX)
    TIP_L, TIP_R = s(R.TIP_L), s(R.TIP_R)
    ARM_L, ARM_R = s(R.ARM_L), s(R.ARM_R)

    for p1, p2, w1, w2 in [(VERTEX, ARM_L, 17, 17), (VERTEX, ARM_R, 17, 17)]:
        q, n = R.band(p1, p2, w1, w2)
        applied_rgba(q, n, R.GOLD, boost=0.86)

    d = ImageDraw.Draw(canvas)
    d.line([R.P(*VERTEX), R.P(*ARM_L)], fill=(26, 20, 8, 210), width=int(1.4 * SS))
    d.line([R.P(*VERTEX), R.P(*ARM_R)], fill=(26, 20, 8, 210), width=int(1.4 * SS))

    for p1, p2, w1, w2 in [(HINGE, TIP_L, 15, 10), (HINGE, TIP_R, 15, 10)]:
        q, n = R.band(p1, p2, w1, w2)
        applied_rgba(q, n, R.GOLD)

    for tip in (TIP_L, TIP_R):
        dx, dy = tip[0] - HINGE[0], tip[1] - HINGE[1]
        ln = math.hypot(dx, dy)
        ux, uy = dx / ln, dy / ln
        nx, ny = -uy, ux
        tri = [R.P(tip[0] + nx * 8, tip[1] + ny * 8),
               R.P(tip[0] + ux * 21, tip[1] + uy * 21),
               R.P(tip[0] - nx * 8, tip[1] - ny * 8)]
        applied_rgba(tri, (nx, ny), R.GOLD)

    d = ImageDraw.Draw(canvas)
    hx, hy = R.P(*HINGE)
    d.ellipse([hx - 12 * SS, hy - 12 * SS, hx + 12 * SS, hy + 12 * SS],
              fill=(120, 94, 44, 255), outline=(248, 226, 170, 255),
              width=int(2 * SS))
    d.ellipse([hx - 4.5 * SS, hy - 4.5 * SS, hx + 4.5 * SS, hy + 4.5 * SS],
              fill=(0, 0, 0, 0))

    mask_rgba(V.text_mask("G", R.font(R.SERIF, 86), (C, C + 8 * SS)),
              (0.0, 1.0), V.GOLD_TEXT, drop=3.0)


def main():
    build()
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
        print("!! update the offset in source/DialRenderer.mc to", bbox[:2],
              "and EXPECTED_* above.")


if __name__ == "__main__":
    main()
