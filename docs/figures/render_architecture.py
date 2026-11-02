#!/usr/bin/env python3
"""Rebuild the editable architecture SVG; --render also writes PDF and PNG."""
import argparse
from html import escape
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
W, H = 1200, 1080
INK, MUTED, LINE = '#173042', '#4d6372', '#6a7f8d'
BLUE, TEAL, GOLD = '#eaf2f8', '#e8f4f0', '#fff2db'
parts = []


def rect(x, y, w, h, fill, stroke='#c4d0d8', radius=10):
    assert 0 <= x <= W-w and 0 <= y <= H-h
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>')


def text(x, y, lines, size=20, bold=False, color=INK, anchor='start', gap=27):
    if isinstance(lines, str):
        lines = [lines]
    for i, line in enumerate(lines):
        assert 0 <= x <= W and 0 <= y+i*gap <= H
        parts.append(f'<text x="{x}" y="{y+i*gap}" font-size="{size}" font-weight="{"bold" if bold else "normal"}" fill="{color}" text-anchor="{anchor}">{escape(line)}</text>')


def arrow(points, color=LINE, dashed=False):
    assert len(points) >= 2
    for x, y in points:
        assert 0 <= x <= W and 0 <= y <= H
    points_str = ' '.join(f'{x},{y}' for x, y in points)
    dash = ' stroke-dasharray="6 5"' if dashed else ''
    parts.append(f'<polyline points="{points_str}" fill="none" stroke="{color}" stroke-width="2"{dash}/>')
    (ax, ay), (bx, by) = points[-2:]
    dx, dy = bx-ax, by-ay
    length = (dx*dx+dy*dy)**0.5
    assert length > 0
    ux, uy = dx/length, dy/length
    triangle = f'{bx},{by} {bx-9*ux+4*uy},{by-9*uy-4*ux} {bx-9*ux-4*uy},{by-9*uy+4*ux}'
    parts.append(f'<polygon points="{triangle}" fill="{color}"/>')


def panel(letter, title, top, height):
    rect(16, top, 1168, height, '#ffffff', '#ccd7dd', 12)
    text(35, top+32, letter, 26, True)
    text(72, top+32, title, 23, True)


def build():
    parts.clear()
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">')
    parts.append('<title id="title">Scientist-directed collaboration architecture</title><desc id="desc">Three panels show an iterative research workflow, scientist control through host agents and durable project records, and an optional two-round independent review process. The workflow is instructional and host-mediated, not an automated research service.</desc>')
    parts.append('<g font-family="Helvetica, Arial, sans-serif">')
    rect(0, 0, W, H, '#ffffff', '#ffffff', 0)
    panel('a', 'Research cycle directed by the scientist', 12, 290)
    text(36, 78, 'The scientist sets the question, methods, acceptance criteria, and next decision.', 20)
    nodes = [
        ('Inspect evidence', ['Literature and', 'source records'], BLUE),
        ('Compare ideas', ['Alternatives and', 'predictions'], BLUE),
        ('Agree a plan', ['Controls, endpoint,', 'replication'], GOLD),
        ('Run experiment', ['Scientist performs', 'the experiment'], TEAL),
        ('Interpret results', ['Analysis linked to', 'primary records'], BLUE),
        ('Update context', ['Current view and', 'next question'], BLUE),
    ]
    for i, (title, lines, fill) in enumerate(nodes):
        x = 36 + i*190
        rect(x, 105, 177, 116, fill)
        text(x+88.5, 135, title, 18, True, anchor='middle')
        text(x+88.5, 167, lines, 17, anchor='middle', gap=25)
        if i < len(nodes)-1:
            arrow([(x+177, 163), (x+190, 163)])
    arrow([(1074, 222), (1074, 269), (124, 269), (124, 222)])
    rect(364, 251, 470, 35, '#ffffff', '#ffffff', 0)
    text(599, 275, 'New evidence informs the next question', 19, anchor='middle')

    panel('b', 'Scientist control, host execution, and persistent records', 318, 414)
    # Colors denote ownership/function; every card also has a textual label.
    rect(36, 383, 290, 232, GOLD)
    text(54, 414, 'SCIENTIST', 18, True)
    text(54, 451, ['Scientific choices', 'Methods and evidence standards', 'Outputs and review preferences', 'Models, permissions, spending'], 18, gap=32)
    text(54, 598, 'Recorded in collaboration.md', 17, color=MUTED)

    rect(431, 383, 318, 232, BLUE)
    text(449, 414, 'HOST: CODEX / CLAUDE CODE', 18, True)
    text(449, 450, ['Conversation and reasoning', 'Project skills: instructions', 'Utilities: executable code', 'Available tools and permissions'], 18, gap=32)
    text(449, 598, 'Reads files and performs tasks', 17, color=MUTED)

    rect(854, 383, 310, 232, TEAL)
    text(872, 414, 'DURABLE PROJECT FILES', 18, True)
    text(872, 450, ['Preferences and decisions', 'Current view and task log', 'Evidence and primary records', 'Analyses and review records'], 18, gap=32)
    text(872, 598, 'Context links to detailed evidence', 17, color=MUTED)
    arrow([(326, 482), (431, 482)])
    text(378, 465, 'directs', 16, anchor='middle')
    arrow([(749, 471), (854, 471)])
    text(801, 431, ['writes', 'outputs'], 16, anchor='middle', gap=20)
    arrow([(854, 540), (749, 540)])
    text(801, 565, 'reads', 16, anchor='middle')
    rect(36, 639, 1128, 70, '#f6f8fa')
    text(54, 667, 'EXTEND THE PROJECT', 17, True)
    text(54, 692, 'Describe a task → add or adapt a skill/tool → check its behavior → register inputs, assumptions, and use', 18)

    panel('c', 'Independent review on request', 748, 287)
    text(36, 811, 'Scientist selects scope, depth, and models; the host provides separate reviewer contexts.', 19)
    rect(36, 836, 353, 112, BLUE)
    text(54, 865, 'THREE INDEPENDENT LENSES', 17, True)
    text(54, 895, ['Evidence • Methods • Interpretation', 'Each reviewer works separately'], 18, gap=27)
    rect(434, 836, 324, 112, GOLD)
    text(452, 865, 'EDITORIAL DECISION', 17, True)
    text(452, 895, ['Accept, partly accept, or decline', 'Record evidence and rationale'], 18, gap=27)
    rect(803, 836, 361, 112, TEAL)
    text(821, 865, 'REVISION AND RESPONSE', 17, True)
    text(821, 895, ['Apply and verify accepted changes', 'Preserve the response ledger'], 18, gap=27)
    arrow([(389, 891), (434, 891)])
    arrow([(758, 891), (803, 891)])
    arrow([(983, 949), (983, 999), (212, 999), (212, 949)], dashed=True)
    rect(310, 979, 580, 35, '#ffffff', '#ffffff', 0)
    text(600, 1003, 'Round 2: new independent reviewers reassess the revision', 18, anchor='middle')
    text(600, 1066, 'Arrows describe agent-followed procedures.', 17, color=MUTED, anchor='middle')
    parts.append('</g></svg>')
    svg = '\n'.join(parts)+'\n'
    root = ET.fromstring(svg)
    assert root.attrib['viewBox'] == f'0 0 {W} {H}'
    assert len(root.findall('.//{http://www.w3.org/2000/svg}text')) >= 50
    assert 'Run experiment' in svg and 'Independent review on request' in svg
    return svg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render', action='store_true', help='Also render PDF and 200-dpi PNG; requires figure dependencies and pdftoppm')
    args = parser.parse_args()
    if args.render:
        from reportlab import rl_config
        from reportlab.graphics import renderPDF
        from svglib.svglib import svg2rlg
        if not shutil.which('pdftoppm'):
            parser.error('--render requires pdftoppm from Poppler')
        rl_config.invariant = 1
    svg_path = OUT / 'architecture.svg'
    svg_path.write_text(build(), encoding='utf-8')
    if args.render:
        drawing = svg2rlg(str(svg_path))
        assert drawing is not None and (drawing.width, drawing.height) == (W, H)
        # Scale to a 183 mm double-column figure, preserving editable vector text.
        scale = (183/25.4*72)/W
        drawing.scale(scale, scale)
        drawing.width *= scale
        drawing.height *= scale
        pdf_path = OUT / 'architecture.pdf'
        renderPDF.drawToFile(drawing, str(pdf_path), title='Scientist-directed collaboration architecture')
        subprocess.run(['pdftoppm', '-singlefile', '-r', '200', '-png', str(pdf_path), str(OUT/'architecture')], check=True)
        assert pdf_path.read_bytes().startswith(b'%PDF-')
        assert (OUT/'architecture.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    print('Wrote architecture.svg' + (', architecture.pdf, architecture.png' if args.render else ''))


if __name__ == '__main__':
    main()
