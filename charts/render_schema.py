"""Render the Mermaid TPC-H schema to PNG and SVG on white.

Requires dbt-charts 0.8.0 and @mermaid-js/mermaid-cli 12.0.0 (mmdc on PATH).
Set PUPPETEER_EXECUTABLE_PATH to use an existing Chrome installation.
"""
from pathlib import Path
from importlib.resources import files
import base64
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent


def render():
    mmdc = shutil.which('mmdc')
    if not mmdc:
        raise SystemExit('Install @mermaid-js/mermaid-cli@12.0.0 and put mmdc on PATH.')
    fonts = files('dbt_charts').joinpath('core/render/fonts')
    css = []
    for family, filename, weight in [
        ('Inter Variable', 'InterVariable.woff2', '100 900'),
        ('dbt Sans Tabular', 'DBTSansTabular-Regular.woff2', '400'),
    ]:
        data = base64.b64encode(fonts.joinpath(filename).read_bytes()).decode()
        css.append(f'@font-face {{font-family: "{family}"; font-weight: {weight}; '
                   f'src: url(data:font/woff2;base64,{data}) format("woff2");}}')
    css.append('''
        svg, text, .label, .nodeLabel {
            font-family: "Inter Variable", sans-serif !important;
        }
        foreignObject {overflow: visible !important;}
        .flowchartTitleText {
            font-family: "Inter Variable", sans-serif !important;
            font-weight: 600 !important; fill: #313233 !important;
        }
        .nodeLabel tspan:nth-child(n+2) {
            font-family: "dbt Sans Tabular", sans-serif !important;
        }
        .node rect, .node polygon, .node path {filter: none !important;}
    ''')
    with tempfile.TemporaryDirectory(prefix='tpch-mermaid-') as temp:
        stylesheet = Path(temp) / 'fonts.css'
        stylesheet.write_text('\n'.join(css))
        svg = ROOT / 'tpch_schema.svg'
        subprocess.run([
            mmdc, '--input', str(ROOT / 'tpch_schema.mmd'),
            '--output', str(svg), '--backgroundColor', 'white',
            '--cssFile', str(stylesheet), '--no-font-embed', '--size', '1400',
        ], check=True)
        # Mermaid's CSS compiler drops @font-face rules. Embed them afterward,
        # then rasterize this exact SVG so PNG and SVG use identical fonts.
        import re
        source = svg.read_text()
        # Preserve XHTML label namespaces; remove unused Mermaid effect defs.
        for tag in ('linearGradient', 'radialGradient', 'filter'):
            source = re.sub(rf'<{tag}\b[^>]*>.*?</{tag}>', '', source, flags=re.S)
        source = source.replace('</svg>', '<style>' + '\n'.join(css[:2]) + '</style></svg>')
        svg.write_text(source)
        rasterizer = r"""
const fs = require('node:fs');
const { createRequire } = require('node:module');
const puppeteer = createRequire(process.argv[1])('puppeteer');
(async () => {
  const browser = await puppeteer.launch({headless: true,
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined});
  try {
    const page = await browser.newPage();
    await page.setViewport({width: 1440, height: 1800, deviceScaleFactor: 2});
    await page.setContent('<style>body{margin:0;background:white}svg{display:block}</style>' +
      fs.readFileSync(process.argv[2], 'utf8'));
    await page.evaluate(() => document.fonts.ready);
    const svg = await page.$('svg');
    await svg.screenshot({path: process.argv[3]});
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exit(1); });
"""
        png = ROOT / 'tpch_schema.png'
        subprocess.run(['node', '-e', rasterizer, str(Path(mmdc).resolve()),
                        str(svg), str(png)], check=True)
        print(svg)
        print(png)


if __name__ == '__main__':
    render()
