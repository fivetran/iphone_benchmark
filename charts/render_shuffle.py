"""Render the label-free shuffle diagram with dbt Charts vivid colors.

uv run --python 3.12 --with dbt-charts==0.8.0 --with playwright==1.56.0 python charts/render_shuffle.py
Requires Google Chrome, or PUPPETEER_EXECUTABLE_PATH pointing to Chromium.
"""

from importlib.resources import files
import os
from pathlib import Path

from playwright.sync_api import sync_playwright
import yaml


ROOT = Path(__file__).resolve().parent
SCALE = 0.85
WIDTH, HEIGHT = round(1200 * SCALE), round(700 * SCALE)


def diagram():
    package = files('dbt_charts')
    palette = yaml.safe_load(package.joinpath(
        'core/defaults/palettes/categorical/vivid-10.yml').read_text())
    blue, orange = (palette['colors'][i] for i in (0, 4))
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}"
        viewBox="0 140 1200 700" role="img" aria-labelledby="title description">
      <title id="title">Shuffle</title>
      <desc id="description">Three nodes each contain partitions of Table A in blue
        and Table B in orange. Matching colored arrows between every pair of nodes
        show data exchanged in both directions to colocate matching join keys.</desc>
      <style>path, rect {{ vector-effect: non-scaling-stroke; }}</style>
      <rect width="1200" height="880" fill="white"/>
      <defs>''']
    for name, color in [('a', blue), ('b', orange)]:
        parts.append(f'''<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5"
          markerWidth="{10 / SCALE}" markerHeight="{10 / SCALE}" markerUnits="userSpaceOnUse"
          orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 Z" fill="{color}"/></marker>''')
    parts.append('</defs>')

    # Each pair has one bidirectional path per table. The paths terminate at
    # node boundaries; color identifies the table whose partitions they carry.
    for name, color, paths in [
        ('a', blue, [
            'M 405 268 L 795 268',
            'M 240 395 C 240 490 395 475 425 663',
            'M 960 395 C 960 490 805 475 775 663',
        ]),
        ('b', orange, [
            'M 405 328 L 795 328',
            'M 320 395 C 320 460 450 465 475 585',
            'M 880 395 C 880 460 750 465 725 585',
        ]),
    ]:
        for path in paths:
            parts.append(f'<path d="{path}" fill="none" stroke="{color}" '
                         f'stroke-width="3.5" marker-start="url(#{name})" '
                         f'marker-end="url(#{name})"/>')

    for x, y in [(60, 185), (800, 185), (430, 590)]:
        parts.append(f'<rect x="{x}" y="{y}" width="340" height="205" '
                     'rx="8" fill="white" stroke="#949daa" stroke-width="2"/>')
        for color, offset in [(blue, 24), (orange, 182)]:
            tx, ty = x + offset, y + 44.5
            parts.append(f'<rect x="{tx}" y="{ty}" width="134" height="116" rx="3" fill="{color}"/>')
            for row in range(2):
                parts.append(f'<path d="M {tx + 16} {ty + 52 + row * 12} h 102" '
                             'stroke="white" stroke-opacity="0.45" stroke-width="3"/>')
    parts.append('</svg>')
    return '\n'.join(parts)


def render():
    svg = ROOT / 'shuffle.svg'
    png = ROOT / 'shuffle.png'
    svg.write_text(diagram())
    with sync_playwright() as playwright:
        executable = os.environ.get('PUPPETEER_EXECUTABLE_PATH')
        options = {'executable_path': executable} if executable else {'channel': 'chrome'}
        browser = playwright.chromium.launch(**options)
        try:
            page = browser.new_page(viewport={'width': WIDTH, 'height': HEIGHT}, device_scale_factor=2)
            page.set_content('<style>body{margin:0}svg{display:block}</style>' + svg.read_text())
            page.locator('svg').screenshot(path=str(png))
        finally:
            browser.close()
    print(svg)
    print(png)


if __name__ == '__main__':
    render()
