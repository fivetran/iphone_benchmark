# Compute-cost lab notebook

This notebook records how we produced the [historical AWS compute-cost chart](charts/compute_cost.png)
and the [service-price comparison](charts/service_cost.png). The historical analysis
was assembled September 30, 2026; service hardware and prices were inspected
October 1 and audited October 5. The October 7 reorganization preserved the
calculations and chart observations; it did not collect new prices or run new
cloud benchmarks.

The research is described here so a human or AI agent can repeat it with a
browser, a spreadsheet, or newly written code. Only chart-generation code is
maintained in this project. Rendering the saved figures does not rerun the
research: the historical chart reads [103 saved observations](charts/compute_cost_data.json),
and the service chart contains its inputs in [its definition](charts/service_cost.yml).
See [CHARTS.md](CHARTS.md) for rendering commands.

## 1. Define the two questions and keep their units separate

For the historical chart, we asked: what was the lowest **observed** public
price for single-core-normalized capacity among measured AWS C-series instances?
We used Linux/UNIX, shared tenancy, Northern Virginia (`us-east-1`), nominal USD,
and public one- or three-year Reserved Instances (RIs) and Savings Plans (SPs).
We compared available payment options, assuming full-term utilization and no
financing cost. We excluded Spot, volume tiers, negotiated discounts, taxes,
separately billed EBS, transfer, and software licenses. Bundled RAM, networking,
and any included local disk remain part of the EC2 price.

For each eligible instance and commitment, calculate:

- Effective hourly price = upfront USD / (years × 365 × 24) + recurring USD/hour.
- Normalized cores = physical cores × Geekbench 6 single-core score / 1,000.
- USD per normalized core-hour = effective hourly price / normalized cores.

The score of 1,000 is an arbitrary unit anchor. Do not divide by vCPUs when SMT
exposes two threads per core. Do not use the multi-core Geekbench score. Multiplying
single-core performance by core count is a capacity model, not a measurement of
sustained whole-instance throughput: turbo, parallel scaling, memory contention,
and SMT throughput are outside this model.

For the service comparison, we asked: how does the service's on-demand price per
assumed or reported physical core compare with committed EC2 equivalents?
**There is no Geekbench normalization in this chart.** These are different units
and the two charts must not be combined as if they shared a denominator.

## 2. Assemble the C-series inventory and establish physical cores

Start with AWS's [compute-optimized instance specifications](https://docs.aws.amazon.com/ec2/latest/instancetypes/co.html)
and [supported CPU options](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/cpu-options-supported-instances-values.html).
For every size, record instance name, physical cores, threads per core, vCPUs,
and the source. Expand the inventory with all instance names found in historical
prices and the benchmark repository below. Include retired C1 and Cluster Compute
predecessors; the [CC1 launch announcement](https://aws.amazon.com/blogs/aws/the-new-amazon-ec2-instance-type-the-cluster-compute-instance/)
is evidence for an instance absent from modern tables. The original name filter
accepted names beginning with `c` followed by a digit, or `cc` followed by a digit.

Check that physical cores × threads per core equals vCPUs. Prefer AWS's explicit
size-specific counts; use saved guest topology only where appropriate for retired
hardware. Intel and older AMD instances generally expose two threads per core;
Graviton and C7a/C8a expose one. Do not apply a blanket “divide every vCPU count
by two” rule, and do not copy one size's topology to another.

Keep an audit row even when an instance cannot be priced or benchmarked. Our
saved inventory contained **327 configurations in 36 families/variants**:
252 eligible measurements, 59 missing measurements, 14 Flex exclusions, and two
retired-C1 topology exclusions. The 252 eligible measurements covered 27 families;
all had at least one price observation. The latest sampled RI/SP catalogs
contained 324 configurations, of which 252 had eligible measurements.

## 3. Obtain a size-specific single-core measurement

We pinned [Spare Cores' raw AWS data](https://github.com/SpareCores/sc-inspector-data/tree/5f5b4605dfaed33170a1ec85daa15db5ba08207e/data/aws)
to commit `5f5b4605dfaed33170a1ec85daa15db5ba08207e`. Enumerate the complete Git tree
rather than relying on GitHub's directory listing, which can omit entries beyond
its listing limit. For each instance directory, inspect:

- `geekbench/results.json`: `Single-Core Performance` → `Score` → `score`.
- `geekbench/meta.json`: benchmark version and start timestamp.
- `lscpu/stdout`: CPU model, architecture, CPU count, and threads per core.
- `geekbench/stdout`: only as a fallback when the parsed result is unavailable.

For example, the first chart winner has a [C3.2xlarge benchmark record](https://raw.githubusercontent.com/SpareCores/sc-inspector-data/5f5b4605dfaed33170a1ec85daa15db5ba08207e/data/aws/c3.2xlarge/geekbench/results.json).
The last has a [C9g.12xlarge benchmark record](https://raw.githubusercontent.com/SpareCores/sc-inspector-data/5f5b4605dfaed33170a1ec85daa15db5ba08207e/data/aws/c9g.12xlarge/geekbench/results.json).
The same pinned directory structure supplies metadata and topology for each.

We accepted Geekbench **6.3–6.7**, following the [Geekbench 6.7 compatibility note](https://www.geekbench.com/blog/2026/04/geekbench-67/).
GB7 and unsupported versions were excluded. A failed upload can still leave a
complete single-core summary in stdout: this recovered `c8a.metal-48xl`, with
its unavailable measurement timestamp left unknown. Incomplete subtests without
an explicit final summary do not establish a score. Never infer an unmeasured
size's score from a neighboring size.

We excluded Flex instances because a short burst score does not establish
sustained full-core capacity. Retired C1 had replaced CPUs and no sufficiently
verified physical-core mapping, so guest vCPU topology alone was insufficient.

Then assign a **valid-from date** to each measurement. A newer replacement CPU
must not be paired with an old price for the same instance name. Original
Skylake C5/C5d measurements, identified by model strings containing `8124`, were
allowed wherever historical prices existed. Other CPUs in smaller C5/C5d sizes
were allowed only from their measurement dates. Cascade Lake 12xlarge, 24xlarge,
and metal sizes were bounded by the [June 18, 2019 launch](https://aws.amazon.com/blogs/aws/now-available-new-c5-instance-sizes-and-bare-metal-instances/)
and their subsequent price availability. Other accepted measurements used the
analysis start date as their validity floor, with actual eligibility also
requiring a price observation for that instance.

These are modern runs on old and new hardware, not historical operating systems
or compilers. Usually there is one run per size; small differences may be noise.
Keep CPU identity, version, measured-at date, valid-from date, score, topology,
and source URL beside each measurement.

## 4. Recover historical commitment prices

Record observation date separately from a vendor's stated effective date.
The former says when the source was seen or published; it does not necessarily
say when a customer could first buy that price.

### November 2013 and the reconstructed April 2014 reduction

Use the [archived AWS Heavy Utilization RI table](https://gist.githubusercontent.com/ckelner/7490989/raw/8d5d70ded94b17e0c50b45e91f1511a1223fdb1d/linux-ri-heavy.json)
from [this November 15, 2013 gist](https://gist.github.com/ckelner/7490989).
Select region `us-east` (Northern Virginia) and C-series sizes. For each one- and
three-year term, pair `yrTerm1` or `yrTerm3` with its corresponding
`yrTerm1Hourly` or `yrTerm3Hourly`, then amortize using step 1. November 15 is the
first usable archived observation, not the beginning of EC2 or C-series history.

AWS's [March 2014 price announcement](https://aws.amazon.com/blogs/aws/aws-price-reduction-42-ec2-s3-rds-elasticache-and-elastic-mapreduce/)
stated a 30% reduction for new Linux C3 one- and three-year RI purchases,
effective April 1. We multiplied the preceding C3 effective hourly rates by
0.70. The old calculation also multiplied both upfront and recurring components
by 0.70; that split is a reconstruction, not a recovered complete fee schedule.
Label this observation accordingly. Existing reservations do not automatically
receive a newly purchased reservation's price.

### Archived RI observations, 2015–2022

Read `www/instances.json` at the 87 pinned commits of
[Vantage/ec2instances.info](https://github.com/vantage-sh/ec2instances.info)
listed in the source ledger below. Within each C-series instance, select
`pricing` → `us-east-1` → `linux` → `reserved`. Each term's positive numeric
value is already an effective hourly price; **do not amortize it again**.
Keep the term name and exact commit URL with the observation date.

The original snapshot selection was sampled, not continuous. Some archived
rates are rounded. C4 first appears in our usable observations on August 2,
2015, despite launching earlier that year. Do not relabel that point as its
launch or claim every intervening price change has been recovered.

### Official EC2 Reserved Instance catalogs

Use the [EC2 offer version index](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/index.json)
to locate the dated Northern Virginia catalogs in the source ledger. The original
selection used versions whose effective-begin date was January 1 or September 1
from 2022 onward; the version's publication date can be later than that date.
The ledger pins the actual catalogs rather than leaving this selection implicit.

Join `products` to `terms.Reserved` by SKU. Retain C-series products with
`productFamily = Compute Instance`, `operatingSystem = Linux`, `tenancy = Shared`,
`preInstalledSw = NA`, `capacitystatus = Used`, and `operation = RunInstances`.
For each term, read lease years, purchase option, offering class, and effective
date. Sum USD price dimensions with unit `Quantity` as upfront cost and those
with unit `Hrs` as recurring hourly cost. Reject unexpected units or non-base
ranges instead of silently treating them as ordinary rates. Amortize once using
step 1. Retain Standard and Convertible RI options when present; choose the
minimum eligible price later, not during collection.

### Savings Plans, from 2019 onward

Use the [Savings Plans version index](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/index.json)
and the [current offer](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/current/index.json)
to find regional catalogs. We sampled around these target dates, taking the
latest published version no later than each target: November 7, 2019; June 12,
2020; August 28, 2021; February 15 and May 24, 2022; August 18, 2023; September 27,
2024; September 30 and December 3, 2025; January 29, July 1, and September 30,
2026. The retained cache also contains a November 21, 2019 catalog; the source
ledger distinguishes cached catalogs from those actually used in the price panel.

Join each `terms.savingsPlan` entry to its product by SKU. Read the product's
family (EC2 Instance or Compute Savings Plan), purchase term, and payment option.
Within `rates`, select `discountedServiceCode = AmazonEC2`,
`discountedOperation = RunInstances`, Northern Virginia, and exact
`discountedUsageType = BoxUsage:<instance name>`. Older catalogs omit the redundant
region and instance fields; unprefixed `BoxUsage` identifies Northern Virginia.
Require hourly units and USD currency. The `discountedRate.price` is already an
effective hourly rate, including the upfront commitment's amortization; do not
add upfront cost again. Preserve its discounted SKU and offer/product SKU.

For all sources, retain prices even for instances without a usable benchmark.
Our combined price panel contained **62,666 records**. Hash downloaded catalogs
before discarding their large raw originals; preserve the extracted rows, URLs,
and hashes in the working evidence for a fresh study.

## 5. Join prices to benchmarks and select the observed frontier

Sort the union of price-observation dates and any benchmark valid-from dates
that fall within the pricing window. Maintain separate current snapshots for
RI and SP. At a new RI date, replace the entire preceding RI snapshot; do the
same independently for SP. Carry the latest snapshot forward only until its
next observation. Do not keep an old, cheaper product indefinitely, and do not
use a cumulative minimum that forces prices always to fall.

At each date, join current prices to an eligible measurement of the exact
instance size, require valid-from ≤ observation date, and calculate USD per
normalized core-hour. Select the smallest result across all eligible instances,
terms, and payment options. Retain the winning price's original observation
date, term, price source, and benchmark source alongside the frontier date.
Also record the ages of the RI and SP snapshots and the eligible candidate count.
An observation represents a **new purchase opportunity**, not the ability to
switch an existing three-year contract for free.

Keep every date even when the winner does not change. We obtained **103
observations**, from November 15, 2013 through September 29, 2026. For the
human-readable change list, we kept a row when either the instance changed or
the cost rounded to nine decimal places changed. The exact chart data preserves
unrounded values and all dates.

### Check the endpoints by hand

The initial winner was `c3.2xlarge`: $2,902 upfront for three years plus
$0.128/hour. Its effective rate was $2,902 / 26,280 + $0.128 =
**$0.2384261796042618/hour**. Four physical cores and a score of 717 give
4 × 717 / 1,000 = **2.868 normalized cores**. Dividing yields
**$0.08313325648684164 per normalized core-hour**.

The final winner was `c9g.12xlarge`, at **$0.79807/hour**, with 48 physical cores
and a score of 2,387. Thus 48 × 2,387 / 1,000 = **114.576 normalized cores** and
$0.79807 / 114.576 = **$0.006965420332355816 per normalized core-hour**.
The price comes from the [September 29, 2026 SP catalog](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/20260929170952/us-east-1/index.json),
three-year All Upfront EC2 Instance Savings Plan, offer SKU `Q4CRUAQBH89E99MA`
and discounted instance SKU `92EX9HD9BJAENJXX`.

The ratio is **11.9351×**, a **91.6214% decline**. This is the best observed value
among our measured and priced candidates, not proof of the global cheapest
possible AWS purchase or equivalent improvement for every application.

## 6. Keep volume discounts as a separate sensitivity

The published chart excludes volume tiers. A separate endpoint experiment asked
about a marginal purchase by a buyer already in the highest explicitly priced
public tier. The [older EC2 guide](https://awsdocs.s3.amazonaws.com/EC2/2013-10-15/ec2-ug-2013-10-15.pdf),
created March 21, 2014, documented 10%/20% tiers at $250,000/$2 million of active
RI upfront list fees per region. The [next saved guide](https://awsdocs.s3.amazonaws.com/EC2/2014-02-01/ec2-ug-2014-02-01.pdf),
created May 14, documented 5%/10% at those thresholds. We did not establish the
exact transition date.

The [RI pricing page](https://aws.amazon.com/ec2/pricing/reserved-instances/pricing/)
checked September 30, 2026 used 5%/10% tiers at $500,000/$4 million of total
reservation list value, including recurring payments. Thresholds therefore do
not measure the same thing across time. Apply the historical 20% scenario to
the initial rate; at the endpoint, reduce eligible Standard RI rates by 10%,
leave Convertible RIs and SPs unchanged, and choose the winner again. See
[AWS's RI discount rules](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts-reserved-instances-application.html)
and [RI/SP differences](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-ris.html).

We obtained a starting cost of **$0.06650660518947331**, while `c9g.12xlarge`
remained the endpoint winner at **$0.006965420332355816**. The best discounted
current Standard RI, `c8g.16xlarge`, was still higher at
**$0.0072558460822786655**. This gives **9.5481×**, or an **89.5267% decline**.
It is a sensitivity with an assumed historical tier, not a blended portfolio
bill or a complete historical discount curve.

## 7. Establish the service hardware denominators

### Snowflake: explicitly speculative

The requested scenario assumes X-Small is one `c7g.2xlarge` and Medium is four,
so Medium has **32 physical cores**. The motivating source is Maeda Kentaro's
[May 7, 2025 independent Gen2 investigation](https://medium.com/snowflake-engineering/deep-dive-inside-snowflakes-new-gen2-standard-warehouses-powered-by-aws-graviton3-6aacca73ae2d)
in the **unofficial** Snowflake Engineering Medium publication. It reports eight
logical processors, ARM64, CPU part `0xd40`, about 15.3 GiB of OS-visible memory,
and roughly 400 GB of disk, and infers Graviton3 / C7g.

The exact EC2 SKU, the one-node XS/four-node Medium mapping, and their continued
applicability in October 2026 are assumptions. The article does not prove the
node counts, and this project did not inspect a live Snowflake warehouse.
Use AWS's [C7g specifications](https://aws.amazon.com/ec2/instance-types/c7g/)
to check the equivalent's eight cores and 16 GiB of RAM. C7g is EBS-only; the
reported disk does not come free with that EC2 equivalent. C7gd is a different SKU.

### Databricks: reported configuration differs from active workers

On October 1 we started the existing AWS Premium serverless SQL XS, S, and M
warehouses, kept the ten-minute auto-stop setting, submitted a small generated-row
sum, and inspected query history, the cluster API, and the authenticated Spark UI.
To repeat the method on an authorized workspace:

1. Select AWS Northern Virginia serverless SQL warehouses of the three sizes.
   Start them and submit a read-only sum of integers from 0 through 999,999.
2. In query history, find that statement and record its Spark UI URL. Extract
   the cluster ID and inspect `/api/2.0/clusters/get` for total cores, total
   memory, configured worker count, driver type, and worker type.
3. Open the same query's Spark UI Executors page. Record active executor count,
   each executor's cores/task slots, completed tasks, and host-memory metrics.
   Exclude inactive warm-pool entries. Keep large driver/context IDs as strings;
   a floating-point JSON parser can round them.
4. On Medium, run a second generated-data probe: create 100 million integers
   across 96 input partitions, hash each with `xxhash64`, cast to double, and
   sum. Compare active executors and completed tasks before and after.
5. Record configured and active counts separately. Leave auto-stop enabled or
   stop the inspection resources after capture. A new run measures that run's
   allocation, not the allocation of a prior benchmark.

Our results were:

| Size | Driver cores / RAM | Configured workers | Active workers | Reported total cores / RAM |
| --- | --- | ---: | ---: | --- |
| XS | 8 / 64 GiB | 2 | 1 | 24 / 128 GiB |
| S | 16 / 128 GiB | 3 | 2 | 40 / 224 GiB |
| M | 32 / 256 GiB | 6 | 3 | 80 / 448 GiB |

Driver types were `serverless-driver-{8,16,32}cpu-graviton-gen4-aws`; workers
were `serverless-executor-32mem-graviton-gen4-aws`. Subtract driver cores from
total cores and divide by configured workers to obtain eight cores per worker.
Subtract configured workers × 32 GiB from total RAM to derive driver RAM.
Live executors independently showed eight cores each. OS-visible driver memory
was 61.63 / 123.52 / 247.21 GiB; workers showed 30.73 GiB. Do not confuse host
memory with Spark's smaller storage-memory pool.

The Medium hash probe succeeded with **three** active eight-core executors.
Completed-task counters rose from 9 / 8 / 8 to 42 / 40 / 40, or 97 additional
tasks. The API executor lists agreed with the UI's 1 / 2 / 3 active-worker counts,
despite configured counts of 2 / 3 / 6. This discrepancy remains unresolved.
The driver's zero Spark task slots do not imply zero driver CPUs or zero work.
No CPU quota, affinity, utilization, or exclusive host ownership was measured.

We used a 32-core/256-GiB `r8g.8xlarge` driver equivalent and six
8-core/32-GiB `m8g.2xlarge` worker equivalents for Medium. AWS's
[R8g](https://aws.amazon.com/ec2/instance-types/r8g/) and
[M8g](https://aws.amazon.com/ec2/instance-types/m8g/) specifications match these
shapes, but the actual EC2 SKUs were not exposed. All are EBS-only.
Databricks [documents that serverless architecture can change across restarts](https://docs.databricks.com/aws/en/admin/sql/serverless).
The public [warehouse sizing table](https://docs.databricks.com/aws/en/compute/sql-warehouse/warehouse-behavior)
for pro/classic i3 instances is not a serverless hardware specification.

The main chart uses **32 + 6 × 8 = 80 configured cores**, including the driver.
A sensitivity uses **32 + 3 × 8 = 56 host-shape cores**. Neither proves dedicated
CPU allocation. These later observations do not establish the hardware used
for the original TPC-H runs.

## 8. Recover contemporaneous service and EC2 prices

### Service prices, audited October 5

In the [Snowflake Credit Consumption Table](https://www.snowflake.com/legal-files/CreditConsumptionTable.pdf),
select AWS **Gen2 Medium**, table 1(b), page 2: **5.4 credits/hour**. Then select
**Standard edition**, Northern Virginia, table 2(a), page 4: **$2/credit**.
Generation and edition are distinct choices. We corrected an earlier error
that combined the Gen2 hardware hypothesis with Gen1's four credits/hour.
Gen2 gives **5.4 × $2 = $10.80/hour**, excluding storage, transfer, and separately
billed cloud services.

For Databricks, use the [official AWS calculator data](https://www.databricks.com/en-pricing-assets/data/pricing/AWS.json),
linked from its [pricing/instance page](https://www.databricks.com/product/pricing/product-pricing/instance-types).
Filter `cloud = AWS`, `plan = Premium`, `region = US East (N. Virginia)`, and
`compute = SQL Serverless Compute`. Read `dburate`, `baserate`, and `hourrate`.
We recorded:

| Size | DBU/hour | USD/DBU | USD/hour |
| --- | ---: | ---: | ---: |
| X-Small | 6 | 0.70 | 4.20 |
| Small | 12 | 0.70 | 8.40 |
| Medium | 24 | 0.70 | 16.80 |

Serverless infrastructure is included. Adding an EC2 bill to the service
numerator would double-count it. These are public list prices, not invoices,
trial credits, negotiated rates, or measured billed uptime. The October 5
current source corroborated the October 1 assumptions but is not an archived
October 1 tariff.

### AWS equivalent prices

For the comparison dated October 1, use the
[September 29, 2026 regional Savings Plans catalog](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/20260929170952/us-east-1/index.json).
Select **EC2 Instance Savings Plans**, Northern Virginia, **3yr**, **All Upfront**,
Linux/shared `RunInstances`, and the exact `BoxUsage` instance size. This service
comparison fixes the commitment type; it does not repeat the historical chart's
minimization across all RI/SP options.

| Instance | Effective USD/hour | Offer/product SKU | Discounted instance SKU | Rate effective date |
| --- | ---: | --- | --- | --- |
| c7g.2xlarge | 0.11090 | QPV6FSY56NBTGC4N | N8XXGSFK676QFC8T | 2024-07-01 |
| r8g.8xlarge | 0.74425 | 7XHMTEUBNUF4YA9D | ZQH8GWX9C5JG5FHD | 2024-07-09 |
| m8g.2xlarge | 0.14175 | K8ZS8HTR5V7YM2DD | J7KUHQQVD4RH56V4 | 2024-09-25 |

The [October 3 catalog](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/20261003071546/us-east-1/index.json),
checked October 5, gave the same three rates. The [current regional index](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/current/region_index.json)
is a discovery starting point for a new study, not a substitute for these dated
sources. Use `discountedRate.price` directly as effective USD/hour.

An earlier version mixed the R8g SP price with an M8g RI of $3,725 / 26,280 hours.
We standardized both on verified SP rates; the six-worker total changed by only
$0.000043379/hour, leaving the displayed ratio unchanged.

## 9. Calculate and audit the service bars

For Snowflake, divide the hourly service and equivalent AWS costs by 32 cores:

- Service: $10.80 / 32 = **$0.337500000/core-hour**.
- AWS: 4 × $0.11090 / 32 = **$0.013862500/core-hour**.
- Ratio: $0.3375 / $0.0138625 = **24.3×**, rounded only for display.

For Databricks' six configured workers, divide by 80 cores:

- Service: $16.80 / 80 = **$0.210000000/core-hour**.
- AWS: ($0.74425 + 6 × $0.14175) / 80 = **$0.019934375/core-hour**.
- Ratio: $0.21 / $0.019934375 = **10.5×**.

For the three observed workers, divide by 56 cores instead:

- Service: $16.80 / 56 = **$0.300000000/core-hour**.
- AWS: ($0.74425 + 3 × $0.14175) / 56 = **$0.020883929/core-hour**.
- Ratio using unrounded values: **14.4×**. This is a sensitivity, not the main bar.

The AWS denominator includes RAM and baseline network capability as part of the
instance price; “CPU cost” is shorthand for instance cost divided by cores.
Attached storage, IOPS, throughput, data transfer, global services, software,
and operations are not priced. We did not subtract those functions from the
service numerator. These ratios are neither gross margins nor like-for-like
TCO savings. A fully utilized three-year All Upfront commitment and service
on-demand pricing are different purchasing terms. An intermittently running
warehouse cannot treat a commitment as pay-only-while-running. Query timings
alone cannot recover a bill with idle time, loading, setup, minimum billing,
auto-stop, cooling, and other costs.

## 10. Turn completed calculations into chart inputs

Save one record per frontier date with its exact instance, hourly price, score,
physical cores, normalized cores, normalized cost, original price observation
date, term, and price/benchmark source URLs. The maintained
[chart input](charts/compute_cost_data.json) is an exact export of the 103
original frontier records, checked against the locally retained SQLite table
on October 7. It is the completed result of the research, not a new collector.
Its SHA-256 at export was
`6f2a5f0b6556b3b58c7a521763f538dc67f23c70ec029a132fc55c2cdc420dbf`.

[The historical chart](charts/compute_cost.yml) reads that JSON through dbt Charts.
It plots a continuous date axis with step-after interpolation and a logarithmic
$0.005–$0.10 cost axis. A final display point at September 30 repeats the last
September 29 value; it is not another price observation. Annotation stems start
at actual observations. Their date/value offsets only position labels and must
not be fed back into the research calculations.

[The service chart](charts/service_cost.yml) contains the step-9 inputs directly.
Its log axis is USD per **physical** core-hour. Each floating bar spans the AWS
and service prices; its ratio label is positioned at the geometric midpoint,
the square root of their product. Hidden horizontal slots separate the two
services and do not encode elapsed time.

A fresh repetition should check topology identities, score-version eligibility,
valid-from dates, positive prices, correct amortization, independent RI/SP
snapshot replacement, and per-date minima. Compare endpoint arithmetic and
coverage counts before reproducing the picture. If new measurements or sources
change the result, retain the old study's dates and explain the difference
rather than silently overwriting its claims.

The old collectors, builder, hardware note, and audit were consolidated into
this notebook. Local downloaded evidence and raw service captures were moved to
the Git-ignored `results/compute_cost/` working archive; no research code is
required there. The archive is optional and is not supplied by a fresh clone.
Public sources and the exact snapshot ledger below allow the research to be
reconstructed; chart rendering only needs the tracked chart inputs.

## Source ledger for repeating the original study

The following entries preserve the source selection, rather than requiring the
old collection scripts or a private list of commits. When repeating the study,
record new access dates and hashes; current websites can change. All reported
hashes below are historical evidence, not a fresh October 7 download audit.

### Service-source hashes

| Source / captured version | SHA-256 |
| --- | --- |
| AWS SP, September 29, 2026 catalog | `8eca45186ad2af97eb935503ef83cc727783789363ad6943a170c3d63d99189c` |
| AWS SP, October 3, 2026 catalog; checked October 5 | `552212abe310a980e94b14e24cb95b4986d539a4ba55a33df365cdf0bb9f2bb7` |
| Databricks AWS calculator, October 5 | `8498c685da6d6ec878fc95a5f0aff9412e28f6c0e9cde0cc165db9fd2fba46ee` |
| Snowflake consumption PDF, earlier capture | `c2507c3e1a97ca002ad9dfdf5a6aab87dbeb7c28e8a3313e1cb546169247c9ad` |
| Snowflake consumption PDF, October 5 recheck | `83c3305a0d316ac0ba2eab9b15f3fcf8dfde0b54d434bbc1c9f66e7eda657b17` |

### Original frontier changes

These are arithmetic checkpoints from the saved analysis, including small
rounding changes. The chart input also retains dates with no change.

| Date | Instance | Effective USD/hour | GB6 single | Physical cores | USD/normalized core-hour |
| --- | --- | ---: | ---: | ---: | ---: |
| 2013-11-15 | c3.2xlarge | 0.238426179604 | 717 | 4 | 0.0831332564868 |
| 2014-04-01 | c3.2xlarge | 0.166898325723 | 717 | 4 | 0.0581932795408 |
| 2015-08-02 | c4.8xlarge | 0.6874 | 1213 | 18 | 0.0314830081524 |
| 2016-01-13 | c4.8xlarge | 0.653 | 1213 | 18 | 0.029907483741 |
| 2016-12-10 | c4.8xlarge | 0.621 | 1213 | 18 | 0.0284418796373 |
| 2017-11-12 | c5.9xlarge | 0.558 | 1189 | 18 | 0.0260723296888 |
| 2018-11-28 | c5.9xlarge | 0.558029 | 1189 | 18 | 0.0260736847024 |
| 2019-06-19 | c5.metal | 1.488052 | 1456 | 48 | 0.0212919528388 |
| 2019-11-07 | c5.metal | 1.488 | 1456 | 48 | 0.0212912087912 |
| 2020-06-11 | c6g.metal | 0.8182 | 987 | 64 | 0.0129527608916 |
| 2020-09-20 | c6g.metal | 0.818189 | 987 | 64 | 0.0129525867528 |
| 2022-02-01 | c6g.metal | 0.8182 | 987 | 64 | 0.0129527608916 |
| 2022-05-23 | c7g.16xlarge | 0.8874 | 1533 | 64 | 0.00904476516634 |
| 2022-10-04 | c7g.16xlarge | 0.887366818874 | 1533 | 64 | 0.00904442696993 |
| 2023-08-17 | c7g.metal | 0.8874 | 1540 | 64 | 0.0090036525974 |
| 2024-09-25 | c8g.16xlarge | 0.976217656012 | 1892 | 64 | 0.00806205120253 |
| 2024-09-27 | c8g.metal-24xl | 1.46433 | 1903 | 96 | 0.00801546899632 |
| 2025-12-02 | c8a.16xlarge | 1.32149 | 2825 | 64 | 0.00730912610619 |
| 2026-06-30 | c9g.12xlarge | 0.79807 | 2387 | 48 | 0.00696542033236 |

### Pinned archived RI snapshots

Each link is the exact `www/instances.json` file at the recorded commit. Of the
87 inspected snapshots, 85 contributed eligible prices; the first two did not.

| Observation date | Archived file / commit | Used in price panel |
| --- | --- | --- |
| 2015-08-02 | [af15809316f3](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/af15809316f3fe64169dc86e1e41eee19a759e65/www/instances.json) | No eligible rows |
| 2015-08-02 | [310ac5640e49](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/310ac5640e490e9432458bda530ca335f382044c/www/instances.json) | No eligible rows |
| 2015-08-02 | [b3662c0ddd00](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/b3662c0ddd0037eb096716b7bfa51a645f98b15f/www/instances.json) | Yes |
| 2015-11-07 | [ff9096088b27](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/ff9096088b2767202c970410c8e881e753687f51/www/instances.json) | Yes |
| 2015-12-12 | [ab9904b1f2e5](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/ab9904b1f2e58218eb93941792c9e90d8512f6af/www/instances.json) | Yes |
| 2015-12-16 | [585984c3ae54](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/585984c3ae542b1e2470f169a8e91301709cf618/www/instances.json) | Yes |
| 2015-12-17 | [85ee2dd3ec60](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/85ee2dd3ec60fd20d7703b9ff99aec0d1a1a8cb5/www/instances.json) | Yes |
| 2016-01-02 | [92387e243ab8](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/92387e243ab817600985479ffb8a51c9f10860cc/www/instances.json) | Yes |
| 2016-01-13 | [a572356d32a5](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/a572356d32a535ed8805f0855d3f4b8cbbae1225/www/instances.json) | Yes |
| 2016-02-24 | [e65876e68d05](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/e65876e68d05860e1abbf9bf1ff30569055bb2c8/www/instances.json) | Yes |
| 2016-02-24 | [65efaf417c5b](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/65efaf417c5bacbc877b7574253a28da0e4aa757/www/instances.json) | Yes |
| 2016-02-27 | [a54449568e61](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/a54449568e612f6f0c8b383f6af77363598a57c9/www/instances.json) | Yes |
| 2016-03-05 | [bc0d2a7ecab0](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/bc0d2a7ecab0a8e8bb363749ed8eeca320c1b0d2/www/instances.json) | Yes |
| 2016-04-18 | [d62d1be10533](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/d62d1be10533b123255500e6c51bb3f5aa2a256f/www/instances.json) | Yes |
| 2016-05-19 | [e1341f0821cd](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/e1341f0821cdbb7396a973bc111fe3398d27935d/www/instances.json) | Yes |
| 2016-05-20 | [16b64c42a4e9](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/16b64c42a4e9cc4926a247fb122dccce711ff23b/www/instances.json) | Yes |
| 2016-06-03 | [f6c403c2fe0f](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/f6c403c2fe0f065a3b3b84e45ad7d0571aa6f6fa/www/instances.json) | Yes |
| 2016-06-23 | [d6fdf62c26a9](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/d6fdf62c26a9af7c8a8c6cbede01593611d9e46f/www/instances.json) | Yes |
| 2016-06-28 | [fa2f92fda8d0](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/fa2f92fda8d093d36646085f0f4751327079561f/www/instances.json) | Yes |
| 2016-06-29 | [6ddf151f1fb9](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/6ddf151f1fb9b00e89923d6133b43d2d04a81978/www/instances.json) | Yes |
| 2016-08-13 | [e424600544aa](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/e424600544aa4abb8d3177d69fcbb2d1331d0251/www/instances.json) | Yes |
| 2016-09-27 | [630e1a334a4f](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/630e1a334a4f8d66e30006958c93b29669fb45db/www/instances.json) | Yes |
| 2016-10-11 | [abb48f794d37](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/abb48f794d37af4262d3fd2bc41da0566d5e9135/www/instances.json) | Yes |
| 2016-10-19 | [ff72c2f698c0](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/ff72c2f698c0991790af7ab0e0a589c1b86302b8/www/instances.json) | Yes |
| 2016-10-26 | [f34075aa09c5](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/f34075aa09c52233735cd879ebda3f70d77b7ca5/www/instances.json) | Yes |
| 2016-11-30 | [0ecf7b6cb689](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/0ecf7b6cb6897351280156b34e23f284294d5dbd/www/instances.json) | Yes |
| 2016-12-10 | [d2250b8c5785](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/d2250b8c578573f1a6eb900a1e89a21da04d9bfb/www/instances.json) | Yes |
| 2016-12-14 | [e655e36660bc](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/e655e36660bc617713c4ef9a1409cc65a209cb27/www/instances.json) | Yes |
| 2017-01-23 | [6e6d8dec5963](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/6e6d8dec5963b4549632c1ef03bc3f399defbcca/www/instances.json) | Yes |
| 2017-01-31 | [45852ed51f32](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/45852ed51f328872ce2d9e2f9aa892be2970b420/www/instances.json) | Yes |
| 2017-02-18 | [f815d7eb07dd](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/f815d7eb07ddd90cc6bd81ff43ec9aec1e3cc8c3/www/instances.json) | Yes |
| 2017-02-24 | [9611e64de0f0](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/9611e64de0f037f08e20a7c49908824ec7fb2e11/www/instances.json) | Yes |
| 2017-02-24 | [d81a0618f551](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/d81a0618f5511b330ece2454a4f50c338375abbe/www/instances.json) | Yes |
| 2017-02-27 | [3a3115579ffa](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/3a3115579ffa82b9874025e7fb13199643e952c7/www/instances.json) | Yes |
| 2017-03-01 | [d3d6bf362e57](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/d3d6bf362e57906993509ee4dc2738131a92b724/www/instances.json) | Yes |
| 2017-03-02 | [76a09724f352](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/76a09724f352fe0b203ec2d468108c443b1c746b/www/instances.json) | Yes |
| 2017-03-10 | [39eaa8d4b8f4](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/39eaa8d4b8f4846a477ed84e103c9faaa15d12ef/www/instances.json) | Yes |
| 2017-04-23 | [1cb1e66275ac](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/1cb1e66275ac7b5cfa0a4690c5724e8c5ca20623/www/instances.json) | Yes |
| 2017-05-19 | [cc15a3bf361e](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/cc15a3bf361efb258ab83fc074fb9c88514cd4c2/www/instances.json) | Yes |
| 2017-05-19 | [5daf41071b18](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/5daf41071b1835fdae14c136fddd7d7bae1fae2c/www/instances.json) | Yes |
| 2017-06-18 | [56a07d472b54](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/56a07d472b54dab4d5aebf23b38956cd4eb8f3c5/www/instances.json) | Yes |
| 2017-07-13 | [fc22b98520b6](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/fc22b98520b6e24a345ad0b9202051b16bf622b3/www/instances.json) | Yes |
| 2017-07-20 | [8dbdc18c3f82](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/8dbdc18c3f8265af5006271cf52a4affa5374484/www/instances.json) | Yes |
| 2017-08-07 | [13a93d68f5e3](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/13a93d68f5e37e2fc4f07be2a351f24602b35cf8/www/instances.json) | Yes |
| 2017-08-07 | [12a6d38c0d67](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/12a6d38c0d67851da6262cf2528821b2855a0282/www/instances.json) | Yes |
| 2017-08-16 | [96cb57e69789](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/96cb57e697893f720a26ece35a730d458c507a51/www/instances.json) | Yes |
| 2017-10-26 | [3f430174ab51](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/3f430174ab51c58db6a764578f2dcc0f3908ab37/www/instances.json) | Yes |
| 2017-10-26 | [fe3b46075b9d](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/fe3b46075b9da0cfa9e38326a825a97ffd4fcb6f/www/instances.json) | Yes |
| 2017-11-12 | [94e1f006efae](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/94e1f006efae8f18a8194d9122ae7daee179fb5e/www/instances.json) | Yes |
| 2017-11-29 | [5c5579d716eb](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/5c5579d716eb42019b5a759f59832c3b8b89cbb4/www/instances.json) | Yes |
| 2017-12-29 | [b634be0c7f3e](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/b634be0c7f3e981545f1b627c056d0036f64b214/www/instances.json) | Yes |
| 2018-03-13 | [7f56b73918d9](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/7f56b73918d9d98f88e135443c94bc7c7a78b9f0/www/instances.json) | Yes |
| 2018-04-10 | [4fadbc40563c](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/4fadbc40563c0cb791902258561579919c31fefa/www/instances.json) | Yes |
| 2018-05-13 | [1ef910353cc0](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/1ef910353cc0914f7833cf4f3f57579133e4b8b4/www/instances.json) | Yes |
| 2018-06-04 | [d5614a18a74d](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/d5614a18a74d0e70f0e4efefef7422f679b83060/www/instances.json) | Yes |
| 2018-06-04 | [a17bd79bd7bd](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/a17bd79bd7bd11d3e3009349e876702815ae427f/www/instances.json) | Yes |
| 2018-06-08 | [1978f76799fa](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/1978f76799fad0d11f1bba28af1b954c76d6590c/www/instances.json) | Yes |
| 2018-08-01 | [2e9fb2cb6ba5](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/2e9fb2cb6ba5bffbf532e62599856a9a57adeb44/www/instances.json) | Yes |
| 2018-08-14 | [d2b46f60627e](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/d2b46f60627e65b44356251a4ca6558a30e4065c/www/instances.json) | Yes |
| 2018-08-22 | [acd973261819](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/acd973261819475f3f0765baaedb13c65988d6ce/www/instances.json) | Yes |
| 2018-09-24 | [ab43445cc188](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/ab43445cc188b53a9a9dd45159b2543e8a5b8470/www/instances.json) | Yes |
| 2018-09-28 | [06073d93b71e](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/06073d93b71edfc0d13654393df400320ad6eae6/www/instances.json) | Yes |
| 2018-10-12 | [2f62b3907fd1](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/2f62b3907fd1fd7fe17686cd5ae4f59f6e5aed5e/www/instances.json) | Yes |
| 2018-10-20 | [ad6f668fe0e2](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/ad6f668fe0e27f43b1c87257c6499831ced2f1da/www/instances.json) | Yes |
| 2018-11-28 | [e52d3beeea8d](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/e52d3beeea8d614fa3e0c25c2f48c62f23c59250/www/instances.json) | Yes |
| 2018-12-05 | [967c408b8ced](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/967c408b8ced026feab0aaa2e288615a93931e34/www/instances.json) | Yes |
| 2019-05-12 | [44cfb0aa516a](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/44cfb0aa516a93792452a93044aaf0410eb6d489/www/instances.json) | Yes |
| 2019-06-19 | [9bf3765ff23f](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/9bf3765ff23fd11a0a6fae9c1b8b69f0ca5fb6c5/www/instances.json) | Yes |
| 2019-06-28 | [4de34e095f6a](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/4de34e095f6ad955981a6a18b5c159cd8673f5ac/www/instances.json) | Yes |
| 2019-07-10 | [2ab3aeccd462](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/2ab3aeccd462cce955b048ff3fe3818b753a3a40/www/instances.json) | Yes |
| 2019-07-16 | [b56e2e38ebb5](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/b56e2e38ebb5f8d9e20b9cfd73aa89d58db7b8bb/www/instances.json) | Yes |
| 2019-07-26 | [be49c852e1a2](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/be49c852e1a23a2c2504841c666579b2ea94d5aa/www/instances.json) | Yes |
| 2019-09-23 | [d484d3c73bed](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/d484d3c73bed14d7a64a777d09cafb1c7c3101ca/www/instances.json) | Yes |
| 2019-09-28 | [8e8b016c7f3d](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/8e8b016c7f3d39dde98d57032fa349d5af46f037/www/instances.json) | Yes |
| 2019-10-21 | [493ccbfffa58](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/493ccbfffa58725985640f1dfdff6743309f02e6/www/instances.json) | Yes |
| 2019-11-04 | [151366ca191a](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/151366ca191aeff6e7f84d5f03b13db0765c346a/www/instances.json) | Yes |
| 2019-11-08 | [aa49013385fc](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/aa49013385fc2f7caf0a9d58f260ba8064479f0e/www/instances.json) | Yes |
| 2019-11-22 | [a3506b32cd33](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/a3506b32cd33377b7734babe9b586723c89ca447/www/instances.json) | Yes |
| 2019-11-30 | [00573910a38d](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/00573910a38da31a1d8495601c8ded861c99b4a4/www/instances.json) | Yes |
| 2020-06-02 | [70b380e63cb1](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/70b380e63cb14b90ecad6f6a0350c5176fd80aca/www/instances.json) | Yes |
| 2020-09-20 | [91f4e12ec9cc](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/91f4e12ec9cc909a9e762837c6273a1cab1c4c71/www/instances.json) | Yes |
| 2020-11-15 | [2a197f691b82](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/2a197f691b825a38bbdc2faa3c7a58f30de215ab/www/instances.json) | Yes |
| 2021-07-09 | [c8fb72bb0e23](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/c8fb72bb0e23b17fd29df5d1f34b470182b0c79e/www/instances.json) | Yes |
| 2021-07-09 | [26fcfae08e93](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/26fcfae08e93e5a3e038deb4423993890f1089ab/www/instances.json) | Yes |
| 2021-08-03 | [14ede5a54df6](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/14ede5a54df6e33be6ccf96ae9cb60e168635844/www/instances.json) | Yes |
| 2021-12-21 | [d7116b10318f](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/d7116b10318f3b3eef9f2e9a1737da19be024919/www/instances.json) | Yes |
| 2022-01-18 | [4c10336bd130](https://raw.githubusercontent.com/vantage-sh/ec2instances.info/4c10336bd130453c95d42d8bcd8e44d98c310d0c/www/instances.json) | Yes |

### Official EC2 RI catalogs

Only catalogs actually used in the original price panel are listed. Hashes
refer to the full downloaded catalogs, before filtering.

| Version / regional catalog | SHA-256 |
| --- | --- |
| [20220201224621](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20220201224621/us-east-1/index.json) | `99b31cf626b81247ba4bbbf6fa0da2317ee977309c0a5a5ef68eb639dc271273` |
| [20221004190654](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20221004190654/us-east-1/index.json) | `458d527645646c7a8956066a7ca0078d2326a4ba0ef0b2db2183c45887bec912` |
| [20230127181505](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20230127181505/us-east-1/index.json) | `8774eadea573756d5b43bceda1b5bf13c350a1d976b6b1a54f5eaa373dedf0fc` |
| [20230928174545](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20230928174545/us-east-1/index.json) | `8010f3dbdd849431fd29ab58279a3bb9ac42a5fd787e3986b5c4ea4314f0b904` |
| [20240205184227](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20240205184227/us-east-1/index.json) | `520f4b5d14a8acfb6a4ac69eaa4a8957da279ea3fec6e08ccc9ad500a91f7127` |
| [20240925190622](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20240925190622/us-east-1/index.json) | `e2f24026a64602311eb5ea341fa07d7a0f31671d5a8f9ca89603f684b498337c` |
| [20250203145209](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20250203145209/us-east-1/index.json) | `ea1424d410a7f770ca18060adbe21d228f1845ce45fbcd91c11afd3cb6171a2f` |
| [20250930212021](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20250930212021/us-east-1/index.json) | `036773a2d0fe1445ddc661265923e0c2dd01a400bfde65c82c2e956533d84fed` |
| [20260129082055](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20260129082055/us-east-1/index.json) | `0ccc9734ac1057e9618e0c4377d73adf30d523d7c12c04d7d3c1d312ec0af1cf` |
| [20260925174521](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20260925174521/us-east-1/index.json) | `a822b8b9ae885a3e6027860ea08d26c0a3c83db47fcede71db96b7b2b265a502` |

### Official Savings Plans catalogs

Only catalogs actually used in the original price panel are listed. Hashes
refer to the full downloaded catalogs, before filtering.

| Version / regional catalog | SHA-256 |
| --- | --- |
| [20191107232537](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/20191107232537/us-east-1/index.json) | `945e91309a2272e47155ebb9fe986e9e2a55cef0aa067bfd2d7de1df5fea2504` |
| [20200611193302](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/20200611193302/us-east-1/index.json) | `4a5277b23972a9a04a9a95660a68791352d318f36a8ba08d6a9340fcba1a5e43` |
| [20210827233633](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/20210827233633/us-east-1/index.json) | `ea9166db528283c72a1135b9c81da1c8fb0d83594cf5b05cbffd78abbb149997` |
| [20220215191159](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/20220215191159/us-east-1/index.json) | `e3adab55f7b897933da05e4d5d4d6034b312e01b433cc21ce28b0986f1f214e9` |
| [20220523160844](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/20220523160844/us-east-1/index.json) | `8f828b8ba2218c6b6ae1b2d24ca3f66d34b28206e5e89de54baba6bd7f424550` |
| [20230817195151](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/20230817195151/us-east-1/index.json) | `a2a76eeb9c3201d8d3499b2bcd76d272e3e7b0e785be5433c8ecbafcfdbe02ba` |
| [20240927175252](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/20240927175252/us-east-1/index.json) | `5eeffbb08eb3ad5d7f4fe0235d00bba896979a135e28596199ce10075f28e41f` |
| [20250925223655](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/20250925223655/us-east-1/index.json) | `09d02d82f7cf87e643153eab2ce56cdacf3446aec8ad28a7127881c00540400e` |
| [20251202141709](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/20251202141709/us-east-1/index.json) | `5181384c62ab96fd2fdba739c4f37b9304a409a6207ab2ae5d6194aaa9ba8de7` |
| [20260129081157](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/20260129081157/us-east-1/index.json) | `60e8cac9ac91c732a451a8a97a4a1ed92117d202e7600eda36ba58adca3b481d` |
| [20260630175841](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/20260630175841/us-east-1/index.json) | `dbd6c2d41205c55e5cd8b1242f728521b6fb423be92a086f54cd6c1065af262e` |
| [20260929170952](https://pricing.us-east-1.amazonaws.com/savingsPlan/v1.0/aws/AWSComputeSavingsPlan/20260929170952/us-east-1/index.json) | `8eca45186ad2af97eb935503ef83cc727783789363ad6943a170c3d63d99189c` |
