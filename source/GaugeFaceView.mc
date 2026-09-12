import Toybox.Activity;
import Toybox.ActivityMonitor;
import Toybox.Application;
import Toybox.Graphics;
import Toybox.Lang;
import Toybox.Math;
import Toybox.Position;
import Toybox.System;
import Toybox.Time;
import Toybox.Time.Gregorian;
import Toybox.WatchUi;
import Toybox.Weather;

// Two dials share this view. Which one is drawn comes from the DialStyle
// setting; everything style-specific is dispatched from paintStatic, onUpdate
// and drawAlwaysOn. The two are separate designs, not variations: different
// static layers, different hand shapes, different complications.
const STYLE_SQUARE = 0;
const STYLE_GAUGE = 1;

class GaugeFaceView extends WatchUi.WatchFace {

    private var _dial as BufferedBitmap?;
    private var _square as SquareDial?;
    private var _gauge as GaugeDial?;
    private var _script as FontResource?;
    private var _w as Number = 416;
    private var _cx as Number = 208;
    private var _cy as Number = 208;
    private var _s as Float = 1.0;

    private var _lowPower as Boolean = false;
    private var _burnIn as Boolean = false;

    private var _style as Number = STYLE_SQUARE;
    private var _showSeconds as Boolean = true;
    private var _name as String = "Singko";
    private var _left as Number = 0;
    private var _right as Number = 1;
    private var _top as Number = 0;

    private var _sunrise as Float = 5.75;
    private var _sunset as Float = 18.25;

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

        computeSun();
        buildDial();
    }

    function loadSettings() as Void {
        try {
            _style = Application.Properties.getValue("DialStyle") as Number;
            _showSeconds = Application.Properties.getValue("ShowSeconds") as Boolean;
            _left = Application.Properties.getValue("LeftDial") as Number;
            _right = Application.Properties.getValue("RightDial") as Number;
            _top = Application.Properties.getValue("TopWindow") as Number;
            var n = Application.Properties.getValue("OwnerName") as String?;
            _name = (n != null && n.length() > 0) ? n : "Singko";
        } catch (e) {
            _style = STYLE_SQUARE;
            _showSeconds = true;
            _name = "Singko";
            _left = 0; _right = 1; _top = 0;
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

    private function polar(r as Numeric, a as Float) as Array<Number> {
        return [_cx + p(r * Math.sin(a)), _cy - p(r * Math.cos(a))];
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
        paintStatic(bdc);
    }

    private function paintStatic(dc as Dc) as Void {
        dc.setColor(Graphics.COLOR_BLACK, Graphics.COLOR_BLACK);
        dc.clear();
        // drop the renderer for the style we are not drawing; only one dial
        // is ever live, and this app is tight on memory
        if (_style == STYLE_GAUGE) {
            _square = null;
            paintGauge(dc);
        } else {
            _gauge = null;
            paintSquare(dc);
        }
    }

    private function paintSquare(dc as Dc) as Void {
        var r = _square;
        if (r == null) { r = new SquareDial(_w); _square = r; }
        r.drawCentre(dc);
        r.drawRing(dc);
        r.drawMarkers(dc);
        r.drawSymbols(dc);
        r.drawApertureFrame(dc);
        r.drawEmblem(dc);
        drawName(dc);
    }

    private function paintGauge(dc as Dc) as Void {
        var r = _gauge;
        if (r == null) { r = new GaugeDial(_w); _gauge = r; }
        r.drawSunburst(dc);
        r.drawRing(dc, _sunrise, _sunset);
        r.drawSubdial(dc, -SUB_OFFSET, dialLabel(_left));
        r.drawSubdial(dc, SUB_OFFSET, dialLabel(_right));
        r.drawEmblem(dc);
        r.drawWindow(dc, 108, 132, 34);              // date
        if (_top != 2) { r.drawWindow(dc, -132, -110, 32); }
        dc.setColor(0xE2C484, Graphics.COLOR_TRANSPARENT);
        dc.drawText(_cx, _cy + p(54), Graphics.FONT_SYSTEM_MEDIUM, "G",
            Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
    }

    // The owner's name, engraved in script below the emblem. It is a setting,
    // so it cannot live in the baked emblem PNG the way the G does; it is drawn
    // here from the custom bitmap font, into the static layer.
    //
    // Square dial only - the Gauge dial's field is already full.
    private function drawName(dc as Dc) as Void {
        if (_name.length() == 0) { return; }
        var y = _cy + p(110);
        var f = (_script != null) ? _script : Graphics.FONT_SYSTEM_SMALL;

        dc.setColor(0x6A5426, Graphics.COLOR_TRANSPARENT);
        dc.drawText(_cx + p(1.8), y + p(1.8), f, _name,
            Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
        dc.setColor(0xF2DCA8, Graphics.COLOR_TRANSPARENT);
        dc.drawText(_cx, y, f, _name,
            Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
    }

    private function dialLabel(which as Number) as String {
        if (which == 1) { return "STEPS"; }
        if (which == 2) { return "BODY"; }
        return "BATTERY";
    }

    private function dialFraction(which as Number) as Float {
        if (which == 1) {
            var info = ActivityMonitor.getInfo();
            var goal = info.stepGoal;
            if (goal == null || goal <= 0) { goal = 10000; }
            var steps = info.steps;
            if (steps == null) { steps = 0; }
            var f = steps.toFloat() / goal.toFloat();
            return f > 1.0 ? 1.0 : f;
        }
        if (which == 2) {
            var mon = ActivityMonitor.getInfo();
            if (mon has :bodyBattery && mon.bodyBattery != null) {
                return (mon.bodyBattery as Number) / 100.0;
            }
            return 0.0;
        }
        return System.getSystemStats().battery / 100.0;
    }

    // --------------------------------------------------------------- sun times

    private function computeSun() as Void {
        // Sunrise and sunset for the day, from the last known position. Falls
        // back to a fixed pair until the watch has a fix. Gauge dial only, and
        // baked into its static layer.
        try {
            var loc = Position.getInfo().position;
            if (loc != null) {
                var now = Time.now();
                var rise = Time.Gregorian.info(
                    Weather.getSunrise(loc, now), Time.FORMAT_SHORT);
                var set = Time.Gregorian.info(
                    Weather.getSunset(loc, now), Time.FORMAT_SHORT);
                _sunrise = rise.hour + rise.min / 60.0;
                _sunset = set.hour + set.min / 60.0;
            }
        } catch (e) {
            // leave the defaults in place
        }
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

        if (_style == STYLE_GAUGE) {
            liveGauge(dc, clock);
        } else {
            liveSquare(dc, clock);
        }
    }

    private function liveSquare(dc as Dc, clock as System.ClockTime) as Void {
        var now = Gregorian.info(Time.now(), Time.FORMAT_MEDIUM);
        dc.setColor(0x18181C, Graphics.COLOR_TRANSPARENT);
        dc.drawText(_cx + p(75.5), _cy, Graphics.FONT_SYSTEM_XTINY,
            now.day_of_week.toUpper(),
            Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
        dc.setColor(0xBE2022, Graphics.COLOR_TRANSPARENT);
        dc.drawText(_cx + p(95.5), _cy, Graphics.FONT_SYSTEM_XTINY,
            now.day.format("%d"),
            Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);

        handDauphine(dc, hourAngle(clock), 80, 9);
        handDauphine(dc, minuteAngle(clock), 124, 7);
        secondHand(dc, clock, 138, 28, 1.6);
        cap(dc, 6, 2.2);
    }

    private function liveGauge(dc as Dc, clock as System.ClockTime) as Void {
        var now = Gregorian.info(Time.now(), Time.FORMAT_MEDIUM);
        dc.setColor(0xECE4D2, Graphics.COLOR_TRANSPARENT);
        dc.drawText(_cx, _cy + p(120), Graphics.FONT_SYSTEM_XTINY,
            (now.day_of_week + " " + now.day.format("%d")).toUpper(),
            Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);

        if (_top == 0) {
            var hr = "--";
            var info = Activity.getActivityInfo();
            if (info != null && info.currentHeartRate != null) {
                hr = (info.currentHeartRate as Number).format("%d");
            }
            dc.drawText(_cx, _cy - p(121), Graphics.FONT_SYSTEM_XTINY, hr + " bpm",
                Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
        } else if (_top == 1) {
            var alt = "--";
            var info = Activity.getActivityInfo();
            if (info != null && info.altitude != null) {
                alt = (info.altitude as Float).format("%.0f") + " m";
            }
            dc.drawText(_cx, _cy - p(121), Graphics.FONT_SYSTEM_XTINY, alt,
                Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
        }

        drawNeedle(dc, -SUB_OFFSET, dialFraction(_left));
        drawNeedle(dc, SUB_OFFSET, dialFraction(_right));
        drawCursor(dc, clock);

        handTaper(dc, hourAngle(clock), 92, 9);
        handTaper(dc, minuteAngle(clock), 148, 7);
        secondHand(dc, clock, 160, 36, 2.0);
        cap(dc, 8, 3.5);
    }

    private function hourAngle(clock as System.ClockTime) as Float {
        return ((clock.hour % 12) + clock.min / 60.0) / 12.0 * 2 * Math.PI;
    }

    private function minuteAngle(clock as System.ClockTime) as Float {
        return (clock.min + clock.sec / 60.0) / 60.0 * 2 * Math.PI;
    }

    private function drawNeedle(dc as Dc, ox as Number, frac as Float) as Void {
        var cx = _cx + p(ox);
        var a = -2.2 + frac * 4.4;
        dc.setColor(0xF4E8D2, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(2.2) < 1 ? 1 : p(2.2));
        dc.drawLine(cx, _cy, cx + p(27 * Math.sin(a)), _cy - p(27 * Math.cos(a)));
        dc.setColor(0xE2C484, Graphics.COLOR_TRANSPARENT);
        dc.fillCircle(cx, _cy, p(3));
    }

    // The brass cursor on the rim: position in the twenty-four hour day.
    private function drawCursor(dc as Dc, clock as System.ClockTime) as Void {
        var a = ((clock.hour + clock.min / 60.0) / 24.0) * 2 * Math.PI;
        var tip = polar(207, a);
        var base = polar(192, a);
        var dx = tip[0] - _cx;
        var dy = tip[1] - _cy;
        var l = Math.sqrt(dx * dx + dy * dy);
        if (l < 1.0) { l = 1.0; }
        var nx = (-dy / l * p(8)).toNumber();
        var ny = (dx / l * p(8)).toNumber();
        dc.setColor(0xFFF0C8, Graphics.COLOR_TRANSPARENT);
        dc.fillPolygon([[base[0] + nx, base[1] + ny], tip, [base[0] - nx, base[1] - ny]]);
    }

    // Both hand shapes are split down their length, lit on one side and
    // shadowed on the other. That split is what reads as polished metal.
    // The dials use different outlines: a taper on the Gauge, a dauphine kite
    // on the Square.
    private function handTaper(dc as Dc, a as Float, len as Number, wd as Number) as Void {
        dc.setColor(0xFAEED6, Graphics.COLOR_TRANSPARENT);
        dc.fillPolygon([
            rot(-wd, 20, a), rot(-wd * 0.45, -len, a), rot(0, -len, a), rot(0, 20, a)
        ]);
        dc.setColor(0xB09E80, Graphics.COLOR_TRANSPARENT);
        dc.fillPolygon([
            rot(0, 20, a), rot(0, -len, a), rot(wd * 0.45, -len, a), rot(wd, 20, a)
        ]);
    }

    private function handDauphine(dc as Dc, a as Float, len as Number, wd as Number) as Void {
        var tip = rot(0, -len, a);
        var tail = rot(0, 26, a);
        dc.setColor(0xFAE8B6, Graphics.COLOR_TRANSPARENT);
        dc.fillPolygon([rot(-wd, 16, a), tip, tail]);
        dc.setColor(0xB08A3E, Graphics.COLOR_TRANSPARENT);
        dc.fillPolygon([tip, rot(wd, 16, a), tail]);
    }

    private function secondHand(dc as Dc, clock as System.ClockTime,
                                len as Number, tail as Number,
                                pen as Float) as Void {
        if (!_showSeconds) { return; }
        var sa = clock.sec / 60.0 * 2 * Math.PI;
        var t = rot(0, -len, sa);
        var b = rot(0, tail, sa);
        dc.setColor(0xEEC678, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(pen) < 1 ? 1 : p(pen));
        dc.drawLine(b[0], b[1], t[0], t[1]);
    }

    private function cap(dc as Dc, outer as Numeric, inner as Numeric) as Void {
        dc.setColor(0xE2C484, Graphics.COLOR_TRANSPARENT);
        dc.fillCircle(_cx, _cy, p(outer));
        dc.setColor(0x101E38, Graphics.COLOR_TRANSPARENT);
        dc.fillCircle(_cx, _cy, p(inner));
    }

    // ---------------------------------------------------------------- always-on

    // A separate, much darker drawing. Neither lit dial can pass the always-on
    // luminance budget, so this is thin gold on black with a per-minute shift;
    // over 25 minutes it walks a 5 x 5 grid. The Gauge dial reduces to its
    // twenty-four hours, the Square dial to twelve.
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

        var gauge = (_style == STYLE_GAUGE);
        var ticks = gauge ? 24 : 12;
        var major = gauge ? 6 : 3;

        dc.setColor(0x5C4A22, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(2) < 1 ? 1 : p(2));
        for (var h = 0; h < ticks; h++) {
            var a = (h.toFloat() / ticks) * 2 * Math.PI;
            var inner = (h % major == 0) ? (gauge ? 184 : 176) : (gauge ? 191 : 186);
            var outer = gauge ? 200 : 196;
            dc.drawLine(
                cx + p(outer * Math.sin(a)), cy - p(outer * Math.cos(a)),
                cx + p(inner * Math.sin(a)), cy - p(inner * Math.cos(a)));
        }

        // emblem reduced to an outline, at whichever geometry this dial uses
        var sc = gauge ? 1.0 : 0.96;
        dc.setColor(0x6B5628, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(1.8) < 1 ? 1 : p(1.8));
        limb(dc, cx, cy, 0, -88 * sc, -78 * sc, 58 * sc);
        limb(dc, cx, cy, 0, -88 * sc, 78 * sc, 58 * sc);
        limb(dc, cx, cy, 0, 96 * sc, -96 * sc, -2 * sc);
        limb(dc, cx, cy, 0, 96 * sc, 96 * sc, -2 * sc);
        dc.drawCircle(cx, cy - p(88 * sc), p(12));

        var ha = hourAngle(clock);
        var ma = minuteAngle(clock);
        dc.setColor(0x9A9384, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(5) < 1 ? 1 : p(5));
        var hl = gauge ? 92 : 80;
        var ml = gauge ? 148 : 124;
        dc.drawLine(cx, cy, cx + p(hl * Math.sin(ha)), cy - p(hl * Math.cos(ha)));
        dc.setPenWidth(p(3.5) < 1 ? 1 : p(3.5));
        dc.drawLine(cx, cy, cx + p(ml * Math.sin(ma)), cy - p(ml * Math.cos(ma)));

        if (gauge) {
            var ca = ((clock.hour + clock.min / 60.0) / 24.0) * 2 * Math.PI;
            dc.setColor(0xC4A258, Graphics.COLOR_TRANSPARENT);
            dc.fillCircle(cx + p(198 * Math.sin(ca)), cy - p(198 * Math.cos(ca)), p(5));
        }
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
        buildDial();     // style, name and subdial labels are all baked in
    }
}
