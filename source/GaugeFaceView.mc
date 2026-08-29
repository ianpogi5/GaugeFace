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

class GaugeFaceView extends WatchUi.WatchFace {

    private var _dial as BufferedBitmap?;
    private var _render as DialRenderer?;
    private var _w as Number = 416;
    private var _cx as Number = 208;
    private var _cy as Number = 208;
    private var _s as Float = 1.0;

    private var _lowPower as Boolean = false;
    private var _burnIn as Boolean = false;
    private var _antiAlias as Boolean = false;

    private var _showSeconds as Boolean = true;
    private var _left as Number = 0;
    private var _right as Number = 1;
    private var _top as Number = 0;

    private var _sunrise as Float = 5.75;
    private var _sunset as Float = 18.25;

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
        _antiAlias = (dc has :setAntiAlias);

        computeSun();
        buildDial();
    }

    function loadSettings() as Void {
        try {
            _showSeconds = Application.Properties.getValue("ShowSeconds") as Boolean;
            _left = Application.Properties.getValue("LeftDial") as Number;
            _right = Application.Properties.getValue("RightDial") as Number;
            _top = Application.Properties.getValue("TopWindow") as Number;
        } catch (e) {
            _showSeconds = true; _left = 0; _right = 1; _top = 0;
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

        _render = new DialRenderer(_w);
        paintStatic(bdc);
    }

    private function paintStatic(dc as Dc) as Void {
        dc.setColor(Graphics.COLOR_BLACK, Graphics.COLOR_BLACK);
        dc.clear();
        var r = _render;
        if (r == null) { r = new DialRenderer(_w); _render = r; }
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
            var stats = System.getSystemStats();
            if (stats has :charging) { }
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
        // back to a fixed pair until the watch has a fix.
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

        drawReadouts(dc);
        drawCursor(dc, clock);
        drawHands(dc, clock);
    }

    private function drawReadouts(dc as Dc) as Void {
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
    }

    private function drawNeedle(dc as Dc, ox as Number, frac as Float) as Void {
        var cx = _cx + p(ox);
        var a = -2.2 + frac * 4.4;
        dc.setColor(0xF4E8D2, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(2.2));
        dc.drawLine(cx, _cy, cx + p(27 * Math.sin(a)), _cy - p(27 * Math.cos(a)));
        dc.setColor(0xE2C484, Graphics.COLOR_TRANSPARENT);
        dc.fillCircle(cx, _cy, p(3));
    }

    private function drawCursor(dc as Dc, clock as System.ClockTime) as Void {
        var a = ((clock.hour + clock.min / 60.0) / 24.0) * 2 * Math.PI;
        var tip = polar(207, a);
        var base = polar(192, a);
        var dx = tip[0] - _cx;
        var dy = tip[1] - _cy;
        var l = Math.sqrt(dx * dx + dy * dy);
        var nx = (-dy / l * p(8)).toNumber();
        var ny = (dx / l * p(8)).toNumber();
        dc.setColor(0xFFF0C8, Graphics.COLOR_TRANSPARENT);
        dc.fillPolygon([[base[0] + nx, base[1] + ny], tip, [base[0] - nx, base[1] - ny]]);
    }

    // Hands are split down their length: a lit side and a shadowed side. That
    // split is what reads as polished metal rather than a painted shape.
    private function drawHands(dc as Dc, clock as System.ClockTime) as Void {
        var ha = ((clock.hour % 12) + clock.min / 60.0) / 12.0 * 2 * Math.PI;
        var ma = (clock.min + clock.sec / 60.0) / 60.0 * 2 * Math.PI;

        hand(dc, ha, 92, 9);
        hand(dc, ma, 148, 7);

        if (_showSeconds) {
            var sa = clock.sec / 60.0 * 2 * Math.PI;
            var t = rot(0, -160, sa);
            var b = rot(0, 36, sa);
            dc.setColor(0xF2CE8A, Graphics.COLOR_TRANSPARENT);
            dc.setPenWidth(p(2));
            dc.drawLine(b[0], b[1], t[0], t[1]);
        }

        dc.setColor(0xE2C484, Graphics.COLOR_TRANSPARENT);
        dc.fillCircle(_cx, _cy, p(8));
        dc.setColor(0x14223A, Graphics.COLOR_TRANSPARENT);
        dc.fillCircle(_cx, _cy, p(3.5));
    }

    private function hand(dc as Dc, a as Float, len as Number, wd as Number) as Void {
        dc.setColor(0xFAEED6, Graphics.COLOR_TRANSPARENT);
        dc.fillPolygon([
            rot(-wd, 20, a), rot(-wd * 0.45, -len, a), rot(0, -len, a), rot(0, 20, a)
        ]);
        dc.setColor(0xB09E80, Graphics.COLOR_TRANSPARENT);
        dc.fillPolygon([
            rot(0, 20, a), rot(0, -len, a), rot(wd * 0.45, -len, a), rot(wd, 20, a)
        ]);
    }

    // ---------------------------------------------------------------- always-on

    // A separate, much darker drawing. The lit dial cannot pass the always-on
    // luminance budget, so this is thin gold on black with a per-minute shift.
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

        // the twenty-four, reduced to its hours
        dc.setColor(0x5C4A22, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(2));
        for (var h = 0; h < 24; h++) {
            var a = (h.toFloat() / 24) * 2 * Math.PI;
            var inner = (h % 6 == 0) ? 184 : 191;
            dc.drawLine(
                cx + p(200 * Math.sin(a)), cy - p(200 * Math.cos(a)),
                cx + p(inner * Math.sin(a)), cy - p(inner * Math.cos(a)));
        }

        // emblem as an outline only
        dc.setColor(0x6B5628, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(1.8));
        outlineLimb(dc, cx, cy, 0, 96, -96, -2);
        outlineLimb(dc, cx, cy, 0, 96, 96, -2);
        outlineLimb(dc, cx, cy, 0, -88, -78, 58);
        outlineLimb(dc, cx, cy, 0, -88, 78, 58);
        dc.drawCircle(cx, cy - p(88), p(12));

        var ha = ((clock.hour % 12) + clock.min / 60.0) / 12.0 * 2 * Math.PI;
        var ma = (clock.min + clock.sec / 60.0) / 60.0 * 2 * Math.PI;
        dc.setColor(0x9A9384, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(5));
        dc.drawLine(cx, cy, cx + p(92 * Math.sin(ha)), cy - p(92 * Math.cos(ha)));
        dc.setPenWidth(p(3.5));
        dc.drawLine(cx, cy, cx + p(148 * Math.sin(ma)), cy - p(148 * Math.cos(ma)));

        var ca = ((clock.hour + clock.min / 60.0) / 24.0) * 2 * Math.PI;
        dc.setColor(0xC4A258, Graphics.COLOR_TRANSPARENT);
        dc.fillCircle(cx + p(198 * Math.sin(ca)), cy - p(198 * Math.cos(ca)), p(5));
    }

    private function outlineLimb(dc as Dc, cx as Number, cy as Number,
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
        buildDial();
    }
}
