import Toybox.Graphics;
import Toybox.Lang;
import Toybox.Math;
import Toybox.WatchUi;

// The Twenty-Four Inch Gauge dial. Everything on this layer is fixed for the
// life of the app: the sunburst, the
// twenty-four hour ring, the subdial wells, the applied emblem and the two
// windows. It is rendered once into a buffered bitmap and blitted every second,
// which is what makes the detail affordable at 1Hz.

const DIAL_INNER = 172;     // inside the applied ring: the sunburst proper
const RING_OUTER = 204;

// The baked emblem asset, and where bake_emblem.py says it lands on a 416 dial.
// This one has no G: the Gauge dial draws its own, as text below centre.
const GA_EMBLEM_X = 103;
const GA_EMBLEM_Y = 103;
const SUB_OFFSET = 132;     // subdial centres, left and right of centre
const SUB_RADIUS = 34;

class GaugeDial {

    private var _s as Float;
    private var _cx as Number;
    private var _cy as Number;

    function initialize(width as Number) {
        _s = width / 416.0;
        _cx = width / 2;
        _cy = width / 2;
    }

    private function p(v as Numeric) as Number {
        return Math.round(v * _s).toNumber();
    }

    private function polar(r as Numeric, a as Float) as Array<Number> {
        return [_cx + p(r * Math.sin(a)), _cy - p(r * Math.cos(a))];
    }

    private function mix(a as Array<Number>, b as Array<Number>, t as Float) as Number {
        if (t < 0.0) { t = 0.0; }
        if (t > 1.0) { t = 1.0; }
        var r = (a[0] + (b[0] - a[0]) * t).toNumber();
        var g = (a[1] + (b[1] - a[1]) * t).toNumber();
        var bl = (a[2] + (b[2] - a[2]) * t).toNumber();
        return (r << 16) | (g << 8) | bl;
    }

    // Two opposing bright lobes plus fine angular streaking, the same formula
    // used to render the mock-up. Drawn as wedges in three radial bands so the
    // brightness also falls off toward the rim.
    function drawSunburst(dc as Dc) as Void {
        var base = [16, 38, 74];
        var hi = [58, 108, 176];
        var N = 180;
        var bands = [[0, 70, 1.00], [70, 140, 0.92], [140, DIAL_INNER, 0.80]];

        for (var i = 0; i < N; i++) {
            var a0 = (i.toFloat() / N) * 2 * Math.PI;
            var a1 = ((i + 1).toFloat() / N) * 2 * Math.PI;
            var th = (a0 + a1) / 2.0;

            var lobe = 0.5 + 0.5 * Math.cos(2 * (th - 0.6));
            var streak = 0.30 * Math.sin(th * 320.0 + 1.1)
                       + 0.20 * Math.sin(th * 137.0 + 3.7)
                       + 0.14 * Math.sin(th * 61.0 + 5.2);
            streak = (streak + 0.64) / 1.28;
            var t = 0.22 * lobe + 0.34 * streak * lobe + 0.10 * streak;

            for (var b = 0; b < bands.size(); b++) {
                var r0 = bands[b][0];
                var r1 = bands[b][1];
                var f = bands[b][2];
                dc.setColor(mix(base, hi, t * f), Graphics.COLOR_TRANSPARENT);
                dc.fillPolygon([
                    polar(r0, a0), polar(r1, a0), polar(r1, a1), polar(r0, a1)
                ] as Array);
            }
        }
    }

    // The outer ring carries the gauge. Night hours are darkened so the ring
    // shows the shape of the day, not just an abstract scale.
    function drawRing(dc as Dc, sunrise as Float, sunset as Float) as Void {
        var day = 0x162E54;         // [22, 46, 84]
        var night = 0x071022;       // [7, 16, 34]
        var N = 96;
        for (var i = 0; i < N; i++) {
            var a0 = (i.toFloat() / N) * 2 * Math.PI;
            var a1 = ((i + 1).toFloat() / N) * 2 * Math.PI;
            var hour = (i.toFloat() / N) * 24.0;
            var isDay = (hour >= sunrise) && (hour < sunset);
            dc.setColor(isDay ? day : night, Graphics.COLOR_TRANSPARENT);
            dc.fillPolygon([
                polar(DIAL_INNER, a0), polar(212, a0), polar(212, a1), polar(DIAL_INNER, a1)
            ] as Array);
        }

        // twenty-four inches, divided to eighths
        for (var i = 0; i < 192; i++) {
            var a = (i.toFloat() / 192) * 2 * Math.PI;
            var k = i % 8;
            var end; var col; var wid;
            if (k == 0)      { end = 178; col = 0xF8E2AA; wid = 3; }
            else if (k == 4) { end = 186; col = 0xC4A870; wid = 2; }
            else if (k == 2 || k == 6) { end = 190; col = 0x96825A; wid = 1; }
            else             { end = 194; col = 0x70644A; wid = 1; }
            dc.setColor(col, Graphics.COLOR_TRANSPARENT);
            dc.setPenWidth(p(wid));
            var q = polar(RING_OUTER, a);
            var r = polar(end, a);
            dc.drawLine(q[0], q[1], r[0], r[1]);
        }

        // hour numerals
        for (var h = 0; h < 24; h += 2) {
            var a = (h.toFloat() / 24) * 2 * Math.PI;
            var q = polar(168, a);
            dc.setColor(h % 6 == 0 ? 0xF8E2AA : 0xACBAD0, Graphics.COLOR_TRANSPARENT);
            dc.drawText(q[0], q[1], Graphics.FONT_SYSTEM_XTINY, h.format("%d"),
                Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
        }

        // the three divisions of the day
        var marks = [0, 8, 16];
        dc.setColor(0xE2C484, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(2.4));
        for (var i = 0; i < marks.size(); i++) {
            var a = (marks[i].toFloat() / 24) * 2 * Math.PI;
            var q = polar(200, a);
            var r = polar(178, a);
            dc.drawLine(q[0], q[1], r[0], r[1]);
        }

        var labels = ["refreshment", "labour", "service"];
        var at = [4.0, 12.0, 20.0];
        dc.setColor(0x96AAC6, Graphics.COLOR_TRANSPARENT);
        for (var i = 0; i < labels.size(); i++) {
            var a = (at[i] / 24) * 2 * Math.PI;
            var q = polar(150, a);
            dc.drawText(q[0], q[1], Graphics.FONT_SYSTEM_XTINY, labels[i],
                Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
        }

        // sunrise and sunset
        var sr = polar(186, (sunrise / 24.0) * 2 * Math.PI);
        var ss = polar(186, (sunset / 24.0) * 2 * Math.PI);
        dc.setColor(0xFAD678, Graphics.COLOR_TRANSPARENT);
        dc.fillCircle(sr[0], sr[1], p(4.5));
        dc.setColor(0x96B0DC, Graphics.COLOR_TRANSPARENT);
        dc.fillCircle(ss[0], ss[1], p(4.5));

        // applied ring between dial and gauge
        dc.setColor(0xC4A258, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(2.2));
        dc.drawCircle(_cx, _cy, p(DIAL_INNER));
    }

    // Recessed well with concentric turning marks, a shadow on the upper edge
    // and a catch-light on the lower.
    function drawSubdial(dc as Dc, ox as Number, label as String) as Void {
        var cx = _cx + p(ox);
        var cy = _cy;
        var rad = p(SUB_RADIUS);

        dc.setColor(0x141E34, Graphics.COLOR_TRANSPARENT);
        dc.fillCircle(cx, cy, rad);

        dc.setPenWidth(p(1.1));
        var steps = 14;
        for (var i = 0; i < steps; i++) {
            var rr = rad * (1.0 - i.toFloat() / steps);
            var f = 1.0 + 0.16 * Math.sin(i * 1.7);
            dc.setColor(mix([20, 30, 52], [30, 44, 74], f - 1.0), Graphics.COLOR_TRANSPARENT);
            dc.drawCircle(cx, cy, rr.toNumber());
        }

        dc.setPenWidth(p(2.6));
        dc.setColor(0x080E1A, Graphics.COLOR_TRANSPARENT);
        dc.drawArc(cx, cy, rad, Graphics.ARC_CLOCKWISE, 210, 30);
        dc.setPenWidth(p(1.6));
        dc.setColor(0x4A76B2, Graphics.COLOR_TRANSPARENT);
        dc.drawArc(cx, cy, rad, Graphics.ARC_CLOCKWISE, 30, 210);

        dc.setPenWidth(p(1.8));
        dc.setColor(0xB08E48, Graphics.COLOR_TRANSPARENT);
        dc.drawCircle(cx, cy, rad);

        // graduations across the needle's sweep
        for (var i = 0; i <= 10; i++) {
            var a = -2.2 + i * 0.44;
            var major = (i % 5 == 0);
            dc.setColor(major ? 0xCEB074 : 0x8092AC, Graphics.COLOR_TRANSPARENT);
            dc.setPenWidth(p(major ? 1.8 : 1.1));
            dc.drawLine(
                cx + p(30 * Math.sin(a)), cy - p(30 * Math.cos(a)),
                cx + p(25 * Math.sin(a)), cy - p(25 * Math.cos(a)));
        }

        dc.setColor(0xBAC8DC, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, cy + p(20), Graphics.FONT_SYSTEM_XTINY, label,
            Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
    }

    function drawWindow(dc as Dc, y0 as Number, y1 as Number, halfW as Number) as Void {
        dc.setColor(0x0A1426, Graphics.COLOR_TRANSPARENT);
        dc.fillRectangle(_cx - p(halfW), _cy + p(y0), p(halfW * 2), p(y1 - y0));
        dc.setColor(0xC4A258, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(1.6));
        dc.drawRectangle(_cx - p(halfW), _cy + p(y0), p(halfW * 2), p(y1 - y0));
    }

    function drawEmblem(dc as Dc) as Void {
        var bmp = WatchUi.loadResource(Rez.Drawables.EmblemGauge) as BitmapResource;
        // Baked against a 416 dial; bake_emblem.py prints and checks this.
        dc.drawBitmap(_cx + p(GA_EMBLEM_X - 208), _cy + p(GA_EMBLEM_Y - 208), bmp);
    }
}
