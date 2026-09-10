# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Context for continuing the Square and Compasses watch face. Read before changing the dial.

## What this is

A Connect IQ analog watch face, Masonic theme, built to match a specific
reference watch: a navy engine-turned centre, a guilloche gold chapter ring, an
applied square and compasses around an ornate G, a day/date aperture at three,
and **the owner's name engraved in script below the emblem** — configurable,
defaulting to `Singko`.

Primary target is the Epix Gen 2 (416 × 416 AMOLED, 65k colours); `manifest.xml`
also lists `epix2pro42mm`, `epix2pro47mm` and `epix2pro51mm`.

An earlier "Twenty-Four Inch Gauge" design (a 24-hour rule ring, three arcs of
eight, sunrise/sunset markers, two subdials) was **replaced** by this one. It
survives only as `render_v2.py` — see the note on that file below, because it is
still a live dependency.

## Design decisions worth not relitigating

These were arrived at by iteration; earlier attempts failed for the reasons noted.

- **The emblem is applied metal, not a flat shape.** Each limb has a cast
  shadow, a gradient body running across its width, and a lit edge. Flat-filled
  polygons were tried first and looked like a sticker.
- **The G is baked into the emblem PNG, not drawn on device.** It needs the same
  gradient metal as the limbs, and Monkey C primitives cannot produce that. It
  is static, so baking costs nothing.
- **Numerals and hour darts are engraved *into* the gold**, not laid on top: a
  light lower lip with the dark shape over it. Gold-on-gold was illegible — the
  first pass had an invisible `XII`.
- **Text gets its own gold ramp (`GOLD_TEXT`).** The full `GOLD` ramp runs dark
  at both ends, which buries small glyphs; the first `G` and the first engraved
  name both disappeared into the dial.
- **Blue centre, not black.** Black-and-gold reads as the cheap end of the
  fraternal-supply market.
- **Hands are split down their length**, lit on one side and shadowed on the
  other. That split is what reads as polished metal.
- **The gold band must not dominate.** Two early passes had it too wide and too
  bright, and the dial read as a gold watch with a blue hole in it. The centre
  is the subject.

## Architecture

### The static/live split

The static layer is expensive and changes only with the settings, so
`buildDial()` renders it once into a `BufferedBitmap` from the graphics pool
(`Graphics.createBufferedBitmap`, API 4.0.0) and `onUpdate` blits it. Per-frame
work is only the hands and the day/date text.

- `source/GaugeFaceApp.mc` — `AppBase`; holds the view so `onSettingsChanged`
  can forward to it.
- `source/DialRenderer.mc` — static layer: `drawCentre` (rayed blue),
  `drawRing` (guilloche band, lattice, beads), `drawMarkers` (engraved darts and
  `XII`), `drawApertureFrame`, `drawEmblem` (blit).
- `source/GaugeFaceView.mc` — live layer, the engraved name, and a separate
  always-on drawing.

**The owner's name is baked into the static layer.** It is drawn by
`GaugeFaceView.drawName` into the buffer, not per frame, which is why
`onSettingsChanged()` calls `loadSettings()` then `buildDial()` rather than just
`requestUpdate()`. If you add anything else that varies with settings, it must
go through the same rebuild.

`buildDial()` degrades gracefully: if `createBufferedBitmap` is absent, `_dial`
stays null and `onUpdate` calls `paintStatic(dc)` live each second.

### Coordinates are authored at 416 and scaled

Every geometry constant in both the Monkey C and the Python is in "416-dial
units". `DialRenderer` and `GaugeFaceView` each hold `_s = width / 416.0` and a
private `p(v)` that scales-and-rounds. **Write new geometry in 416 units and put
it through `p()`** — that is what makes the Epix Pro sizes work.

Shared constants at the top of `DialRenderer.mc`: `BLUE_R` 148, `RING_IN` 150,
`RING_OUT` 198, `EMBLEM_X`/`EMBLEM_Y` 98/100, plus the cost tunables `RAYS`,
`BANDS` and `LATTICE`.

### Always-on

`drawAlwaysOn` is a **separate drawing**, not a dimmed version of the main one.
A lit blue dial cannot pass the always-on luminance budget. Thin gold on black,
12 hour ticks, the emblem as four outline strokes, no second hand, no name, and
— when `settings.requiresBurnInProtection` is set — a per-minute pixel shift
that walks a 5 × 5 grid over 25 minutes.

## The Python renderers are part of the project

Requires **Pillow and numpy** (`apt-get install -y python3-numpy`; there is no
pip on this box). A full render is about a second — this is the fast loop, use
it in preference to a simulator cycle for anything about how the dial *looks*.

```bash
python3 render_v3.py            # the design mock-up -> out/ (gitignored)
python3 render_v3.py Amanda     # any name, to check how it sits
python3 bake_emblem.py          # emblem + G -> resources/drawables/emblem.png
python3 bake_font.py            # script atlas -> resources/fonts/
```

- **`render_v3.py` is the current design.** Change the look here first.
- **`render_v2.py` is the superseded 24-hour design, but it is still imported.**
  `render_v3.py` and `bake_emblem.py` both `import render_v2` for the shared
  toolbox: `GOLD`, `ramp`, `applied`, `band`, `pol`, `P`, `rot`, `font`, and the
  `HERE`/`OUT`/`SS`/`W`/`C` constants. Do not delete it, and keep its render
  behind `if __name__ == "__main__"` so importing it stays side-effect free.
- Paths resolve from `render_v2.HERE` (the script's own directory), so all of
  these run from any cwd.

### The geometry is duplicated, and the bakers check it

Emblem geometry (`HINGE`, `TIP_*`, `VERTEX`, `ARM_*`, scaled by `SCALE = 1.06`)
lives in the Python, in the baked PNG, and implicitly in the Monkey C blit
offset. `bake_emblem.py` compares the cropped bbox against `EXPECTED_ORIGIN` /
`EXPECTED_SIZE` and shouts if it has moved; silence means `EMBLEM_X`/`EMBLEM_Y`
in `DialRenderer.mc` are still right. It can only warn — updating the Monkey C
is manual.

The bake is not bit-reproducible across library versions (64-colour median-cut
picks slightly different palette entries). Don't read a small pixel diff as a
geometry change; check the printed bbox.

### The script font

Connect IQ has no cursive system font, and the name is a user setting, so it
cannot be baked into the emblem PNG the way the G is. `bake_font.py` renders
`assets/GreatVibes-Regular.ttf` (SIL OFL 1.1, licence in `assets/`) into a
BMFont `.fnt` plus a glyph atlas at `resources/fonts/`, declared as
`Rez.Fonts.ScriptName`.

Two things to know:

- **Connect IQ bitmap fonts do not scale.** One atlas is baked at `BAKE_PX = 44`
  and used on every product. Across 390/416/454 px screens that is a few percent
  of apparent size — not worth three atlases and per-device resource qualifiers.
- `BAKE_PX` must track `size` in `render_v3.engraved_name`, or the mock-up and
  the watch will disagree about how big the name is.

If you change the typeface, keep it OFL or similarly redistributable — this repo
is public.

## Settings

Two properties in `resources/properties.xml`: `OwnerName` (string, default
`Singko`, `alphaNumeric` with `maxLength="16"`) and `ShowSeconds` (boolean).
Roughly twelve characters fit on the dial before the script starts crowding the
square.

Sideloaded apps don't get settings in the phone app — change them in the
simulator, or publish as a private Connect IQ app.

## Known unknowns — none of this has ever compiled

Written without an SDK available; there is no `monkeyc` on PATH here. Expect
first-build friction:

- **The font is the least certain part.** `bake_font.py`'s output is verified
  self-consistent — glyphs reassembled from the `.fnt` metrics are pixel-identical
  to a direct render — but nothing has confirmed that Garmin's resource compiler
  accepts this exact BMFont dialect, or that it wants an RGBA atlas rather than a
  palettised one. If it rejects the font, `drawName` already falls back to
  `FONT_SYSTEM_SMALL`.
- Device IDs in `manifest.xml` need reconciling against
  `~/.Garmin/ConnectIQ/Devices/`.
- Full-screen buffered bitmap may fail to allocate. Fallbacks: halve `RAYS`, or
  buffer at half resolution and scale on blit.
- The static layer is roughly 900 primitive calls. Once only, in `onLayout`, but
  if the face is slow to appear, `RAYS` and `LATTICE` are the levers.
- Type checking is likely to complain; the code was written to `-l 2` style but
  never verified. `drawName`'s font fallback mixes `FontResource` and
  `FontDefinition` in one ternary, which is a likely first complaint.

## Build

Needs a developer key (once, ever):

```bash
openssl genrsa -out developer_key.pem 4096
openssl pkcs8 -topk8 -inform PEM -outform DER \
  -in developer_key.pem -out developer_key.der -nocrypt
```

Keys, `bin/`, `out/` and build outputs are gitignored.

```bash
monkeyc -f monkey.jungle -o bin/GaugeFace.prg -y developer_key.der -d epix2 -r
connectiq                       # start the simulator, then:
monkeydo bin/GaugeFace.prg epix2
```

Run the simulator's burn-in test (simulates 24 hours) before wearing it
overnight.

## Working notes for Claude

- Build and run the simulator after each change to the Monkey C; don't batch up
  unverified edits.
- When something looks wrong, render it in Python first and compare — it is
  cheaper than a simulator cycle and isolates design from behaviour.
- Constants are duplicated between `render_v3.py` and the Monkey C on purpose.
  After changing either, check them against each other; a mismatch shows up as a
  dial that looks right in Python and wrong on the watch.
- The design has been iterated on hard. If a change makes the dial simpler or
  flatter, that is probably a regression, not a cleanup.
