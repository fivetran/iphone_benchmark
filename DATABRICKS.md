# Reproduce Databricks serverless SQL

This is the final M, S, and XS comparison at TPC-H scale factors **200, 100, 50, 25**, in that order. Each scale runs queries 1–22 serially, twice consecutively per query, with a fresh SQL connection for each execution. Use the exact SQL and schema retained in [results/results.duckdb](results/results.duckdb). The queries are DuckDB 1.5.6 TPC-H templates, including Q11's fixed constant; this is a comparative workload, not an audited TPC-H result.

The chart uses **Databricks server total time**, `QueryMetrics.total_time_ms / 1000`, including compilation and server-side overhead and excluding client/network elapsed time. First average each query's two measurements, then take the geometric mean of the 22 query averages. Do not substitute execution-only time or summed task CPU time.

## Environment and setup

Use a Mac with Python 3.13, `uv`, and at least 200 GB free for database generation, staging and spill. The retained compressed databases were about 6.8, 13.7, 27.7 and 55.4 GB; scale factor is nominal uncompressed TPC-H GB, not file size. No other benchmark or data generation should run concurrently with measurements.

Pinned Python packages: DuckDB **1.5.6**, Databricks SDK **0.143.0**, SQL connector **4.6.0**, PyArrow **25.0.1**. The original service ran the current serverless release channel; recorded query histories contain the actual runtime versions. Databricks controls that runtime, so a later rerun cannot guarantee the identical service build.

From this folder, extract the `file=` code blocks from all three guides. They are the complete reproduction source; generated files and large data live under `.work/`.

```sh
python3 - <<'PYCODE'
from pathlib import Path
import re
root = Path.cwd()
assert (root / 'results/results.duckdb').is_file()
for name in ['DATABRICKS.md', 'IPHONE.md', 'CHARTS.md']:
    for path, code in re.findall(r'^```\w+ file=(\S+)\n(.*?)^```$', (root/name).read_text(), re.M | re.S):
        dest = (root/path).resolve()
        assert dest.is_relative_to(root/'.work')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code)
print('Extracted reproduction code into .work/')
PYCODE

uv venv --python 3.13 .work/.venv
uv pip install --python .work/.venv/bin/python duckdb==1.5.6 databricks-sdk==0.143.0 databricks-sql-connector==4.6.0 pyarrow==25.0.1
.work/.venv/bin/python .work/benchmark.py
```

The bootstrap verifies the retained SQL hashes, writes the 22 statements and schema, and exports the saved reference result sets. Use these statements without dialect rewrites or scale-dependent substitutions.

```python file=.work/benchmark.py
from pathlib import Path
import hashlib,json
import duckdb
ROOT=Path(__file__).resolve().parent
TABLES=['region','nation','supplier','customer','part','partsupp','orders','lineitem']
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,indent=2,default=str)+'\n')
    tmp.replace(path)
if __name__=='__main__':
    assert duckdb.__version__=='1.5.6'
    (ROOT/'data').mkdir(exist_ok=True)
    (ROOT/'queries').mkdir(exist_ok=True)
    with duckdb.connect(str(ROOT.parent/'results/results.duckdb'),read_only=True) as c:
        for q,sql,sha in c.execute('SELECT * FROM queries ORDER BY query').fetchall():
            assert hashlib.sha256(sql.encode()).hexdigest()==sha
            (ROOT/'queries'/f'q{q:02}.sql').write_text(sql)
        schema=json.loads(c.execute("SELECT details FROM provenance WHERE name='schema_sql'").fetchone()[0])['sql']
        (ROOT/'schema.sql').write_text(schema)
        for sf in [200,100,50,25]:
            refs={str(q):json.loads(result) for q,result in c.execute('SELECT query,result FROM reference_results WHERE scale_factor=?',[sf]).fetchall()}
            save(ROOT/'reference'/f'sf{sf}.json',refs)
```

## Generate the identical workload in DuckDB

Generate each scale as eight independent `dbgen(sf=SF, children=8, step=i)` shards (one thread and 2 GB per worker). Merge the shards in child order into an empty `dbgen(sf=0)` schema using eight threads and 8 GB. Do not replace this with a single different generation/merge scheme: row placement can affect the scan workload. The script verifies all table counts and every column's order, type and nullability against the retained metadata. It deletes shards only after validation. Database storage bytes/hashes may differ after regeneration; hash the new file and transfer that exact file to the phone.

```sh
for sf in 200 100 50 25; do
  .work/.venv/bin/python .work/generate_sharded.py --sf "$sf" --workers 8
done
```

```python file=.work/generate_sharded.py
"""Generate a large TPC-H database using dbgen's disjoint child ranges.

Workers are independent Python processes, not concurrent connections to one file.
Merge completed shards in child order into a native DuckDB file. No rows are
sampled, duplicated, or rescaled. Shards are deleted only after final validation.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import time

import duckdb

from benchmark import ROOT, TABLES, save


def generate_child(sf, workers, step, directory):
    path = Path(directory) / f'part{step}.duckdb'
    meta = path.with_suffix('.json')
    if path.exists() and meta.exists():
        return json.loads(meta.read_text())
    building = path.with_suffix('.building.duckdb')
    if building.exists():
        raise RuntimeError(f'Incomplete shard exists: {building}')
    started = time.perf_counter()
    with duckdb.connect(str(building), config={'threads': 1, 'memory_limit': '2GB'}) as c:
        c.execute('LOAD tpch')
        c.execute(f'CALL dbgen(sf={sf}, children={workers}, step={step})')
        c.execute('CHECKPOINT')
        counts = {t: c.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in TABLES}
    building.rename(path)
    result = {'step': step, 'table_rows': counts, 'bytes': path.stat().st_size,
              'seconds': time.perf_counter() - started}
    save(meta, result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sf', type=float, required=True)
    p.add_argument('--workers', type=int, default=8)
    args = p.parse_args()
    if args.sf <= 0 or (args.sf >= 1 and not args.sf.is_integer()) or args.workers < 1:
        p.error('Use a positive valid scale and positive worker count')
    label = f'{args.sf:g}'
    db = ROOT / 'data' / f'tpch_sf{label}.duckdb'
    meta_path = ROOT / 'results' / f'sf{label}' / 'metadata.json'
    if db.exists():
        p.error(f'Database already exists: {db}')
    shards = ROOT / 'data' / f'.shards_sf{label}'
    shards.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with duckdb.connect() as c:
        c.execute('INSTALL tpch')
    child_meta = []
    print(f'SF{label}: generating {args.workers} disjoint ranges', flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(generate_child, args.sf, args.workers, i, str(shards)) for i in range(args.workers)]
        for future in as_completed(futures):
            m = future.result()
            child_meta.append(m)
            print(f'Child {m["step"]} done: {m["bytes"]/2**30:.2f} GiB, {m["seconds"]:.1f}s', flush=True)
    expected = {t: sum(m['table_rows'][t] for m in child_meta) for t in TABLES}
    assert expected['orders'] == round(1_500_000 * args.sf)
    assert expected['nation'] == 25 and expected['region'] == 5
    building = db.with_suffix('.building.duckdb')
    if building.exists():
        raise RuntimeError(f'Incomplete merge exists: {building}')
    with duckdb.connect(str(building), config={'threads': 8, 'memory_limit': '8GB'}) as c:
        c.execute('LOAD tpch; CALL dbgen(sf=0)')
        for i in range(args.workers):
            part = shards / f'part{i}.duckdb'
            escaped = str(part).replace("'", "''")
            c.execute(f"ATTACH '{escaped}' AS child (READ_ONLY)")
            for t in TABLES:
                c.execute(f'INSERT INTO main.{t} SELECT * FROM child.main.{t}')
            c.execute('CHECKPOINT; DETACH child')
            print(f'Merged child {i+1}/{args.workers}', flush=True)
        counts = {t: c.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in TABLES}
    assert counts == expected
    with duckdb.connect(str(ROOT.parent/'results/results.duckdb'),read_only=True) as saved, duckdb.connect(str(building),read_only=True) as actual:
        for table in TABLES:
            want=saved.execute('SELECT column_name,data_type,is_nullable FROM table_columns WHERE table_name=? ORDER BY ordinal_position',[table]).fetchall()
            got=actual.execute('SELECT column_name,data_type,is_nullable FROM information_schema.columns WHERE table_name=? ORDER BY ordinal_position',[table]).fetchall()
            assert got == want, table
        old_counts=json.loads(saved.execute('SELECT generation FROM datasets WHERE scale_factor=?',[args.sf]).fetchone()[0])['table_rows']
        assert counts == old_counts
    building.rename(db)
    save(meta_path, {'scale_factor': args.sf, 'generation_seconds': time.perf_counter() - started,
                     'table_rows': counts, 'database_bytes': db.stat().st_size,
                     'generation_duckdb_version': duckdb.__version__,
                     'generation_method': 'dbgen disjoint children, merged in child order',
                     'generation_workers': args.workers, 'generation_worker_memory_limit': '2GB',
                     'generation_children': sorted(child_meta, key=lambda m: m['step'])})
    for i in range(args.workers):
        (shards / f'part{i}.duckdb').unlink()
        (shards / f'part{i}.json').unlink()
    shards.rmdir()
    print(f'Ready: {db}, {db.stat().st_size/2**30:.2f} GiB', flush=True)


if __name__ == '__main__':
    main()
```

## Authenticate and run all three warehouse sizes

A human signs into the target workspace through the Databricks CLI's OAuth flow. The account needs permission to create serverless SQL warehouses and schemas/tables and to stage files in DBFS. This reproduction matches the original workspace's **`hive_metastore` and DBFS** setup; those features must be available. No credentials are saved in this folder.

```sh
databricks auth login --host https://YOUR-WORKSPACE-HOST --profile tpch
export DATABRICKS_CONFIG_PROFILE=tpch
export TPCH_RUN_TAG="bench_$(date -u +%Y%m%d_%H%M%S)"
.work/.venv/bin/python .work/databricks/sweep.py
```

Keep `TPCH_RUN_TAG` unchanged when resuming (its value is saved under `.work/results/databricks/run_tag.txt`). Use a fresh `.work/results/databricks/` output directory and a new tag for a completely new experiment.

The sweep creates dedicated **Medium, Small, X-Small** warehouses with serverless compute, Photon, warehouse type PRO, minimum=maximum one cluster and a 10-minute auto-stop. It runs one warehouse at a time and stops it in `finally`. Table loading, validation, warehouse startup and connection setup are outside the measured query time. The result cache is disabled on every connection and query history is checked for cache hits. Databricks storage/data caches are retained; there is no forced cache flush or extra warmup phase.

Medium uploads the generated DuckDB data as Parquet (500,000-row batches, 125,000-row groups, Zstandard level 3) to a run-specific DBFS prefix, then uses `COPY INTO` to populate Delta tables. Tables have the same column order, numeric/date types and NOT NULL constraints as DuckDB; VARCHAR maps to STRING and INTEGER may display as INT. Small and X-Small reuse those exact Delta tables. No additional partitioning, clustering or OPTIMIZE is requested. Uploaded tables/staging files remain in the workspace after the run; stopping compute does not delete data.

The runner records query IDs, server metrics, runtime/warehouse metadata and complete result sets. Every result is checked against a fresh DuckDB evaluation, itself checked against the retained reference. Integer/decimal values must match exactly; floating values use absolute tolerance 1e-6 or relative 1e-14, whichever is larger. Comparison is order-insensitive. Failures stop the run; never chart a partial scale.

```python file=.work/databricks/sweep.py
"""Run the unchanged benchmark on dedicated Small and X-Small serverless warehouses."""
import json
import os
from pathlib import Path

import duckdb
from databricks.sdk.service.sql import CreateWarehouseRequestWarehouseType
import run as benchmark

ROOT = benchmark.ROOT
DEST = ROOT / 'results/databricks'
SIZES = [('medium','Medium'),('small','Small'),('xsmall','X-Small')]
SCALES = [200, 100, 50, 25]


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    tag_file=DEST/'run_tag.txt'
    if tag_file.exists(): assert tag_file.read_text()==benchmark.RUN_TAG, 'Resume with the original TPCH_RUN_TAG'
    else: tag_file.write_text(benchmark.RUN_TAG)
    with duckdb.connect(str(ROOT.parent/'results/results.duckdb'), read_only=True) as c:
        queries = c.execute('SELECT query,sql FROM queries ORDER BY query').fetchall()
    for q, sql in queries:
        assert (ROOT/f'queries/q{q:02}.sql').read_text() == sql
    for slug, size in SIZES:
        benchmark.DATASET_SOURCE = None if slug == 'medium' else DEST/'medium'
        folder = DEST/slug
        folder.mkdir(exist_ok=True)
        benchmark.DEST = folder
        if all((folder/f'sf{sf}/complete.json').exists() for sf in SCALES):
            print(f'{size}: all scales already complete', flush=True)
            continue
        config = dict(name=f'tpch_{benchmark.RUN_TAG}_{slug}', cluster_size=size,
                      enable_serverless_compute=True, enable_photon=True,
                      warehouse_type=CreateWarehouseRequestWarehouseType.PRO,
                      min_num_clusters=1, max_num_clusters=1, auto_stop_mins=10)
        id_file = folder/'warehouse_id.json'
        if id_file.exists():
            warehouse_id = json.loads(id_file.read_text())['id']
        else:
            warehouse_id = benchmark.WORKSPACE.warehouses.create(**config).response.id
            benchmark.save(id_file, {'id':warehouse_id})
        benchmark.WAREHOUSE = warehouse_id
        try:
            current = benchmark.WORKSPACE.warehouses.get(warehouse_id)
            assert current.cluster_size == size and current.enable_serverless_compute and current.enable_photon
            assert current.min_num_clusters == current.max_num_clusters == 1
            print(f'{size}: starting dedicated serverless warehouse {warehouse_id}', flush=True)
            current = benchmark.WORKSPACE.warehouses.start_and_wait(warehouse_id)
            benchmark.save(folder/'warehouse_initial.json', current.as_dict())
            for sf in SCALES:
                if (folder/f'sf{sf}/complete.json').exists():
                    print(f'{size} SF{sf}: already complete', flush=True)
                    continue
                print(f'{size}: starting SF{sf}', flush=True)
                benchmark.run(sf, queries)
                print(f'{size}: SF{sf} complete', flush=True)
        finally:
            print(f'{size}: stopping warehouse', flush=True)
            final = benchmark.WORKSPACE.warehouses.stop_and_wait(warehouse_id)
            benchmark.save(folder/'warehouse_final.json', final.as_dict())
            print(f'{size}: warehouse {final.state.value}', flush=True)


if __name__ == '__main__':
    main()
```

```python file=.work/databricks/run.py
"""Copy existing DuckDB data to Delta and run unchanged TPC-H SQL."""
import argparse
import os
import re
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import datetime
import hashlib
import json
import math
import shutil
from pathlib import Path
import sys
import time

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks.sdk.service.sql import QueryFilter

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'results/databricks/medium'
WAREHOUSE = None
RUN_TAG = os.environ['TPCH_RUN_TAG']
assert re.fullmatch(r'[a-z][a-z0-9_]{0,40}', RUN_TAG), 'Use a short SQL-safe unique run tag'
REMOTE = f'/tmp/iphone_benchmark_{RUN_TAG}'
TABLES = ['region','nation','supplier','customer','part','partsupp','orders','lineitem']
CONFIG = Config(profile=os.environ.get('DATABRICKS_CONFIG_PROFILE','tpch'))
WORKSPACE = WorkspaceClient(config=CONFIG)
DATASET_SOURCE = None


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(obj, indent=2, default=str) + '\n')
    temp.replace(path)


def connect(schema='default'):
    return sql.connect(server_hostname=CONFIG.host.removeprefix('https://'),
        http_path=f'/sql/1.0/warehouses/{WAREHOUSE}',
        credentials_provider=lambda: CONFIG.authenticate, catalog='hive_metastore',
        schema=schema, session_configuration={'use_cached_result':'false'},
        user_agent_entry='iphone_benchmark_tpch')


def query(connection, statement):
    with connection.cursor() as cur:
        cur.execute(statement)
        return [tuple(x) for x in cur.fetchall()]


def canonical(value):
    if value is None: return None
    if isinstance(value, (datetime.date, datetime.datetime)): return value.isoformat()
    if isinstance(value, (int, float, Decimal)):
        return {'number': str(value), 'kind':type(value).__name__}
    return value


def normalized(rows):
    rows = [[canonical(x) for x in r] for r in rows]
    def sortkey(row):
        return tuple((0,'') if v is None else (1,Decimal(v['number'])) if isinstance(v,dict)
                     else (2,v) for v in row)
    return sorted(rows, key=sortkey)


def compare(actual, expected):
    assert len(actual) == len(expected), f'Row count differs: {len(actual)} vs {len(expected)}'
    max_error = Decimal(0)
    for i,(a,b) in enumerate(zip(actual,expected)):
        assert len(a) == len(b)
        for j,(x,y) in enumerate(zip(a,b)):
            if isinstance(x,dict) and isinstance(y,dict):
                dx,dy = Decimal(x['number']),Decimal(y['number'])
                err = abs(dx-dy); max_error = max(max_error,err)
                if x.get('kind') != 'float' and y.get('kind') != 'float':
                    assert dx == dy, (i,j,x,y)
                else:
                    assert err <= max(Decimal('0.000001'),abs(dy)*Decimal('1e-14')), (i,j,x,y)
            else:
                assert x == y, (i,j,x,y)
    return str(max_error)


def columns(db):
    with duckdb.connect(str(db),read_only=True) as c:
        return {t:c.execute('SELECT column_name,data_type,is_nullable FROM information_schema.columns '
                            'WHERE table_name=? ORDER BY ordinal_position',[t]).fetchall() for t in TABLES}


def check_schema(connection, schema, table, cols):
    actual = query(connection,f'DESCRIBE TABLE `{schema}`.`{table}`')
    actual = [(r[0],r[1].upper()) for r in actual if r[0] and not r[0].startswith('#')]
    expected = [(name, 'STRING' if typ == 'VARCHAR' else 'INT' if typ == 'INTEGER' else typ)
                for name,typ,_ in cols]
    assert actual[:len(cols)] == expected, (table, actual, expected)
    ddl = query(connection,f'SHOW CREATE TABLE `{schema}`.`{table}`')[0][0]
    import re
    for name,_,nullable in cols:
        if nullable == 'NO':
            assert re.search(r'\b'+name+r'\s+[^,\n]+(?:,\d+\))?\s+NOT NULL',ddl,re.I), (table,name,ddl)
    return ddl


def upload(local, remote):
    started=time.perf_counter()
    data_hash=hashlib.sha256()
    with local.open('rb') as f:
        while b:=f.read(8*1024*1024): data_hash.update(b)
    size=local.stat().st_size
    with local.open('rb') as f: WORKSPACE.dbfs.upload(remote,f,overwrite=True)
    assert WORKSPACE.dbfs.get_status(remote).file_size == size
    local.unlink()
    return {'remote':remote,'bytes':size,'sha256':data_hash.hexdigest(),
            'upload_seconds':time.perf_counter()-started}


def load_scale(sf):
    label=f'{sf:g}'; slug=label.replace('.','_'); dest=DEST/f'sf{label}'
    schema=f'tpch_{RUN_TAG}_sf{slug}'
    db=ROOT/'data'/f'tpch_sf{label}.duckdb'
    meta=json.loads((ROOT/'results'/f'sf{label}'/'metadata.json').read_text())
    cols=columns(db)
    if DATASET_SOURCE is not None:
        dest.mkdir(parents=True, exist_ok=True)
        original = DATASET_SOURCE / f'sf{label}'
        saved = json.loads((original/'metadata.json').read_text())
        assert saved['schema'] == schema
        assert saved['columns'] == {t:[list(c) for c in values] for t,values in cols.items()}
        evidence = {}
        with connect(schema) as conn:
            for table in TABLES:
                ddl = check_schema(conn, schema, table, cols[table])
                count = query(conn, f'SELECT count(*) FROM `{table}`')[0][0]
                assert count == meta['table_rows'][table]
                detail = query(conn, f'DESCRIBE DETAIL `{table}`')
                version = query(conn, f'DESCRIBE HISTORY `{table}` LIMIT 1')
                evidence[table] = {'verified_rows':count, 'target_ddl':ddl, 'detail':detail, 'latest_history':version}
            assert query(conn, 'SET use_cached_result')[0][1].lower() == 'false'
        save(dest/'reused_data.json', {'source':str(original), 'tables':evidence})
        shutil.copy2(original/'duckdb_reference.json', dest/'duckdb_reference.json')
        save(dest/'metadata.json', {**saved, 'warehouse_id':WAREHOUSE,
             'warehouse':WORKSPACE.warehouses.get(WAREHOUSE).as_dict(),
             'reused_data_from':str(original), 'result_cache':False})
        print(f'SF{label}: existing tables verified; unchanged SQL and data reused', flush=True)
        return db,schema,dest
    stage=ROOT/'data/.databricks_stage'/f'sf{slug}'; stage.mkdir(parents=True,exist_ok=True)
    dest.mkdir(parents=True,exist_ok=True)
    with connect() as conn:
        query(conn,f'CREATE SCHEMA IF NOT EXISTS `{schema}`')
    with connect(schema) as conn:
        for table in TABLES:
            manifest_path=dest/f'{table}_upload.json'
            manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'files':{}}
            ddlcols=', '.join(f'`{name}` {"STRING" if typ=="VARCHAR" else typ}'+
                             (' NOT NULL' if nullable=='NO' else '') for name,typ,nullable in cols[table])
            query(conn,f'CREATE TABLE IF NOT EXISTS `{table}` ({ddlcols}) USING DELTA')
            target_ddl=check_schema(conn,schema,table,cols[table])
            if not manifest.get('loaded'):
                pending=[]
                def finish(item):
                    index,count,future=item
                    record=future.result(); record['rows']=count
                    manifest['files'][str(index)]=record
                    save(manifest_path,manifest)
                with ThreadPoolExecutor(max_workers=16) as pool:
                    with duckdb.connect(str(db),read_only=True,config={'threads':4,'memory_limit':'4GB'}) as dc:
                        reader=dc.execute(f'SELECT * FROM {table}').to_arrow_reader(batch_size=500_000)
                        for index,batch in enumerate(reader):
                            if str(index) in manifest['files']: continue
                            local=stage/f'{table}-{index:06d}.parquet'
                            pq.write_table(pa.Table.from_batches([batch]),local,compression='zstd',
                                           compression_level=3,row_group_size=125_000)
                            remote=f'{REMOTE}/sf{slug}/{table}/part-{index:06d}.parquet'
                            pending.append((index,batch.num_rows,pool.submit(upload,local,remote)))
                            if len(pending)>=16: finish(pending.pop(0))
                            if (index+1)%20==0:
                                print(f'SF{label} {table}: exported {index+1} chunks',flush=True)
                    for item in pending: finish(item)
                assert sum(f['rows'] for f in manifest['files'].values()) == meta['table_rows'][table]
                started=time.perf_counter()
                result=query(conn,f"COPY INTO `{table}` FROM 'dbfs:{REMOTE}/sf{slug}/{table}' "
                             "FILEFORMAT = PARQUET COPY_OPTIONS ('mergeSchema' = 'false')")
                manifest['copy_result']=result
                manifest['copy_seconds']=time.perf_counter()-started
                manifest['loaded']=True
                save(manifest_path,manifest)
            n=query(conn,f'SELECT count(*) FROM `{table}`')[0][0]
            assert n == meta['table_rows'][table], (table,n,meta['table_rows'][table])
            manifest['verified_rows']=n; manifest['target_ddl']=target_ddl
            save(manifest_path,manifest)
            print(f'SF{label} {table}: {n:,} rows loaded and schema verified',flush=True)
    save(dest/'metadata.json',{'scale_factor':sf,'schema':schema,'warehouse_id':WAREHOUSE,
         'warehouse':WORKSPACE.warehouses.get(WAREHOUSE).as_dict(),
         'source_duckdb':str(db),'source_metadata':meta,'columns':cols,
         'type_mapping':{'VARCHAR':'STRING'},'repeats':2,'result_cache':False})
    return db,schema,dest


def references(db, dest, queries, sf):
    path=dest/'duckdb_reference.json'
    if path.exists():
        cached=json.loads(path.read_text())
        if all(not isinstance(v,dict) or 'kind' in v for rows in cached.values() for row in rows for v in row):
            return cached
    result={}
    baseline=json.loads((ROOT/'reference'/f'sf{sf:g}.json').read_text())
    for nr,statement in queries:
        with duckdb.connect(str(db),read_only=True,config={'threads':9,'memory_limit':'8GB',
                            'temp_directory':str(ROOT/'data/.query_tmp')}) as c:
            rows=c.execute(statement).fetchall()
        result[str(nr)]=normalized(rows)
        compare(result[str(nr)],baseline[str(nr)])
    save(path,result)
    return result


def collect_metrics(rows, dest):
    ids=[r['query_id'] for r in rows]
    for attempt in range(10):
        history=[]
        for start in range(0,len(ids),20):
            response=WORKSPACE.query_history.list(filter_by=QueryFilter(statement_ids=ids[start:start+20]),
                                                  include_metrics=True,max_results=100)
            history.extend(response.res or [])
        by_id={h.query_id:h.as_dict() for h in history}
        ready=True
        for row in rows:
            h=by_id.get(row['query_id'],{})
            metrics=h.get('metrics',{})
            if not h.get('is_final') or not all(k in metrics for k in ('execution_time_ms','total_time_ms')):
                ready=False; continue
            assert not metrics.get('result_from_cache'), row
            row['history']=h
            row['execution_seconds']=metrics['execution_time_ms']/1000
            row['server_total_seconds']=metrics['total_time_ms']/1000
        if ready: break
        time.sleep(5)
    assert all('server_total_seconds' in r for r in rows), 'Query history metrics not yet available'
    save(dest/'measurements.json',rows)


def record(sf, rows, queries, dest):
    with duckdb.connect(str(DEST/'results.duckdb')) as c:
        c.execute('''CREATE TABLE IF NOT EXISTS measurements (
            scale_factor DOUBLE, query INTEGER, repeat INTEGER, query_id VARCHAR,
            wall_seconds DOUBLE, execution_seconds DOUBLE, server_total_seconds DOUBLE,
            rows_returned BIGINT, max_numeric_error VARCHAR, details JSON,
            PRIMARY KEY(scale_factor,query,repeat))''')
        c.execute('CREATE TABLE IF NOT EXISTS queries (query INTEGER PRIMARY KEY, sql VARCHAR, sha256 VARCHAR)')
        c.execute('CREATE TABLE IF NOT EXISTS runs (scale_factor DOUBLE PRIMARY KEY, metadata JSON)')
        c.execute('BEGIN')
        c.execute('DELETE FROM measurements WHERE scale_factor=?',[sf])
        for r in rows:
            c.execute('INSERT INTO measurements VALUES (?,?,?,?,?,?,?,?,?,?)',
                [sf,r['query'],r['repeat'],r['query_id'],r['wall_seconds'],r['execution_seconds'],
                 r['server_total_seconds'],r['rows_returned'],r['max_numeric_error'],json.dumps(r)])
        c.executemany('INSERT OR REPLACE INTO queries VALUES (?,?,?)',
            [(n,s,hashlib.sha256(s.encode()).hexdigest()) for n,s in queries])
        c.execute('INSERT OR REPLACE INTO runs VALUES (?,?)',[sf,(dest/'metadata.json').read_text()])
        c.execute('''CREATE OR REPLACE VIEW query_summary AS SELECT scale_factor,query,
            avg(wall_seconds) wall_seconds, avg(execution_seconds) execution_seconds,
            avg(server_total_seconds) server_total_seconds FROM measurements GROUP BY ALL''')
        c.execute('''CREATE OR REPLACE VIEW scale_summary AS SELECT scale_factor,count(*) queries,
            exp(avg(ln(wall_seconds))) geomean_wall_seconds,
            exp(avg(ln(execution_seconds))) geomean_execution_seconds,
            exp(avg(ln(server_total_seconds))) geomean_server_total_seconds
            FROM query_summary GROUP BY scale_factor''')
        c.execute('COMMIT')
        print(c.execute('SELECT * FROM scale_summary ORDER BY scale_factor').fetchall(),flush=True)


def run(sf, queries):
    db,schema,dest=load_scale(sf)
    expected=references(db,dest,queries,sf)
    path=dest/'measurements.json'
    rows=json.loads(path.read_text()) if path.exists() else []
    completed={(r['query'],r['repeat']) for r in rows}
    for row in rows:
        actual=json.loads((dest/f'q{row["query"]:02}_r{row["repeat"]}_result.json').read_text())
        row['max_numeric_error']=compare(actual,expected[str(row['query'])])
    for nr,statement in queries:
        for rep in [1,2]:
            if (nr,rep) in completed: continue
            with connect(schema) as conn:
                assert query(conn,'SET use_cached_result')[0][1].lower() == 'false'
                with conn.cursor() as cur:
                    started=time.perf_counter(); cur.execute(statement); result=cur.fetchall()
                    elapsed=time.perf_counter()-started; query_id=cur.query_id
            actual=normalized(result)
            save(dest/f'q{nr:02}_r{rep}_result.json',actual)
            error=compare(actual,expected[str(nr)])
            row={'scale_factor':sf,'query':nr,'repeat':rep,'query_id':query_id,
                 'wall_seconds':elapsed,'rows_returned':len(result),'max_numeric_error':error,
                 'query_sha256':hashlib.sha256(statement.encode()).hexdigest()}
            rows.append(row); save(path,rows)
            print(f'SF{sf:g} Q{nr:02} r{rep}: {elapsed:.3f}s client; {len(result)} rows match DuckDB',flush=True)
    collect_metrics(rows,dest)
    record(sf,rows,queries,dest)
    save(dest/'complete.json',{'executions':len(rows),'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
```

## Outputs and expected aggregate

New per-query JSON and the per-warehouse DuckDB result databases are written below `.work/results/databricks/{medium,small,xsmall}/`. Each warehouse must have 176 executions: 4 scales × 22 queries × 2 repeats. All 528 retained executions passed result validation and had no SQL result-cache hits.

| Scale | M server total (s) | S server total (s) | XS server total (s) |
|---:|---:|---:|---:|
| 25 | 1.343877 | 1.663699 | 1.904716 |
| 50 | 1.635030 | 2.057327 | 2.530192 |
| 100 | 2.706988 | 2.862745 | 3.909349 |
| 200 | 3.326081 | 4.649120 | 7.018267 |

These are observed geometric means, not pass/fail performance thresholds. The immutable retained outputs are in [results/results.duckdb](results/results.duckdb); see [CHARTS.md](CHARTS.md) for schema, aggregation, importing reruns and rendering. Continue with [IPHONE.md](IPHONE.md) using the same generated databases and SQL.
