"""Render the cost frontier and service comparisons without rebuilding data."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent

def render():
    dct = shutil.which('dct')
    if not dct:
        raise SystemExit('Install dbt-charts==0.8.0: uv tool install --python 3.12 dbt-charts==0.8.0')
    version = subprocess.check_output([dct, '--version'], text=True)
    assert version.startswith('dct 0.8.0 '), version
    for name in ['compute_cost', 'service_cost']:
        subprocess.run([dct, 'validate', f'{name}.yml'], cwd=ROOT/'charts', check=True)
        for format in ['png', 'svg']:
            subprocess.run([dct, 'render', f'{name}.yml', '--format', format, '--no-cache',
                            '--output', str(ROOT/'charts'/f'{name}.{format}')],
                           cwd=ROOT/'charts', check=True)
        assert (ROOT/'charts'/f'{name}.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')

if __name__ == '__main__':
    render()
