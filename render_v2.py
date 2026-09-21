"""Twenty-four inch gauge dial, rendered as a real watch.

Depth comes from four things: a sunburst blue base, applied gold elements with a
lit edge and a cast shadow, recessed snailed subdials, and a vignette under the
crystal. Nothing here is a flat fill.

Static layer  = sunburst, gauge ring, subdial wells, applied emblem, indices.
Dynamic layer = hands, cursor, needles, date text, live readings.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"

S = 416
SS = 4
W = S * SS
C = W // 2

# DejaVu, wherever the distro keeps it. Debian puts it under truetype/dejavu/,
# Fedora under dejavu-*-fonts/. Resolved rather than hardcoded so the same
# checkout renders identically on either; the dial's XII/VI and the emblem's G
# are DejaVu Serif Bold, so a silent substitution would change the artwork.
def _dejavu(stem):
    roots = ("/usr/share/fonts", "/usr/local/share/fonts",
             str(Path.home() / ".local/share/fonts"))
    for root in roots:
        for hit in Path(root).rglob(stem):
            return str(hit)
    raise SystemExit(
        f"{stem} not found. Install DejaVu:\n"
        f"  Debian/Ubuntu: apt-get install -y fonts-dejavu-core\n"
        f"  Fedora:        dnf install -y dejavu-serif-fonts dejavu-sans-fonts")


SERIF = _dejavu("DejaVuSerif-Bold.ttf")
SANS = _dejavu("DejaVuSans.ttf")
SANSB = _dejavu("DejaVuSans-Bold.ttf")

rng = np.random.default_rng(7)


def font(path, size):
    return ImageFont.truetype(path, max(1, int(size * SS)))


def pol(r, a):
    return (C + r * SS * math.sin(a), C - r * SS * math.cos(a))


def P(x, y):
    return (C + x * SS, C + y * SS)


def rot(x, y, a):
    return (C + (x * math.cos(a) - y * math.sin(a)) * SS,
            C + (x * math.sin(a) + y * math.cos(a)) * SS)


def ramp(stops):
    ts = np.array([s[0] for s in stops])
    cs = np.array([s[1] for s in stops], dtype=float)
    x = np.linspace(0, 1, 256)
    out = np.zeros((256, 3))
    for ch in range(3):
        out[:, ch] = np.interp(x, ts, cs[:, ch])
    return out


GOLD = ramp([
    (0.00, (46, 33, 12)),
    (0.12, (96, 72, 30)),
    (0.28, (188, 150, 74)),
    (0.40, (248, 226, 170)),
    (0.52, (206, 168, 92)),
    (0.72, (120, 92, 42)),
    (0.90, (58, 43, 18)),
    (1.00, (32, 24, 10)),
])

# ---------------------------------------------------------------- sunburst base

def sunburst():
    y, x = np.mgrid[0:W, 0:W]
    dx = (x - C) / SS
    dy = (y - C) / SS
    r = np.hypot(dx, dy)
    th = np.arctan2(dy, dx)

    base = np.array([16, 38, 74], dtype=float)
    hi = np.array([58, 108, 176], dtype=float)

    lobe = 0.5 + 0.5 * np.cos(2 * (th - 0.6))
    streak = np.zeros_like(th)
    for f, amp in ((320, 0.30), (137, 0.20), (61, 0.14)):
        streak += amp * np.sin(th * f + rng.uniform(0, 6.28))
    streak = (streak + 0.64) / 1.28

    t = np.clip(0.22 * lobe + 0.34 * streak * lobe + 0.10 * streak, 0, 1)
    t *= np.clip(1.15 - r / 300.0, 0.35, 1.0)

    img = base[None, None, :] + (hi - base)[None, None, :] * t[:, :, None]

    # vignette under the crystal
    vig = np.clip(1.06 - (r / 208.0) ** 3 * 0.55, 0, 1.2)
    img *= vig[:, :, None]

    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def snail(img, cx, cy, rad, tint=(20, 30, 52)):
    """Recessed subdial well with concentric turning marks."""
    d = ImageDraw.Draw(img)
    box = [cx - rad, cy - rad, cx + rad, cy + rad]
    d.ellipse(box, fill=tint)
    steps = int(rad / (1.4 * SS))
    for i in range(steps):
        rr = rad * (1 - i / steps)
        f = 1.0 + 0.16 * math.sin(i * 1.7)
        col = tuple(int(min(255, c * f)) for c in tint)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=col,
                  width=max(1, int(1.1 * SS)))
    # inner shadow top-left, catch-light bottom-right
    d.arc(box, 150, 330, fill=(8, 14, 26), width=int(2.6 * SS))
    d.arc(box, 330, 150, fill=(74, 118, 178), width=int(1.6 * SS))
    d.ellipse(box, outline=(176, 142, 72), width=int(1.8 * SS))


# --------------------------------------------------------------- applied metal

def applied(img, pts, normal, lut, drop=2.4, boost=1.0):
    """Gold element with a cast shadow, gradient body and a lit top edge."""
    sh = Image.new("L", img.size, 0)
    ImageDraw.Draw(sh).polygon([(p[0] + drop * SS, p[1] + drop * SS) for p in pts],
                               fill=190)
    sh = sh.filter(ImageFilter.GaussianBlur(1.8 * SS))
    img.paste(Image.new("RGB", img.size, (6, 12, 24)), (0, 0), sh)

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
    img.paste(Image.fromarray(rgb, "RGB"), (x0, y0), mask.crop(bbox))


def band(p1, p2, w1, w2):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    ln = math.hypot(dx, dy)
    nx, ny = -dy / ln, dx / ln
    pts = [(p1[0] + nx * w1 / 2, p1[1] + ny * w1 / 2),
           (p2[0] + nx * w2 / 2, p2[1] + ny * w2 / 2),
           (p2[0] - nx * w2 / 2, p2[1] - ny * w2 / 2),
           (p1[0] - nx * w1 / 2, p1[1] - ny * w1 / 2)]
    return [P(*p) for p in pts], (nx, ny)


def arc_text(img, text, radius, a_mid, size, fill, spacing=1.0, fnt=SANS):
    d = ImageDraw.Draw(img)
    f = font(fnt, size)
    widths = [d.textlength(ch, font=f) for ch in text]
    total = sum(widths) + spacing * SS * (len(text) - 1)
    a = a_mid - (total / (radius * SS)) / 2
    flip = 100 < math.degrees(a_mid) % 360 < 260
    if flip:
        text, widths = text[::-1], widths[::-1]
    for ch, w in zip(text, widths):
        step = (w + spacing * SS) / (radius * SS)
        ac = a + step / 2
        g = Image.new("RGBA", (int(w) + 8 * SS, int(size * SS * 1.9)), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((g.width / 2, g.height / 2), ch, font=f,
                               fill=fill, anchor="mm")
        g = g.rotate(-math.degrees(ac) + (180 if flip else 0),
                     resample=Image.BICUBIC, expand=True)
        px, py = pol(radius, ac)
        img.paste(g, (int(px - g.width / 2), int(py - g.height / 2)), g)
        a += step


HINGE = (0, -88)
TIP_L, TIP_R = (-78, 58), (78, 58)
VERTEX = (0, 96)
ARM_L, ARM_R = (-96, -2), (96, -2)

DIVISIONS = [(0, 8, "refreshment"), (8, 16, "labour"), (16, 24, "service")]
SUNRISE, SUNSET = 5.75, 18.25


def draw_static():
    img = sunburst()
    d = ImageDraw.Draw(img, "RGBA")

    # night portion of the twenty-four, darkened
    d.pieslice([C - 206 * SS, C - 206 * SS, C + 206 * SS, C + 206 * SS],
               SUNSET / 24 * 360 - 90, (SUNRISE + 24) / 24 * 360 - 90,
               fill=(2, 6, 16, 215))
    d.ellipse([C - 172 * SS, C - 172 * SS, C + 172 * SS, C + 172 * SS],
              fill=None)
    inner = Image.new("L", img.size, 0)
    ImageDraw.Draw(inner).ellipse([C - 172 * SS, C - 172 * SS,
                                   C + 172 * SS, C + 172 * SS], fill=255)
    img.paste(sunburst(), (0, 0), inner)

    d = ImageDraw.Draw(img, "RGBA")

    # gauge ring: twenty-four inches, eighths
    for i in range(192):
        a = i / 192 * 2 * math.pi
        k = i % 8
        if k == 0:
            end, col, wid = 178, (248, 226, 170), 2.8
        elif k == 4:
            end, col, wid = 186, (196, 168, 112), 1.5
        elif k in (2, 6):
            end, col, wid = 190, (150, 130, 90), 1.2
        else:
            end, col, wid = 194, (112, 100, 74), 1.0
        d.line([pol(204, a), pol(end, a)], fill=col, width=int(wid * SS))

    fnum = font(SANS, 12)
    for h in range(0, 24, 2):
        a = h / 24 * 2 * math.pi
        d.text(pol(168, a), str(h), font=fnum,
               fill=(248, 226, 170) if h % 6 == 0 else (172, 186, 208), anchor="mm")

    for h0, _, _ in DIVISIONS:
        a = h0 / 24 * 2 * math.pi
        d.line([pol(200, a), pol(178, a)], fill=(226, 196, 132), width=int(2.4 * SS))

    for h0, h1, label in DIVISIONS:
        arc_text(img, label, 150, (h0 + h1) / 2 / 24 * 2 * math.pi, 10,
                 (150, 170, 198), spacing=2.6)
    d = ImageDraw.Draw(img, "RGBA")

    # sunrise and sunset on the twenty-four hour ring
    for hr, col in ((SUNRISE, (250, 214, 120)), (SUNSET, (150, 176, 220))):
        a = hr / 24 * 2 * math.pi
        p = pol(186, a)
        d.ellipse([p[0] - 4.5 * SS, p[1] - 4.5 * SS, p[0] + 4.5 * SS, p[1] + 4.5 * SS],
                  fill=col, outline=(20, 30, 50), width=int(1.2 * SS))

    # applied inner ring
    d.ellipse([C - 172 * SS, C - 172 * SS, C + 172 * SS, C + 172 * SS],
              outline=(196, 162, 88), width=int(2.2 * SS))

    # subdial wells
    snail(img, C - 132 * SS, C, 34 * SS)
    snail(img, C + 132 * SS, C, 34 * SS)
    d = ImageDraw.Draw(img, "RGBA")

    fl = font(SANS, 9)
    d.text((C - 132 * SS, C + 20 * SS), "BATTERY", font=fl, fill=(186, 200, 220), anchor="mm")
    d.text((C + 132 * SS, C + 20 * SS), "STEPS", font=fl, fill=(186, 200, 220), anchor="mm")
    for i in range(11):
        for cx in (C - 132 * SS, C + 132 * SS):
            a = -2.2 + i * 4.4 / 10
            d.line([(cx + 30 * SS * math.sin(a), C - 30 * SS * math.cos(a)),
                    (cx + 25 * SS * math.sin(a), C - 25 * SS * math.cos(a))],
                   fill=(206, 176, 116) if i % 5 == 0 else (128, 146, 172),
                   width=int((1.8 if i % 5 == 0 else 1.1) * SS))

    # applied emblem
    for p1, p2, w1, w2 in [(VERTEX, ARM_L, 19, 19), (VERTEX, ARM_R, 19, 19)]:
        q, n = band(p1, p2, w1, w2)
        applied(img, q, n, GOLD, boost=0.88)
    for p1, p2, w1, w2 in [(HINGE, TIP_L, 17, 11), (HINGE, TIP_R, 17, 11)]:
        q, n = band(p1, p2, w1, w2)
        applied(img, q, n, GOLD)
    for tip in (TIP_L, TIP_R):
        dx, dy = tip[0] - HINGE[0], tip[1] - HINGE[1]
        ln = math.hypot(dx, dy)
        ux, uy = dx / ln, dy / ln
        nx, ny = -uy, ux
        tri = [P(tip[0] + nx * 9, tip[1] + ny * 9),
               P(tip[0] + ux * 24, tip[1] + uy * 24),
               P(tip[0] - nx * 9, tip[1] - ny * 9)]
        applied(img, tri, (nx, ny), GOLD)

    d = ImageDraw.Draw(img, "RGBA")
    hx, hy = P(*HINGE)
    d.ellipse([hx - 14 * SS, hy - 14 * SS, hx + 14 * SS, hy + 14 * SS],
              fill=(120, 94, 44), outline=(248, 226, 170), width=int(2 * SS))
    d.ellipse([hx - 5 * SS, hy - 5 * SS, hx + 5 * SS, hy + 5 * SS], fill=(14, 26, 46))

    fg = font(SERIF, 34)
    d.text((C + 1.5 * SS, C + 54 * SS + 1.5 * SS), "G", font=fg, fill=(10, 20, 38), anchor="mm")
    d.text((C, C + 54 * SS), "G", font=fg, fill=(226, 196, 132), anchor="mm")

    # date aperture, cut into the dial
    d.rounded_rectangle([C - 34 * SS, C + 108 * SS, C + 34 * SS, C + 132 * SS],
                        radius=2 * SS, fill=(10, 20, 38))
    d.rounded_rectangle([C - 34 * SS, C + 108 * SS, C + 34 * SS, C + 132 * SS],
                        radius=2 * SS, outline=(196, 162, 88), width=int(1.6 * SS))

    # heart rate well
    d.rounded_rectangle([C - 32 * SS, C - 132 * SS, C + 32 * SS, C - 110 * SS],
                        radius=2 * SS, fill=(10, 20, 38))
    d.rounded_rectangle([C - 32 * SS, C - 132 * SS, C + 32 * SS, C - 110 * SS],
                        radius=2 * SS, outline=(196, 162, 88), width=int(1.6 * SS))
    return img


def needle(d, cx, cy, frac, length, col=(244, 232, 210)):
    a = -2.2 + frac * 4.4
    tip = (cx + length * math.sin(a), C - length * math.cos(a))
    d.line([(cx, cy), tip], fill=col, width=int(2.2 * SS))
    d.ellipse([cx - 3 * SS, cy - 3 * SS, cx + 3 * SS, cy + 3 * SS], fill=(226, 196, 132))


def add_dynamic(base, h, m, s, batt=78, steps=8420, goal=10000, hr=62,
                date="SAT 29"):
    img = base.copy()
    d = ImageDraw.Draw(img, "RGBA")

    d.text((C, C + 120 * SS), date, font=font(SANSB, 13),
           fill=(236, 228, 210), anchor="mm")
    d.text((C - 12 * SS, C - 121 * SS), str(hr), font=font(SANSB, 13),
           fill=(236, 228, 210), anchor="mm")
    d.text((C + 14 * SS, C - 120 * SS), "bpm", font=font(SANS, 9),
           fill=(150, 170, 198), anchor="mm")

    needle(d, C - 132 * SS, C, batt / 100, 27 * SS)
    needle(d, C + 132 * SS, C, min(1.0, steps / goal), 27 * SS)

    ca = (h + m / 60) / 24 * 2 * math.pi
    cp, ci = pol(207, ca), pol(192, ca)
    dx, dy = cp[0] - C, cp[1] - C
    ln = math.hypot(dx, dy)
    nx, ny = -dy / ln * 8 * SS, dx / ln * 8 * SS
    d.polygon([(ci[0] + nx, ci[1] + ny), cp, (ci[0] - nx, ci[1] - ny)],
              fill=(255, 240, 200))

    ha = ((h % 12) + m / 60) / 12 * 2 * math.pi
    ma = (m + s / 60) / 60 * 2 * math.pi

    for ang, L in ((ha, 92), (ma, 148)):
        sh = Image.new("L", img.size, 0)
        ImageDraw.Draw(sh).polygon(
            [rot(-9, 20, ang), rot(-4, -L, ang), rot(4, -L, ang), rot(9, 20, ang)],
            fill=170)
        sh = sh.transform(img.size, Image.AFFINE, (1, 0, -3.5 * SS, 0, 1, -3.5 * SS))
        sh = sh.filter(ImageFilter.GaussianBlur(1.6 * SS))
        img.paste(Image.new("RGB", img.size, (6, 14, 28)), (0, 0), sh)

    d = ImageDraw.Draw(img, "RGBA")
    # two-tone polished hands: lit half and shadowed half
    for ang, L, wd in ((ha, 92, 9), (ma, 148, 7)):
        d.polygon([rot(-wd, 20, ang), rot(-wd * 0.45, -L, ang),
                   rot(0, -L, ang), rot(0, 20, ang)], fill=(250, 238, 214))
        d.polygon([rot(0, 20, ang), rot(0, -L, ang),
                   rot(wd * 0.45, -L, ang), rot(wd, 20, ang)], fill=(176, 158, 128))
        d.polygon([rot(-wd, 20, ang), rot(-wd * 0.45, -L, ang), rot(0, -L, ang),
                   rot(wd * 0.45, -L, ang), rot(wd, 20, ang)],
                  outline=(92, 78, 54), width=int(1.1 * SS))

    sa = s / 60 * 2 * math.pi
    d.line([rot(0, 36, sa), rot(0, -160, sa)], fill=(242, 206, 138), width=int(1.8 * SS))
    d.ellipse([C - 8 * SS, C - 8 * SS, C + 8 * SS, C + 8 * SS], fill=(226, 196, 132))
    d.ellipse([C - 3.5 * SS, C - 3.5 * SS, C + 3.5 * SS, C + 3.5 * SS], fill=(20, 34, 58))
    return img


def finish(img):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, W - 1, W - 1], fill=255)
    out = Image.new("RGB", img.size, (14, 14, 16))
    out.paste(img, (0, 0), mask)
    return out.resize((S, S), Image.LANCZOS)


def main():
    OUT.mkdir(exist_ok=True)
    static = draw_static()
    full = add_dynamic(static, 10, 9, 32)
    finish(static).save(OUT / "v2_static.png")
    finish(full).save(OUT / "v2_full.png")
    full.crop((C - 150 * SS, C - 150 * SS, C + 150 * SS, C + 150 * SS)) \
        .resize((640, 640), Image.LANCZOS).save(OUT / "v2_detail.png")
    print("wrote v2_static.png, v2_full.png, v2_detail.png to", OUT)


if __name__ == "__main__":
    main()
