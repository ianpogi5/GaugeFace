# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Context for continuing a Masonic watch face with **two selectable dials**. Read
before changing either.

## What this is

A Connect IQ analog watch face carrying two separate dial designs, chosen by the
`DialStyle` setting. They are not variations on each other — different static
layers, different hand shapes, different complications:

- **Square and Compasses** (`DialStyle` 0, default). Built to match a reference
  watch: navy engine-turned centre, a near-black chapter ring carrying a gold
  quilted lattice, applied square and compasses around an ornate G, day/date
  aperture at three, and **the owner's name engraved in script** below the
  emblem — configurable, defaulting to `Singko`.
- **Twenty-Four Inch Gauge** (`DialStyle` 1). The outer ring is a rule marked to
  eighths across a 24-hour rotation, divided into three arcs of eight for
  refreshment, labour and service, with sunrise and sunset marked and the night
  hours shaded. Central hands read normal 12-hour time; a brass cursor on the
  rim shows position in the 24-hour day. That split is deliberate — it gives the
  concept without forcing a 24-hour dial read. Two subdials and a top window.

Primary target is the Epix Gen 2 (416 × 416 AMOLED, 65k colours); `manifest.xml`
also lists `epix2pro42mm` (390 × 390), `epix2pro47mm` (416 × 416) and
`epix2pro51mm` (454 × 454). Those three sizes are the `deviceFamily` values that
select the baked Square dial, so they matter more than the product names do.

The Square dial has had a photo-fidelity pass: the band was widened to the
reference's proportions, the crosshatch replaced with its quilted lozenge
lattice, the scattered line-work added (blazing star, small square, point within
a circle), VI added at the bottom, the limbs thinned and the name retucked.
A second pass fixed the band's material — a blue field with gold ornament, not a
gold slab with dark engraving — a third narrowed the band to taste, and a
fourth ran it to the screen edge and faded it out there, taking the band's
field from navy to near-black on the way. It was then baked to a PNG, not for
looks but because drawing it live killed the watch face. What is still
approximate rather than matched: the band is narrower than the reference's, the
reference's faceted bezel is part of the physical watch and has no dial
equivalent, and the G is DejaVu Serif Bold rather than the reference's own
letterform.

## Design decisions worth not relitigating

These were arrived at by iteration; earlier attempts failed for the reasons noted.

These apply to both dials unless noted.

- **Legibility outranks ornament.** After a few days on the wrist the Square
  dial could not be read: gold dauphine hands the width of the compass limbs
  disappeared into the emblem, the minute hand (130) stopped inside the blue
  centre, and the hour darts were the same size and gold as the lattice's
  diamonds. The fix kept every material decision below and changed only what
  wins attention: the lattice is held at half brightness, the ten hours without
  numerals get bright radial batons (`BATON_*`), XII/VI are larger with a dark
  outline, and the hands are inlaid swords — dark rim, gold halves, ivory
  centre — with the minute hand (172) reaching into the batons and a thin red
  seconds hand. Removing the band was considered and rejected: it is where the
  markers live, so it would have made the dial harder to read, not easier. If
  a change dims the batons or the hands back toward the ornament, it is a
  regression.

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
- **Marker treatment follows what they sit on.** On the Square dial's blue band
  the numerals and batons are gold with a dark relief behind them. They were
  previously engraved dark-into-gold, which was right when the band was a gold
  slab and would vanish now. The Gauge dial's gold-on-gold first pass had an
  invisible `XII`, which is what started this rule.
- **Text gets its own gold ramp (`GOLD_TEXT`).** The full `GOLD` ramp runs dark
  at both ends, which buries small glyphs; the first `G` and the first engraved
  name both disappeared into the dial.
- **The *centre* stays blue.** Black-and-gold throughout reads as the cheap end
  of the fraternal-supply market, which is why an all-dark variant was rejected.
  The band going near-black is fine precisely because the navy centre still
  carries the dial.
- **Hands are split down their length**, lit on one side and shadowed on the
  other. That split is what reads as polished metal. On the Square dial the
  hands also carry a dark rim and an ivory inlay (`handInlaid`), drawn with
  flat fills only so the mock-up in `render_v3.hands` is exactly what the
  device can draw; hand sizes are `render_v3.HOUR_*`/`MIN_*`/`SEC_*` and are
  duplicated as literals in `liveSquare`.
- **The band is a dark field carrying gold ornament — not a gold slab.** This is
  the part that matters, and it took three passes to get right. The band was
  first built as gold with dark engraving cut into it; widening that toward the
  reference's proportions made the dial *worse*, because it widened the wrong
  material. Do not turn it back into gold. It was navy for a while and is now
  near-black, which is crisper under the gold and, on an AMOLED, genuinely off.
- **The dial runs to the screen edge and fades out there; it has no outer rim.**
  Ending the band at radius 196 and capping it with a bright gold circle left a
  12px black margin of our own between the dial and the bezel, and on the watch
  it read as a disc pasted onto the screen. The band now reaches `RING_OUT` 208
  and falls to black from `FADE_FROM` 192. Do not add an outer rim or an outer
  bead ring back — both reinstate the hard edge.
- **No black ring between the dial and the bezel — ever.** The owner has asked
  for this explicitly. The lattice runs one row past the screen edge
  (`LATTICE_R + 1` rows) so the bezel cuts the ornament off rather than the
  ornament stopping short of it. A black ring came back once by accident: the
  crop was derived as `RING_OUT + 2`, so moving `RING_OUT` to 208 moved the crop
  to 210 while `SQ_EDGE` stayed 198 — the dial shrank 6% under its own hands and
  left ~20 units of bare field at the rim. The mock-up hid it because it showed
  the full 416 frame. `render_v3.EDGE` now owns the crop, `bake_dial` and
  `finish()` both use it, and it is a literal, not derived from the band.
- **The band's *width* is a taste call, not a fidelity one.** The reference gives
  roughly 40% of the radius to the band; this dial gives it 30%
  (`BLUE_R` 144, band 146–208 with the outer 16 fading out), because a narrower
  ring was preferred once the material was right. Earlier notes here asserted first that the band must not
  dominate and then that it must be wide — both overstated. Change the width
  freely; just remember `NUM_R`, `LATTICE_R`, the line-work radii, the emblem
  scale and the name's `y` all key off it — and that changing it now means
  changing `render_v3.py` and re-running `bake_dial.py`, since that is what
  ships.
- **The band carries a quilted lozenge lattice, not a crosshatch.** Two families
  of chords across the annulus was tried and reads as mesh or mosquito netting.
  The reference is a diaper of discrete cells, each a gold lozenge with a small
  gold diamond in every other eye. **Leave the other cells empty** — filling
  them all turns the band back into a solid mat. Keep `LATTICE_R` such that
  cells stay roughly square — two rows across a 50-unit band matches three rows
  across 66. (`DialSquare.drawRing` builds each lozenge as a gold fill with the
  local blue inset back inside it — two fills per cell rather than four lines
  for an outline. That is a record of how it was done in primitives; the dial
  that ships comes from `render_v3.ornate_ring`.) The lattice is drawn at
  about half brightness (`(104, 86, 50)`, diamonds `(124, 112, 84)`), so it
  sits behind the batons — see *Legibility outranks ornament*.
- **The blue field carries fine gold line-work**, not just the emblem: a blazing
  star, a small square, a point within a circle. Without them the field reads
  empty next to the reference.

## Architecture

### The static/live split

The static layer is expensive and changes only with the settings, so
`buildDial()` renders it once into a `BufferedBitmap` from the graphics pool
(`Graphics.createBufferedBitmap`, API 4.0.0) and `onUpdate` blits it. Per-frame
work is only the hands and the day/date text.

The two dials fill that buffer differently. **The Gauge dial is drawn into it by
`GaugeDial`; the Square dial blits a pre-baked PNG** — see the next section,
which is the single most important thing on this page to know before touching
`DialSquare.mc`.

- `source/GaugeFaceApp.mc` — `AppBase`; holds the view so `onSettingsChanged`
  can forward to it.
- `source/DialSquare.mc` — the Square dial's constants, and class `SquareDial`
  (`drawCentre`, `drawRing`, `drawMarkers`, `drawSymbols`, `drawApertureFrame`,
  `drawEmblem`). **The class is no longer reached on device** — nothing calls
  `new SquareDial` since the dial was baked. Of the whole file only `SQ_EDGE` is
  referenced outside it, by `GaugeFaceView.applyScale`. Don't "clean it up":
  see *The Square dial's static layer is a baked PNG*.
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
stays null and `onUpdate` calls `paintStatic(dc)` live each second. That is now
cheap for the Square dial — it is a blit either way — and expensive for the
Gauge dial, which is the one that would actually suffer.

### The Square dial's static layer is a baked PNG

Drawing it live **tripped the Connect IQ watchdog on a real Epix**. The band
alone is ~470 `fillPolygon` calls and every vertex goes through `polar()`, so
`onLayout` asked the VM for roughly 3,200 trig evaluations in one callback; the
watch killed the face twice and showed the broken-icon placeholder. This is the
single hardest constraint the project has hit, and it is what the current
architecture is shaped around.

`bake_dial.py` renders the same artwork out of `render_v3.draw_static` — one PNG
per screen size, into `resources-round-{390x390,416x416,454x454}/drawables/` —
and `paintSquare` does `drawBitmap` plus `drawName`. Consequences:

- **Connect IQ picks the directory by `deviceFamily`, not by product.** `epix2`
  and `epix2pro47mm` are both `round-416x416`; `epix2pro42mm` is `round-390x390`
  and `epix2pro51mm` is `round-454x454`. That mapping is `bake_dial.TARGETS`, and
  it is why `monkey.jungle` needs no resource paths — the convention finds them.
- **`render_v3.draw_static` is now the only place the Square dial's draw *order*
  exists.** The old warning about the aperture frame having to follow the emblem
  still applies; it just moved out of the Monkey C along with the drawing.
- **The name is not baked.** It is a user setting, so `bake_dial` passes
  `name=None` and `drawName` writes it over the bitmap, into the same buffer.
  The aperture is likewise baked empty — day and date are live.
- **Re-run `bake_dial.py` after any change to `render_v3`'s static layer**, or
  the watch keeps showing the old dial while the mock-up shows the new one.
- **`DialSquare.mc` is now the Monkey C mirror of that Python, not a code path.**
  Keeping it costs flash and nothing else, and it is the only in-repo record of
  how the dial is constructed in primitives. If the two ever have to agree
  again, they still can; if you delete it, keep `SQ_EDGE` somewhere.

The Gauge dial is still drawn live — it never tripped the watchdog, being ~700
calls without the lattice.

### Coordinates are authored at 416 and scaled

Every geometry constant in both the Monkey C and the Python is in "416-dial
units". The dial classes and `GaugeFaceView` each hold an `_s` and a private
`p(v)` that scales-and-rounds. **Write new geometry in 416 units and put it
through `p()`** — that is what makes the Epix Pro sizes work.

**The two dials do not share a scale**, which is the trap here.
`GaugeFaceView.applyScale` sets

```
_s = (_style == STYLE_GAUGE) ? (_w / 416.0) : (_w / (2.0 * SQ_EDGE));
```

because the Square dial's PNG is baked *cropped to the dial's rim* — so the
screen is `2 * SQ_EDGE` = 396 units wide for that dial, not 416. Crop it
otherwise and the band floats inside a black ring instead of reaching the edge
of a round screen. `SQ_EDGE` (`DialSquare.mc`) and `EDGE` (`render_v3.py`, used by `bake_dial.py`) must
stay equal, or the live layer — name, day/date, hands — drifts off the artwork.
`applyScale` runs from `buildDial`, not `onLayout`, because the style can change
without a relayout.

Square dial constants (`DialSquare.mc`): `BLUE_R` 144, `RING_IN` 146,
`RING_OUT` 208, `FADE_FROM` 192, `SQ_EDGE` 198, `NUM_R` 171,
`SQ_EMBLEM_X`/`Y` 97/99, plus the cost tunables `RAYS` 80, `BANDS` 3,
`LATTICE_A` 56 and `LATTICE_R` 2 — all of which now only drive the Python's
counterparts, since the class is unreachable. Gauge dial constants
(`DialGauge.mc`), which are live: `DIAL_INNER` 172, `RING_OUTER` 204,
`SUB_OFFSET` 132, `SUB_RADIUS` 34, `GA_EMBLEM_X`/`Y` 103/103.

### Always-on

`drawAlwaysOn` is a **separate drawing**, not a dimmed version of either dial.
Neither lit dial can pass the always-on luminance budget. Thin gold on black,
the emblem as four outline strokes, no second hand, no name, and — when
`settings.requiresBurnInProtection` is set — a per-minute pixel shift that walks
a 5 × 5 grid over 25 minutes. It branches on style only for tick count (24 vs
12), emblem scale and hand length, and the Gauge dial keeps its rim cursor.

## The Python renderers are part of the project

Requires **Pillow, numpy and DejaVu**. On this box (Fedora) they are installed;
`dnf install -y python3-pillow python3-numpy dejavu-serif-fonts dejavu-sans-fonts`
is the equivalent elsewhere. `render_v2._dejavu` resolves the font paths by
search rather than hardcoding Debian's, because the dial's `XII`/`VI` and the
emblem's `G` are DejaVu Serif Bold and a silent substitution would change the
artwork — it exits with an install hint rather than rendering something else.

A full render is about a second (measured: 1.0s for `render_v3`, 1.2s for
`render_v2`, 2.4s for all three dial bakes). **This is the fast loop** — use it
in preference to a simulator cycle for anything about how the dial *looks*.

```bash
python3 render_v3.py            # Square dial mock-up -> out/ (gitignored)
python3 render_v3.py Amanda     # any name, to check how it sits
python3 render_v2.py            # Gauge dial mock-up -> out/
python3 bake_dial.py            # Square static layer -> resources-round-*/
python3 bake_dial.py /tmp       # elsewhere, to compare before overwriting
python3 bake_emblem.py          # both emblems -> resources/drawables/
python3 bake_emblem.py /tmp sq  # one target, elsewhere, to compare first
python3 bake_font.py            # script atlas -> resources/fonts/
```

- **`render_v3.py` is the Square dial. `render_v2.py` is the Gauge dial.** One
  mock-up per dial; change the look in the matching file.
- **`bake_dial.py` is not a mock-up — it is a build step.** It imports
  `render_v3.draw_static`, so `render_v3` is now the *source* of what ships for
  the Square dial, not just a preview of it. Change `render_v3`'s static layer
  and the device shows the old dial until you re-run it.
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
  of apparent size — still judged not worth three atlases. (The per-device
  `resources-round-*` directories now exist for the baked dial, so doing it
  would be cheap; it just has not been worth doing.)
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

## Build status

**The SDK is installed here now** — `connectiq-sdk-lin-9.2.0-2026-06-09` under
`~/.Garmin/ConnectIQ/Sdks/`, with `monkeyc`, `monkeydo` and `connectiq` on PATH.
Changes made in this environment can and should be compiled before being
handed over. Earlier notes on this page assumed no compiler; that is no longer
true, and the advice that followed from it has been rewritten.

Verified in this environment:

- **All four products build clean at `-l 2`** — `epix2`, `epix2pro42mm`,
  `epix2pro47mm`, `epix2pro51mm`. A device build takes about four seconds.
- **Device IDs in `manifest.xml` reconcile** against
  `~/.Garmin/ConnectIQ/Devices/`; all four exist. Their `deviceFamily` values
  are what select the baked dial, see above.
- **`bake_emblem.py` and `bake_dial.py` both run clean.** The emblem baker
  exits 0 with `square bbox (97, 99, …) size (225, 223)` and `gauge bbox
  (103, 103, …) size (214, 214)`, so `SQ_EMBLEM_*` and `GA_EMBLEM_*` are still
  right; the dial baker reproduces all three sizes. (`bake_font.py` was not
  re-run — the atlas in the repo is the one known to work on device.)
- **`.prg` sizes**: 394 KB at `-l 2`, 299 KB with `-r`, against a 64 MB
  `maxPrgFilespace` — the three baked dials (78–98 KB each) and the two emblems
  (26 + 33 KB) are nowhere near a budget problem. Only one dial PNG ships per
  device family.
- **`-l 3` does not pass** — 19 errors, all mechanical and none behavioural:
  `fillPolygon` being handed a bare `Array` where it wants
  `Array<Array[Numeric, Numeric]>` (13 of them), `Numeric` reaching a `Float`
  parameter (3), `Weather.getSunrise` being passed a nullable `Moment` (2), and
  `now.day_of_week.toUpper()` on a `FORMAT_MEDIUM` info where the type says
  `Number` (1). Worth fixing if you want `-l 3`; nothing here misbehaves at
  runtime. The `drawName` font-fallback ternary that an earlier note predicted
  would be the first complaint is *not* among them.

Known from the device, not reproducible here:

- **The font works on device.** Garmin's resource compiler accepts the BMFont
  dialect `bake_font.py` emits, with the RGBA atlas, and the name renders in
  script on a real Epix Gen 2. `drawName` still falls back to
  `FONT_SYSTEM_SMALL` if the resource fails to load; leave that in.
- **Drawing the Square dial live tripped the watchdog**, twice. That is why it
  is baked — see *The Square dial's static layer is a baked PNG*. Do not put
  the live path back without a measurement.
- Full-screen buffered bitmap allocation has not failed, but has not been
  stress-tested either. If it ever does: buffer at half resolution and scale on
  blit.
- The Gauge dial's static layer is still ~700 primitive calls drawn in
  `onLayout`. It has not tripped the watchdog, being the one without the
  lattice, but it is the remaining candidate if one ever appears. The Square
  dial's old ~875-call figure now describes `DialSquare.mc`, which nothing
  calls.

## Build

Needs a developer key (once, ever):

```bash
openssl genrsa -out developer_key.pem 4096
openssl pkcs8 -topk8 -inform PEM -outform DER \
  -in developer_key.pem -out developer_key.der -nocrypt
```

Keys, `bin/`, `out/` and build outputs are gitignored.

```bash
monkeyc -f monkey.jungle -o bin/GaugeFace.prg -y developer_key.der -d epix2 -l 2
monkeyc -f monkey.jungle -o bin/GaugeFace.prg -y developer_key.der -d epix2 -r
connectiq                       # start the simulator, then:
monkeydo bin/GaugeFace.prg epix2
```

`monkey.jungle` is one line — the manifest, nothing else. Resources are found by
convention: `resources/` always, plus `resources-<deviceFamily>/` for the
product being built. Don't add paths for the `resources-round-*` directories.

Run the simulator's burn-in test (simulates 24 hours) before wearing it
overnight.

## Working notes for Claude

- **Compile after each change to the Monkey C** — `monkeyc … -d epix2 -l 2` takes
  four seconds and there is no reason to batch unverified edits. Build all four
  products before handing anything over; the per-family resources mean `epix2`
  passing does not prove `epix2pro42mm` does.
- When something looks wrong *visually*, render it in Python first and compare.
  That is still cheaper than a simulator cycle and isolates design from
  behaviour.
- **After changing `render_v3`'s static layer, run `bake_dial.py`.** The
  compiler cannot catch a stale dial PNG; the watch will simply show the old
  artwork. Same for `bake_emblem.py` and `bake_font.py`.
- Constants are duplicated between the Python and the Monkey C on purpose. After
  changing either, check them against each other; a mismatch shows up as a dial
  that looks right in Python and wrong on the watch. `SQ_EDGE` ↔
  `render_v3.EDGE` is the pair that breaks the live layer's alignment.
- The compiler now catches what the old cross-reference-by-script audit was for
  — `Rez.*` against the resource declarations, `@Strings.*` in `settings.xml`
  against `strings.xml`. It does **not** catch property names passed as strings
  to `Application.Properties.getValue`; check those against `properties.xml`
  by hand.
- **Check draw *order* against the Python, not just the constants.** The square's
  right arm crosses the date aperture, so the frame must be drawn after the
  emblem. `paintSquare` had them reversed from the first port onwards and no
  constant check would ever have noticed; only comparing the call order with
  `render_v3.draw_static` found it. For the Square dial that order now lives
  *only* in `render_v3.draw_static`.
- The design has been iterated on hard. If a change makes the dial simpler or
  flatter, that is probably a regression, not a cleanup.
