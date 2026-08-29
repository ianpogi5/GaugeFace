# Twenty-Four Inch Gauge — Garmin watch face

Blue sunburst dial with an applied square and compasses, a 24-hour gauge ring
marked to eighths, sunrise and sunset markers, two subdials and two windows.
Built for the Epix Gen 2 (416 × 416 AMOLED) and the Epix Pro sizes.

## How it's put together

The dial is expensive to draw and never changes, so it's rendered once into a
`BufferedBitmap` from the graphics pool and blitted each second. Only the hands,
the gauge cursor, the subdial needles and the text are drawn per frame.

- `DialRenderer.mc` — the static layer: sunburst wedges, gauge ring, night
  shading, subdial wells, windows, emblem.
- `GaugeFaceView.mc` — the live layer, plus a separate always-on drawing.
- `resources/drawables/emblem.png` — the applied emblem, baked with real
  gradients because Monkey C primitives can't produce them. 214 × 214, 26 KB.
- `render_v2.py` / `bake_emblem.py` — the Python renderers used to design the
  dial and produce the emblem asset. Re-run `bake_emblem.py` to regenerate it.

Always-on is a separate, much darker drawing — thin gold on black, no sunburst,
no second hand, shifted a few pixels each minute. A lit blue dial can't pass the
always-on budget, so the two states deliberately look different.

## Installing on your Epix Gen 2

**1. Install the tools.** Download the Connect IQ SDK Manager from
developer.garmin.com, install a current SDK, and in the Devices tab install the
`epix2` device definition. Then add the Monkey C extension to VS Code.

**2. Make a developer key** (once, ever):

```bash
openssl genrsa -out developer_key.pem 4096
openssl pkcs8 -topk8 -inform PEM -outform DER \
  -in developer_key.pem -out developer_key.der -nocrypt
```

Point VS Code at the `.der` file when it asks, or pass it with `-y`.

**3. Build.** In VS Code: Ctrl+Shift+P → *Monkey C: Build for Device* → pick
epix2. Or from a terminal:

```bash
monkeyc -f monkey.jungle -o GaugeFace.prg -y developer_key.der -d epix2 -r
```

Try it first in the simulator with *Monkey C: Run App* — and while it's running,
use the simulator's burn-in test, which simulates 24 hours and reports whether
the always-on state would cause burn-in.

**4. Copy it to the watch.**

- Plug the Epix into your computer with the charging cable. It mounts as a USB
  drive (on macOS you may need Android File Transfer or Garmin Express).
- Copy `GaugeFace.prg` into the `GARMIN/APPS/` folder on the watch.
- Eject the drive properly and unplug.

**5. Select it.** On the watch, hold MENU from any watch face → Watch Face →
scroll to it → Apply. If it doesn't appear, restart the watch (hold LIGHT →
Power Off, then back on).

**6. Settings.** Second hand, both subdials and the top window are configurable.
Sideloaded apps don't show settings in the Garmin Connect phone app — use the
Connect IQ desktop simulator, or upload the app to the Connect IQ store as a
private app if you want phone-side settings.

## Things to expect on first build

I couldn't compile this — no Garmin SDK in the environment it was written in.
Budget an hour for the usual friction:

- **Device IDs.** Check the folder names under `~/.Garmin/ConnectIQ/Devices/`
  and reconcile `manifest.xml` against them.
- **Memory.** The buffered bitmap comes from the graphics pool rather than app
  memory, but a full-screen buffer is still large. If it fails to allocate,
  drop `drawSunburst` from 180 wedges to 120, or render the buffer at half
  resolution and scale on blit.
- **Startup cost.** The static layer is ~700 `fillPolygon` calls. That happens
  once in `onLayout`, but if the face is slow to appear, reduce the wedge count.
- **Sunrise and sunset.** `computeSun()` uses `Toybox.Weather` and needs a
  position fix; until the watch has one it falls back to 05:45 and 18:15. Adjust
  the defaults for Manila if you want them right out of the box.
- **Body battery.** Guarded with a `has` check — it will read zero on devices
  or firmware that don't expose it through ActivityMonitor.

## On the artwork

The emblem is a generic square and compasses built from scratch. Grand Lodge
seals and lodge crests are protected marks — if you want one, supply the asset
and add it as another bitmap drawable.
