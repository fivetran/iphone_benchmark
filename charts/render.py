"""Validate final result coverage and regenerate both dbt Charts PNGs."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import duckdb

ROOT=Path(__file__).resolve().parent.parent
SCALES={25,50,100,200}
EXPECTED={(sf,q,rep) for sf in SCALES for q in range(1,23) for rep in (1,2)}
def validate(path):
    with duckdb.connect(str(path),read_only=True) as c:
        queries=c.execute('SELECT * FROM queries').fetchall()
        assert len(queries)==22 and {r[0] for r in queries}==set(range(1,23))
        hashes={q:sha for q,sql,sha in queries}
        assert all(hashlib.sha256(sql.encode()).hexdigest()==sha for q,sql,sha in queries)
        rows=c.execute('SELECT scale_factor,query,repeat,wall_seconds,details FROM iphone_measurements JOIN iphone_runs USING(run_id)').fetchall()
        assert len(rows)==176 and {r[:3] for r in rows}==EXPECTED
        for sf,q,rep,seconds,details in rows:
            d=json.loads(details)
            assert math.isfinite(seconds) and seconds>0
            assert d['query_sha256']==hashes[q]
            assert d['memory_before']['thermal_state']==0
        for size in ['medium','small','xsmall']:
            rows=c.execute('SELECT scale_factor,query,repeat,server_total_seconds,details FROM databricks_measurements WHERE size=?',[size]).fetchall()
            assert len(rows)==176 and {r[:3] for r in rows}==EXPECTED
            for sf,q,rep,seconds,details in rows:
                d=json.loads(details); metrics=d['history']['metrics']
                assert not metrics.get('result_from_cache')
                assert d['query_sha256']==hashes[q]
                assert math.isfinite(seconds) and seconds>0
                assert seconds==metrics['total_time_ms']/1000
        rows=c.execute('SELECT scale_factor,query,repeat,bytes_read,profile FROM mac_scans').fetchall()
        assert len(rows)==176 and {r[:3] for r in rows}==EXPECTED
        assert all(n>=2**20 and n==json.loads(p)['total_bytes_read'] for sf,q,r,n,p in rows)
        totals=dict(c.execute('SELECT warehouse,sum(query_count) FROM published_bins GROUP BY warehouse').fetchall())
        assert totals=={'Snowflake':17184788,'Redshift':63276038}
        assert c.execute('SELECT count(*) FROM timing_summary').fetchone()[0]==16
        assert c.execute('SELECT count(*) FROM histogram').fetchone()[0]==42
        assert all(math.isclose(v,1) for _,v in c.execute('SELECT series,sum(query_fraction) FROM histogram GROUP BY series').fetchall())
        for row in c.execute('SELECT * FROM timing_summary ORDER BY scale_factor,engine').fetchall(): print(row)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',type=Path,default=ROOT/'results/results.duckdb')
    p.add_argument('--output',type=Path,default=ROOT/'charts')
    args=p.parse_args(); db=args.database.resolve(); output=args.output.resolve()
    validate(db)
    dct=shutil.which('dct')
    if not dct: raise SystemExit('Install dbt-charts==0.8.0 with uv tool install first')
    assert subprocess.check_output([dct,'--version'],text=True).startswith('dct 0.8.0 ')
    output.mkdir(parents=True,exist_ok=True)
    # Temporary config supports alternate result databases without editing tracked files.
    with tempfile.TemporaryDirectory(prefix='tpch-charts-') as temp:
        project=Path(temp)
        config={'sources':{name:{'type':'duckdb','path':str(db)} for name in ['benchmark','scan_volumes']}}
        (project/'dbt_charts.yml').write_text(json.dumps(config))
        for name in ['timing','scans']:
            shutil.copy2(ROOT/'charts'/f'{name}.yml',project/f'{name}.yml')
            subprocess.run([dct,'validate',f'{name}.yml'],cwd=project,check=True)
            target=output/f'{name}.png'
            subprocess.run([dct,'render',f'{name}.yml','--format','png','--no-cache','--output',str(target)],cwd=project,check=True)
            assert target.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
            print(target)
if __name__=='__main__': main()
