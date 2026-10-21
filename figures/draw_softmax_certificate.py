#!/usr/bin/env python3
"""Draw same-input softmax bounds and RMS dilution."""
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
    register_fonts(font_dir)

    WIDTH, HEIGHT = (740, 360)
    PDF = output_dir / 'softmax_certificate.pdf'
    INK = HexColor('#18212b')
    GRAY = HexColor('#68727c')
    TEAL = HexColor('#126f8e')
    LIGHT = HexColor('#eaf3f6')
    LINE = HexColor('#c9d1d8')
    ZERO = HexColor('#f4f5f6')
    c = canvas.Canvas(str(PDF), pagesize=(WIDTH, HEIGHT), pageCompression=1, initialFontName='PaperSans', initialFontSize=12)
    c.setTitle('State-to-output certificates and complete-coordinate RMS dilution')
    c.setAuthor('Hiroyasu Usami')
    text_boxes = []
    used_chars = set()

    def text_parts(string, size):
        scripts = {'⁰': ('0', 1), '₁': ('1', -1), '₂': ('2', -1)}
        parts, normal = ([], '')
        for ch in string:
            if ch in scripts:
                if normal:
                    parts.append((normal, size, 0))
                    normal = ''
                plain, direction = scripts[ch]
                parts.append((plain, max(12, 0.8 * size), direction * 0.27 * size))
            else:
                normal += ch
        if normal:
            parts.append((normal, size, 0))
        return parts

    def text_width(string, font, size):
        return sum((pdfmetrics.stringWidth(part, font, part_size) for part, part_size, dy in text_parts(string, size)))

    def text(x, y, string, size=12, bold=False, color=INK, align='left'):
        assert size >= 12
        font = 'PaperSansBold' if bold else 'PaperSans'
        width = text_width(string, font, size)
        x0 = x if align == 'left' else x - width / (2 if align == 'center' else 1)
        assert x0 >= 0 and x0 + width <= WIDTH, (string, x0, width)
        c.setFillColor(color)
        part_x = x0
        for part, part_size, dy in text_parts(string, size):
            part_width = pdfmetrics.stringWidth(part, font, part_size)
            c.setFont(font, part_size)
            c.drawString(part_x, y + dy, part)
            text_boxes.append({'text': part, 'x': part_x, 'baseline': y + dy, 'width': part_width, 'size': part_size, 'font': font})
            used_chars.update(part)
            part_x += part_width

    def rich(x, y, runs, align='left', color=INK):
        widths = [text_width(s, 'PaperSansBold' if b else 'PaperSans', size) for s, size, dy, b in runs]
        total = sum(widths)
        if align == 'center':
            x -= total / 2
        elif align == 'right':
            x -= total
        for (s, size, dy, bold), width in zip(runs, widths):
            text(x, y + dy, s, size=size, bold=bold, color=color)
            x += width
        return total

    def line(x0, y0, x1, y1, color=INK, width=1, dash=None):
        c.setStrokeColor(color)
        c.setLineWidth(width)
        c.setDash(dash or [])
        c.line(x0, y0, x1, y1)
        c.setDash([])

    def arrow(x0, y, x1, color=INK):
        line(x0, y, x1, y, color, 1.2)
        p = c.beginPath()
        p.moveTo(x1, y)
        p.lineTo(x1 - 6, y + 3.5)
        p.lineTo(x1 - 6, y - 3.5)
        p.close()
        c.setFillColor(color)
        c.drawPath(p, stroke=0, fill=1)

    def node(x, title):
        c.setFillColor(HexColor('#ffffff'))
        c.setStrokeColor(LINE)
        c.setLineWidth(0.8)
        c.rect(x, 216, 158, 84, stroke=1, fill=1)
        text(x + 79, 282, title, bold=True, align='center')
    text(18, 340, 'A  From state drift to same-input output error', 14, bold=True)
    text(18, 317, 'Unit-ball states; ϑ > 0; same current input, values, and readout.', 12)
    xs = [18, 200, 382, 564]
    for x, title in zip(xs, ['State drift', 'Logit oscillation', 'Probability change', 'Output discrepancy']):
        node(x, title)
    for left, right in zip(xs, xs[1:]):
        arrow(left + 161, 256, right - 3, TEAL)
    text(97, 256, 'ρ = ‖z − z⁰‖₂', 16, align='center')
    text(279, 256, 'R = osc(ℓ − ℓ⁰)', 15, align='center')
    text(279, 233, 'R ≤ 6ρ/ϑ', 16, align='center', color=TEAL)
    text(461, 256, 'TV(p, q) ≤', 16, align='center')
    text(461, 233, 'tanh(R/4)', 16, align='center', color=TEAL)
    rich(643, 256, [('‖Δy', 16, 0, False), ('t', 12, -3, False), ('‖ ≤', 16, 0, False)], align='center')
    rich(643, 233, [('L', 15, 0, False), ('H,t', 12, -3, False), (' W', 15, 0, False), ('t', 12, -3, False), (' TV(p, q)', 15, 0, False)], align='center', color=TEAL)
    line(18, 198, 722, 198, LINE, 0.8)
    text(18, 179, 'B  Same output error, smaller RMS.', 14, bold=True)
    text(18, 160, 'n = 2, ϑ = 1; references ±e₁ and current values ±1 stay fixed; identity readout.', 12)
    text(18, 143, 'Query: u⁰ = 0 → u = h e₁ with h = 1/2.  Complete drift Δz is shown below.', 12)
    bottom, cell_h, cell_w = (53, 24, 35)

    def matrix(x, dim, label):
        for row in range(3):
            for col in range(dim):
                active = row == 0 and col == 0
                c.setFillColor(LIGHT if active else ZERO)
                c.setStrokeColor(TEAL if active else LINE)
                c.setLineWidth(1.2 if active else 0.6)
                yy = bottom + (2 - row) * cell_h
                c.rect(x + col * cell_w, yy, cell_w, cell_h, stroke=1, fill=1)
                text(x + (col + 0.5) * cell_w, yy + 7, 'h' if active else '0', 13, bold=active, align='center', color=TEAL if active else GRAY)
        text(x + dim * cell_w / 2, 132, label, 12, bold=True, align='center')
        if dim > 1:
            c.setStrokeColor(GRAY)
            c.setLineWidth(0.9)
            c.setDash([3, 2])
            c.rect(x + cell_w, bottom, (dim - 1) * cell_w, 3 * cell_h, stroke=1, fill=0)
            c.setDash([])
    for y, label in [(108, 'Δu'), (84, 'Δw₁'), (60, 'Δw₂')]:
        text(65, y, label, 12, align='right')
        text(293, y, label, 12, align='right')
    matrix(79, 1, 'd = 1')
    matrix(307, 4, 'd = 4')
    text(208, 117, 'append unchanged', 12, align='center', color=GRAY)
    text(208, 100, 'zero coordinates', 12, align='center', color=GRAY)
    arrow(140, 79, 265, INK)
    text(485, 120, 'Output discrepancy unchanged', 12, bold=True)
    text(485, 97, 'tanh(1) ≈ 0.7616', 16, color=TEAL)
    text(485, 77, 'ρ = 1/2 in every dimension', 12)
    text(485, 57, 'r = (1/2)/√(3d) → 0', 15)
    text(18, 24, 'Every appended coordinate is unchanged; only the complete-coordinate RMS denominator grows.', 12, color=GRAY)
    for font_name in ['PaperSans', 'PaperSansBold']:
        face = pdfmetrics.getFont(font_name).face
        missing = sorted((ord(ch) for ch in used_chars if ord(ch) not in face.charWidths))
        assert not missing, (font_name, missing)
    c.showPage()
    c.save()
    h, temperature = (0.5, 1.0)
    dim_examples = []
    for d in [1, 4, 100]:
        query0 = [0.0] * d
        query = [h] + [0.0] * (d - 1)
        refs = [[1.0] + [0.0] * (d - 1), [-1.0] + [0.0] * (d - 1)]
        norm = lambda v: math.sqrt(sum((x * x for x in v)))
        squared_distance = lambda x, y: sum(((a - b) ** 2 for a, b in zip(x, y)))
        logits0 = [-squared_distance(query0, w) / temperature for w in refs]
        logits = [-squared_distance(query, w) / temperature for w in refs]
        softmax = lambda values: [math.exp(a - max(values)) / sum((math.exp(b - max(values)) for b in values)) for a in values]
        q, p = (softmax(logits0), softmax(logits))
        values = [1.0, -1.0]
        out0, out = (sum((a * v for a, v in zip(q, values))), sum((a * v for a, v in zip(p, values))))
        rho = norm([a - b for a, b in zip(query, query0)])
        r = rho / math.sqrt(3 * d)
        delta_logit = [a - b for a, b in zip(logits, logits0)]
        R = max(delta_logit) - min(delta_logit)
        tv = 0.5 * sum((abs(a - b) for a, b in zip(p, q)))
        assert all((norm(v) <= 1 for v in [query0, query, *refs]))
        assert math.isclose(out0, 0, abs_tol=1e-14)
        assert math.isclose(out, math.tanh(1), abs_tol=1e-14)
        assert math.isclose(rho, h, abs_tol=1e-14)
        assert math.isclose(R, 2.0, abs_tol=1e-14)
        assert tv <= math.tanh(R / 4) + 1e-14
        assert R <= 6 * rho / temperature + 1e-14
        assert math.isclose(abs(out - out0), 2 * tv, abs_tol=1e-14)
        dim_examples.append({'d': d, 'n': 2, 'complete_coordinate_count': 3 * d, 'rho': rho, 'R': R, 'TV': tv, 'rms': r, 'projective_TV_upper_bound': math.tanh(R / 4), 'logits_cached': logits0, 'logits_fresh': logits, 'weights_cached': q, 'weights_fresh': p, 'output_cached': out0, 'output_fresh': out, 'absolute_output_discrepancy': abs(out - out0), 'max_vector_norm': max((norm(v) for v in [query0, query, *refs]))})
    (output_dir / 'softmax_values.json').write_text(json.dumps(dim_examples, indent=2) + '\n')
    return PDF


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
