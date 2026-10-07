# Create the charts

The eight final deliverables are [charts/timing.png](charts/timing.png),
[charts/scans.png](charts/scans.png), [charts/compute_cost.png](charts/compute_cost.png),
[charts/service_cost.png](charts/service_cost.png),
[charts/tpch_schema.png](charts/tpch_schema.png), [charts/shuffle.png](charts/shuffle.png),
[charts/query_distribution.png](charts/query_distribution.png), and
[charts/open_data_lake.png](charts/open_data_lake.png).
All titles and subtitles use sentence case while preserving proper names and
acronyms (TPC-H, iPhone, AWS, CPU). Explicit `font.case: none` prevents the theme
from converting authored text into title case.
The four data charts use **dbt Charts 0.8.0** and the **vivid** theme; the schema
diagram uses **Mermaid** on an opaque white background. The TPC-H data charts use default
colors, fonts, sizes, and dimensions with the footer/timestamp hidden. The cost
chart adds native annotation stems and labels, preserves the requested title
case, and fixes the logarithmic y-axis to $0.005–$0.10; its legend/footer/timestamp
are hidden.
## Render the retained results

Run from this folder. `uv tool install` supplies `dct`; ensure the uv tool binary directory is on PATH. Rendering uses local data only and needs neither Databricks credentials nor a phone.

```sh
uv tool install --python 3.12 dbt-charts==0.8.0
uv run --python 3.13 --with duckdb==1.5.6 python charts/render.py
python3 charts/render_cost.py
uv run --python 3.12 --with dbt-charts==0.8.0 python charts/render_schema.py
```

[charts/render.py](charts/render.py) checks SQL hashes, all execution keys, thermal starts, server metric selection, cache flags, scan counters and distribution totals; it validates both TPC-H boards and renders their PNGs without a query cache. [charts/render_cost.py](charts/render_cost.py) validates both cost boards and renders their PNGs and SVGs. The frontier reads the tracked [JSON chart input](charts/compute_cost_data.json); the service chart uses embedded inputs. Neither cost chart needs a research database. [charts/dbt_charts.yml](charts/dbt_charts.yml) is also usable directly:

```sh
cd charts
dct validate timing.yml scans.yml compute_cost.yml service_cost.yml
dct render timing.yml scans.yml compute_cost.yml service_cost.yml --format png --no-cache --output '{stem}.png'
```

## TPC-H schema

[charts/tpch_schema.png](charts/tpch_schema.png) is rendered from the editable
[Mermaid source](charts/tpch_schema.mmd). It shows only the eight table names,
SF200 row counts abbreviated with M (million) and B (billion), and parent-to-child arrows for the logical one-to-many
relationships. No columns or key fields appear. The `partsupp` → `lineitem`
relationship represents the composite part/supplier key.

At SF200 (nominal 200 GB), counts are region 5, nation 25, supplier 2,000,000,
customer 30,000,000, part 40,000,000, partsupp 160,000,000 and orders 300,000,000.
Lineitem is explicitly **approximately 1,200,000,000**: rows per order vary, so
its exact generated count is not a strict scale-factor multiple. These are
schema cardinalities from the [TPC-H specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-h_v3.0.1.pdf),
not a fresh count of the generated benchmark tables. Nominal scale is not the
compressed database file size.

The [renderer](charts/render_schema.py) invokes Mermaid CLI to write PNG and SVG
on white. It uses the dbt Charts 0.8.0 vivid palette: solid blue `#0073c2`, white canvas,
heading gray `#313233` and connector gray `#D0D3D9`. The renderer embeds the same
Inter and dbt Sans Tabular fonts used by the data charts, with a semibold title.
Shapes are flat, without shadows or gradients. Font data comes from the pinned
dbt Charts package; it is embedded so rendering does not depend on installed fonts.
It requires Python 3.12, dbt Charts 0.8.0, Node.js and Mermaid CLI 12.0.0:

```sh
npm install --global @mermaid-js/mermaid-cli@12.0.0
uv run --python 3.12 --with dbt-charts==0.8.0 python charts/render_schema.py
```

To use an existing Chrome installation instead of downloading Puppeteer's browser,
set `PUPPETEER_SKIP_DOWNLOAD=true` during installation and set
`PUPPETEER_EXECUTABLE_PATH` to the Chrome executable when rendering.

## Shuffle

[charts/shuffle.png](charts/shuffle.png) shows three nodes, each containing a
partition of two tables. Table A uses vivid blue (`#0073c2`); Table B uses vivid
orange (`#da5a23`). Matching bidirectional arrows between each pair of nodes
represent partition exchange to colocate matching join keys. Some rows remain
local; this is a conceptual shuffle, not measured network traffic. The diagram
contains no visible text labels.

[charts/render_shuffle.py](charts/render_shuffle.py) draws the SVG, reads colors
directly from dbt Charts 0.8.0, then renders a 2× PNG on white.
It also produces an editable [SVG](charts/shuffle.svg). Run with Google Chrome
installed, or set `PUPPETEER_EXECUTABLE_PATH` to a Chromium executable:

```sh
uv run --python 3.12 --with dbt-charts==0.8.0 --with playwright==1.56.0 python charts/render_shuffle.py
```

## Query distribution

[charts/query_distribution.png](charts/query_distribution.png) shows five users
across the top, each submitting one query to a single node. Three compute nodes
along the bottom each process one query, marked with a play symbol. Two more
queries wait outside the left and right nodes, marked with pause symbols and
dashed arrows into their assigned nodes. All five queries appear exactly once.
The diagram has no visible text labels and uses only blue (`#0073c2`) and gray
(`#949daa`) from dbt Charts 0.8.0's vivid palette on white, with the same scale
and line weights as the shuffle diagram.

[charts/render_query_distribution.py](charts/render_query_distribution.py)
produces the 2× PNG and editable [SVG](charts/query_distribution.svg).
Use Google Chrome or set `PUPPETEER_EXECUTABLE_PATH` to Chromium:

```sh
uv run --python 3.12 --with dbt-charts==0.8.0 --with playwright==1.56.0 python charts/render_query_distribution.py
```

## Open data lake

[charts/open_data_lake.png](charts/open_data_lake.png) places table icons in
the center beneath “Open data lake,” with no “Iceberg tables” label. Six floating
labels group the surrounding icons: compute engines (Snowflake, BigQuery,
Databricks), connectors (Fivetran), notebooks (a notebook), AI agents (ChatGPT, Claude),
BI tools (a chart and Hex), and local compute (a laptop). Each icon connects directly to
the lake. The surrounding icons have no enclosing boxes. This is a conceptual architecture:
connections abstract away adapters and execution engines, and do not claim
that every product natively reads and writes Iceberg files itself.

[charts/render_open_data_lake.py](charts/render_open_data_lake.py) uses vivid blue
and charcoal from dbt Charts 0.8.0, embeds its Inter font, and produces the 2× PNG
and editable [SVG](charts/open_data_lake.svg).
[The retained icon paths](charts/open_data_lake_icons.json) include their source
URLs: Simple Icons 16.0.0 (Snowflake, BigQuery, Databricks, Claude), Simple Icons
13.0.0 (OpenAI), and the official Fivetran and Hex sites. The brand symbols are
rendered in monochrome; the chart, notebook, and laptop are drawn by the renderer. All
assets are local, so rendering requires no network access. Use Google Chrome or set
`PUPPETEER_EXECUTABLE_PATH` to Chromium:

```sh
uv run --python 3.12 --with dbt-charts==0.8.0 --with playwright==1.56.0 python charts/render_open_data_lake.py
```

## Retained data

[results/results.duckdb](results/results.duckdb) is the data source for the two TPC-H charts. Raw outputs are retained alongside derived views; no live workspace, removed source file or generated TPC-H database is needed to reproduce the PNGs.

| Table/view | Contents |
|---|---|
| `queries` | 22 exact SQL statements and SHA-256 hashes |
| `table_columns` | Column order, logical types and nullability for all eight tables |
| `datasets` | Four original generation records and phone input/hash manifests |
| `reference_results` | 88 complete normalized DuckDB reference result sets |
| `iphone_runs`, `iphone_measurements` | Four selected runs, 176 timings, native result sets, profiles, memory/thermal observations and build metadata |
| `databricks_runs`, `databricks_measurements` | 12 size/scale configurations, 528 timings and result sets, query histories/IDs, upload and schema evidence |
| `mac_runs`, `mac_scans` | Four Mac configurations, 176 scan-byte observations and complete profiler JSON |
| `published_bins` | Original Snowflake and Redshift bucket counts, before tail pooling |
| `provenance` | Source commit/hash/filters, schema SQL and original run audit evidence |
| `timing_summary` | 16 geometric-mean chart points, computed from raw timings |
| `histogram` | 42 rows: 21 doubling bins × two normalized series |

All timings and profiles are outputs of the recorded experiment, not predicted values. Paths inside original metadata are historical provenance, not current dependencies. Reference results and histories include other raw fields that are useful for verification; only the metrics specified below are plotted.

## Compute cost

[charts/compute_cost.yml](charts/compute_cost.yml) reads the `frontier` table
registered from [charts/compute_cost_data.json](charts/compute_cost_data.json).
The input preserves all 103 original observations and their source URLs.
It plots the effective hourly price divided by physical cores times Geekbench 6
single-core score divided by 1,000, with step-after interpolation on a continuous
date axis. Annotation origins come from saved frontier observations; offset
endpoints position the labels without changing the cost series. See
[COMPUTE_COST.md](COMPUTE_COST.md) for the research lab notebook, arithmetic,
source ledger, and instructions for independently repeating the calculations.

The compute-cost chart contains only the frontier line and its instance/price-cut
annotations. Its log y-axis spans $0.005–$0.10; service comparisons are separate.

## Service price vs AWS compute

[charts/service_cost.yml](charts/service_cost.yml) renders two floating bars with the
x-axis hidden (title, labels, ticks, baseline and vertical gridlines). Both
comparisons are dated October 1, 2026. Horizontal spacing separates the
services and does not encode elapsed time. The y-axis is **USD per physical core-hour**,
with a logarithmic scale and no Geekbench or other performance normalization.

| Comparison date | Assumed physical cores | AWS USD/core-hour | Service USD/core-hour | Service / AWS |
| --- | ---: | ---: | ---: | ---: |
| Snowflake M, 2026-10-01 | 32 | 0.013862500 | 0.337500000 | 24.3× |
| Databricks M, 2026-10-01 | 80 | 0.019934375 | 0.210000000 | 10.5× |

The bars use Snowflake blue (`#29B5E8`) and Databricks Lava (`#FF3621`).
Color references: [Snowflake](https://brandfetch.com/snowflake.com) and
[Databricks](https://brand.databricks.com/colors). Native thick line segments
with flat ends span the AWS and service prices; invisible scatter marks anchor
the labels. The subtitle is omitted; a small footer reads
“Excludes attached SSDs, global services, software, overhead...”.
All layers share the $0.01–$0.80 log axis, and ratio labels sit at
`sqrt(service_price * aws_price)` using unrounded prices.

Snowflake Medium uses the user's speculative assumption of four `c7g.2xlarge`
nodes, each with eight physical cores: `$10.80 / 32 = $0.3375/core-hour` (Gen2, Standard edition), versus
`4 * $0.1109 / 32 = $0.0138625/core-hour` for AWS.
Databricks Medium uses an inferred `r8g.8xlarge`-equivalent driver
plus **six** `m8g.2xlarge`-equivalent workers: 32 + 6 × 8 = 80 reported cores.
The October 1 live cluster API confirms that configured count, so the chart says
`AWS r8g + m8g * 6, 3-year commit`. Its AWS rate is
`($0.74425 + 6 * $0.14175) / 80 = $0.019934375/core-hour`.

AWS rates were checked against the current catalog, and Snowflake's current
Credit Consumption Table confirms AWS Gen2 Medium at 5.4 credits/hour and
Standard edition in Northern Virginia at $2/credit. Snowflake hardware is
explicitly speculative. The [Databricks inspection notes](COMPUTE_COST.md#databricks-reported-configuration-differs-from-active-workers)
confirms the reported 80-core / 448-GiB configuration but found only three active
eight-core executors in the tested Medium queries. The chart uses reported
configuration, not measured active capacity; actual EC2 SKUs remain inferred.
See [COMPUTE_COST.md](COMPUTE_COST.md) for pricing sources and qualifications.

This board uses an in-memory DuckDB source and embedded SQL constants, so it can
be rendered without the ignored research databases:

```sh
cd charts
dct validate service_cost.yml
dct render service_cost.yml --format png --no-cache --output service_cost.png
```

## Runtime comparison

| | **Databricks XS** | **Databricks S** | **Databricks M** | **iPhone 17 Pro** |
| --- | ---: | ---: | ---: | ---: |
| **CPUs** | 24 cores | 40 cores | 80 cores | 6 cores |
| **Memory** | 128 GiB | 224 GiB | 448 GiB | 11.45 GiB physical; 6 GB DuckDB buffer limit |
| **Cost / Hour** | $4.20 | $8.40 | $16.80 | Not modeled |

CPU counts mean cores, not processor sockets. Databricks values are the configured
totals including the driver, captured on October 1, 2026; prices are USD public
list rates checked on October 5. These are the sources and calculations:

- **Databricks CPUs:** the saved `/api/2.0/clusters/get` responses report
  `cluster_cores` of 24, 40, and 80. Driver node types identify 8, 16, and 32
  cores, and `num_workers` is 2, 3, and 6. Each worker has eight cores, giving
  XS `8 + 2 × 8 = 24`, S `16 + 3 × 8 = 40`, and M `32 + 6 × 8 = 80`.
  See the [hardware inspection method and findings](COMPUTE_COST.md#databricks-reported-configuration-differs-from-active-workers)
  and the optional local [API capture](results/compute_cost/evidence/databricks_hardware_2026-10-01.json).
- **Databricks memory:** those same responses report `cluster_memory_mb` of
  131,072, 229,376, and 458,752. Dividing by 1,024 gives 128, 224, and 448 GiB.
  The configured breakdown is XS `64 + 2 × 32`, S `128 + 3 × 32`, and
  M `256 + 6 × 32` GiB, with driver memory first. These are total configured
  host-memory capacities, not Spark storage-pool sizes or query memory limits.
- **Databricks cost:** the [official AWS pricing data](https://www.databricks.com/en-pricing-assets/data/pricing/AWS.json),
  filtered to Premium, US East (N. Virginia), SQL Serverless Compute, gives
  6, 12, and 24 DBU/hour at $0.70/DBU. Thus XS `6 × $0.70 = $4.20/hour`,
  S `12 × $0.70 = $8.40/hour`, and M `24 × $0.70 = $16.80/hour`.
  Serverless infrastructure is included; no separate EC2 charge is added.
  These are list rates, not measured invoice charges or negotiated prices.
  See the [pricing notebook](COMPUTE_COST.md#service-prices-audited-october-5)
  and optional local [October 5 pricing capture](results/compute_cost/evidence/databricks_pricing_2026-10-05.json).
- **iPhone CPUs and memory:** all four retained `iphone_runs.metadata` records in
  [the result database](results/results.duckdb) contain `cpu_count = 6` and
  `physical_memory_bytes = 12291735552`. The app records these using
  `NSProcessInfo.processorCount` and `physicalMemory`; dividing the byte count
  by `2^30` gives 11.44757 GiB, rounded to 11.45 in the table. The same records
  specify six DuckDB threads and `memory_limit = '6GB'`: 6,000,000,000 buffer
  bytes, displayed by DuckDB as 5.5 GiB. That limit is neither total phone RAM
  nor a cap on total app memory. See the [phone method and recording code](IPHONE.md).
- **iPhone cost:** the experiment did not measure electricity or cooling cost
  or choose a purchase-price amortization period. An hourly cost therefore
  cannot be calculated from the retained evidence; “Not modeled” does not mean
  zero cost.

The Databricks inspection found only 1, 2, and 3 active eight-core workers for
XS, S, and M, despite the configured worker counts above. The discrepancy is
unresolved. Configured totals do not establish dedicated CPU allocation, and
this later inspection does not prove which hardware served the original TPC-H
runs. The table also does not imply equal performance per core across platforms.

[charts/timing.yml](charts/timing.yml) reads `timing_summary`. For each engine/scale, average the two repetitions of each query, then compute `exp(avg(ln(mean_query_seconds)))` across all 22 queries, with equal query weight. Databricks uses `server_total_seconds` (history `total_time_ms / 1000`); the phone uses local `wall_seconds` including query compilation and full result conversion. See [DATABRICKS.md](DATABRICKS.md) and [IPHONE.md](IPHONE.md) for precise timer boundaries and execution conditions.

The legend reads **DuckDB on iPhone 17 Pro**, **Databricks serverless M**, **Databricks serverless S**, and **Databricks serverless XS**. The selected four cooled 6 GB phone runs supply the only phone series. There is no Mac timing series.

The x-axis label is **TPC-H scale factor (GB, log scale)**. For this dbt Charts version the line chart uses ordered categories 25, 50, 100, 200: equal spacing is exactly equivalent to logarithmic positioning for these doubling values. Do not add a non-doubling scale without updating the axis implementation. The y-axis uses a genuine base-2 logarithmic scale.

```sql
SELECT * FROM timing_summary ORDER BY scale_factor, engine;
```

## Scan-volume histogram

[charts/scans.yml](charts/scans.yml) compares **snowflake + redshift published data** with **workload** as grouped bars. Add Snowflake and Redshift raw counts first, then normalize the combined distribution; do not average their percentages. This preserves the published query weighting: 17,184,788 Snowflake + 63,276,038 Redshift = **80,460,826 queries**.

The published counts came from the cached HTML/Altair output of cell 11 in [2.IngestCost.ipynb at commit 82a6cd00e80e6eb54bf571105bf370bf89c4d3a0](https://github.com/fivetran/snowflake_redshift_usage/blob/82a6cd00e80e6eb54bf571105bf370bf89c4d3a0/2.IngestCost.ipynb), linked by the [Fivetran blog post](https://www.fivetran.com/blog/how-do-people-use-snowflake-and-redshift). The downloaded notebook SHA-256 was `1f79e0c39389652cbcf945e6b03bc1b1e2646e492a18ae520e5c0ba97f7a9d0f`. The extracted original counts and source metadata are retained in the database, so no notebook execution or source-data access is required.

The local workload pools **all 176 executions**: all 22 queries, both repetitions and all four scales, each execution weighted equally. It uses the original Mac M2 Ultra run with **9 DuckDB threads, 8GB memory_limit, spilling enabled**, DuckDB 1.5.6 and fresh connections. No phone scan counts enter this histogram. The metric is the JSON profiler's `total_bytes_read`: compressed persistent-storage reads into a fresh DuckDB buffer pool. OS caching is retained, so this is not physical SSD traffic or uncompressed logical bytes. In this DuckDB version the counter excludes spill-file reads. The published Snowflake metric counts compressed persistent reads including cache; the notebook uses Redshift `mbytes_scanned` directly, whose binary/decimal MB convention is not specified. Treat this as a scan-volume comparison with those source metric differences.

Buckets are `[2^k MiB, 2^(k+1) MiB)` for k=0…19, followed by `≥1 TiB`. Labels show inclusive lower bounds. The source plot's population starts at 1 MiB; all retained local observations exceed that threshold. The y-axis is the fraction of each population (displayed as percent), not an absolute query count; each series sums to 100%. The x-axis is categorical doubling bins, including the pooled final tail, not a continuous byte axis.

```sql
SELECT * FROM histogram ORDER BY bin_index, series;
SELECT warehouse, sum(query_count) FROM published_bins GROUP BY warehouse;
```

## Reproduce the Mac scan measurements

Run the shared extraction, setup and data generation in [DATABRICKS.md](DATABRICKS.md), then run this embedded script on the Mac separately from other benchmark activity. Its database layout, SQL, fetch/profiling behavior and nine-thread/8 GB configuration match the retained scan run. It validates all result sets and saves the same per-query byte metric. Mac elapsed times are not collected for presentation.

```sh
.work/.venv/bin/python .work/mac_scans.py
```

```python file=.work/mac_scans.py
"""Record the 176 Mac scan-volume observations used in the workload histogram."""
from pathlib import Path
import datetime,hashlib,json,platform,subprocess
from decimal import Decimal
import duckdb
from benchmark import ROOT,save
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


def main():
    assert duckdb.__version__=='1.5.6'
    config={'threads':9,'memory_limit':'8GB','temp_directory':str(ROOT/'data/.scan_spill')}
    for sf in [200,100,50,25]:
        folder=ROOT/'results/mac_scans'/f'sf{sf}'
        folder.mkdir(parents=True,exist_ok=True)
        refs=json.loads((ROOT/'reference'/f'sf{sf}.json').read_text())
        rows=[]
        for q in range(1,23):
            statement=(ROOT/'queries'/f'q{q:02}.sql').read_text()
            for rep in (1,2):
                profile=folder/f'q{q:02}_r{rep}.json'
                with duckdb.connect(str(ROOT/'data'/f'tpch_sf{sf}.duckdb'),read_only=True,config=config) as c:
                    c.execute("PRAGMA enable_profiling='json'")
                    c.execute('SET profiling_output = ?',[str(profile)])
                    result=c.execute(statement).fetchall()
                p=json.loads(profile.read_text())
                assert p['query_name']==statement
                error=compare(normalized(result),refs[str(q)])
                rows.append({'scale_factor':sf,'query':q,'repeat':rep,'bytes_read':p['total_bytes_read'],
                             'maximum_numeric_error':error,'query_sha256':hashlib.sha256(statement.encode()).hexdigest()})
                save(folder/'measurements.json',rows)
                print(f'SF{sf} Q{q:02} r{rep}: {p["total_bytes_read"]/2**20:.2f} MiB',flush=True)
        save(folder/'metadata.json',{'scale_factor':sf,'config':config,'repeats':2,'duckdb_version':duckdb.__version__,
             'platform':platform.platform(),'cpu':subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True).strip(),
             'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
if __name__=='__main__': main()
```

## Chart a complete new experiment

Preserve the shipped result database. After completing all three Databricks sweeps, the phone sweep and the Mac scan collection, use the embedded importer to write a new database. It copies the fixed SQL/schema/reference definitions and published counts, replaces measured rows/configurations and keeps the same derived views. Missing/partial outputs are errors.

```sh
.work/.venv/bin/python .work/import_results.py --output .work/new_results.duckdb
uv run --python 3.13 --with duckdb==1.5.6 python charts/render.py --database .work/new_results.duckdb --output .work/charts
```

```python file=.work/import_results.py
"""Import a complete rerun into a new chart database, preserving the retained baseline."""
import argparse,json,shutil
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'results/results.duckdb'
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output',type=Path,required=True)
args=p.parse_args(); out=args.output.resolve()
assert not out.exists(), 'Choose a new result database path'
out.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(BASE,out)
with duckdb.connect(str(out)) as c:
    c.execute('BEGIN')
    try:
        for table in ['iphone_runs','iphone_measurements','databricks_runs','databricks_measurements','datasets','mac_runs','mac_scans']:
            c.execute(f'DELETE FROM {table}')
        selection=json.loads((ROOT/'results/iphone_device/sweep_selection.json').read_text())
        with duckdb.connect(str(ROOT/'results/iphone_device/results.duckdb'),read_only=True) as phone:
            for sf in [200,100,50,25]:
                entry=selection['runs'][str(sf)]; assert entry['complete']; rid=entry['run_id']
                metadata,validation=phone.execute('SELECT metadata,validation FROM runs WHERE run_id=?',[rid]).fetchone()
                exported=ROOT/'results/iphone_device'/f'sf{sf}'/'exported'/rid
                c.execute('INSERT INTO iphone_runs VALUES (?,?,?,?,?)',[rid,sf,metadata,validation,(exported/'build_manifest.json').read_text()])
                rows=phone.execute('SELECT run_id,query,repeat,wall_seconds,details,profile,result FROM measurements WHERE run_id=?',[rid]).fetchall()
                assert len(rows)==44
                c.executemany('INSERT INTO iphone_measurements VALUES (?,?,?,?,?,?,?)',rows)
                c.execute('INSERT INTO datasets VALUES (?,?,?)',[sf,(ROOT/f'results/sf{sf}/metadata.json').read_text(),(ROOT/f'results/iphone_device/sf{sf}/input.json').read_text()])
        for size in ['medium','small','xsmall']:
            base=ROOT/'results/databricks'/size
            with duckdb.connect(str(base/'results.duckdb'),read_only=True) as db:
                assert db.execute('SELECT query,sql,sha256 FROM queries ORDER BY query').fetchall()==c.execute('SELECT * FROM queries ORDER BY query').fetchall()
                for sf in [200,100,50,25]:
                    folder=base/f'sf{sf}'
                    assert json.loads((folder/'complete.json').read_text())['executions']==44
                    metadata=db.execute('SELECT metadata FROM runs WHERE scale_factor=?',[sf]).fetchone()[0]
                    evidence={f.name:json.loads(f.read_text()) for f in folder.glob('*_upload.json')}
                    for name in ['reused_data.json','complete.json']:
                        if (folder/name).exists(): evidence[name]=json.loads((folder/name).read_text())
                    c.execute('INSERT INTO databricks_runs VALUES (?,?,?,?)',[size,sf,metadata,json.dumps(evidence)])
                    rows=db.execute('SELECT scale_factor,query,repeat,query_id,server_total_seconds,rows_returned,max_numeric_error,details FROM measurements WHERE scale_factor=?',[sf]).fetchall()
                    assert len(rows)==44
                    c.executemany('INSERT INTO databricks_measurements VALUES (?,?,?,?,?,?,?,?,?,?)',[(size,*r,(folder/f'q{r[1]:02}_r{r[2]}_result.json').read_text()) for r in rows])
        for sf in [200,100,50,25]:
            folder=ROOT/'results/mac_scans'/f'sf{sf}'
            c.execute('INSERT INTO mac_runs VALUES (?,?)',[sf,(folder/'metadata.json').read_text()])
            rows=json.loads((folder/'measurements.json').read_text()); assert len(rows)==44
            c.executemany('INSERT INTO mac_scans VALUES (?,?,?,?,?)',[(sf,r['query'],r['repeat'],r['bytes_read'],(folder/f'q{r["query"]:02}_r{r["repeat"]}.json').read_text()) for r in rows])
        c.execute("DELETE FROM provenance WHERE name LIKE 'databricks_audit_%' OR name IN ('native_source','retention')")
        c.execute('INSERT OR REPLACE INTO provenance VALUES (?,?)',['rerun',json.dumps({'baseline':str(BASE),'work_directory':str(ROOT),'note':'Imported complete new measurements; published histogram and SQL/reference definitions retained.'})])
        c.execute('COMMIT')
    except:
        c.execute('ROLLBACK')
        raise
print(out)
```

## Audit and evidence limits

The October 5 audit's cost findings and live hardware inspection are consolidated
in [the cost notebook](COMPUTE_COST.md). Its earlier claim that the databases and
source cache were missing does not describe the October 7 workspace: those local
files are present. They are still Git-ignored and absent from a fresh clone.
Both cost charts now render from tracked chart inputs. Rendering a saved result
does not independently re-audit all of its underlying observations.

The October 5 benchmark caveats remain relevant:

| Item | Interpretation |
| --- | --- |
| iPhone | Six threads, a 6 GB DuckDB buffer limit, external cooling, and nominal thermal state were specified. Six threads are not six equivalent performance cores; buffer limits are not total process RAM. No phone amortization, power, or cooling cost is modeled. |
| Databricks | Server total elapsed time includes compilation and excludes client/network overhead. Serverless is enabled despite `warehouse_type = PRO`. Result caching is disabled; data caches remain. |
| Timing comparison | Phone time includes result conversion; Databricks time excludes client transfer. Two consecutive repeats are averaged per query before equal-weight geometric-mean aggregation. This is not a cold-cache, production-concurrency, equal-core, or audited TPC-H comparison. |
| Scans | Local scans are DuckDB on the Mac, not the phone or Databricks. Read counters have source-specific meanings; they are not a uniform measure of logical bytes or physical SSD traffic. Pool published warehouse counts before normalization. |
| Historical cost | The cost frontier is a single-core-normalized proxy with sampled prices and incomplete benchmark coverage. Some dates are first observations; the April 2014 cut is reconstructed. |
| Schema | Lineitem cardinality is approximate. The diagram shows logical relationships, not enforced dbgen constraints. |

The October 5 public scan audit downloaded the pinned Fivetran notebook cited
above and matched SHA-256
`1f79e0c39389652cbcf945e6b03bc1b1e2646e492a18ae520e5c0ba97f7a9d0f`.
Its cell 11 contains 54 embedded rows totaling 17,184,788 Snowflake and 63,276,038
Redshift queries. Pool separate tail observations into the final bucket. This
public-source check does not validate private Mac profiles. The raw public
capture is preserved in the optional local evidence archive.

All eight charts and diagrams were regenerated on October 7 from the retained
inputs. The timing and scan PNGs reflect the sentence-case YAML, and the cost
charts render successfully using the standalone inputs.
