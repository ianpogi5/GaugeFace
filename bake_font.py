"""Bakes a TrueType script face into a Connect IQ bitmap font (BMFont .fnt plus
a glyph atlas PNG).

Connect IQ has no cursive system font, and the owner's name is a user setting,
so it cannot be baked into the emblem PNG the way the G is. A custom bitmap
font is the only way to draw arbitrary text in script on device.

Caveat worth knowing: Connect IQ bitmap fonts do not scale. One atlas is baked
at BAKE_PX and used on every product; across the supported screens (390, 416
and 454 px) that is a few percent of apparent size, which is not worth three
atlases and per-device resource qualifiers.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
TTF = HERE / "assets" / "GreatVibes-Regular.ttf"
DEST_DIR = HERE / "resources" / "fonts"
FACE = "ScriptName"

BAKE_PX = 44          # matches `size` in render_v3.engraved_name
STROKE = 0            # hairline relief; see render_v3 for the design-side note
PAD = 2               # transparent gutter so neighbours can't bleed
ATLAS_W = 512

CHARS = (" !'(),-.0123456789:"
         "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
         "abcdefghijklmnopqrstuvwxyz")


def bake(ttf=TTF, px=BAKE_PX, chars=CHARS, face=FACE, dest_dir=DEST_DIR):
    fnt = ImageFont.truetype(str(ttf), px)
    ascent, descent = fnt.getmetrics()
    line_height = ascent + descent

    # measure first so the atlas can be sized before anything is drawn
    glyphs = []
    for ch in chars:
        bbox = fnt.getbbox(ch, stroke_width=STROKE)
        adv = fnt.getlength(ch)
        x0, y0, x1, y1 = bbox
        w, h = max(0, x1 - x0), max(0, y1 - y0)
        glyphs.append({"ch": ch, "w": w, "h": h, "xoff": x0, "yoff": y0,
                       "adv": int(round(adv))})

    # shelf-pack into rows
    x = y = row_h = 0
    for g in glyphs:
        if g["w"] == 0:
            g["x"], g["y"] = 0, 0
            continue
        if x + g["w"] + PAD > ATLAS_W:
            x = 0
            y += row_h + PAD
            row_h = 0
        g["x"], g["y"] = x, y
        x += g["w"] + PAD
        row_h = max(row_h, g["h"])
    atlas_h = y + row_h + PAD

    pot = 1
    while pot < atlas_h:
        pot *= 2

    atlas = Image.new("RGBA", (ATLAS_W, pot), (255, 255, 255, 0))
    d = ImageDraw.Draw(atlas)
    for g in glyphs:
        if g["w"] == 0:
            continue
        # draw at the glyph's own origin so the bbox lands exactly on (x, y)
        d.text((g["x"] - g["xoff"], g["y"] - g["yoff"]), g["ch"], font=fnt,
               fill=(255, 255, 255, 255), stroke_width=STROKE,
               stroke_fill=(255, 255, 255, 255))

    dest_dir.mkdir(parents=True, exist_ok=True)
    png_name = f"{face.lower()}.png"
    atlas.save(dest_dir / png_name, optimize=True)

    lines = [
        f'info face="{face}" size={px} bold=0 italic=0 charset="" unicode=1 '
        f'stretchH=100 smooth=1 aa=1 padding=0,0,0,0 spacing={PAD},{PAD} outline=0',
        f'common lineHeight={line_height} base={ascent} scaleW={ATLAS_W} '
        f'scaleH={pot} pages=1 packed=0 alphaChnl=1 redChnl=0 greenChnl=0 blueChnl=0',
        f'page id=0 file="{png_name}"',
        f'chars count={len(glyphs)}',
    ]
    for g in glyphs:
        lines.append(
            f'char id={ord(g["ch"])} x={g["x"]} y={g["y"]} width={g["w"]} '
            f'height={g["h"]} xoffset={g["xoff"]} yoffset={g["yoff"]} '
            f'xadvance={g["adv"]} page=0 chnl=15')
    (dest_dir / f"{face.lower()}.fnt").write_text("\n".join(lines) + "\n")

    return {"png": dest_dir / png_name, "fnt": dest_dir / f"{face.lower()}.fnt",
            "atlas": (ATLAS_W, pot), "glyphs": len(glyphs),
            "line_height": line_height, "base": ascent}


def main():
    px = int(sys.argv[1]) if len(sys.argv) > 1 else BAKE_PX
    r = bake(px=px)
    print(f"atlas {r['atlas'][0]}x{r['atlas'][1]}, {r['glyphs']} glyphs, "
          f"lineHeight {r['line_height']}, base {r['base']}")
    print("wrote", r["fnt"], "-", r["fnt"].stat().st_size, "bytes")
    print("wrote", r["png"], "-", r["png"].stat().st_size, "bytes")


if __name__ == "__main__":
    main()
