#!/usr/bin/env python3
"""Draw candidate presentation and nested-interval phases."""
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
    f = Figure('nested_intervals', 340, 'A legal offline center and randomized nested-interval phases')

    def subtoken(x, y, base, index, color=INK):
        f.sub(x, y, base, index, color)
        return x + pdfmetrics.stringWidth(base, 'PSans', 14) + pdfmetrics.stringWidth(index, 'PSans', 12) + 1
    f.line(274, 18, 274, 326, GRID, 0.8)
    f.text(14, 320, 'A  A legal offline center', 13, bold=True)
    f.text(14, 293, 'Common prefix exposes the grid', color=GRAY)
    f.line(28, 256, 245, 256, GRID, 1.1)
    for x in [28, 68, 151, 245]:
        f.dot(x, 256, 3, TEAL if x in [28, 151] else INK)
    for x, label in [(28, '0'), (68, 'δ'), (108, '…'), (151, 'δx'), (194, '…'), (239, 'δ(M−1)')]:
        f.text(x, 271, label, align='center')
    f.arrow(151, 251, 151, 207, TEAL, 1.5)
    f.text(162, 226, 'when observed', color=TEAL)
    f.box(28, 161, 223, 46, fill=LIGHT, stroke=TEAL)
    f.text(139.5, 187, 'Offline knows the final x', align='center')
    f.text(139.5, 170, 'and keeps δx from here.', align='center')
    f.text(14, 137, 'Initial 0; reset at δx’s occurrence')
    f.text(14, 119, '≤ 2 total refreshes', bold=True, color=TEAL)
    f.text(14, 86, 'Holds δx through every phase.')
    f.text(14, 68, 'Phase distortion < λ/b.')
    f.text(14, 38, 'δ = λ/M²')
    f.text(14, 20, 'Horizon fixed before the run.', color=GRAY)
    f.text(290, 320, 'B  A fixed-length random phase', 13, bold=True)
    f.text(290, 299, 'Uniform children are sampled before the run.', color=GRAY)
    subtoken(290, 270, 'R', 'i−1')
    px, pw, py = (360, 362, 264)
    for j in range(4):
        f.box(px + j * pw / 4, py, pw / 4, 18, fill=LIGHT if j == 1 else HexColor('#f5f7f8'), stroke=TEAL if j == 1 else GRID)
    x = subtoken(638, 286, 'm', 'i', GRAY)
    f.text(x + 3, 286, 'points', color=GRAY)
    sel0 = px + pw / 4
    selw = pw / 4
    f.arrow(sel0 + selw / 2, 264, sel0 + selw / 2, 250, TEAL, 1.2)
    f.box(sel0, 232, selw, 18, fill=LIGHT, stroke=TEAL)
    f.dot(sel0, 241, 3, INK)
    subtoken(sel0 + 34, 237, 'R', 'i', TEAL)
    subtoken(407, 237, 'r', 'i')
    f.arrow(427, 241, sel0 - 4, 241, GRAY, 1.0)
    f.line(sel0 + selw, 241, 584, 241, GRAY, 1.1)
    f.arrow(584, 241, 584, 204, GRAY, 1.1)
    x = 290
    f.text(x, 214, 'Far child: distance ≥ δ')
    x += pdfmetrics.stringWidth('Far child: distance ≥ δ', 'PSans', 12)
    x = subtoken(x, 214, 'm', 'i')
    f.text(x, 214, '/4  (Pr ≥ 1/4)')
    f.box(355, 164, 278, 40, fill=LIGHT, stroke=TEAL)
    f.text(454, 187, 'Repeat δ')
    subtoken(454 + pdfmetrics.stringWidth('Repeat δ', 'PSans', 12), 187, 'r', 'i')
    x = subtoken(443, 169, 'L', 'i')
    f.text(x, 169, '= M²/', 14)
    x += pdfmetrics.stringWidth('= M²/', 'PSans', 14)
    subtoken(x, 169, 'm', 'i')
    f.arrow(465, 164, 394, 132, INK, 1.2)
    f.arrow(524, 164, 626, 132, INK, 1.2)
    f.box(298, 90, 191, 42, fill=HexColor('#f5f7f8'), stroke=GRID)
    f.text(393.5, 115, '≥ 1 refresh', bold=True, align='center')
    f.text(393.5, 98, 'charge ≥ λ', align='center')
    f.box(526, 90, 200, 42, fill=HexColor('#f5f7f8'), stroke=GRID)
    f.text(626, 115, 'no refresh', bold=True, align='center')
    f.text(538, 98, 'distortion =')
    x = 538 + pdfmetrics.stringWidth('distortion =', 'PSans', 12) + 3
    x = subtoken(x, 98, 'L', 'i')
    f.text(x, 98, '|p − δ', 14)
    x += pdfmetrics.stringWidth('|p − δ', 'PSans', 14)
    x = subtoken(x, 98, 'r', 'i')
    f.text(x, 98, '|', 14)
    f.line(394, 90, 394, 68, GRAY, 1.1)
    f.line(394, 68, 626, 68, GRAY, 1.1)
    f.line(626, 90, 626, 68, GRAY, 1.1)
    f.arrow(494, 68, 494, 52, GRAY, 1.1)
    f.box(290, 12, 436, 40, fill=LIGHT, stroke=TEAL)
    f.text(302, 37, 'Expected phase cost ≥ λ/16', bold=True, color=TEAL)
    f.text(302, 21, 'After the fixed phase: next interval, or finish at i = b.')
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
