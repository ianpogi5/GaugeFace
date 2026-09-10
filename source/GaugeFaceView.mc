import Toybox.Application;
import Toybox.Graphics;
import Toybox.Lang;
import Toybox.Math;
import Toybox.System;
import Toybox.Time;
import Toybox.Time.Gregorian;
import Toybox.WatchUi;

class GaugeFaceView extends WatchUi.WatchFace {

    private var _dial as BufferedBitmap?;
    private var _render as DialRenderer?;
    private var _script as FontResource?;
    private var _w as Number = 416;
    private var _cx as Number = 208;
    private var _cy as Number = 208;
    private var _s as Float = 1.0;

    private var _lowPower as Boolean = false;
    private var _burnIn as Boolean = false;

    private var _showSeconds as Boolean = true;
    private var _name as String = "Singko";

    // Nothing on the static layer changes with the clock, so the buffer is
    // only rebuilt when the settings change - see onSettingsChanged.
    function initialize() {
        WatchFace.initialize();
        loadSettings();
    }

    function onLayout(dc as Dc) as Void {
        _w = dc.getWidth();
        _cx = _w / 2;
        _cy = dc.getHeight() / 2;
        _s = _w / 416.0;

        var settings = System.getDeviceSettings();
        if (settings has :requiresBurnInProtection) {
            _burnIn = settings.requiresBurnInProtection;
        }

        try {
            _script = WatchUi.loadResource(Rez.Fonts.ScriptName) as FontResource;
        } catch (e) {
            _script = null;     // fall back to a system font for the name
        }

        buildDial();
    }

    function loadSettings() as Void {
        try {
            _showSeconds = Application.Properties.getValue("ShowSeconds") as Boolean;
            var n = Application.Properties.getValue("OwnerName") as String?;
            if (n != null && n.length() > 0) {
                _name = n;
            } else {
                _name = "Singko";
            }
        } catch (e) {
            _showSeconds = true;
            _name = "Singko";
        }
    }

    private function p(v as Numeric) as Number {
        return Math.round(v * _s).toNumber();
    }

    private function rot(x as Numeric, y as Numeric, a as Float) as Array<Number> {
        var c = Math.cos(a);
        var s = Math.sin(a);
        return [_cx + p(x * c - y * s), _cy + p(x * s + y * c)];
    }

    // ------------------------------------------------------------ static layer

    private function buildDial() as Void {
        if (!(Graphics has :createBufferedBitmap)) {
            _dial = null;   // fall back to drawing live in onUpdate
            return;
        }
        var ref = Graphics.createBufferedBitmap({:width => _w, :height => _w});
        _dial = ref.get() as BufferedBitmap;
        var bdc = _dial.getDc();
        if (bdc has :setAntiAlias) { bdc.setAntiAlias(true); }

        _render = new DialRenderer(_w);
        paintStatic(bdc);
    }

    private function paintStatic(dc as Dc) as Void {
        dc.setColor(Graphics.COLOR_BLACK, Graphics.COLOR_BLACK);
        dc.clear();
        var r = _render;
        if (r == null) { r = new DialRenderer(_w); _render = r; }
        r.drawCentre(dc);
        r.drawRing(dc);
        r.drawMarkers(dc);
        r.drawApertureFrame(dc);
        r.drawEmblem(dc);
        drawName(dc);
    }

    // The owner's name, engraved in script below the emblem. It is a setting,
    // so it cannot live in the baked emblem PNG the way the G does; it is drawn
    // here from the custom bitmap font, into the static layer.
    private function drawName(dc as Dc) as Void {
        if (_name.length() == 0) { return; }
        var y = _cy + p(104);
        var f = (_script != null) ? _script : Graphics.FONT_SYSTEM_SMALL;

        dc.setColor(0x6A5426, Graphics.COLOR_TRANSPARENT);
        dc.drawText(_cx + p(1.8), y + p(1.8), f, _name,
            Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
        dc.setColor(0xF2DCA8, Graphics.COLOR_TRANSPARENT);
        dc.drawText(_cx, y, f, _name,
            Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
    }

    // ------------------------------------------------------------------ update

    function onUpdate(dc as Dc) as Void {
        var clock = System.getClockTime();

        if (_lowPower) {
            drawAlwaysOn(dc, clock);
            return;
        }

        if (dc has :setAntiAlias) { dc.setAntiAlias(true); }

        if (_dial != null) {
            dc.drawBitmap(0, 0, _dial);
        } else {
            paintStatic(dc);
        }

        drawAperture(dc);
        drawHands(dc, clock);
    }

    private function drawAperture(dc as Dc) as Void {
        var now = Gregorian.info(Time.now(), Time.FORMAT_MEDIUM);
        dc.setColor(0x18181C, Graphics.COLOR_TRANSPARENT);
        dc.drawText(_cx + p(83.5), _cy, Graphics.FONT_SYSTEM_XTINY,
            now.day_of_week.toUpper(),
            Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
        dc.setColor(0xBE2022, Graphics.COLOR_TRANSPARENT);
        dc.drawText(_cx + p(104.5), _cy, Graphics.FONT_SYSTEM_XTINY,
            now.day.format("%d"),
            Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
    }

    // Dauphine hands, split down their length: a lit side and a shadowed side.
    // That split is what reads as polished metal rather than a painted shape.
    private function drawHands(dc as Dc, clock as System.ClockTime) as Void {
        var ha = ((clock.hour % 12) + clock.min / 60.0) / 12.0 * 2 * Math.PI;
        var ma = (clock.min + clock.sec / 60.0) / 60.0 * 2 * Math.PI;

        hand(dc, ha, 88, 10);
        hand(dc, ma, 132, 8);

        if (_showSeconds) {
            var sa = clock.sec / 60.0 * 2 * Math.PI;
            var t = rot(0, -140, sa);
            var b = rot(0, 30, sa);
            dc.setColor(0xEEC678, Graphics.COLOR_TRANSPARENT);
            dc.setPenWidth(p(1.6) < 1 ? 1 : p(1.6));
            dc.drawLine(b[0], b[1], t[0], t[1]);
        }

        dc.setColor(0xE2C484, Graphics.COLOR_TRANSPARENT);
        dc.fillCircle(_cx, _cy, p(7));
        dc.setColor(0x101E38, Graphics.COLOR_TRANSPARENT);
        dc.fillCircle(_cx, _cy, p(2.5));
    }

    private function hand(dc as Dc, a as Float, len as Number, wd as Number) as Void {
        var tip = rot(0, -len, a);
        var tail = rot(0, 26, a);
        var left = rot(-wd, 16, a);
        var right = rot(wd, 16, a);

        dc.setColor(0xFAE8B6, Graphics.COLOR_TRANSPARENT);
        dc.fillPolygon([left, tip, tail]);
        dc.setColor(0xB08A3E, Graphics.COLOR_TRANSPARENT);
        dc.fillPolygon([tip, right, tail]);
    }

    // ---------------------------------------------------------------- always-on

    // A separate, much darker drawing. The lit blue dial cannot pass the
    // always-on luminance budget, so this is thin gold on black with a
    // per-minute shift; over 25 minutes it walks a 5 x 5 grid.
    private function drawAlwaysOn(dc as Dc, clock as System.ClockTime) as Void {
        var ox = 0;
        var oy = 0;
        if (_burnIn) {
            ox = p(((clock.min % 5) - 2) * 3);
            oy = p((((clock.min / 5) % 5) - 2) * 3);
        }
        var cx = _cx + ox;
        var cy = _cy + oy;

        dc.setColor(Graphics.COLOR_BLACK, Graphics.COLOR_BLACK);
        dc.clear();

        dc.setColor(0x5C4A22, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(2) < 1 ? 1 : p(2));
        for (var h = 0; h < 12; h++) {
            var a = (h.toFloat() / 12) * 2 * Math.PI;
            var inner = (h % 3 == 0) ? 176 : 186;
            dc.drawLine(
                cx + p(196 * Math.sin(a)), cy - p(196 * Math.cos(a)),
                cx + p(inner * Math.sin(a)), cy - p(inner * Math.cos(a)));
        }

        // emblem reduced to an outline
        dc.setColor(0x6B5628, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(1.8) < 1 ? 1 : p(1.8));
        limb(dc, cx, cy, 0, -93, -83, 61);
        limb(dc, cx, cy, 0, -93, 83, 61);
        limb(dc, cx, cy, 0, 102, -102, -2);
        limb(dc, cx, cy, 0, 102, 102, -2);
        dc.drawCircle(cx, cy - p(93), p(12));

        var ha = ((clock.hour % 12) + clock.min / 60.0) / 12.0 * 2 * Math.PI;
        var ma = (clock.min + clock.sec / 60.0) / 60.0 * 2 * Math.PI;
        dc.setColor(0x9A9384, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(5) < 1 ? 1 : p(5));
        dc.drawLine(cx, cy, cx + p(88 * Math.sin(ha)), cy - p(88 * Math.cos(ha)));
        dc.setPenWidth(p(3.5) < 1 ? 1 : p(3.5));
        dc.drawLine(cx, cy, cx + p(132 * Math.sin(ma)), cy - p(132 * Math.cos(ma)));
    }

    private function limb(dc as Dc, cx as Number, cy as Number,
                          x1 as Numeric, y1 as Numeric,
                          x2 as Numeric, y2 as Numeric) as Void {
        dc.drawLine(cx + p(x1), cy + p(y1), cx + p(x2), cy + p(y2));
    }

    function onEnterSleep() as Void {
        _lowPower = true;
        WatchUi.requestUpdate();
    }

    function onExitSleep() as Void {
        _lowPower = false;
        WatchUi.requestUpdate();
    }

    function onSettingsChanged() as Void {
        loadSettings();
        buildDial();     // the name is baked into the static layer
    }
}
