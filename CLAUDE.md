# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Context for continuing a Masonic watch face with **two selectable dials**. Read
before changing either.

## What this is

A Connect IQ analog watch face carrying two separate dial designs, chosen by the
`DialStyle` setting. They are not variations on each other — different static
layers, different hand shapes, different complications:

- **Square and Compasses** (`DialStyle` 0, default). Built to match a reference
  watch: navy engine-turned centre, guilloche gold chapter ring, applied square
  and compasses around an ornate G, day/date aperture at three, and **the
  owner's name engraved in script** below the emblem — configurable, defaulting
  to `Singko`.
- **Twenty-Four Inch Gauge** (`DialStyle` 1). The outer ring is a rule marked to
  eighths across a 24-hour rotation, divided into three arcs of eight for
  refreshment, labour and service, with sunrise and sunset marked and the night
  hours shaded. Central hands read normal 12-hour time; a brass cursor on the
  rim shows position in the 24-hour day. That split is deliberate — it gives the
  concept without forcing a 24-hour dial read. Two subdials and a top window.

Primary target is the Epix Gen 2 (416 × 416 AMOLED, 65k colours); `manifest.xml`
also lists `epix2pro42mm`, `epix2pro47mm` and `epix2pro51mm`.

The Square dial has had a photo-fidelity pass: the band was widened to the
reference's proportions, the crosshatch replaced with its quilted lozenge
lattice, the scattered line-work added (blazing star, small square, point within
a circle), VI added at the bottom, the limbs thinned and the name retucked.
What is still approximate rather than matched: the reference's faceted bezel is
part of the physical watch and has no dial equivalent, and the G is DejaVu Serif
Bold rather than the reference's own letterform.

## Design decisions worth not relitigating

These were arrived at by iteration; earlier attempts failed for the reasons noted.

These apply to both dials unless noted.

- **The emblem is applied metal, not a flat shape.** Each limb has a cast
  shadow, a gradient body running across its width, and a lit edge. Flat-filled
  polygons were tried first and looked like a sticker.
- **The two dials get separate emblem assets.** Not one drawing at two scales:
  the Gauge emblem has heavier limbs and a larger hinge, and no G, because that
  dial draws its own G as text below centre. Baking one asset for both was
  tried and produced a 213 × 211 crop where the Gauge dial expected 214 × 214.
- **A thin dark line separates the compasses from the square** on the Square
  dial. Without it the crossing is illegible. A wide contact shadow was tried
  and swallowed the square's vertex.
- **The Gauge dial's subdials are recessed wells** with concentric turning
  marks, a dark inner arc on the upper edge and a catch-light on the lower.
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
- **The gold band is wide, and that is correct.** An earlier note here said the
  opposite — that the band must not dominate — which was wrong, and narrowing it
  was the single biggest reason the dial did not read as the reference watch.
  The reference gives roughly 40% of the radius to the band. Do not narrow it
  again.
- **The band carries a quilted lozenge lattice, not a crosshatch.** Two families
  of chords across the annulus was tried and reads as mesh or mosquito netting.
  The reference is a diaper of discrete cells, each with a lozenge outline and
  alternating bright diamond or dark saltire. In Monkey C each lozenge is a dark
  fill with the local band colour inset inside it — two fills per cell, rather
  than four lines for an outline.
- **The blue field carries fine gold line-work**, not just the emblem: a blazing
  star, a small square, a point within a circle. Without them the field reads
  empty next to the reference.

## Architecture

### The static/live split

The static layer is expensive and changes only with the settings, so
`buildDial()` renders it once into a `BufferedBitmap` from the graphics pool
(`Graphics.createBufferedBitmap`, API 4.0.0) and `onUpdate` blits it. Per-frame
work is only the hands and the day/date text.

- `source/GaugeFaceApp.mc` — `AppBase`; holds the view so `onSettingsChanged`
  can forward to it.
- `source/DialSquare.mc` — class `SquareDial`: `drawCentre` (rayed blue),
  `drawRing` (band, quilted lattice, teeth, beads), `drawMarkers` (engraved
  darts, `XII` and `VI`), `drawSymbols` (blazing star, small square, point
  within a circle), `drawApertureFrame`, `drawEmblem`.
- `source/DialGauge.mc` — class `GaugeDial`: `drawSunburst`, `drawRing` (the
  24-hour rule, night shading, division labels, sun markers), `drawSubdial`,
  `drawWindow`, `drawEmblem`.
- `source/GaugeFaceView.mc` — holds the style and dispatches everything:
  `paintStatic` → `paintSquare`/`paintGauge`, `onUpdate` → `liveSquare`/
  `liveGauge`, plus one always-on drawing that branches on style.

Both dial classes deliberately expose a `drawRing` and a `drawEmblem`; they are
separate classes, so the signatures differ freely. File-scope constants are
prefixed per style (`SQ_EMBLEM_*`, `GA_EMBLEM_*`) because Monkey C puts them all
in one namespace — watch out for `RING_OUT` (Square) versus `RING_OUTER`
(Gauge), which are different dials' constants.

**The style, the owner's name and the subdial labels are all baked into the
static layer.** That is why `onSettingsChanged()` calls `loadSettings()` then
`buildDial()` rather than just `requestUpdate()`. Sunrise and sunset are baked
too, so a position fix arriving later does not move the Gauge dial's night
shading until the buffer is rebuilt. `paintStatic` also nulls the renderer for
the style it is not drawing; only one dial is ever live.

`buildDial()` degrades gracefully: if `createBufferedBitmap` is absent, `_dial`
stays null and `onUpdate` calls `paintStatic(dc)` live each second.

### Coordinates are authored at 416 and scaled

Every geometry constant in both the Monkey C and the Python is in "416-dial
units". `DialRenderer` and `GaugeFaceView` each hold `_s = width / 416.0` and a
private `p(v)` that scales-and-rounds. **Write new geometry in 416 units and put
it through `p()`** — that is what makes the Epix Pro sizes work.

Square dial constants (`DialSquare.mc`): `BLUE_R` 128, `RING_IN` 130,
`RING_OUT` 196, `NUM_R` 163, `SQ_EMBLEM_X`/`Y` 109/110, plus the cost tunables
`RAYS` 80, `BANDS` 3, `LATTICE_A` 56 and `LATTICE_R` 3. Gauge dial constants
(`DialGauge.mc`): `DIAL_INNER` 172, `RING_OUTER` 204, `SUB_OFFSET` 132,
`SUB_RADIUS` 34, `GA_EMBLEM_X`/`Y` 103/103.

### Always-on

`drawAlwaysOn` is a **separate drawing**, not a dimmed version of either dial.
Neither lit dial can pass the always-on luminance budget. Thin gold on black,
the emblem as four outline strokes, no second hand, no name, and — when
`settings.requiresBurnInProtection` is set — a per-minute pixel shift that walks
a 5 × 5 grid over 25 minutes. It branches on style only for tick count (24 vs
12), emblem scale and hand length, and the Gauge dial keeps its rim cursor.

## The Python renderers are part of the project

Requires **Pillow and numpy** (`apt-get install -y python3-numpy`; there is no
pip on this box). A full render is about a second — this is the fast loop, use
it in preference to a simulator cycle for anything about how the dial *looks*.

```bash
python3 render_v3.py            # Square dial mock-up -> out/ (gitignored)
python3 render_v3.py Amanda     # any name, to check how it sits
python3 render_v2.py            # Gauge dial mock-up -> out/
python3 bake_emblem.py          # both emblems -> resources/drawables/
python3 bake_emblem.py /tmp sq  # one target, elsewhere, to compare first
python3 bake_font.py            # script atlas -> resources/fonts/
```

- **`render_v3.py` is the Square dial. `render_v2.py` is the Gauge dial.** One
  mock-up per dial; change the look in the matching file.
- `render_v2.py` is **also** the shared toolbox: `render_v3.py` and
  `bake_emblem.py` both import it for `GOLD`, `ramp`, `applied`, `band`, `pol`,
  `P`, `rot`, `font` and the `HERE`/`OUT`/`SS`/`W`/`C` constants. Keep its render
  behind `if __name__ == "__main__"` so importing it stays side-effect free.
- Paths resolve from `render_v2.HERE` (the script's own directory), so all of
  these run from any cwd.

### The geometry is duplicated, and the bakers check it

Emblem geometry (`HINGE`, `TIP_*`, `VERTEX`, `ARM_*`) lives in the Python, in
the two baked PNGs, and implicitly in the Monkey C blit offsets. `bake_emblem.py`
holds a `TARGETS` table — per-style scale, limb widths, tip size, hinge radius,
whether the G is baked in — and checks each cropped bbox against the `origin`
and `size` it expects, naming the Monkey C constant to fix. It exits non-zero if
either drifts. Silence means `SQ_EMBLEM_*` and `GA_EMBLEM_*` are still right.
It can only warn — updating the Monkey C is manual.

The bake is not bit-reproducible across library versions (64-colour median-cut
picks slightly different palette entries). Don't read a small pixel diff as a
geometry change; check the printed bbox.

### The script font

Connect IQ has no cursive system font, and the name is a user setting, so it
cannot be baked into the emblem PNG the way the G is. `bake_font.py` renders
`assets/GreatVibes-Regular.ttf` (SIL OFL 1.1, licence in `assets/`) into a
BMFont `.fnt` plus a glyph atlas at `resources/fonts/`, declared as
`Rez.Fonts.ScriptName`.

Three things to know:

- **Connect IQ bitmap fonts do not scale.** One atlas is baked at `BAKE_PX = 34`
  and used on every product. Across 390/416/454 px screens that is a few percent
  of apparent size — not worth three atlases and per-device resource qualifiers.
- `BAKE_PX` must track `size` in `render_v3.engraved_name`, or the mock-up and
  the watch will disagree about how big the name is.
- **A bitmap font carries one integer advance per glyph and no kerning**, so it
  cannot reproduce PIL's own string layout: the rounding drifts by up to a pixel
  per letter (−2.5px across "Singko" at 34px; it happened to cancel at 44px,
  which made an earlier check look perfect). `render_v3.name_mask` therefore
  steps a pen by the same rounded advances the atlas stores instead of calling
  `text()` on the whole string. Keep it that way — it is what makes the mock-up
  honest about the device.

If you change the typeface, keep it OFL or similarly redistributable — this repo
is public.

## Settings

Six properties in `resources/properties.xml`:

| property | applies to | notes |
| --- | --- | --- |
| `DialStyle` | both | 0 Square (default), 1 Gauge |
| `OwnerName` | Square | string, default `Singko`, `maxLength="16"`; about twelve characters fit before the script crowds the square |
| `ShowSeconds` | both | |
| `LeftDial`, `RightDial` | Gauge | 0 battery, 1 steps, 2 body battery |
| `TopWindow` | Gauge | 0 heart rate, 1 altitude, 2 off |

The style-specific settings stay visible on both dials — Connect IQ settings
cannot be conditionally hidden — so their prompts say which dial they affect.
Adding a Gauge complication means touching `dialLabel` and `dialFraction`
together, and `liveGauge` for the top window.

Sideloaded apps don't get settings in the phone app — change them in the
simulator, or publish as a private Connect IQ app.

## Known unknowns — none of this has ever compiled

Written without an SDK available; there is no `monkeyc` on PATH here. Expect
first-build friction:

- **The font is the least certain part.** Nothing has confirmed that Garmin's
  resource compiler accepts this exact BMFont dialect, or that it wants an RGBA
  atlas rather than a palettised one. If it rejects the font, `drawName` already
  falls back to `FONT_SYSTEM_SMALL`. What *is* verified: glyphs reassembled from
  the baked `.fnt` metrics match the mock-up's own layout to within half a pixel
  of centre on several names.
- Device IDs in `manifest.xml` need reconciling against
  `~/.Garmin/ConnectIQ/Devices/`.
- Full-screen buffered bitmap may fail to allocate. Fallbacks: halve `RAYS`, or
  buffer at half resolution and scale on blit.
- The static layer is roughly **1,180** primitive calls for the Square dial
  (the quilted band is 688 of them) and ~700 for the Gauge. Once only, in
  `onLayout`, but if the face is slow to appear, drop `LATTICE_R` to 2 before
  touching `RAYS` — the band matters more to the likeness than the rays, which
  the emblem largely covers.
- Carrying two dials doubles the static-layer code and adds a second emblem
  asset (~60 KB of drawables total). Only one dial's renderer and bitmap are
  live at a time, so the cost is mostly flash rather than RAM — but this app was
  already flagged as possibly unable to allocate a full-screen buffer.
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
- Constants are duplicated between the Python and the Monkey C on purpose. After
  changing either, check them against each other; a mismatch shows up as a dial
  that looks right in Python and wrong on the watch.
- There is no compiler here, so cross-reference by script instead: properties
  read by Monkey C against `properties.xml`, `@Strings.*` in `settings.xml`
  against `strings.xml`, `Rez.*` against the resource declarations, and the
  methods `paintSquare`/`paintGauge` call against what each dial class defines.
  That audit is what caught the shared-emblem and missing-marker mistakes.
- The design has been iterated on hard. If a change makes the dial simpler or
  flatter, that is probably a regression, not a cleanup.
