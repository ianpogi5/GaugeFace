"""Bake the Square dial's static layer to a drawable, one per screen size.

Why this exists: drawing the static layer on device tripped the Connect IQ
watchdog. The band alone is ~470 fillPolygon calls, and every vertex goes
through polar(), so onLayout was asking for ~3,200 trig evaluations in one
callback. The watch killed it twice and showed a broken-icon watch face.

The Python renderer already produces the exact dial, so bake it: onLayout
blits one bitmap and the per-frame cost is the hands and the text, as before.
The owner's name is NOT baked in -- it is a user setting, so DialSquare.mc
draws it over the top in the script font.

Run after any change to render_v3's static layer:

    python3 bake_dial.py              # all sizes -> resources-round-*/drawables/
    python3 bake_dial.py /tmp         # elsewhere, to compare first

Geometry is authored at 416 and rendered supersampled, so the other sizes are
a LANCZOS downsample of the same image -- matching the `_s = width / 416.0`
scaling the Monkey C applies to everything else.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import render_v2 as R
import render_v3 as V3

HERE = R.HERE
W = R.W

# deviceFamily -> screen size. epix2 and epix2pro47mm share round-416x416.
TARGETS = {
    "round-390x390": 390,
    "round-416x416": 416,
    "round-454x454": 454,
}

FILE = "dial_square.png"
RES_ID = "DialSquare"

# The dial's outermost painted radius, in 416-units: the band's outer rim plus
# its stroke. The bake is cropped to this rather than to the full 416 frame, so
# the gold band reaches the rim of a round screen. Cropping the 4x supersample
# costs no resolution -- nothing is scaled up.
#
# The consequence: the screen is 2*EDGE units wide for this dial, not 416. The
# live layer (name, day/date, hands) must scale to match or it drifts off the
# artwork, which is what SQ_EDGE in DialSquare.mc is for. Keep the two equal.
EDGE = V3.EDGE      # render_v3 owns it, so the mock-up crops the same way

# 256 is the most a palettised PNG carries, and the dial is two ramps (navy and
# gold) so it quantises well. Dithering matters here: without it the blue field
# and the gold band both band visibly on a 65k-colour AMOLED.
COLORS = 256


def bake(px):
    """The static layer, minus the name, cropped to the dial's outer edge."""
    img = V3.draw_static(name=None, day=None, date=None)

    e = EDGE * R.SS
    out = img.crop((R.C - e, R.C - e, R.C + e, R.C + e))

    # round off the corners the crop leaves, so nothing juts past the bezel
    mask = Image.new("L", out.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, out.size[0] - 1, out.size[1] - 1], fill=255)
    disc = Image.new("RGB", out.size, (0, 0, 0))
    disc.paste(out, (0, 0), mask)

    out = disc.resize((px, px), Image.LANCZOS)
    return out.quantize(colors=COLORS, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG)


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE
    for family, px in sorted(TARGETS.items()):
        dest = root / f"resources-{family}" / "drawables"
        dest.mkdir(parents=True, exist_ok=True)

        img = bake(px)
        path = dest / FILE
        img.save(path, optimize=True)

        (dest / "drawables.xml").write_text(
            '<drawables>\n'
            f'    <!-- Baked by bake_dial.py; see the module docstring. -->\n'
            f'    <bitmap id="{RES_ID}" filename="{FILE}" />\n'
            '</drawables>\n')

        print(f"{family:16s} {px}x{px}  {path.stat().st_size:7d} bytes  -> {path}")


if __name__ == "__main__":
    main()
