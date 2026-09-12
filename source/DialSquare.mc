import Toybox.Graphics;
import Toybox.Lang;
import Toybox.Math;
import Toybox.WatchUi;

// The Square and Compasses dial. Everything on this layer is fixed for as long
// as the settings are: the rayed
// blue centre, the guilloche gold chapter ring, the engraved numerals and
// darts, the applied emblem and the day/date aperture frame. It is rendered
// once into a buffered bitmap and blitted every second, which is what makes
// the detail affordable at 1Hz.
//
// Geometry is in 416-dial units and goes through p(); that is what makes the
// other Epix sizes work. See CLAUDE.md.

const BLUE_R = 148;         // inner blue dial
const RING_IN = 150;
const RING_OUT = 198;

// The baked emblem asset, and where bake_emblem.py says it lands on a 416 dial.
const SQ_EMBLEM_X = 98;
const SQ_EMBLEM_Y = 100;

// Tunables if the static layer is too slow to appear or the buffer won't fit.
// RAYS x BANDS fillPolygon calls dominate the cost; halving RAYS is the first
// thing to try.
const RAYS = 120;
const BANDS = 3;
const LATTICE = 90;

class SquareDial {

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

    // Fine radial engine-turning under the emblem. Alternate wedges are lit,
    // which is what reads as turning; the three radial bands carry the falloff
    // from the centre, since a wedge can only hold one colour.
    function drawCentre(dc as Dc) as Void {
        var deep = [8, 22, 58];
        var lift = [46, 86, 148];
        var bands = [[0, 58, 1.00], [58, 106, 0.72], [106, BLUE_R, 0.44]];

        for (var i = 0; i < RAYS; i++) {
            var a0 = (i.toFloat() / RAYS) * 2 * Math.PI;
            var a1 = ((i + 1).toFloat() / RAYS) * 2 * Math.PI;
            var ray = (i % 2 == 0) ? 1.0 : 0.34;

            for (var b = 0; b < BANDS; b++) {
                var r0 = bands[b][0];
                var r1 = bands[b][1];
                var glow = bands[b][2];
                var t = 0.34 * ray * glow + 0.54 * glow + 0.12 * ray;
                dc.setColor(mix(deep, lift, t), Graphics.COLOR_TRANSPARENT);
                dc.fillPolygon([
                    polar(r0, a0), polar(r1, a0), polar(r1, a1), polar(r0, a1)
                ]);
            }
        }
    }

    // The gold band: a top-lit annulus, an engine-turned lattice cut into it,
    // a dot in the eye of every other diamond, and beaded borders.
    function drawRing(dc as Dc) as Void {
        var dark = [150, 116, 52];
        var bright = [246, 226, 172];
        var N = 96;

        for (var i = 0; i < N; i++) {
            var a0 = (i.toFloat() / N) * 2 * Math.PI;
            var a1 = ((i + 1).toFloat() / N) * 2 * Math.PI;
            var th = (a0 + a1) / 2.0;
            // light sits at the top of the dial
            var t = 0.30 + 0.42 * ((1.0 - Math.cos(th)) / 2.0);
            dc.setColor(mix(dark, bright, t), Graphics.COLOR_TRANSPARENT);
            dc.fillPolygon([
                polar(RING_IN, a0), polar(RING_OUT, a0),
                polar(RING_OUT, a1), polar(RING_IN, a1)
            ]);
        }

        // two opposing families of chords make the diamonds
        dc.setColor(0x4A3616, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(0.8) < 1 ? 1 : p(0.8));
        for (var k = 0; k < LATTICE; k++) {
            var a = (k.toFloat() / LATTICE) * 2 * Math.PI;
            var b = ((k + 3.2) / LATTICE) * 2 * Math.PI;
            var q1 = polar(RING_IN + 5, a);
            var q2 = polar(RING_OUT - 6, b);
            dc.drawLine(q1[0], q1[1], q2[0], q2[1]);
            var q3 = polar(RING_IN + 5, b);
            var q4 = polar(RING_OUT - 6, a);
            dc.drawLine(q3[0], q3[1], q4[0], q4[1]);
        }

        dc.setColor(0xF6E2AC, Graphics.COLOR_TRANSPARENT);
        for (var k = 0; k < LATTICE; k += 2) {
            var a = ((k + 1.6) / LATTICE) * 2 * Math.PI;
            var q = polar((RING_IN + RING_OUT) / 2, a);
            dc.fillCircle(q[0], q[1], p(1.6) < 1 ? 1 : p(1.6));
        }

        dc.setColor(0xE8CE96, Graphics.COLOR_TRANSPARENT);
        var beads = [[RING_IN + 4, 60], [RING_OUT - 4, 72]];
        for (var i = 0; i < beads.size(); i++) {
            var rad = beads[i][0];
            var n = beads[i][1];
            for (var k = 0; k < n; k++) {
                var a = (k.toFloat() / n) * 2 * Math.PI;
                var q = polar(rad, a);
                dc.fillCircle(q[0], q[1], p(1.5) < 1 ? 1 : p(1.5));
            }
        }

        dc.setColor(0xD0AC60, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(2.2));
        dc.drawCircle(_cx, _cy, p(RING_IN));
        dc.setPenWidth(p(2.6));
        dc.drawCircle(_cx, _cy, p(RING_OUT));
        dc.setColor(0x96783C, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(1.6));
        dc.drawCircle(_cx, _cy, p(BLUE_R));
    }

    // Numerals and darts are cut *into* the gold: a light lower lip with the
    // dark shape over it. Gold laid on gold is illegible.
    function drawMarkers(dc as Dc) as Void {
        for (var h = 0; h < 12; h++) {
            if (h == 0) { continue; }               // XII sits there instead
            var a = (h.toFloat() / 12) * 2 * Math.PI;
            var p1 = polar(RING_IN + 12, a);
            var p2 = polar(RING_IN + 26, a);
            var dx = p2[0] - p1[0];
            var dy = p2[1] - p1[1];
            var l = Math.sqrt(dx * dx + dy * dy);
            if (l < 1.0) { l = 1.0; }
            var nx = (-dy / l * p(3.4)).toNumber();
            var ny = (dx / l * p(3.4)).toNumber();
            var lip = p(1.2);

            dc.setColor(0xEED69E, Graphics.COLOR_TRANSPARENT);
            dc.fillPolygon([
                [p1[0] + nx + lip, p1[1] + ny + lip],
                [p2[0] + lip, p2[1] + lip],
                [p1[0] - nx + lip, p1[1] - ny + lip]
            ]);
            dc.setColor(0x3A2A10, Graphics.COLOR_TRANSPARENT);
            dc.fillPolygon([
                [p1[0] + nx, p1[1] + ny], p2, [p1[0] - nx, p1[1] - ny]
            ]);
        }

        var q = polar(RING_IN + 24, 0.0);
        var lip2 = p(1.2);
        dc.setColor(0xF0DAA2, Graphics.COLOR_TRANSPARENT);
        dc.drawText(q[0] + lip2, q[1] + lip2, Graphics.FONT_SYSTEM_SMALL, "XII",
            Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
        dc.setColor(0x36260E, Graphics.COLOR_TRANSPARENT);
        dc.drawText(q[0], q[1], Graphics.FONT_SYSTEM_SMALL, "XII",
            Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
    }

    // Frame only. The day and date themselves change, so they are drawn on the
    // live layer; see GaugeFaceView.drawAperture.
    function drawApertureFrame(dc as Dc) as Void {
        var x0 = _cx + p(72);
        var y0 = _cy - p(11);
        var w = p(114 - 72);
        var h = p(22);

        dc.setColor(0x96783A, Graphics.COLOR_TRANSPARENT);
        dc.fillRectangle(x0 - p(2), y0 - p(2), w + p(4), h + p(4));
        dc.setColor(0xEEECE6, Graphics.COLOR_TRANSPARENT);
        dc.fillRectangle(x0, y0, w, h);
        dc.setColor(0xAAA8A2, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(1);
        dc.drawLine(x0 + p(23), y0, x0 + p(23), y0 + h);
    }

    function drawEmblem(dc as Dc) as Void {
        var bmp = WatchUi.loadResource(Rez.Drawables.EmblemSquare) as BitmapResource;
        // Baked against a 416 dial; bake_emblem.py prints and checks this.
        dc.drawBitmap(_cx + p(SQ_EMBLEM_X - 208), _cy + p(SQ_EMBLEM_Y - 208), bmp);
    }
}
