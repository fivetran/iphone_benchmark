"""Render the conceptual open data lake diagram in dbt Charts' vivid palette.

uv run --python 3.12 --with dbt-charts==0.8.0 --with playwright==1.56.0 python charts/render_open_data_lake.py
Requires Google Chrome, or PUPPETEER_EXECUTABLE_PATH pointing to Chromium.
"""

import base64
from html import escape
from importlib.resources import files
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright
import yaml


ROOT = Path(__file__).resolve().parent
SCALE = 0.85
WIDTH, HEIGHT = round(1400 * SCALE), round(1000 * SCALE)

def brand_icon(name, x, y, color, size=72):
    asset = json.loads((ROOT / 'open_data_lake_icons.json').read_text())[name]
    paths = ''.join('<path ' + ' '.join(f'{key}="{escape(value, quote=True)}"'
                    for key, value in path.items()) + '/>' for path in asset['paths'])
    return (f'<svg x="{x - size / 2}" y="{y - size / 2}" width="{size}" height="{size}" '
            f'viewBox="{asset["viewBox"]}" fill="{color}"><title>{escape(name)}</title>{paths}</svg>')


def diagram():
    package = files('dbt_charts')
    palette = yaml.safe_load(package.joinpath(
        'core/defaults/palettes/categorical/vivid-10.yml').read_text())
    blue, gray = (palette['colors'][i] for i in (0, 9))
    font = base64.b64encode(package.joinpath(
        'core/render/fonts/InterVariable.woff2').read_bytes()).decode()
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}"
      viewBox="0 0 1400 1000" role="img" aria-labelledby="title description">
      <title id="title">Open data lake</title>
      <desc id="description">Iceberg tables at the center of an open data lake.
        Six labeled icon clusters connect directly to the lake: compute engines
        (Snowflake, BigQuery, Databricks), connectors (Fivetran), notebooks (a notebook),
        AI agents (ChatGPT and Claude), BI tools (a chart and Hex), and local compute
        (a laptop). Conceptual architecture; adapters and execution engines
        are abstracted.</desc>
      <style>
        @font-face {{font-family: Inter; font-weight: 100 900;
          src: url(data:font/woff2;base64,{font}) format('woff2');}}
        text {{font-family: Inter, sans-serif; text-anchor: middle; fill: #313233;}}
        path, rect {{vector-effect: non-scaling-stroke;}}
      </style>
      <rect width="1400" height="1000" fill="white"/>
      <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
        markerWidth="{10 / SCALE}" markerHeight="{10 / SCALE}" markerUnits="userSpaceOnUse"
        orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 Z" fill="{blue}"/></marker></defs>''']

    for path in [
        'M 590 187 L 590 357', 'M 700 187 L 700 357', 'M 810 187 L 810 357',
        'M 250 320 L 502 430', 'M 1150 320 L 898 430',
        'M 198 660 L 502 535', 'M 306 684 L 502 580',
        'M 1140 680 L 898 555',
        'M 590 633 C 540 710 540 860 594 860',
        'M 810 633 C 860 710 860 860 806 860',
    ]:
        parts.append(f'<path d="{path}" fill="none" '
                     f'stroke="{blue}" stroke-width="3" marker-start="url(#arrow)" '
                     'marker-end="url(#arrow)"/>')
    for x, y, label in [
        (700, 78, 'Compute engines'), (200, 240, 'Connectors'),
        (1200, 240, 'Notebooks'), (200, 618, 'BI tools'),
        (1200, 618, 'Local compute'), (700, 792, 'AI agents'),
    ]:
        parts.append(f'<text x="{x}" y="{y}" font-size="26" '
                     f'font-weight="500">{escape(label)}</text>')
    for name, x, y in [
        ('snowflake', 590, 140), ('googlebigquery', 700, 140),
        ('databricks', 810, 140), ('fivetran', 200, 308),
        ('hex', 260, 684), ('openai', 640, 860), ('claude', 760, 860),
    ]:
        parts.append(brand_icon(name, x, y, gray))

    # Generic chart, notebook, and laptop glyphs use the same monochrome ink.
    parts.append(f'''<g fill="none" stroke="{gray}" stroke-width="3.5" stroke-linejoin="round">
      <path d="M 90 649 V 719 H 188"/>
      <path d="M 108 704 V 684 H 122 V 704 Z M 137 704 V 666 H 151 V 704 Z
        M 166 704 V 645 H 180 V 704 Z" fill="{gray}" stroke="none"/>
      <rect x="1170" y="272" width="60" height="72" rx="4"/>
      <path d="M 1182 272 V 344 M 1164 284 H 1176 M 1164 300 H 1176
        M 1164 316 H 1176 M 1164 332 H 1176 M 1192 290 H 1220
        M 1192 304 H 1220 M 1192 318 H 1212"/>
      <rect x="1156" y="648" width="88" height="58" rx="4"/>
      <path d="M 1156 706 L 1145 721 H 1255 L 1244 706 M 1188 713 H 1212"/>
      </g>''')

    parts.append(f'''<rect x="510" y="365" width="380" height="260" rx="12" fill="{blue}"/>
      <text x="700" y="427" font-size="28" font-weight="600" style="fill:white">Open data lake</text>''')
    for x in (561, 659, 757):
        parts.append(f'''<rect x="{x}" y="479" width="82" height="70" rx="3"
          fill="none" stroke="white" stroke-width="2"/>
          <path d="M {x} 501 h 82 M {x} 525 h 82 M {x + 27} 501 v 48
            M {x + 55} 501 v 48" fill="none" stroke="white" stroke-width="2"/>
          <rect x="{x + 1}" y="480" width="80" height="20" fill="white" fill-opacity="0.25"/>''')
    parts.append('</svg>')
    return '\n'.join(parts)


def render():
    svg = ROOT / 'open_data_lake.svg'
    png = ROOT / 'open_data_lake.png'
    svg.write_text(diagram())
    with sync_playwright() as playwright:
        executable = os.environ.get('PUPPETEER_EXECUTABLE_PATH')
        options = {'executable_path': executable} if executable else {'channel': 'chrome'}
        browser = playwright.chromium.launch(**options)
        try:
            page = browser.new_page(viewport={'width': WIDTH, 'height': HEIGHT}, device_scale_factor=2)
            page.set_content('<style>body{margin:0}svg{display:block}</style>' + svg.read_text())
            page.evaluate('document.fonts.ready')
            page.locator('body > svg').screenshot(path=str(png))
        finally:
            browser.close()
    print(svg)
    print(png)


if __name__ == '__main__':
    render()
