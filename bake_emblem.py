"""Bakes the applied gold emblems to transparent PNGs for use as Connect IQ
bitmap resources. One per dial style:

  emblem_square.png  square, compasses and the G, at the Square dial geometry
  emblem_gauge.png   square and compasses only, at the Gauge dial geometry

The two are not the same drawing at two scales: the Gauge emblem has heavier
limbs and a larger hinge, and draws its own G as text below centre, which is
why that asset leaves the G out. Everything else on either dial is drawn with
primitives on device; these are the only elements needing real gradients.

The owner's name is never baked in: it is a user setting, and is drawn on
device from the custom script font (see bake_font.py).
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import render_v2 as R
import render_v3 as V

# Each dial's drawEmblem blits its asset at `origin` on a 416 dial, at `size`.
# Changing emblem geometry moves the crop; if these stop matching, the Monkey C
# constants have to follow.
TARGETS = {
    "square": {
        "file": "emblem_square.png",
        "origin": (98, 100),
        "size": (224, 222),
        "mc": "SQ_EMBLEM_X / SQ_EMBLEM_Y in source/DialSquare.mc",
        "scale": 1.06,          # must match render_v3.emblem(scale=...)
        "square_w": 17,
        "comp_w": (15, 10),
        "tip": (8, 21),         # half-width at the shoulder, length past it
        "hinge": (12, 4.5),     # outer radius, hole radius
        "separator": True,
        "with_g": True,
    },
    "gauge": {
        "file": "emblem_gauge.png",
        "origin": (103, 103),
        "size": (214, 214),
        "mc": "GA_EMBLEM_X / GA_EMBLEM_Y in source/DialGauge.mc",
        "scale": 1.0,           # the original render_v2 geometry
        "square_w": 19,
        "comp_w": (17, 11),
        "tip": (9, 24),
        "hinge": (14, 5),
        "separator": False,
        "with_g": False,
    },
}
DRAWABLES = R.HERE / "resources" / "drawables"

SS, W, C = R.SS, R.W, R.C


class Bake:
    """One emblem on its own transparent canvas."""

    def __init__(self):
        self.canvas = Image.new("RGBA", (W, W), (0, 0, 0, 0))

    def shadow(self, pts=None, mask=None, drop=2.4, alpha=120):
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
        self.canvas.alpha_composite(layer)

    def gradient(self, mask, cx, cy, normal, half, lut, boost):
        bbox = mask.getbbox()
        if bbox is None:
            return
        x0, y0, x1, y1 = bbox
        ys, xs = np.mgrid[y0:y1, x0:x1]
        nx, ny = normal
        t = np.clip((((xs - cx) * nx + (ys - cy) * ny) / half + 1.0) / 2.0, 0, 1)
        rgb = (lut[(t * 255).astype(int)] * boost).clip(0, 255).astype(np.uint8)
        self.canvas.paste(Image.fromarray(rgb, "RGB").convert("RGBA"),
                          (x0, y0), mask.crop(bbox))

    def polygon(self, pts, normal, lut, drop=2.4, boost=1.0):
        self.shadow(pts=pts, drop=drop)
        mask = Image.new("L", (W, W), 0)
        ImageDraw.Draw(mask).polygon(pts, fill=255)
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        nx, ny = normal
        # the gradient runs across the limb, so measure along its own normal
        half = max(abs((p[0] - cx) * nx + (p[1] - cy) * ny) for p in pts) or 1.0
        self.gradient(mask, cx, cy, normal, half, lut, boost)

    def glyph(self, mask, normal, lut, drop=2.6, boost=1.0):
        self.shadow(mask=mask, drop=drop, alpha=140)
        bbox = mask.getbbox()
        if bbox is None:
            return
        x0, y0, x1, y1 = bbox
        nx, ny = normal
        half = max(abs((x1 - x0) * nx), abs((y1 - y0) * ny)) / 2 or 1.0
        self.gradient(mask, (x0 + x1) / 2, (y0 + y1) / 2, normal, half, lut, boost)


def build(spec):
    b = Bake()
    scale = spec["scale"]

    def s(pt):
        return (pt[0] * scale, pt[1] * scale)

    HINGE, VERTEX = s(R.HINGE), s(R.VERTEX)
    TIP_L, TIP_R = s(R.TIP_L), s(R.TIP_R)
    ARM_L, ARM_R = s(R.ARM_L), s(R.ARM_R)
    sq = spec["square_w"]
    cw1, cw2 = spec["comp_w"]
    tip_n, tip_l = spec["tip"]
    hinge_r, hinge_hole = spec["hinge"]

    # square first, compasses over it
    for p1, p2 in ((VERTEX, ARM_L), (VERTEX, ARM_R)):
        q, n = R.band(p1, p2, sq, sq)
        b.polygon(q, n, R.GOLD, boost=0.86 if spec["with_g"] else 0.88)

    if spec["separator"]:
        # without this the crossing is illegible; a wide contact shadow was
        # tried and swallowed the square's vertex
        d = ImageDraw.Draw(b.canvas)
        d.line([R.P(*VERTEX), R.P(*ARM_L)], fill=(26, 20, 8, 210),
               width=int(1.4 * SS))
        d.line([R.P(*VERTEX), R.P(*ARM_R)], fill=(26, 20, 8, 210),
               width=int(1.4 * SS))

    for p1, p2 in ((HINGE, TIP_L), (HINGE, TIP_R)):
        q, n = R.band(p1, p2, cw1, cw2)
        b.polygon(q, n, R.GOLD)

    for tip in (TIP_L, TIP_R):
        dx, dy = tip[0] - HINGE[0], tip[1] - HINGE[1]
        ln = math.hypot(dx, dy)
        ux, uy = dx / ln, dy / ln
        nx, ny = -uy, ux
        tri = [R.P(tip[0] + nx * tip_n, tip[1] + ny * tip_n),
               R.P(tip[0] + ux * tip_l, tip[1] + uy * tip_l),
               R.P(tip[0] - nx * tip_n, tip[1] - ny * tip_n)]
        b.polygon(tri, (nx, ny), R.GOLD)

    d = ImageDraw.Draw(b.canvas)
    hx, hy = R.P(*HINGE)
    d.ellipse([hx - hinge_r * SS, hy - hinge_r * SS,
               hx + hinge_r * SS, hy + hinge_r * SS],
              fill=(120, 94, 44, 255), outline=(248, 226, 170, 255),
              width=int(2 * SS))
    d.ellipse([hx - hinge_hole * SS, hy - hinge_hole * SS,
               hx + hinge_hole * SS, hy + hinge_hole * SS], fill=(0, 0, 0, 0))

    if spec["with_g"]:
        b.glyph(V.text_mask("G", R.font(R.SERIF, 86), (C, C + 8 * SS)),
                (0.0, 1.0), V.GOLD_TEXT, drop=3.0)

    return b.canvas


def bake_one(key, out_dir=DRAWABLES):
    spec = TARGETS[key]
    canvas = build(spec)

    small = canvas.resize((416, 416), Image.LANCZOS)
    bbox = small.getbbox()
    crop = small.crop(bbox)

    alpha = crop.split()[3]
    flat = crop.convert("RGB").quantize(colors=64, method=Image.MEDIANCUT)
    flat = flat.convert("RGBA")
    flat.putalpha(alpha)

    dest = Path(out_dir) / spec["file"]
    flat.save(dest, optimize=True)
    print(f"{key:7s} bbox {bbox} size {crop.size} -> {dest.name} "
          f"({dest.stat().st_size} bytes)")

    if bbox[:2] != spec["origin"] or crop.size != spec["size"]:
        print(f"!! {key}: geometry moved. Monkey C still blits at "
              f"{spec['origin']} expecting {spec['size']}.")
        print(f"!! update {spec['mc']} to {bbox[:2]}, and TARGETS above.")
        return False
    return True


def main():
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DRAWABLES
    keys = sys.argv[2:] or list(TARGETS.keys())
    ok = True
    for key in keys:
        ok = bake_one(key, out_dir) and ok
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
