import Toybox.Graphics;
import Toybox.Lang;
import Toybox.Math;
import Toybox.WatchUi;

// The Square and Compasses dial, drawn after a reference watch: a rayed navy
// centre, a wide gold band carrying an engraved quilted lattice, XII and VI,
// fine gold line-work in the blue field, the applied emblem, and a day/date
// aperture at three. Fixed for as long as the settings are, so it is rendered
// once into a buffered bitmap and blitted each second.
//
// Geometry is in 416-dial units and goes through p(); that is what makes the
// other Epix sizes work. See CLAUDE.md.

// The band is a *blue* field carrying gold ornament, not a gold slab with dark
// engraving cut into it. Getting that backwards is also why widening the band
// once made the dial worse - it widened the wrong material.
const BLUE_R = 144;
const RING_IN = 146;
const RING_OUT = 196;

// The baked emblem asset, and where bake_emblem.py says it lands on a 416 dial.
const SQ_EMBLEM_X = 97;
const SQ_EMBLEM_Y = 99;

const NUM_R = 171;          // RING_IN + 25: numerals and darts share this

// Cost tunables. The band is the expensive part: LATTICE_A x LATTICE_R cells at
// two or three primitives each. Two rows across a 50-unit band keeps the cells
// the same shape they had at three rows across 66.
const RAYS = 80;
const BANDS = 3;
const LATTICE_A = 56;
const LATTICE_R = 2;

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
    // which is what reads as turning; the radial bands carry the falloff from
    // the centre, since a wedge can only hold one colour.
    function drawCentre(dc as Dc) as Void {
        var deep = [8, 22, 58];
        var lift = [46, 86, 148];
        var bands = [[0, 56, 1.00], [56, 104, 0.72], [104, BLUE_R, 0.44]];

        for (var i = 0; i < RAYS; i++) {
            var a0 = (i.toFloat() / RAYS) * 2 * Math.PI;
            var a1 = ((i + 1).toFloat() / RAYS) * 2 * Math.PI;
            var ray = (i % 2 == 0) ? 1.0 : 0.34;

            for (var b = 0; b < BANDS; b++) {
                var glow = bands[b][2];
                var t = 0.34 * ray * glow + 0.54 * glow + 0.12 * ray;
                dc.setColor(mix(deep, lift, t), Graphics.COLOR_TRANSPARENT);
                dc.fillPolygon([
                    polar(bands[b][0], a0), polar(bands[b][1], a0),
                    polar(bands[b][1], a1), polar(bands[b][0], a1)
                ]);
            }
        }
    }

    // The band's navy, a shade deeper than the centre. One colour per wedge is
    // all a fillPolygon can carry, so the radial falloff comes from splitting
    // the annulus into two sub-bands.
    private function ringBlue(r as Numeric, th as Float) as Number {
        var t = (1.0 + r * Math.cos(th) / RING_OUT) / 2.0;
        if (t < 0.0) { t = 0.0; }
        if (t > 1.0) { t = 1.0; }
        t = t * 0.7 + 0.15;
        var fall = 1.18 - r / RING_OUT.toFloat() * 0.5;
        if (fall < 0.5) { fall = 0.5; }
        if (fall > 1.0) { fall = 1.0; }
        return mix([8, 20, 50], [22, 48, 96], t * fall);
    }

    // Blue field, then a gold lozenge lattice over it with a small gold diamond
    // in every other eye. The empty cells matter: filling them all turns the
    // band back into a solid mat.
    function drawRing(dc as Dc) as Void {
        var N = 96;
        var rmid = (RING_IN + RING_OUT) / 2;
        var sub = [[RING_IN, rmid], [rmid, RING_OUT]];
        for (var b = 0; b < sub.size(); b++) {
            var q0 = sub[b][0];
            var q1 = sub[b][1];
            var qm = (q0 + q1) / 2;
            for (var i = 0; i < N; i++) {
                var a0 = (i.toFloat() / N) * 2 * Math.PI;
                var a1 = ((i + 1).toFloat() / N) * 2 * Math.PI;
                dc.setColor(ringBlue(qm, (a0 + a1) / 2.0), Graphics.COLOR_TRANSPARENT);
                dc.fillPolygon([
                    polar(q0, a0), polar(q1, a0), polar(q1, a1), polar(q0, a1)
                ]);
            }
        }

        var fieldIn = RING_IN + 9;
        var fieldOut = RING_OUT - 11;
        var step = (fieldOut - fieldIn).toFloat() / LATTICE_R;

        for (var row = 0; row < LATTICE_R; row++) {
            var r0 = fieldIn + row * step;
            var r1 = r0 + step;
            var rm = (r0 + r1) / 2.0;

            for (var k = 0; k < LATTICE_A; k++) {
                var a0 = (k.toFloat() / LATTICE_A) * 2 * Math.PI;
                var a1 = ((k + 1).toFloat() / LATTICE_A) * 2 * Math.PI;
                var am = (a0 + a1) / 2.0;

                // gold lozenge, then the blue field inset back inside it, which
                // leaves a one-pixel gold outline for two fills instead of four
                // lines
                dc.setColor(0xCEAA60, Graphics.COLOR_TRANSPARENT);
                dc.fillPolygon([
                    polar(rm, a0), polar(r1, am), polar(rm, a1), polar(r0, am)
                ]);

                var f = 0.86;
                dc.setColor(ringBlue(rm, am), Graphics.COLOR_TRANSPARENT);
                dc.fillPolygon([
                    polar(rm, am + (a0 - am) * f),
                    polar(rm + (r1 - rm) * f, am),
                    polar(rm, am + (a1 - am) * f),
                    polar(rm - (rm - r0) * f, am)
                ]);

                if ((k + row) % 2 == 0) {
                    var g = 0.26;
                    dc.setColor(0xF4E0A8, Graphics.COLOR_TRANSPARENT);
                    dc.fillPolygon([
                        polar(rm, am + (a0 - am) * g),
                        polar(rm + (r1 - rm) * g, am),
                        polar(rm, am + (a1 - am) * g),
                        polar(rm - (rm - r0) * g, am)
                    ]);
                }
            }
        }

        // fine gold teeth on the inner edge, bead on the outer
        dc.setColor(0xB49250, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(1);
        for (var k = 0; k < LATTICE_A * 2; k++) {
            var a = (k.toFloat() / (LATTICE_A * 2)) * 2 * Math.PI;
            var q = polar(RING_IN + 2.0, a);
            var r = polar(fieldIn - 1.0, a);
            dc.drawLine(q[0], q[1], r[0], r[1]);
        }

        dc.setColor(0xF4E0A8, Graphics.COLOR_TRANSPARENT);
        for (var k = 0; k < 112; k++) {
            var a = (k.toFloat() / 112) * 2 * Math.PI;
            var q = polar(RING_OUT - 5, a);
            dc.fillCircle(q[0], q[1], p(1.5) < 1 ? 1 : p(1.5));
        }

        dc.setColor(0xD6B264, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(2.4) < 1 ? 1 : p(2.4));
        dc.drawCircle(_cx, _cy, p(RING_IN));
        dc.setColor(0xDEBC72, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(3.0) < 1 ? 1 : p(3.0));
        dc.drawCircle(_cx, _cy, p(RING_OUT));
        dc.setColor(0x96783C, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(1.8) < 1 ? 1 : p(1.8));
        dc.drawCircle(_cx, _cy, p(BLUE_R));
    }

    // Numerals and darts sit on the band's blue, so they are gold with a dark
    // relief behind them. The engraved dark-on-gold treatment this dial used
    // when the band was a gold slab would simply vanish here.
    function drawMarkers(dc as Dc) as Void {
        for (var h = 0; h < 12; h++) {
            if (h == 0 || h == 6) { continue; }     // XII and VI sit there
            var a = (h.toFloat() / 12) * 2 * Math.PI;
            var p1 = polar(NUM_R - 9, a);
            var p2 = polar(NUM_R + 9, a);
            var dx = p2[0] - p1[0];
            var dy = p2[1] - p1[1];
            var l = Math.sqrt(dx * dx + dy * dy);
            if (l < 1.0) { l = 1.0; }
            var nx = (-dy / l * p(4.0)).toNumber();
            var ny = (dx / l * p(4.0)).toNumber();

            dc.setColor(0xF4E0A8, Graphics.COLOR_TRANSPARENT);
            dc.fillPolygon([
                [p1[0] + nx, p1[1] + ny], p2, [p1[0] - nx, p1[1] - ny]
            ]);
        }

        var labels = ["XII", "VI"];
        var at = [0.0, Math.PI];
        var lip = p(1.3);
        for (var i = 0; i < labels.size(); i++) {
            var q = polar(NUM_R, at[i]);
            dc.setColor(0x0A162E, Graphics.COLOR_TRANSPARENT);
            dc.drawText(q[0] + lip, q[1] + lip, Graphics.FONT_SYSTEM_SMALL,
                labels[i],
                Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
            dc.setColor(0xF6E4B0, Graphics.COLOR_TRANSPARENT);
            dc.drawText(q[0], q[1], Graphics.FONT_SYSTEM_SMALL, labels[i],
                Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
        }
    }

    // Fine gold line-work in the blue field between the limbs: a blazing star
    // upper-left, a small square upper-right, a point within a circle below the
    // G. Engraved lines, not applied metal.
    function drawSymbols(dc as Dc) as Void {
        dc.setColor(0xD8B46A, Graphics.COLOR_TRANSPARENT);
        dc.setPenWidth(p(1.1) < 1 ? 1 : p(1.1));

        var s = polar(96, -0.94);
        var rr = p(12);
        dc.drawCircle(s[0], s[1], rr);
        for (var i = 0; i < 8; i++) {
            var a = (i.toFloat() / 8) * 2 * Math.PI;
            dc.drawLine(
                s[0] + (Math.sin(a) * rr * 0.35).toNumber(),
                s[1] - (Math.cos(a) * rr * 0.35).toNumber(),
                s[0] + (Math.sin(a) * rr * 1.55).toNumber(),
                s[1] - (Math.cos(a) * rr * 1.55).toNumber());
        }
        dc.fillCircle(s[0], s[1], p(2.4) < 1 ? 1 : p(2.4));

        var q = polar(96, 0.94);
        var h = p(11);
        dc.drawRectangle(q[0] - h, q[1] - h, h * 2, h * 2);
        var h2 = (h * 0.55).toNumber();
        dc.drawRectangle(q[0] - h2, q[1] - h2, h2 * 2, h2 * 2);

        var c = polar(72, Math.PI);
        dc.drawCircle(c[0], c[1], p(9.5));
        dc.fillCircle(c[0], c[1], p(2.6) < 1 ? 1 : p(2.6));
    }

    // Frame only. The day and date themselves change, so they are drawn on the
    // live layer; see GaugeFaceView.liveSquare.
    function drawApertureFrame(dc as Dc) as Void {
        var x0 = _cx + p(70);
        var y0 = _cy - p(10);
        var w = p(40);
        var h = p(20);

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
