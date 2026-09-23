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
# The band now runs to the screen edge and fades out there. Stopping it short
# of the edge and capping it with a bright rim made the dial read as a disc
# pasted onto the screen, with our own black margin between it and the bezel.
RING_IN, RING_OUT = 146, 208
FADE_FROM = 192       # band is solid to here, then falls to black by RING_OUT

# Where the round screen actually ends, in 416-units. The baked dial is cropped
# here, so this is the radius the bezel sits at on device -- and it must equal
# SQ_EDGE in DialSquare.mc, which scales the live layer to match. It used to be
# derived as RING_OUT + 2; when RING_OUT moved out to 208 the crop went to 210
# while SQ_EDGE stayed 198, the dial shrank 6% under its own hands, and the
# lattice stopped ~20 units short of the bezel. That bare margin read as a black
# ring round the face. Nothing between the ornament and the bezel may be black.
EDGE = 198

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
LATTICE_R = 2         # rows across the band, plus one more run under the bezel


def ring_field():
    """Near-black base for the band, fading to true black at the screen edge.

    Gold on black is far crisper than gold on navy, and on an AMOLED the black
    is genuinely off - so the band merges into the bezel instead of ending at
    a visible edge.
    """
    y, x = np.mgrid[0:W, 0:W]
    dx, dy = (x - C) / SS, (y - C) / SS
    r = np.hypot(dx, dy)
    deep = np.array([2, 4, 10], dtype=float)
    lift = np.array([10, 16, 30], dtype=float)
    t = np.clip((1.0 - dy / RING_OUT) / 2.0, 0, 1) * 0.7 + 0.15
    img = deep[None, None, :] + (lift - deep)[None, None, :] * t[:, :, None]
    fade = np.clip((RING_OUT - r) / float(RING_OUT - FADE_FROM), 0, 1)
    img *= fade[:, :, None]
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

    field_in, field_out = RING_IN + 9, FADE_FROM - 2
    step = (field_out - field_in) / LATTICE_R
    # The lattice is ornament behind the markers, not competing with them. At
    # full gold its diamonds were the same size and colour as the hour darts
    # and, after a few days of wearing it, the time could not be read. Held at
    # about half brightness it still carries the band; the batons sit on top.
    gold = (104, 86, 50, 255)
    bright = (124, 112, 84, 255)

    # the extra row lies across EDGE, so the screen cuts the lattice off
    # instead of the lattice stopping short of the screen
    for row in range(LATTICE_R + 1):
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
    for rad, wid, col in ((RING_IN, 2.4, (214, 178, 100)),
                          (BLUE_R, 1.8, (150, 120, 60))):
        d.ellipse([C - rad * SS, C - rad * SS, C + rad * SS, C + rad * SS],
                  outline=col, width=int(wid * SS))


NUM_R = RING_IN + 25        # numerals and batons share the band's mid-radius

# Hour batons, radial, in the band. They replaced small gold darts that were
# lost among the lattice's diamonds: markers have to be the brightest thing in
# the band or the hands have nothing to be read against.
BATON_IN, BATON_OUT, BATON_W = RING_IN + 8, RING_IN + 34, 4.2


def markers(img):
    d = ImageDraw.Draw(img, "RGBA")
    for h in range(12):
        if h == 0 or h == 6:
            continue        # XII and VI sit there instead
        a = h / 12 * 2 * math.pi
        r0, r1, w = BATON_IN, BATON_OUT, BATON_W
        d.polygon([rot(-w, -r0, a), rot(w, -r0, a), rot(w, -r1, a), rot(-w, -r1, a)],
                  fill=(0, 0, 0, 210))
        w, r0, r1 = w - 1.2, r0 + 1.2, r1 - 1.2
        d.polygon([rot(-w, -r0, a), rot(0, -r0, a), rot(0, -r1, a), rot(-w, -r1, a)],
                  fill=(252, 238, 196))
        d.polygon([rot(0, -r0, a), rot(w, -r0, a), rot(w, -r1, a), rot(0, -r1, a)],
                  fill=(200, 160, 80))

    f = font(SERIF, 34)
    for label, a in (("XII", 0.0), ("VI", math.pi)):
        px, py = pol(NUM_R, a)
        d.text((px, py), label, font=f, fill=(0, 0, 0, 220), anchor="mm",
               stroke_width=int(2.5 * SS), stroke_fill=(0, 0, 0, 220))
        d.text((px, py), label, font=f, fill=(250, 234, 186), anchor="mm")


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
    """The day/date window. `day=None, date=None` draws the frame and the white
    window but no text, which is what bake_dial.py wants -- the day and date
    are live, so GaugeFaceView draws them into the window every update."""
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = C + 70 * SS, C - 10 * SS, C + 110 * SS, C + 10 * SS
    d.rounded_rectangle([x0 - 2 * SS, y0 - 2 * SS, x1 + 2 * SS, y1 + 2 * SS],
                        radius=2 * SS, fill=(150, 120, 58))
    d.rounded_rectangle([x0, y0, x1, y1], radius=1.5 * SS, fill=(238, 236, 230))
    d.line([(x0 + 23 * SS, y0), (x0 + 23 * SS, y1)], fill=(170, 168, 162),
           width=int(1.0 * SS))
    if day is not None:
        d.text(((x0 + x0 + 23 * SS) / 2, (y0 + y1) / 2), day, font=font(SANSB, 10),
               fill=(24, 24, 28), anchor="mm")
    if date is not None:
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

def draw_static(name=NAME, day="SUN", date="8"):
    """Everything that does not move. `name=None` leaves the engraved name off,
    which is what bake_dial.py wants: the name is a user setting, so on device
    it is drawn over the baked dial rather than baked into it."""
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
    aperture(img, day, date)
    if name is not None:
        engraved_name(img, name)
    return img


# Hand geometry, shared with GaugeFaceView.liveSquare. The minute hand reaches
# into the batons; the old 84/130 pair stopped inside the blue centre and never
# pointed at anything.
HOUR_L, HOUR_W = 100, 11
MIN_L, MIN_W = 172, 8
SEC_L, SEC_TAIL = 178, 30


def hand_outline(ang, L, wd, grow=0.0):
    g = grow
    return [rot(-(wd + g), 18 + g, ang), rot(-(wd * 0.6 + g), -L * 0.8, ang),
            rot(0, -(L + g * 1.5), ang),
            rot(wd * 0.6 + g, -L * 0.8, ang), rot(wd + g, 18 + g, ang)]


def hands(img, h, m, s):
    """Drawn only with what liveSquare can do: flat polygon fills, no blur.

    The hands used to be plain gold dauphines, the same metal and width as the
    compass limbs, and at most times they vanished into the emblem. Now each
    one has a dark rim, which separates it from the gold under it, and an
    ivory inlay down the middle for the eye to follow.
    """
    ha = ((h % 12) + m / 60) / 12 * 2 * math.pi
    ma = (m + s / 60) / 60 * 2 * math.pi
    d = ImageDraw.Draw(img, "RGBA")

    for ang, L, wd in ((ha, HOUR_L, HOUR_W), (ma, MIN_L, MIN_W)):
        d.polygon(hand_outline(ang, L, wd, grow=2.0), fill=(6, 10, 20))
        d.polygon([rot(-wd, 18, ang), rot(-wd * 0.6, -L * 0.8, ang),
                   rot(0, -L, ang), rot(0, 18, ang)], fill=(250, 232, 182))
        d.polygon([rot(0, 18, ang), rot(0, -L, ang),
                   rot(wd * 0.6, -L * 0.8, ang), rot(wd, 18, ang)],
                  fill=(176, 138, 62))
        iw = wd * 0.38
        d.polygon([rot(-iw, -14, ang), rot(-iw * 0.7, -L * 0.74, ang),
                   rot(0, -L * 0.84, ang), rot(iw * 0.7, -L * 0.74, ang),
                   rot(iw, -14, ang)], fill=(12, 24, 52))
        d.polygon([rot(-iw + 1, -16, ang), rot(-iw * 0.7 + 0.8, -L * 0.74 + 1, ang),
                   rot(0, -L * 0.84 + 2, ang), rot(iw * 0.7 - 0.8, -L * 0.74 + 1, ang),
                   rot(iw - 1, -16, ang)], fill=(246, 244, 236))

    sa = s / 60 * 2 * math.pi
    d.line([rot(0, SEC_TAIL, sa), rot(0, -SEC_L, sa)], fill=(214, 58, 48),
           width=int(1.6 * SS))
    d.ellipse([C - 7 * SS, C - 7 * SS, C + 7 * SS, C + 7 * SS],
              fill=(226, 196, 132), outline=(40, 30, 12), width=int(1.2 * SS))
    d.ellipse([C - 2.4 * SS, C - 2.4 * SS, C + 2.4 * SS, C + 2.4 * SS],
              fill=(16, 30, 56))
    return img


def finish(img):
    """Crop to EDGE, as bake_dial does, so the mock-up shows the device's
    framing. Showing the full 416 frame here is what hid the black ring."""
    e = EDGE * SS
    img = img.crop((C - e, C - e, C + e, C + e))
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, img.size[0] - 1, img.size[1] - 1], fill=255)
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
