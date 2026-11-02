#!/usr/bin/env python3
"""Rebuild the Co-Investigator SVG; --render also writes PDF and PNG."""
import argparse
from html import escape
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
W, H = 1440, 1040
INK, MUTED, LINE = '#24333e', '#54636d', '#71818c'
HUMAN, SKILL, TOOL, RECORD, REVIEW = '#e8f0f9', '#f8ede7', '#eef0f2', '#eaf3ed', '#f0edf7'
parts = []


def rect(x, y, w, h, fill, stroke='#b9c5cc', radius=2, dashed=False):
    assert 0 <= x <= W-w and 0 <= y <= H-h
    dash = ' stroke-dasharray="7 5"' if dashed else ''
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="1.6"{dash}/>')


def text(x, y, lines, size=24, bold=False, color=INK, anchor='start', gap=29):
    if isinstance(lines, str):
        lines = [lines]
    for i, line in enumerate(lines):
        assert 0 <= x <= W and 0 <= y+i*gap <= H
        parts.append(f'<text x="{x}" y="{y+i*gap}" font-size="{size}" font-weight="{"bold" if bold else "normal"}" fill="{color}" text-anchor="{anchor}">{escape(line)}</text>')


def line(points, color=LINE, dashed=False):
    for x, y in points:
        assert 0 <= x <= W and 0 <= y <= H
    dash = ' stroke-dasharray="6 5"' if dashed else ''
    coords = ' '.join(f'{x},{y}' for x, y in points)
    parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="1.8" stroke-linejoin="round"{dash}/>')


def arrow(points, color=LINE, dashed=False, both=False):
    assert len(points) >= 2
    line(points, color, dashed)
    ends = [(points[-2], points[-1])]
    if both:
        ends.append((points[1], points[0]))
    for (ax, ay), (bx, by) in ends:
        dx, dy = bx-ax, by-ay
        length = (dx*dx+dy*dy)**0.5
        assert length > 0
        ux, uy = dx/length, dy/length
        triangle = f'{bx},{by} {bx-9*ux+4*uy},{by-9*uy-4*ux} {bx-9*ux-4*uy},{by-9*uy+4*ux}'
        parts.append(f'<polygon points="{triangle}" fill="{color}"/>')


def node(x, y, w, h, lines, fill=SKILL, size=24):
    rect(x, y, w, h, fill)
    lines = [lines] if isinstance(lines, str) else lines
    text(x+w/2, y+h/2+size*.34-(len(lines)-1)*14, lines, size, anchor='middle', gap=28)


def build():
    parts.clear()
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">')
    parts.append('<title id="title">Co-Investigator architecture</title><desc id="desc">A scientist directs Codex or Claude Code through goals, methods, preferences, and feedback. The host applies interacting scientific skills, invokes executable tools, and maintains project context linked to preserved evidence. Plans and interpretation return to the scientist. Independent reviewers operate in separate contexts on request. The scientist performs experiments and supplies observations.</desc>')
    parts.append('<g font-family="Helvetica, Arial, sans-serif">')
    rect(0, 0, W, H, '#ffffff', '#ffffff', 0)

    # A single system boundary separates host-followed skills from the scientist,
    # executable resources, durable records, and independent reviewer contexts.
    rect(330, 80, 780, 650, '#ffffff', '#8798a4', 12)
    text(720, 54, 'Co-Investigator', 34, True, anchor='middle')
    rect(390, 115, 650, 90, '#e8edf1', '#8fa1ae', 3)
    text(715, 150, 'Codex / Claude Code', 29, True, anchor='middle')
    text(715, 182, 'Conversation · reasoning · tool execution', 24, anchor='middle')

    # The host routes the task to relevant skill instructions; the buses do not
    # imply simultaneous worker agents or an autonomous scheduling service.
    text(720, 245, 'Applies task-relevant skills', 23, color=MUTED, anchor='middle')
    line([(715, 205), (715, 216)])
    line([(355, 266), (1085, 266)])
    arrow([(715, 253), (715, 266)])
    line([(355, 266), (355, 646)])
    line([(1085, 266), (1085, 646)])
    for y in (332, 422, 512, 646):
        arrow([(355, y), (380, y)])
    for y in (397, 512, 646):
        arrow([(1085, y), (1050, y)])

    node(380, 300, 300, 64, 'Retrieve & read papers')
    node(380, 390, 300, 64, 'Literature synthesis')
    node(380, 480, 300, 64, 'Citation validation')
    node(750, 300, 300, 154, ['Experiment cycle', 'Plan · predict', 'Analyze · interpret'])
    node(750, 480, 300, 64, 'Scientific writing')
    arrow([(530, 364), (530, 390)])
    arrow([(530, 454), (530, 480)])
    arrow([(680, 422), (750, 422)], both=True)
    arrow([(900, 454), (900, 480)])
    arrow([(680, 512), (750, 512)], both=True)
    text(715, 575, 'Extend and apply project tools', 23, color=MUTED, anchor='middle')
    node(380, 602, 300, 88, ['Scientific tool', 'building'])
    node(750, 602, 300, 88, ['sgRNA sequence', 'verification'])
    text(715, 716, 'Project-local skills · shared across both hosts', 22, color=MUTED, anchor='middle')

    # Human control and the output/feedback loop occupy the left side.
    text(145, 54, 'Scientist', 29, True, anchor='middle')
    rect(30, 95, 235, 205, HUMAN, '#aac0d6')
    text(147, 132, 'Research direction', 24, True, anchor='middle')
    text(147, 173, ['Question & goals', 'Methods & preferences', 'Models & permissions', 'Feedback & decisions'], 22, anchor='middle', gap=32)
    arrow([(265, 160), (390, 160)], '#5e7f9e')
    text(327, 143, 'request', 22, color='#5e7f9e', anchor='middle')
    parts.append('<circle cx="145" cy="365" r="22" fill="#9ab7d1"/>')
    parts.append('<path d="M105 428 L105 412 C105 386 185 386 185 412 L185 428 Z" fill="#9ab7d1"/>')
    arrow([(145, 342), (145, 300)], '#5e7f9e')
    node(30, 520, 235, 108, ['Plans & hypotheses', 'Analyses &', 'interpretation'], HUMAN, 23)
    arrow([(390, 185), (290, 185), (290, 574), (265, 574)], '#5e7f9e')
    arrow([(145, 520), (145, 440)], '#5e7f9e')
    text(162, 480, 'discuss', 22, color='#5e7f9e')
    node(30, 725, 235, 85, ['Experiments', 'Scientist executes'], HUMAN, 23)
    arrow([(105, 410), (14, 410), (14, 768), (30, 768)], '#5e7f9e')

    # Executable utilities and persistent files have distinct visual types.
    rect(1175, 110, 245, 230, TOOL, '#a6afb8')
    text(1297, 143, 'Executable tools', 24, True, anchor='middle')
    line([(1175, 160), (1420, 160)], '#b7c0c7')
    text(1297, 196, ['PDF retrieval', 'Text / table extraction', 'Sequence checks', 'New project tools'], 22, anchor='middle', gap=37)
    arrow([(1040, 160), (1175, 160)], both=True)
    text(1107, 136, 'uses', 22, color=MUTED, anchor='middle')

    # Record shapes use a ruled header to distinguish files from skill nodes.
    rect(1175, 465, 245, 198, RECORD, '#a2bba9')
    text(1297, 501, 'Project memory', 24, True, anchor='middle')
    line([(1175, 516), (1420, 516)], '#b0c8b6')
    text(1297, 549, ['Context & preferences', 'Decisions & task log', 'Outputs & provenance'], 22, anchor='middle', gap=35)
    arrow([(1040, 190), (1148, 190), (1148, 565), (1175, 565)], both=True)
    text(1297, 425, ['Reads / maintains', 'durable files'], 22, color=MUTED, anchor='middle', gap=27)
    rect(1175, 735, 245, 112, RECORD, '#a2bba9')
    text(1297, 769, 'Primary evidence', 24, True, anchor='middle')
    text(1297, 806, ['Literature · raw data', 'Experimental records'], 22, anchor='middle', gap=27)
    arrow([(1297, 735), (1297, 663)])
    text(1313, 705, 'informs', 22, color=MUTED)
    arrow([(145, 810), (145, 1006), (1297, 1006), (1297, 847)], '#5e7f9e')
    rect(563, 990, 320, 32, '#ffffff', '#ffffff', 0)
    text(723, 1014, 'Supplied observations & data', 22, color='#5e7f9e', anchor='middle')

    # Review is a branch using independent contexts, not routine skill self-review.
    rect(380, 808, 670, 152, '#ffffff', '#9b91af', 7, True)
    text(715, 781, 'Independent review · on request', 26, True, color='#695b80', anchor='middle')
    for x, label in [(400, 'Evidence'), (620, 'Methods'), (840, 'Interpretation')]:
        node(x, 829, 190, 47, label, REVIEW, 23)
        arrow([(x+95, 876), (x+95, 899)], '#8d829f')
    rect(400, 899, 630, 40, REVIEW, '#c7bfd4')
    text(715, 927, 'Editorial decisions & response ledger', 23, anchor='middle')
    text(715, 988, 'Two rounds; new reviewer contexts in round 2', 22, color='#695b80', anchor='middle')
    arrow([(410, 205), (410, 224), (310, 224), (310, 854), (380, 854)], '#8d829f', True)
    arrow([(1050, 919), (1130, 919), (1130, 213), (1000, 213), (1000, 205)], '#8d829f', True)

    parts.append('</g></svg>')
    svg = '\n'.join(parts)+'\n'
    root = ET.fromstring(svg)
    assert root.attrib['viewBox'] == f'0 0 {W} {H}'
    assert len(root.findall('.//{http://www.w3.org/2000/svg}text')) >= 40
    for label in ('Retrieve &amp; read papers', 'Literature synthesis', 'Experiment cycle', 'Citation validation', 'Scientific writing', 'Scientific tool', 'sgRNA sequence', 'Independent review'):
        assert label in svg, label
    return svg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render', action='store_true', help='Also render PDF and 200-dpi PNG; requires figure dependencies and pdftoppm')
    args = parser.parse_args()
    if args.render:
        from reportlab import rl_config
        from reportlab.graphics import renderPDF
        from reportlab.pdfgen.canvas import Canvas
        from svglib.svglib import svg2rlg
        if not shutil.which('pdftoppm'):
            parser.error('--render requires pdftoppm from Poppler')
        rl_config.invariant = 1
    svg_path = OUT / 'architecture.svg'
    svg_path.write_text(build(), encoding='utf-8')
    if args.render:
        drawing = svg2rlg(str(svg_path))
        assert drawing is not None and (drawing.width, drawing.height) == (W, H)
        scale = (183/25.4*72)/W
        drawing.scale(scale, scale)
        drawing.width *= scale
        drawing.height *= scale
        pdf_path = OUT / 'architecture.pdf'
        canvas = Canvas(str(pdf_path), pagesize=(drawing.width, drawing.height), invariant=1)
        canvas.setTitle('Co-Investigator architecture')
        renderPDF.draw(drawing, canvas, 0, 0)
        canvas.showPage()
        canvas.save()
        subprocess.run(['pdftoppm', '-singlefile', '-r', '200', '-png', str(pdf_path), str(OUT/'architecture')], check=True)
        assert pdf_path.read_bytes().startswith(b'%PDF-')
        assert (OUT/'architecture.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    print('Wrote architecture.svg' + (', architecture.pdf, architecture.png' if args.render else ''))


if __name__ == '__main__':
    main()
