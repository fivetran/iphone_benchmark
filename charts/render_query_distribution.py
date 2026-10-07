"""Render whole queries assigned to individual nodes, using dbt Charts vivid colors.

uv run --python 3.12 --with dbt-charts==0.8.0 --with playwright==1.56.0 python charts/render_query_distribution.py
Requires Google Chrome, or PUPPETEER_EXECUTABLE_PATH pointing to Chromium.
"""

from importlib.resources import files
import os
from pathlib import Path

from playwright.sync_api import sync_playwright
import yaml


ROOT = Path(__file__).resolve().parent
SCALE = 0.85
WIDTH, HEIGHT = round(1200 * SCALE), round(740 * SCALE)


def query_card(x, y, color, waiting=False):
    """A document glyph distinguishes a complete query from a table partition."""
    status = (f'<path d="M {x + 114} {y + 66} v 14 M {x + 125} {y + 66} v 14" '
              f'stroke="{color}" stroke-width="3"/>' if waiting else
              f'<path d="M {x + 115} {y + 65} l 13 8 l -13 8 Z" fill="{color}"/>')
    return f'''<path d="M {x} {y} h 100 l 20 20 v 56 h -120 Z" fill="{color}"/>
      <path d="M {x + 100} {y} v 20 h 20" fill="white" fill-opacity="0.35"/>
      <path d="M {x + 18} {y + 30} h 55 M {x + 18} {y + 43} h 84
        M {x + 18} {y + 56} h 66" fill="none" stroke="white"
        stroke-opacity="0.65" stroke-width="3"/>
      <circle cx="{x + 120}" cy="{y + 73}" r="19" fill="white" stroke="{color}" stroke-width="2"/>
      {status}'''


def diagram():
    palette = yaml.safe_load(files('dbt_charts').joinpath(
        'core/defaults/palettes/categorical/vivid-10.yml').read_text())
    blue, gray = (palette['colors'][i] for i in (0, 8))
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}"
      viewBox="0 0 1200 740" role="img" aria-labelledby="title description">
      <title id="title">Queries distributed across nodes</title>
      <desc id="description">Five users across the top each submit one query.
        Three compute nodes along the bottom each process exactly one query,
        shown inside the node with a play symbol. Two additional queries wait
        outside the left and right nodes, marked with pause symbols and dashed
        arrows into their assigned nodes. Each query belongs to only one node.</desc>
      <style>path, rect, circle {{ vector-effect: non-scaling-stroke; }}</style>
      <rect width="1200" height="740" fill="white"/>
      <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
          markerWidth="{10 / SCALE}" markerHeight="{10 / SCALE}" markerUnits="userSpaceOnUse"
          orient="auto"><path d="M 0 0 L 10 5 L 0 10 Z" fill="{blue}"/></marker></defs>''']

    for x in (140, 370, 600, 830, 1060):
        parts.append(f'''<circle cx="{x}" cy="82" r="24" fill="{gray}"/>
          <path d="M {x - 42} 147 v -7 C {x - 42} 101 {x + 42} 101 {x + 42} 140
            v 7 Z" fill="{gray}"/>''')

    # One occupied execution slot in each node; only the outer nodes have queues.
    for center in (215, 600, 985):
        parts.append(f'<rect x="{center - 150}" y="510" width="300" height="170" '
                     f'rx="8" fill="white" stroke="{gray}" stroke-width="2"/>')
        parts.append(query_card(center - 60, 557, blue))

    # Every user has one outgoing submission path to their single destination.
    for path in [
        'M 140 164 L 140 502',
        'M 370 164 C 370 245 310 245 310 328',
        'M 600 164 L 600 502',
        'M 830 164 C 830 245 890 245 890 328',
        'M 1060 164 L 1060 502',
    ]:
        parts.append(f'<path d="{path}" fill="none" stroke="{blue}" '
                     'stroke-width="3.5" marker-end="url(#arrow)"/>')

    for center in (310, 890):
        parts.append(query_card(center - 60, 340, blue, waiting=True))
        parts.append(f'<path d="M {center} 430 L {center} 502" fill="none" '
                     f'stroke="{blue}" stroke-width="3.5" stroke-dasharray="7 7" '
                     'marker-end="url(#arrow)"/>')
    parts.append('</svg>')
    return '\n'.join(parts)


def render():
    svg = ROOT / 'query_distribution.svg'
    png = ROOT / 'query_distribution.png'
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
