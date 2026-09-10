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
from PIL import Image, ImageDraw, ImageFilter

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

BLUE_R = 148          # inner blue dial
RING_IN, RING_OUT = 150, 198

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

def gold_ring(img):
    d = ImageDraw.Draw(img, "RGBA")

    # annulus base, brighter at the top where the light sits
    y, x = np.mgrid[0:W, 0:W]
    dx, dy = (x - C) / SS, (y - C) / SS
    r = np.hypot(dx, dy)
    t = np.clip((dy / RING_OUT + 1) / 2, 0, 1)
    base = (GOLD[(np.clip(0.30 + t * 0.42, 0, 1) * 255).astype(int)]
            ).astype(np.uint8)
    ann = Image.new("L", img.size, 0)
    ImageDraw.Draw(ann).ellipse(
        [C - RING_OUT * SS, C - RING_OUT * SS, C + RING_OUT * SS, C + RING_OUT * SS],
        fill=255)
    ImageDraw.Draw(ann).ellipse(
        [C - RING_IN * SS, C - RING_IN * SS, C + RING_IN * SS, C + RING_IN * SS],
        fill=0)
    img.paste(Image.fromarray(base, "RGB"), (0, 0), ann)

    # engine-turned lattice: two opposing families of chords make the diamonds
    N = 90
    dark = (74, 54, 22, 165)
    for k in range(N):
        a = k / N * 2 * math.pi
        b = (k + 3.2) / N * 2 * math.pi
        d.line([pol(RING_IN + 5, a), pol(RING_OUT - 6, b)], fill=dark,
               width=int(0.8 * SS))
        d.line([pol(RING_IN + 5, b), pol(RING_OUT - 6, a)], fill=dark,
               width=int(0.8 * SS))

    # a dot in the eye of every second diamond
    for k in range(0, N, 2):
        a = (k + 1.6) / N * 2 * math.pi
        p = pol((RING_IN + RING_OUT) / 2, a)
        rr = 1.6 * SS
        d.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr],
                  fill=(246, 226, 172, 235))

    # beaded borders, inner and outer
    for rad, n, br in ((RING_IN + 4, 96, 1.5), (RING_OUT - 4, 120, 1.5)):
        for k in range(n):
            a = k / n * 2 * math.pi
            p = pol(rad, a)
            d.ellipse([p[0] - br * SS, p[1] - br * SS,
                       p[0] + br * SS, p[1] + br * SS],
                      fill=(232, 206, 150, 255))

    for rad, wid, col in ((RING_IN, 2.2, (208, 172, 96)),
                          (RING_OUT, 2.6, (208, 172, 96)),
                          (BLUE_R, 1.6, (150, 120, 60))):
        d.ellipse([C - rad * SS, C - rad * SS, C + rad * SS, C + rad * SS],
                  outline=col, width=int(wid * SS))


# -------------------------------------------------------------------- markers

def markers(img):
    d = ImageDraw.Draw(img, "RGBA")
    for h in range(12):
        if h == 0:
            continue        # XII sits there instead
        a = h / 12 * 2 * math.pi
        p1, p2 = pol(RING_IN + 12, a), pol(RING_IN + 26, a)
        n = (-(p2[1] - p1[1]), p2[0] - p1[0])
        ln = math.hypot(*n) or 1
        nx, ny = n[0] / ln * 3.4 * SS, n[1] / ln * 3.4 * SS
        d.polygon([(p1[0] + nx + 1.2 * SS, p1[1] + ny + 1.2 * SS),
                   (p2[0] + 1.2 * SS, p2[1] + 1.2 * SS),
                   (p1[0] - nx + 1.2 * SS, p1[1] - ny + 1.2 * SS)],
                  fill=(238, 214, 158, 200))
        d.polygon([(p1[0] + nx, p1[1] + ny), p2, (p1[0] - nx, p1[1] - ny)],
                  fill=(58, 42, 16, 235))

    px, py = pol(RING_IN + 24, 0)
    f = font(SERIF, 26)
    d.text((px + 1.2 * SS, py + 1.2 * SS), "XII", font=f,
           fill=(240, 218, 162, 210), anchor="mm")
    d.text((px, py), "XII", font=f, fill=(54, 38, 14, 240), anchor="mm")


# --------------------------------------------------------------------- emblem

def emblem(img, scale=1.06):
    def s(pt):
        return (pt[0] * scale, pt[1] * scale)

    HINGE, VERTEX = s(R.HINGE), s(R.VERTEX)
    TIP_L, TIP_R = s(R.TIP_L), s(R.TIP_R)
    ARM_L, ARM_R = s(R.ARM_L), s(R.ARM_R)

    # square first, compasses over it
    for p1, p2, w1, w2 in [(VERTEX, ARM_L, 17, 17), (VERTEX, ARM_R, 17, 17)]:
        q, n = R.band(p1, p2, w1, w2)
        R.applied(img, q, n, GOLD, boost=0.86)

    d = ImageDraw.Draw(img, "RGBA")
    d.line([P(*VERTEX), P(*ARM_L)], fill=(26, 20, 8, 210), width=int(1.4 * SS))
    d.line([P(*VERTEX), P(*ARM_R)], fill=(26, 20, 8, 210), width=int(1.4 * SS))

    for p1, p2, w1, w2 in [(HINGE, TIP_L, 15, 10), (HINGE, TIP_R, 15, 10)]:
        q, n = R.band(p1, p2, w1, w2)
        R.applied(img, q, n, GOLD)
    for tip in (TIP_L, TIP_R):
        dx, dy = tip[0] - HINGE[0], tip[1] - HINGE[1]
        ln = math.hypot(dx, dy)
        ux, uy = dx / ln, dy / ln
        nx, ny = -uy, ux
        tri = [P(tip[0] + nx * 8, tip[1] + ny * 8),
               P(tip[0] + ux * 21, tip[1] + uy * 21),
               P(tip[0] - nx * 8, tip[1] - ny * 8)]
        R.applied(img, tri, (nx, ny), GOLD)

    d = ImageDraw.Draw(img, "RGBA")
    hx, hy = P(*HINGE)
    d.ellipse([hx - 12 * SS, hy - 12 * SS, hx + 12 * SS, hy + 12 * SS],
              fill=(120, 94, 44), outline=(248, 226, 170), width=int(2 * SS))
    d.ellipse([hx - 4.5 * SS, hy - 4.5 * SS, hx + 4.5 * SS, hy + 4.5 * SS],
              fill=(12, 28, 58))

    # the G is the hero of this dial: large, bright, over the crossing
    gold_from_mask(img, text_mask("G", font(SERIF, 86), (C, C + 8 * SS)),
                   (0.0, 1.0), lut=GOLD_TEXT, drop=3.0)


# ------------------------------------------------------------------- aperture

def aperture(img, day="SUN", date="8"):
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = C + 72 * SS, C - 11 * SS, C + 114 * SS, C + 11 * SS
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

def engraved_name(img, name=NAME, y=104, size=44):
    """The owner's name in engraved script, applied gold like everything else.

    Great Vibes is a high-contrast face: its hairlines land near a single pixel
    at dial scale, so a hair of stroke keeps them from dropping out on device.
    """
    f = font(SCRIPT, size)
    gold_from_mask(img, text_mask(name, f, (C, C + y * SS), stroke=0.45),
                   (0.0, 1.0), lut=GOLD_TEXT, drop=1.8)


# --------------------------------------------------------------------- layers

def draw_static(name=NAME):
    img = Image.new("RGB", (W, W), (6, 10, 20))
    disc = Image.new("L", (W, W), 0)
    ImageDraw.Draw(disc).ellipse(
        [C - BLUE_R * SS, C - BLUE_R * SS, C + BLUE_R * SS, C + BLUE_R * SS],
        fill=255)
    img.paste(blue_centre(), (0, 0), disc)

    gold_ring(img)
    markers(img)
    emblem(img)
    aperture(img)
    engraved_name(img, name)
    return img


def hands(img, h, m, s):
    d = ImageDraw.Draw(img, "RGBA")
    ha = ((h % 12) + m / 60) / 12 * 2 * math.pi
    ma = (m + s / 60) / 60 * 2 * math.pi

    for ang, L, wd in ((ha, 88, 10), (ma, 132, 8)):
        sh = Image.new("L", img.size, 0)
        ImageDraw.Draw(sh).polygon(
            [rot(-wd, 16, ang), rot(0, -L, ang), rot(wd, 16, ang), rot(0, 26, ang)],
            fill=170)
        sh = sh.transform(img.size, Image.AFFINE,
                          (1, 0, -3 * SS, 0, 1, -3 * SS))
        sh = sh.filter(ImageFilter.GaussianBlur(1.5 * SS))
        img.paste(Image.new("RGB", img.size, (5, 12, 26)), (0, 0), sh)

    d = ImageDraw.Draw(img, "RGBA")
    for ang, L, wd in ((ha, 88, 10), (ma, 132, 8)):
        d.polygon([rot(-wd, 16, ang), rot(0, -L, ang), rot(0, 26, ang)],
                  fill=(250, 232, 182))
        d.polygon([rot(0, 16, ang), rot(0, -L, ang), rot(wd, 16, ang),
                   rot(0, 26, ang)], fill=(176, 138, 62))
        d.polygon([rot(-wd, 16, ang), rot(0, -L, ang), rot(wd, 16, ang),
                   rot(0, 26, ang)], outline=(92, 70, 28), width=int(1.0 * SS))

    sa = s / 60 * 2 * math.pi
    d.line([rot(0, 30, sa), rot(0, -140, sa)], fill=(238, 198, 120),
           width=int(1.6 * SS))
    d.ellipse([C - 7 * SS, C - 7 * SS, C + 7 * SS, C + 7 * SS],
              fill=(226, 196, 132), outline=(120, 92, 40), width=int(1.2 * SS))
    d.ellipse([C - 2.5 * SS, C - 2.5 * SS, C + 2.5 * SS, C + 2.5 * SS],
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
