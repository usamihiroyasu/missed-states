#!/usr/bin/env python3
"""Draw the current-observation reset construction."""
from pathlib import Path
from fractions import Fraction as F, Fraction as Q
import argparse
import json
import math
import sys
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.colors import HexColor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from figures.fonts import add_font_arguments, register_fonts

def render(output_dir, font_dir=None):
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    register_fonts(font_dir, regular_name='PSans', bold_name='PSansBold')

    INK = HexColor('#18212b')
    GRAY = HexColor('#68727c')
    TEAL = HexColor('#126f8e')
    LIGHT = HexColor('#eaf3f6')
    GRID = HexColor('#dce3e8')
    WHITE = HexColor('#ffffff')

    class Figure:

        def __init__(self, name, height, title):
            self.name = name
            self.height = height
            self.boxes = []
            self.path = output_dir / (name + '.pdf')
            self.c = canvas.Canvas(str(self.path), pagesize=(740, height), pageCompression=1, initialFontName='PSans', initialFontSize=12)
            self.c.setTitle(title)
            self.c.setAuthor('Hiroyasu Usami')

        def text(self, x, y, s, size=12, bold=False, color=INK, align='left'):
            c = self.c
            font = 'PSansBold' if bold else 'PSans'
            c.setFont(font, size)
            c.setFillColor(color)
            w = pdfmetrics.stringWidth(s, font, size)
            x0 = x if align == 'left' else x - w / 2 if align == 'center' else x - w
            assert 0 <= x0 and x0 + w <= 740, (s, x0, w)
            assert 0 <= y and y + size <= self.height, (s, y)
            self.boxes.append({'text': s, 'x0': x0, 'x1': x0 + w, 'baseline': y, 'size': size})
            getattr(c, {'left': 'drawString', 'center': 'drawCentredString', 'right': 'drawRightString'}[align])(x, y, s)

        def line(self, x0, y0, x1, y1, color=INK, width=1, dash=None):
            c = self.c
            c.setStrokeColor(color)
            c.setLineWidth(width)
            c.setDash(dash or [])
            c.line(x0, y0, x1, y1)
            c.setDash([])

        def arrow(self, x0, y0, x1, y1, color=INK, width=1.3, dash=None):
            self.line(x0, y0, x1, y1, color, width, dash)
            a = math.atan2(y1 - y0, x1 - x0)
            p = self.c.beginPath()
            p.moveTo(x1, y1)
            p.lineTo(x1 - 6 * math.cos(a - 0.45), y1 - 6 * math.sin(a - 0.45))
            p.lineTo(x1 - 6 * math.cos(a + 0.45), y1 - 6 * math.sin(a + 0.45))
            p.close()
            self.c.setFillColor(color)
            self.c.drawPath(p, stroke=0, fill=1)

        def dot(self, x, y, r=3, color=INK):
            self.c.setFillColor(color)
            self.c.circle(x, y, r, stroke=0, fill=1)

        def square(self, x, y, r=4, color=GRAY, fill=False):
            self.c.setStrokeColor(color)
            self.c.setLineWidth(1.2)
            self.c.setFillColor(WHITE)
            self.c.rect(x - r, y - r, 2 * r, 2 * r, stroke=1, fill=int(fill))

        def box(self, x, y, w, h, fill=LIGHT, stroke=GRID):
            self.c.setFillColor(fill)
            self.c.setStrokeColor(stroke)
            self.c.setLineWidth(0.8)
            self.c.roundRect(x, y, w, h, 5, stroke=1, fill=1)

        def sub(self, x, y, base, sub, color=INK):
            self.text(x, y, base, 14, color=color)
            self.text(x + pdfmetrics.stringWidth(base, 'PSans', 14), y - 3, sub, 12, color=color)

        def finish(self):
            self.c.showPage()
            self.c.save()
            return self.path
    f = Figure('actions_and_retention', 360, 'Admissible resets and conditional forced refreshing')
    f.line(214, 116, 214, 345, GRID, 0.8)
    f.line(443, 20, 443, 345, GRID, 0.8)
    f.text(14, 340, 'A  Reset action', 13, bold=True)
    f.text(14, 316, 'Observed history', color=GRAY)
    f.box(14, 258, 188, 48, fill=HexColor('#f5f7f8'))
    for x, s in [(31, '0'), (65, 'a'), (98, 'b'), (129, '…')]:
        f.text(x, 277, s, align='center')
    f.box(155, 268, 39, 27, fill=LIGHT, stroke=TEAL)
    f.sub(168, 278, 'z', 't', TEAL)
    f.box(38, 184, 164, 35, fill=LIGHT, stroke=TEAL)
    f.text(120, 197, 'active state', align='center')
    f.arrow(175, 268, 175, 219, TEAL, 1.8)
    f.text(130, 236, 'current', color=TEAL)
    f.line(65, 258, 85, 228, GRAY, 1.1, [3, 3])
    f.arrow(85, 228, 85, 219, GRAY, 1.1, [3, 3])
    f.line(69, 246, 82, 233, INK, 1.6)
    f.line(69, 233, 82, 246, INK, 1.6)
    f.text(14, 230, 'past', color=GRAY)
    f.text(14, 154, 'Current reset only', bold=True)
    f.text(14, 124, 'History is available.')
    f.text(226, 340, 'B  Two continuations', 13, bold=True)
    f.text(226, 319, 'state / η', color=GRAY)
    bx0, bx1, by0, by1 = (273, 430, 180, 299)
    tx = lambda t: bx0 + (bx1 - bx0) * t / 6
    vy = lambda v: by0 + (by1 - by0) * (v + 1.3) / 2.6
    for val, lab in [(-7 / 6, '−7/6'), (-1 / 3, 'a=−1/3'), (0, '0'), (1 / 3, 'b=1/3'), (7 / 6, '7/6')]:
        f.line(bx0 - 3, vy(val), bx1 + 2, vy(val), GRID, 0.45)
        f.text(bx0 - 6, vy(val) - 4, lab, color=GRAY, align='right')
    split = tx(2.5)
    f.line(split, by0, split, by1, GRAY, 0.8, [2, 3])
    f.text(tx(1), 306, 'prefix', color=GRAY, align='center')
    f.text(tx(4.5), 306, 'suffix', color=GRAY, align='center')
    neg = [0, -1 / 3, 1 / 3, -7 / 6, 0, -7 / 6, 0]
    pos = [0, -1 / 3, 1 / 3, 7 / 6, 0, 7 / 6, 0]
    for t in range(2):
        f.line(tx(t), vy(neg[t]), tx(t + 1), vy(neg[t + 1]), INK, 1.15)
    for t in range(2, 6):
        f.line(tx(t), vy(pos[t]), tx(t + 1), vy(pos[t + 1]), GRAY, 1.1, [1.5, 2.3])
        f.line(tx(t), vy(neg[t]), tx(t + 1), vy(neg[t + 1]), INK, 1.2)
    for t in range(3):
        f.dot(tx(t), vy(neg[t]), 2.8)
    for t in range(3, 7):
        f.square(tx(t), vy(pos[t]), 3.3, GRAY, True)
        f.dot(tx(t), vy(neg[t]), 2.8)
    f.line(bx0, by0, bx1 + 2, by0, GRAY, 0.7)
    for t in range(7):
        f.line(tx(t), by0, tx(t), by0 - 3, GRAY, 0.7)
        f.text(tx(t), by0 - 17, str(t), color=GRAY, align='center')
    f.line(228, 143, 250, 143, INK, 1.2)
    f.dot(239, 143, 2.8)
    f.text(258, 139, 'c = a')
    f.line(339, 143, 361, 143, GRAY, 1.1, [1.5, 2.3])
    f.square(350, 143, 3.3, GRAY, True)
    f.text(369, 139, 'c = b')
    f.box(14, 43, 416, 61, fill=HexColor('#f5f7f8'), stroke=GRID)
    f.text(26, 83, 'Historical resets allowed: 2 total online refreshes suffice.', bold=True)
    f.text(26, 63, 'Retain 0, then restore c at the first suffix observation.')
    f.text(456, 340, 'C  Retain or rebuild', 13, bold=True)
    f.text(456, 319, 'η = 1, c = a = −1/3, y = −7/6', color=GRAY)
    cx0, cx1 = (526, 726)
    xx = lambda t: cx0 + (cx1 - cx0) * t / 8
    rows = {'observed': (253, 309), 'offline': (171, 227), 'online': (82, 138)}
    vals = [0, -1 / 3, 1 / 3, -7 / 6, 0, -7 / 6, 0, -7 / 6, 0]
    for name, (lo, hi) in rows.items():
        yy = lambda v: lo + (hi - lo) * (v + 1.3) / 1.8
        f.line(xx(2.5), lo - 1, xx(2.5), hi, GRAY, 0.7, [2, 3])
        for v, lab in [(0, '0'), (-7 / 6, 'y')]:
            f.line(cx0 - 2, yy(v), cx1 + 2, yy(v), GRID, 0.45)
            f.text(cx0 - 5, yy(v) - 4, lab, color=GRAY, align='right')
        if name == 'observed':
            f.text(456, 303, 'observed', bold=True)
            for t in range(8):
                f.line(xx(t), yy(vals[t]), xx(t + 1), yy(vals[t + 1]), INK, 1.15)
            for t, v in enumerate(vals):
                f.dot(xx(t), yy(v), 2.7)
        elif name == 'offline':
            f.text(456, 209, 'offline', bold=True, color=TEAL)
            f.text(456, 191, 'holds c', color=TEAL)
            f.line(xx(0), yy(0), xx(1), yy(0), TEAL, 1.5, [4, 2])
            f.line(xx(1), yy(0), xx(1), yy(-1 / 3), TEAL, 1.5, [4, 2])
            f.line(xx(1), yy(-1 / 3), xx(8), yy(-1 / 3), TEAL, 1.5, [4, 2])
            f.dot(xx(0), yy(0), 3, TEAL)
            f.dot(xx(1), yy(-1 / 3), 3, TEAL)
            f.text(cx1, lo - 10, '2 refreshes', color=TEAL, align='right')
        else:
            f.text(456, 120, 'online', bold=True)
            f.text(456, 102, 'P ≠ c')
            f.c.setFillColor(HexColor('#f5f7f8'))
            f.c.rect(cx0, lo, xx(2.5) - cx0, hi - lo, stroke=0, fill=1)
            for t in range(3, 8):
                f.line(xx(t), yy(vals[t]), xx(t + 1), yy(vals[t + 1]), INK, 1.15)
            for t in range(3, 9):
                f.square(xx(t), yy(vals[t]), 4.4, TEAL, False)
                f.dot(xx(t), yy(vals[t]), 2.4)
            f.line(cx0, lo - 3, cx1 + 2, lo - 3, GRAY, 0.7)
            for t in range(9):
                f.text(xx(t), lo - 19, str(t), color=GRAY, align='center')
    f.square(462, 43, 4.4, TEAL, False)
    f.dot(462, 43, 2.4)
    f.text(474, 39, 'refresh (conditional)')
    f.text(456, 19, 'Radius 5/6 < 1; step 7/6 > 1.')
    ambient = {F(-7, 6), F(-1, 3), F(0), F(1, 3), F(7, 6)}
    negative = [F(str(x)) for x in ['0', '-1/3', '1/3', '-7/6', '0', '-7/6', '0', '-7/6', '0']]
    positive = [F(str(x)) for x in ['0', '-1/3', '1/3', '7/6', '0', '7/6', '0', '7/6', '0']]
    for path, center, refresh in [(negative, F(-1, 3), 1), (positive, F(1, 3), 2)]:
        assert len(set(path)) == 4 and set(path) <= ambient
        cache = [F(0)] * refresh + [center] * (len(path) - refresh)
        assert max((abs(x - y) for x, y in zip(path, cache))) == F(5, 6)
        for P in [F(0), F(-1, 3), F(1, 3)]:
            assert (abs(path[3] - P) > 1) == (P != center)
    return f.finish()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/figures")
    add_font_arguments(parser)
    args = parser.parse_args()
    path = render(args.output_dir, args.font_dir)
    print(path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
