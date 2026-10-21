#!/usr/bin/env python3
"""Draw adaptive thresholds and exact cost components."""
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

def render(output_dir, font_dir=None, data_path=None):
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    data_path = Path(data_path) if data_path is not None else ROOT / 'data/adaptive_examples.json'
    register_fonts(font_dir)

    SOURCE = data_path
    data = json.loads(SOURCE.read_text())
    low = next((c for c in data['cases'] if c['case_id'] == 'burst_s1_m4_V1over2'))
    high = next((c for c in data['cases'] if c['case_id'] == 'burst_s1_m4_V2over1'))
    assert low['policies']['anytime']['starts'] == [0, 3, 33]
    assert low['policies']['clipped']['starts'] == [0, 1, 2, 3, 4]
    a32 = low['policies']['anytime']['trace'][32]
    a33 = low['policies']['anytime']['trace'][33]
    assert Q(a32['pre_decision_drift_squared']) == Q(a32['threshold_squared']) == Q(1, 64)
    assert not a32['refresh'] and a33['refresh']
    assert Q(a33['pre_decision_drift_squared']) > Q(a33['threshold_squared'])
    OUT = output_dir / 'adaptive_thresholds.pdf'
    c = canvas.Canvas(str(OUT), pagesize=(740, 410), pageCompression=1, initialFontName='PaperSans', initialFontSize=12)
    c.setTitle('Adaptive thresholds on two burst-and-plateau paths')
    c.setAuthor('Hiroyasu Usami')
    INK = HexColor('#18212b')
    GRAY = HexColor('#68727c')
    GRID = HexColor('#d9e0e5')
    BLUE = HexColor('#126f8e')
    PALE = HexColor('#eef2f5')
    WHITE = HexColor('#ffffff')

    def text(x, y, s, size=12, bold=False, color=INK, align='left', background=False):
        font = 'PaperSansBold' if bold else 'PaperSans'
        c.setFont(font, size)
        c.setFillColor(color)
        w = pdfmetrics.stringWidth(s, font, size)
        if background:
            left = x - w / 2 if align == 'center' else x - w if align == 'right' else x
            c.setFillColor(WHITE)
            c.rect(left - 0.8, y - 1, w + 1.6, size + 1, stroke=0, fill=1)
            c.setFillColor(color)
        getattr(c, {'left': 'drawString', 'center': 'drawCentredString', 'right': 'drawRightString'}[align])(x, y, s)

    def line(x1, y1, x2, y2, color=INK, width=1, dash=()):
        c.setStrokeColor(color)
        c.setLineWidth(width)
        c.setDash(dash)
        c.line(x1, y1, x2, y2)
        c.setDash([])

    def triangle(x, y, color=BLUE, r=3.2):
        p = c.beginPath()
        p.moveTo(x, y + r)
        p.lineTo(x - r, y - r)
        p.lineTo(x + r, y - r)
        p.close()
        c.setFillColor(color)
        c.drawPath(p, stroke=0, fill=1)

    def hatched(x, y, w, h):
        if w <= 0:
            return
        c.setFillColor(WHITE)
        c.setStrokeColor(INK)
        c.setLineWidth(0.6)
        c.rect(x, y, w, h, stroke=1, fill=1)
        c.saveState()
        p = c.beginPath()
        p.rect(x, y, w, h)
        c.clipPath(p, stroke=0, fill=0)
        c.setStrokeColor(GRAY)
        c.setLineWidth(0.5)
        for off in range(-20, int(w) + 30, 5):
            c.line(x + off, y, x + off + h, y + h)
        c.restoreState()

    def polyline(points, color=INK, dash=(), width=1.5):
        p = c.beginPath()
        for i, (x, y) in enumerate(points):
            if i:
                p.lineTo(x, y)
            else:
                p.moveTo(x, y)
        c.setStrokeColor(color)
        c.setLineWidth(width)
        c.setDash(dash)
        c.drawPath(p, stroke=1, fill=0)
        c.setDash([])
    text(12, 389, 'A  Burst followed by a plateau', 14, bold=True)
    text(12, 369, 'T = 64, λ = 1, V = 1/2')
    line(13, 350, 34, 350, INK, 1.5)
    text(41, 346, 'Pre-decision distance')
    line(187, 350, 208, 350, BLUE, 1.7, (5, 3))
    text(215, 346, 'Threshold')
    triangle(320, 350)
    text(331, 346, 'Refresh')
    line(454, 18, 454, 397, GRID, 0.8)
    x0, x1 = (61, 438)
    xx = lambda t: x0 + (x1 - x0) * t / 63
    YMAX = 0.42
    for policy, label, y0, y1, titley in [('anytime', 'Anytime', 238, 321, 331), ('clipped', 'Clipped', 118, 201, 211)]:
        text(x0, titley, label, 12, bold=True)
        yy = lambda value: y0 + (y1 - y0) * value / YMAX
        c.setFillColor(PALE)
        c.rect(xx(1), y0, xx(4) - xx(1), y1 - y0, stroke=0, fill=1)
        for tick, labely in [(0, '0'), (0.125, '1/8'), (0.25, '1/4'), (0.375, '3/8')]:
            y = yy(tick)
            line(x0, y, x1, y, GRID, 0.5)
            text(x0 - 9, y - 4, labely, color=GRAY, align='right')
        for t in [0, 4, 16, 32, 48, 63]:
            line(xx(t), y0, xx(t), y1, GRID, 0.5)
            if policy == 'clipped':
                line(xx(t), y0, xx(t), y0 - 4, GRAY, 0.7)
                text(xx(t), y0 - 20, str(t), color=GRAY, align='center')
        line(x0, y0, x1, y0, GRAY, 0.7)
        line(x0, y0, x0, y1, GRAY, 0.7)
        trace = low['policies'][policy]['trace']
        distance = [(xx(0), yy(0))] + [(xx(step['t']), yy(math.sqrt(float(Q(step['pre_decision_drift_squared']))))) for step in trace[1:]]
        threshold = [(xx(step['t']), yy(math.sqrt(float(Q(step['threshold_squared']))))) for step in trace[1:]]
        polyline(distance, INK, width=1.5)
        polyline(threshold, BLUE, (5, 3), 1.7)
        triangle(xx(0), yy(0), r=2.7)
        for step in trace[1:]:
            if step['refresh']:
                triangle(xx(step['t']), yy(math.sqrt(float(Q(step['pre_decision_drift_squared'])))), r=3)
        if policy == 'anytime':
            point = (xx(33), yy(0.125))
            line(point[0] + 2, point[1] + 4, point[0] + 36, point[1] + 28, GRAY, 0.8)
            text(point[0] + 39, point[1] + 26, 't = 33', 12, bold=True)
    text((x0 + x1) / 2, 76, 'Opportunity t', align='center')
    c.saveState()
    c.translate(16, (118 + 321) / 2)
    c.rotate(90)
    text(0, 0, 'Distance / threshold', align='center')
    c.restoreState()
    text(12, 43, 'Shading marks the burst at t = 1,…,4.', color=GRAY)
    text(12, 22, 'Both rows use the same axes.', color=GRAY)
    text(473, 389, 'B  Distortion and refresh cost', 14, bold=True)
    text(473, 369, 'Same burst shape; T = 64, λ = 1')
    c.setFillColor(BLUE)
    c.rect(474, 344, 17, 11, stroke=0, fill=1)
    text(498, 344, 'λN')
    hatched(549, 344, 17, 11)
    text(573, 344, 'Distortion')
    bx0, bx1 = (543, 725)
    by0, by1 = (76, 315)
    costx = lambda value: bx0 + (bx1 - bx0) * float(value) / 7.5
    for val in [0, 2, 4, 6]:
        x = costx(val)
        line(x, by0, x, by1, GRID, 0.5)
        line(x, by0, x, by0 - 4, GRAY, 0.7)
        text(x, by0 - 20, str(val), color=GRAY, align='center')
    line(bx0, by0, bx1, by0, GRAY, 0.7)
    for case, header, ys in [(low, 'V = 1/2', [302, 270, 238]), (high, 'V = 2', [166, 134, 102])]:
        text(473, ys[0] + 23, header, 12, bold=True)
        for kind, label, y in zip(['offline', 'anytime', 'clipped'], ['Offline', 'Anytime', 'Clipped'], ys):
            record = case['policies'][kind]
            charge = Q(record['refresh_cost'])
            D = Q(record['distortion'])
            total = Q(record['cost'])
            assert charge + D == total
            text(bx0 - 9, y - 4, label, align='right')
            charge_end = costx(charge)
            total_end = costx(total)
            c.setFillColor(BLUE)
            c.rect(bx0, y - 8, charge_end - bx0, 16, stroke=0, fill=1)
            hatched(charge_end, y - 8, total_end - charge_end, 16)
            text((bx0 + charge_end) / 2, y - 4, str(charge.numerator), color=WHITE, align='center')
            if D:
                labelD = '¾' if D == Q(3, 4) else str(D)
                text((charge_end + total_end) / 2, y - 4, labelD, align='center', background=True)
            total_label = '2.75' if total == Q(11, 4) else str(total)
            text(total_end + 5, y - 4, total_label)
    text((bx0 + bx1) / 2, 35, 'Total cost', align='center')
    c.showPage()
    c.save()
    return OUT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/figures")
    add_font_arguments(parser)
    parser.add_argument("--data", type=Path, default=ROOT / "data/adaptive_examples.json")
    args = parser.parse_args()
    path = render(args.output_dir, args.font_dir, args.data)
    print(path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
