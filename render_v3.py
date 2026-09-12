"""Blue-and-gold Masonic dial, after the engraved-bezel style: a guilloche gold
chapter ring, a fine-rayed blue centre, applied square and compasses around an
ornate G, a day/date aperture at three, and the owner's name engraved in script.

Same conventions as render_v2: 416-unit geometry, 4x supersample, real
gradients. Run it directly to write the mock-ups to out/.
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import render_v2 as R

HERE = R.HERE
OUT = R.OUT
SS = R.SS
W = R.W
C = R.C
GOLD = R.GOLD

SCRIPT = str(HERE / "assets" / "GreatVibes-Regular.ttf")
SERIF = R.SERIF
SANSB = R.SANSB

NAME = "Singko"

# The reference photo gives roughly 60% of the dial to the blue centre and the
# rest to the gold band. Earlier passes had the band far too narrow and the
# dial read as a blue face with a gold trim rather than an engraved bezel.
BLUE_R = 144          # inner blue dial
RING_IN, RING_OUT = 146, 196

EMBLEM_SCALE = 1.08   # must match bake_emblem.TARGETS["square"]["scale"]

# The full GOLD ramp runs dark at both ends, which buries small glyphs. Text and
# the G get a ramp that stays in the bright half.
GOLD_TEXT = R.ramp([
    (0.00, (150, 116, 52)),
    (0.22, (214, 178, 104)),
    (0.46, (252, 236, 196)),
    (0.62, (238, 210, 148)),
    (0.84, (176, 138, 64)),
    (1.00, (128, 98, 44)),
])

pol, P, rot, font = R.pol, R.P, R.rot, R.font


# ------------------------------------------------------------------ gold masks

def gold_from_mask(img, mask, normal=(0.0, 1.0), lut=GOLD, drop=2.2, boost=1.0):
    """Fill a mask with a gradient running along `normal`, over a cast shadow.

    The polygon version in render_v2 can't do glyphs; this takes any mask, so
    the G and the engraved name get the same metal as the limbs.
    """
    sh = mask.filter(ImageFilter.GaussianBlur(1.6 * SS))
    sh = sh.transform(img.size, Image.AFFINE,
                      (1, 0, -drop * SS, 0, 1, -drop * SS))
    img.paste(Image.new("RGB", img.size, (4, 10, 22)), (0, 0),
              sh.point(lambda v: int(v * 0.72)))

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
    img.paste(Image.fromarray(rgb, "RGB"), (x0, y0), mask.crop(bbox))


def text_mask(text, fnt, xy, anchor="mm", stroke=0):
    m = Image.new("L", (W, W), 0)
    ImageDraw.Draw(m).text(xy, text, font=fnt, fill=255, anchor=anchor,
                           stroke_width=int(stroke * SS), stroke_fill=255)
    return m


# --------------------------------------------------------------- blue centre

def blue_centre():
    """Navy centre with fine radial engine-turning and a lift behind the emblem."""
    y, x = np.mgrid[0:W, 0:W]
    dx, dy = (x - C) / SS, (y - C) / SS
    r = np.hypot(dx, dy)
    th = np.arctan2(dy, dx)

    deep = np.array([8, 22, 58], dtype=float)
    lift = np.array([46, 86, 148], dtype=float)

    # fine rays: 180 of them, softened so they read as turning, not stripes
    ray = 0.5 + 0.5 * np.cos(th * 180)
    ray = ray ** 1.3
    glow = np.clip(1.0 - (r / BLUE_R) ** 1.6, 0, 1)
    t = np.clip(0.34 * ray + 0.54 * glow + 0.20 * ray * glow, 0, 1)

    img = deep[None, None, :] + (lift - deep)[None, None, :] * t[:, :, None]
    vig = np.clip(1.04 - (r / BLUE_R) ** 3 * 0.5, 0, 1.1)
    img *= vig[:, :, None]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


# ------------------------------------------------------------- guilloche ring

# The band is a *blue* field carrying gold ornament - not a gold slab with dark
# engraving cut into it, which is what was here before and read as a brass
# bezel. Getting this backwards was also why widening the band made the dial
# worse: it was widening the wrong material.
LATTICE_A = 56        # cells around
LATTICE_R = 2         # rows across the band


def ring_field():
    """Navy base for the band, a shade deeper than the centre."""
    y, x = np.mgrid[0:W, 0:W]
    dx, dy = (x - C) / SS, (y - C) / SS
    r = np.hypot(dx, dy)
    deep = np.array([8, 20, 50], dtype=float)
    lift = np.array([22, 48, 96], dtype=float)
    t = np.clip((1.0 - dy / RING_OUT) / 2.0, 0, 1) * 0.7 + 0.15
    t = t * np.clip(1.18 - r / RING_OUT * 0.5, 0.5, 1.0)
    img = deep[None, None, :] + (lift - deep)[None, None, :] * t[:, :, None]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def ornate_ring(img):
    d = ImageDraw.Draw(img, "RGBA")

    ann = Image.new("L", img.size, 0)
    ImageDraw.Draw(ann).ellipse(
        [C - RING_OUT * SS, C - RING_OUT * SS, C + RING_OUT * SS, C + RING_OUT * SS],
        fill=255)
    ImageDraw.Draw(ann).ellipse(
        [C - RING_IN * SS, C - RING_IN * SS, C + RING_IN * SS, C + RING_IN * SS],
        fill=0)
    img.paste(ring_field(), (0, 0), ann)

    field_in, field_out = RING_IN + 9, RING_OUT - 11
    step = (field_out - field_in) / LATTICE_R
    gold = (206, 170, 96, 255)
    bright = (244, 224, 168, 255)

    for row in range(LATTICE_R):
        r0 = field_in + row * step
        r1 = r0 + step
        rm = (r0 + r1) / 2
        for k in range(LATTICE_A):
            a0 = k / LATTICE_A * 2 * math.pi
            a1 = (k + 1) / LATTICE_A * 2 * math.pi
            am = (a0 + a1) / 2

            # gold lozenge over the blue, cell by cell
            d.polygon([pol(rm, a0), pol(r1, am), pol(rm, a1), pol(r0, am)],
                      outline=gold, width=int(1.0 * SS))

            # a small gold diamond in every other eye; the rest stay blue, or
            # the band turns into a solid mat again
            if (k + row) % 2 == 0:
                f = 0.26
                d.polygon([pol(rm, a0 + (am - a0) * (1 - f)),
                           pol(rm + (r1 - rm) * f, am),
                           pol(rm, a1 - (a1 - am) * (1 - f)),
                           pol(rm - (rm - r0) * f, am)], fill=bright)

    # fine gold teeth on the inner edge, bead on the outer
    for k in range(LATTICE_A * 2):
        a = k / (LATTICE_A * 2) * 2 * math.pi
        d.line([pol(RING_IN + 2.0, a), pol(field_in - 1.0, a)],
               fill=(180, 146, 80, 220), width=int(0.9 * SS))
    for k in range(112):
        a = k / 112 * 2 * math.pi
        p = pol(RING_OUT - 5, a)
        br = 1.5 * SS
        d.ellipse([p[0] - br, p[1] - br, p[0] + br, p[1] + br], fill=bright)

    for rad, wid, col in ((RING_IN, 2.4, (214, 178, 100)),
                          (RING_OUT, 3.0, (222, 188, 114)),
                          (BLUE_R, 1.8, (150, 120, 60))):
        d.ellipse([C - rad * SS, C - rad * SS, C + rad * SS, C + rad * SS],
                  outline=col, width=int(wid * SS))


NUM_R = RING_IN + 25        # numerals and darts share the band's mid-radius


def markers(img):
    d = ImageDraw.Draw(img, "RGBA")
    for h in range(12):
        if h == 0 or h == 6:
            continue        # XII and VI sit there instead
        a = h / 12 * 2 * math.pi
        p1, p2 = pol(NUM_R - 9, a), pol(NUM_R + 9, a)
        n = (-(p2[1] - p1[1]), p2[0] - p1[0])
        ln = math.hypot(*n) or 1
        nx, ny = n[0] / ln * 4.0 * SS, n[1] / ln * 4.0 * SS
        d.polygon([(p1[0] + nx, p1[1] + ny), p2, (p1[0] - nx, p1[1] - ny)],
                  fill=(244, 224, 168, 255), outline=(120, 92, 40), width=int(SS))

    f = font(SERIF, 30)
    for label, a in (("XII", 0.0), ("VI", math.pi)):
        px, py = pol(NUM_R, a)
        d.text((px + 1.3 * SS, py + 1.3 * SS), label, font=f,
               fill=(10, 22, 46, 220), anchor="mm")
        d.text((px, py), label, font=f, fill=(246, 228, 176, 255), anchor="mm")


# The photo scatters fine gold line-work in the blue field between the limbs:
# a blazing star upper-left, a small square upper-right, and a point within a
# circle below the G. These are engraved lines, not applied metal.
def symbols(img):
    d = ImageDraw.Draw(img, "RGBA")
    gold = (216, 180, 106, 255)
    pen = int(1.1 * SS)

    sx, sy = pol(96, -0.94)
    rr = 12 * SS
    d.ellipse([sx - rr, sy - rr, sx + rr, sy + rr], outline=gold, width=pen)
    for i in range(8):
        a = i / 8 * 2 * math.pi
        d.line([(sx + math.sin(a) * rr * 0.35, sy - math.cos(a) * rr * 0.35),
                (sx + math.sin(a) * rr * 1.55, sy - math.cos(a) * rr * 1.55)],
               fill=gold, width=pen)
    d.ellipse([sx - 2.4 * SS, sy - 2.4 * SS, sx + 2.4 * SS, sy + 2.4 * SS],
              fill=gold)

    qx, qy = pol(96, 0.94)
    h = 11 * SS
    d.rectangle([qx - h, qy - h, qx + h, qy + h], outline=gold, width=pen)
    d.rectangle([qx - h * 0.55, qy - h * 0.55, qx + h * 0.55, qy + h * 0.55],
                outline=gold, width=pen)

    cx2, cy2 = pol(72, math.pi)
    rr = 9.5 * SS
    d.ellipse([cx2 - rr, cy2 - rr, cx2 + rr, cy2 + rr], outline=gold, width=pen)
    d.ellipse([cx2 - 2.6 * SS, cy2 - 2.6 * SS, cx2 + 2.6 * SS, cy2 + 2.6 * SS],
              fill=gold)


# --------------------------------------------------------------------- emblem

def emblem(img, scale=EMBLEM_SCALE):
    def s(pt):
        return (pt[0] * scale, pt[1] * scale)

    HINGE, VERTEX = s(R.HINGE), s(R.VERTEX)
    TIP_L, TIP_R = s(R.TIP_L), s(R.TIP_R)
    ARM_L, ARM_R = s(R.ARM_L), s(R.ARM_R)

    # square first, compasses over it
    for p1, p2, w1, w2 in [(VERTEX, ARM_L, 13, 13), (VERTEX, ARM_R, 13, 13)]:
        q, n = R.band(p1, p2, w1, w2)
        R.applied(img, q, n, GOLD, boost=0.86)

    d = ImageDraw.Draw(img, "RGBA")
    d.line([P(*VERTEX), P(*ARM_L)], fill=(26, 20, 8, 210), width=int(1.4 * SS))
    d.line([P(*VERTEX), P(*ARM_R)], fill=(26, 20, 8, 210), width=int(1.4 * SS))

    for p1, p2, w1, w2 in [(HINGE, TIP_L, 12, 8), (HINGE, TIP_R, 12, 8)]:
        q, n = R.band(p1, p2, w1, w2)
        R.applied(img, q, n, GOLD)
    for tip in (TIP_L, TIP_R):
        dx, dy = tip[0] - HINGE[0], tip[1] - HINGE[1]
        ln = math.hypot(dx, dy)
        ux, uy = dx / ln, dy / ln
        nx, ny = -uy, ux
        tri = [P(tip[0] + nx * 7, tip[1] + ny * 7),
               P(tip[0] + ux * 19, tip[1] + uy * 19),
               P(tip[0] - nx * 7, tip[1] - ny * 7)]
        R.applied(img, tri, (nx, ny), GOLD)

    d = ImageDraw.Draw(img, "RGBA")
    hx, hy = P(*HINGE)
    d.ellipse([hx - 11 * SS, hy - 11 * SS, hx + 11 * SS, hy + 11 * SS],
              fill=(120, 94, 44), outline=(248, 226, 170), width=int(1.8 * SS))
    d.ellipse([hx - 4 * SS, hy - 4 * SS, hx + 4 * SS, hy + 4 * SS],
              fill=(12, 28, 58))

    # the G is the hero of this dial: large, bright, over the crossing
    gold_from_mask(img, text_mask("G", font(SERIF, 86), (C, C + 7 * SS)),
                   (0.0, 1.0), lut=GOLD_TEXT, drop=3.0)


# ------------------------------------------------------------------- aperture

def aperture(img, day="SUN", date="8"):
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = C + 70 * SS, C - 10 * SS, C + 110 * SS, C + 10 * SS
    d.rounded_rectangle([x0 - 2 * SS, y0 - 2 * SS, x1 + 2 * SS, y1 + 2 * SS],
                        radius=2 * SS, fill=(150, 120, 58))
    d.rounded_rectangle([x0, y0, x1, y1], radius=1.5 * SS, fill=(238, 236, 230))
    d.line([(x0 + 23 * SS, y0), (x0 + 23 * SS, y1)], fill=(170, 168, 162),
           width=int(1.0 * SS))
    d.text(((x0 + x0 + 23 * SS) / 2, (y0 + y1) / 2), day, font=font(SANSB, 10),
           fill=(24, 24, 28), anchor="mm")
    d.text(((x0 + 23 * SS + x1) / 2, (y0 + y1) / 2), date, font=font(SANSB, 12),
           fill=(190, 32, 34), anchor="mm")


# ----------------------------------------------------------------------- name

def name_mask(name, size, y, stroke=0.45):
    """Lay the name out the way the watch will.

    Connect IQ draws from the baked bitmap font, which carries one *integer*
    advance per glyph and no kerning. PIL's own string rendering kerns and uses
    fractional advances, so the two drift - at this size by about 2.5px across
    six letters. Stepping a pen by the same rounded advances the atlas stores
    keeps the mock-up honest about what the device will show.
    """
    f1 = ImageFont.truetype(SCRIPT, size)       # 1x: the atlas's own metrics
    adv = [round(f1.getlength(ch)) for ch in name]
    ascent, descent = f1.getmetrics()
    # Connect IQ centres the line box, so the baseline sits here
    baseline = y + (ascent - descent) / 2.0

    fss = font(SCRIPT, size)                    # 4x for the actual drawing
    m = Image.new("L", (W, W), 0)
    d = ImageDraw.Draw(m)
    pen = C - sum(adv) * SS / 2.0
    for ch, a in zip(name, adv):
        d.text((pen, C + baseline * SS), ch, font=fss, fill=255, anchor="ls",
               stroke_width=int(stroke * SS), stroke_fill=255)
        pen += a * SS
    return m


def engraved_name(img, name=NAME, y=124, size=34):
    """The owner's name in engraved script, applied gold like everything else.

    Great Vibes is a high-contrast face: its hairlines land near a single pixel
    at dial scale, so a hair of stroke keeps them from dropping out on device.
    """
    gold_from_mask(img, name_mask(name, size, y), (0.0, 1.0),
                   lut=GOLD_TEXT, drop=1.8)


# --------------------------------------------------------------------- layers

def draw_static(name=NAME):
    img = Image.new("RGB", (W, W), (6, 10, 20))
    disc = Image.new("L", (W, W), 0)
    ImageDraw.Draw(disc).ellipse(
        [C - BLUE_R * SS, C - BLUE_R * SS, C + BLUE_R * SS, C + BLUE_R * SS],
        fill=255)
    img.paste(blue_centre(), (0, 0), disc)

    ornate_ring(img)
    markers(img)
    symbols(img)
    emblem(img)
    aperture(img)
    engraved_name(img, name)
    return img


def hands(img, h, m, s):
    d = ImageDraw.Draw(img, "RGBA")
    ha = ((h % 12) + m / 60) / 12 * 2 * math.pi
    ma = (m + s / 60) / 60 * 2 * math.pi

    for ang, L, wd in ((ha, 84, 9), (ma, 130, 7)):
        sh = Image.new("L", img.size, 0)
        ImageDraw.Draw(sh).polygon(
            [rot(-wd, 16, ang), rot(0, -L, ang), rot(wd, 16, ang), rot(0, 26, ang)],
            fill=170)
        sh = sh.transform(img.size, Image.AFFINE,
                          (1, 0, -3 * SS, 0, 1, -3 * SS))
        sh = sh.filter(ImageFilter.GaussianBlur(1.5 * SS))
        img.paste(Image.new("RGB", img.size, (5, 12, 26)), (0, 0), sh)

    d = ImageDraw.Draw(img, "RGBA")
    for ang, L, wd in ((ha, 84, 9), (ma, 130, 7)):
        d.polygon([rot(-wd, 16, ang), rot(0, -L, ang), rot(0, 26, ang)],
                  fill=(250, 232, 182))
        d.polygon([rot(0, 16, ang), rot(0, -L, ang), rot(wd, 16, ang),
                   rot(0, 26, ang)], fill=(176, 138, 62))
        d.polygon([rot(-wd, 16, ang), rot(0, -L, ang), rot(wd, 16, ang),
                   rot(0, 26, ang)], outline=(92, 70, 28), width=int(1.0 * SS))

    sa = s / 60 * 2 * math.pi
    d.line([rot(0, 30, sa), rot(0, -146, sa)], fill=(238, 198, 120),
           width=int(1.6 * SS))
    d.ellipse([C - 6 * SS, C - 6 * SS, C + 6 * SS, C + 6 * SS],
              fill=(226, 196, 132), outline=(120, 92, 40), width=int(1.1 * SS))
    d.ellipse([C - 2.2 * SS, C - 2.2 * SS, C + 2.2 * SS, C + 2.2 * SS],
              fill=(16, 30, 56))
    return img


def finish(img):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, W - 1, W - 1], fill=255)
    out = Image.new("RGB", img.size, (14, 14, 16))
    out.paste(img, (0, 0), mask)
    return out.resize((416, 416), Image.LANCZOS)


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else NAME
    OUT.mkdir(exist_ok=True)
    static = draw_static(name)
    full = hands(static.copy(), 10, 9, 32)
    finish(static).save(OUT / "v3_static.png")
    finish(full).save(OUT / "v3_full.png")
    full.crop((C - 140 * SS, C - 140 * SS, C + 140 * SS, C + 140 * SS)) \
        .resize((660, 660), Image.LANCZOS).save(OUT / "v3_detail.png")
    print("wrote v3_static.png, v3_full.png, v3_detail.png to", OUT, "- name:", name)


if __name__ == "__main__":
    main()
