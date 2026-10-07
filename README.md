# iPhone benchmark

This project contains the TPC-H comparison, the published scan-volume comparison,
and the historical AWS C-series compute-cost analysis.

## Final charts

- [TPC-H query runtime](charts/timing.png)
- [Data scanned per query](charts/scans.png)
- [Compute cost](charts/compute_cost.png) ([SVG](charts/compute_cost.svg))
- [2026 service price versus AWS CPU cost](charts/service_cost.png)
- [TPC-H schema](charts/tpch_schema.png)
- [Shuffle](charts/shuffle.png) ([SVG](charts/shuffle.svg))
- [Query distribution](charts/query_distribution.png) ([SVG](charts/query_distribution.svg))
- [Open data lake](charts/open_data_lake.png) ([SVG](charts/open_data_lake.svg))

The four data charts use dbt Charts with the vivid theme; the schema uses Mermaid.
The label-free shuffle and query distribution diagrams use the vivid palette in SVG.
The open data lake diagram uses the same palette with embedded Inter labels.
Titles use sentence case, preserving proper names and acronyms.

## Reproduce

- [IPHONE.md](IPHONE.md): build the native DuckDB app and run the phone benchmark.
- [DATABRICKS.md](DATABRICKS.md): generate/upload the same data and run serverless SQL.
- [CHARTS.md](CHARTS.md): render the eight charts and diagrams.
- [COMPUTE_COST.md](COMPUTE_COST.md): step-by-step lab notebook for repeating the
  AWS pricing/performance research and service comparison, with sources and calculations.

## Layout

```text
charts/                   chart inputs, definitions, renderers, icons, and final PNGs
  compute_cost_data.json  saved historical frontier, with price/benchmark provenance
results/
  results.duckdb          local TPC-H results and published histogram data (ignored)
  compute_cost/           optional local research evidence and results (ignored)
```

Executable code is confined to chart generation. Research procedures live in
the notebooks; repeating them requires browsing the cited sources or writing
new research code. The historical cost chart uses its tracked JSON input and
the service chart uses embedded inputs, so both render without a research archive.

The eight final PNGs and chart sources are version-controlled. Result databases,
downloaded evidence, alternate render formats, environments, and caches are
Git-ignored. The result databases and cost evidence are present locally as of
October 7, 2026, but are not supplied by a fresh clone. Copy local results when
transferring the experiment: timing and scan charts need the benchmark database,
and repeating those measurements requires the phone and Databricks.

See the [cost notebook](COMPUTE_COST.md) for pricing assumptions and hardware
limits, and [chart evidence notes](CHARTS.md#audit-and-evidence-limits) for the
benchmark caveats.
