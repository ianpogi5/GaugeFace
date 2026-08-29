# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Context for continuing the Twenty-Four Inch Gauge watch face. Read before changing the dial.

## What this is

A Connect IQ analog watch face, Masonic theme. Primary target is the Epix Gen 2
(416 × 416 AMOLED, 65k colours); `manifest.xml` also lists `epix2pro42mm`,
`epix2pro47mm` and `epix2pro51mm`. The concept is the twenty-four inch gauge:
the outer ring is a rule marked to eighths across a 24-hour rotation, divided
into three arcs of eight for refreshment, labour and service, with sunrise and
sunset marked and the night hours shaded.

Central hands read normal 12-hour time. The brass cursor on the outer rim shows
position in the 24-hour day. That split is deliberate — it gives the concept
without forcing a 24-hour dial read.

## Design decisions worth not relitigating

These were arrived at by iteration; earlier attempts failed for the reasons noted.

- **The emblem is applied metal, not a flat shape.** Each limb has a cast
  shadow, a gradient body running across its width, and a lit edge. Flat-filled
  polygons were tried first and looked like a sticker.
- **The emblem is large but recessed.** Shrinking it to protect the hands was
  the wrong fix; depth is what lets the hands read across it.
- **A thin dark line separates the compasses from the square.** Without it the
  crossing is illegible. A wide contact shadow was tried and swallowed the
  square's vertex.
- **Blue sunburst, not black.** Black-and-gold reads as the cheap end of the
  fraternal-supply market. The sunburst is two opposing bright lobes plus fine
  angular streaking, with a vignette toward the rim.
- **Hands are split down their length**, lit on one side and shadowed on the
  other. That split is what reads as polished metal.
- **Subdials are recessed wells** with concentric turning marks, a dark inner
  arc on the upper edge and a catch-light on the lower.

## Architecture

Three Monkey C files, plus two Python renderers that are part of the workflow.

- `source/GaugeFaceApp.mc` — `AppBase`; holds the view so `onSettingsChanged`
  can forward to it.
- `source/DialRenderer.mc` — **static layer only.** Sunburst, gauge ring, night
  shading, indices, numerals, division labels, sun markers, subdial wells,
  windows, emblem blit. Draws to whatever `Dc` it's handed.
- `source/GaugeFaceView.mc` — **live layer**, plus a separate always-on
  drawing, plus settings, sun times and the buffer lifecycle.

### The static/live split

The static layer is expensive (~700 `fillPolygon` calls: 180 sunburst wedges ×
3 radial bands, 96 ring segments, 192 indices) and never changes, so
`buildDial()` renders it once into a `BufferedBitmap` from the graphics pool
(`Graphics.createBufferedBitmap`, API 4.0.0) and `onUpdate` blits it. Per-frame
work is only hands, cursor, subdial needles and text.

`buildDial()` degrades gracefully: if `createBufferedBitmap` is absent, `_dial`
stays null and `onUpdate` calls `paintStatic(dc)` live each second. Keep
`paintStatic` free of anything that assumes it's drawing into the buffer.

**Anything baked into the static layer must trigger a rebuild when it changes.**
Subdial labels (`dialLabel`) and the presence of the top window come from
settings and are painted into the buffer, which is why `onSettingsChanged()`
calls `loadSettings()` then `buildDial()` — not just `requestUpdate()`. Sunrise
and sunset are likewise baked (the night shading and the sun markers), so a
position fix arriving later does not update the ring until the dial is rebuilt.

### Coordinates are authored at 416 and scaled

Every geometry constant in both the Monkey C and the Python is in "416-dial
units". `DialRenderer` and `GaugeFaceView` each hold `_s = width / 416.0` and a
private `p(v)` that scales-and-rounds. **Write new geometry in 416 units and put
it through `p()`** — that is what makes the Epix Pro sizes work. `polar()` and
`rot()` already apply it.

Shared constants live at the top of `DialRenderer.mc` (`DIAL_INNER` 172,
`RING_OUTER` 204, `SUB_OFFSET` 132, `SUB_RADIUS` 34) and are referenced from
the view — they are file-scope `const`, so no qualification is needed.

### Always-on

`drawAlwaysOn` is a **separate drawing**, not a dimmed version of the main one.
A lit blue dial cannot pass the always-on luminance budget. Thin gold on black,
24 hour ticks, the emblem as four outline strokes, no sunburst, no second hand,
and — when `settings.requiresBurnInProtection` is set — a per-minute pixel
shift derived from `clock.min`, so the whole drawing walks a 5 × 5 grid over 25
minutes.

## The Python renderers are part of the project

`render_v2.py` produces the design mock-up; `bake_emblem.py` regenerates the
emblem asset from the same geometry.

Requires **Pillow and numpy** (`apt-get install -y python3-numpy`; there is no
pip on this box) and the DejaVu TrueType fonts at
`/usr/share/fonts/truetype/dejavu/`.

Both scripts render at 4× supersample (`SS = 4`) and downsample, which is how
they get gradients Monkey C primitives cannot produce. A full render is about a
second — this is the fast loop, use it.

```bash
python3 render_v2.py            # mock-ups -> out/ (gitignored)
python3 bake_emblem.py          # -> resources/drawables/emblem.png, in place
python3 bake_emblem.py /tmp/x.png   # or somewhere else, to compare before committing
```

Paths are resolved from `render_v2.HERE` (the script's own directory), so both
run from any cwd. `render_v2.py`'s render sits behind `if __name__ ==
"__main__"`, because `bake_emblem.py` imports the module for its geometry and
must not trigger a mock-up re-render as a side effect — keep it that way if you
add anything at module scope.

`bake_emblem.py` compares the cropped bbox against `EXPECTED_ORIGIN` /
`EXPECTED_SIZE` and shouts if the geometry has moved out from under the Monkey
C. Silence means the blit offset is still right.

Note the bake is not bit-reproducible across library versions: the 64-colour
median-cut quantization picks marginally different palette entries, which came
out as 197 of 45,796 pixels differing by at most 22/255 — visually identical.
Don't read a small diff as a geometry change; check the printed bbox instead.

### The geometry is duplicated, in three places

`HINGE`, `TIP_L`/`TIP_R`, `VERTEX`, `ARM_L`/`ARM_R`, the ring radii and the
subdial offsets exist independently in `render_v2.py`, in `DialRenderer.mc`, and
implicitly in the baked `emblem.png`. **If you change the emblem geometry:**
change it in the Python, re-bake (which writes the asset in place), and then
follow the blit offset. `DialRenderer.drawEmblem` hardcodes the asset's
top-left as `(103, 103)` on a 416 dial at 214 × 214, which is exactly what the
current geometry bakes to; `bake_emblem.py` will tell you when that stops being
true, but it can only warn — updating `drawEmblem` and `EXPECTED_*` is manual.

Iterating on the look in Python is far faster than rebuilding for the simulator.
Use it for design changes; use the simulator for behaviour.

## Settings

Four properties in `resources/properties.xml`, surfaced by
`resources/settings/settings.xml`: `ShowSeconds` (bool), `LeftDial`/`RightDial`
(0 battery, 1 steps, 2 body battery), `TopWindow` (0 heart rate, 1 altitude,
2 off). `loadSettings()` wraps the reads in a try/catch and falls back to
`true/0/1/0`. Adding a complication means touching `dialLabel` and
`dialFraction` together, and `drawReadouts` for the top window.

Sideloaded apps don't get settings in the phone app — change them in the
simulator, or publish as a private Connect IQ app.

## Known unknowns — none of this has ever compiled

Written without an SDK available; there is no `monkeyc` on PATH here. Expect
first-build friction:

- Device IDs in `manifest.xml` need reconciling against
  `~/.Garmin/ConnectIQ/Devices/`.
- Full-screen buffered bitmap may fail to allocate. Fallbacks: reduce
  `drawSunburst` from 180 wedges to 120, or buffer at half resolution and scale
  on blit.
- If the face is slow to appear, cut the wedge count — that cost is all in
  `onLayout`.
- `computeSun()` uses `Toybox.Weather` + `Position` and needs a fix. Defaults
  are 05:45 / 18:15 (`_sunrise = 5.75`, `_sunset = 18.25`) — set these to
  Manila values.
- `bodyBattery` is guarded with a `has` check and may read zero.
- Type checking is likely to complain; the code was written to `-l 2` style but
  never verified.

## Build

Needs a developer key (once, ever):

```bash
openssl genrsa -out developer_key.pem 4096
openssl pkcs8 -topk8 -inform PEM -outform DER \
  -in developer_key.pem -out developer_key.der -nocrypt
```

Keys, `bin/` and build outputs are gitignored.

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
- The design has been iterated on hard. If a change makes the dial simpler or
  flatter, that is probably a regression, not a cleanup.
