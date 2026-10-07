# Reproduce DuckDB on iPhone 17 Pro

Use a physical **iPhone 17 Pro**, native arm64 DuckDB **1.5.6**, optimized **Release / -O3**, **6 threads**, **6GB memory_limit**, and disk spilling enabled. The original phone reported iOS 27.0.1 (24A446), approximately 12 GB physical memory, and no attached debugger. It was externally cooled with an ice pack. Wait for iOS `thermalState == nominal` immediately before **every execution**, including each repetition. The app polls once per second and rechecks after status-file I/O. This is an OS thermal classification, not a Celsius temperature or proof of an exact clock frequency.

Run scale factors **200, 100, 50, 25**, then queries 1–22 at each scale, with two consecutive repetitions per query. Each execution opens a fresh read-only DuckDB database/connection and enables JSON profiling. The OS file cache is retained. The plotted elapsed interval covers `duckdb_query`, full conversion of results to strings and result destruction, including planning/compilation. It excludes opening the database, profiling setup, cooling waits, transfer/hash checks, JSON saving and connection teardown.

## Prepare the Mac and phone

First follow the extraction, environment and data-generation sections of [DATABRICKS.md](DATABRICKS.md). Running Databricks itself is not required to run the phone. The shared bootstrap exports the exact SQL and saved reference results from [results/results.duckdb](results/results.duckdb).

Install full Xcode and its iOS SDK, CMake and Ninja. The original build used Xcode 27.0 (27A266a). The app targets iOS 17 or newer, requests the increased-memory-limit entitlement, statically links `core_functions`, and disables runtime extension loading. The TPC-H generator runs on the Mac; the phone needs only DuckDB's query engine. `6GB` means 6,000,000,000 buffer bytes, reported as `5.5 GiB`; it is not a cap on total app memory.

A human must sign into an Apple development team in Xcode, accept any developer agreements, pair/trust the Mac, enable Developer Mode on the phone and confirm its restart prompts. Connect by USB, unlock the phone and trust the developer identity if prompted. Use a signing team that permits the increased-memory-limit entitlement; verify it in the signed app. Keep Low Power Mode off and the benchmark app in the foreground. Provide roughly 130 GB free phone storage for SF200 chunks, assembly, an existing database and spill headroom. Keep the phone and connector dry while using external cooling.

```sh
brew install cmake ninja
xcodebuild -version
xcrun devicectl list devices
export DEVICE='YOUR-DEVICE-IDENTIFIER'
export APPLE_TEAM='YOUR-APPLE-TEAM-ID'
export BUNDLE_ID='com.yourcompany.tpchphone'
bash .work/ios/build.sh
codesign -d --entitlements :- .work/ios/build/app/Release-iphoneos/TPCHPhone.app
xcrun devicectl device install app --device "$DEVICE" .work/ios/build/app/Release-iphoneos/TPCHPhone.app
xcrun devicectl device process launch --device "$DEVICE" --terminate-existing "$BUNDLE_ID" --keep-awake
.work/.venv/bin/python .work/ios/prepare_inputs.py
```

The initial launch creates transfer directories without starting queries. Do not launch through Xcode's debugger for measured runs. Confirm the signed entitlements include `com.apple.developer.kernel.increased-memory-limit = true` and the DuckDB CMake cache/compiler command uses Release `-O3` before proceeding.

```bash file=.work/ios/build.sh
#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${DEVICE:?Set DEVICE}"
: "${APPLE_TEAM:?Set APPLE_TEAM}"
: "${BUNDLE_ID:?Set BUNDLE_ID}"
mkdir -p ios/vendor ios/build
archive=ios/vendor/duckdb-v1.5.6.tar.gz
if [[ ! -f "$archive" ]]; then
  curl -fL https://github.com/duckdb/duckdb/archive/refs/tags/v1.5.6.tar.gz -o "$archive"
fi
printf '%s  %s\n' 1fadcbe9e69e1470f9093b6bcde08daf477d729c449e59a807f45c346622099b "$archive" | shasum -a 256 -c -
if [[ ! -f ios/vendor/duckdb-1.5.6/CMakeLists.txt ]]; then
  tar -xzf "$archive" -C ios/vendor
fi
cmake -S ios/vendor/duckdb-1.5.6 -B ios/build/duckdb -G Ninja \
  -DCMAKE_SYSTEM_NAME=iOS -DCMAKE_OSX_SYSROOT=iphoneos \
  -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_OSX_DEPLOYMENT_TARGET=17.0 \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER_LAUNCHER='' -DCMAKE_CXX_COMPILER_LAUNCHER='' \
  -DBUILD_SHELL=OFF -DBUILD_UNITTESTS=OFF -DENABLE_SANITIZER=OFF -DENABLE_UBSAN=OFF \
  -DENABLE_JEMALLOC=OFF -DDISABLE_EXTENSION_LOAD=ON -DSKIP_EXTENSIONS=parquet \
  -DOVERRIDE_GIT_DESCRIBE=v1.5.6-0-g069cc9f9b5 -DDUCKDB_EXPLICIT_PLATFORM=ios_arm64
cmake --build ios/build/duckdb --parallel 8 \
  --target duckdb_static core_functions_extension duckdb_generated_extension_loader
cmake -S ios -B ios/build/app -G Xcode -DCMAKE_SYSTEM_NAME=iOS \
  -DCMAKE_OSX_SYSROOT=iphoneos -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_OSX_DEPLOYMENT_TARGET=17.0
xcodebuild -project ios/build/app/TPCHPhone.xcodeproj -scheme TPCHPhone \
  -configuration Release -destination "id=$DEVICE" \
  -allowProvisioningUpdates -allowProvisioningDeviceRegistration build
python3 - <<'PYCODE'
from pathlib import Path
import hashlib,json,subprocess
app=Path('ios/build/app/Release-iphoneos/TPCHPhone.app')
assert app.is_dir(), app
manifest={'duckdb_version':'1.5.6','source_commit':'069cc9f9b5be802405797faecc284961b07c70ef',
'source_archive_sha256':'1fadcbe9e69e1470f9093b6bcde08daf477d729c449e59a807f45c346622099b',
'configuration':'Release','compiler_optimization':'-O3','architecture':'arm64',
'xcode':subprocess.check_output(['xcodebuild','-version'],text=True),
'executable_sha256':hashlib.sha256((app/'TPCHPhone').read_bytes()).hexdigest(),
'runner_source_sha256':hashlib.sha256(Path('ios/App/main.mm').read_bytes()).hexdigest()}
Path('ios/build_manifest.json').write_text(json.dumps(manifest,indent=2))
PYCODE
```

```cmake file=.work/ios/CMakeLists.txt
cmake_minimum_required(VERSION 3.25)
project(TPCHPhone LANGUAGES C CXX OBJCXX)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/App/Info.plist")
set(CMAKE_CXX_STANDARD 17)
add_executable(TPCHPhone MACOSX_BUNDLE App/main.mm)
target_include_directories(TPCHPhone PRIVATE vendor/duckdb-1.5.6/src/include)
target_compile_options(TPCHPhone PRIVATE -fobjc-arc)
target_link_libraries(TPCHPhone PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/build/duckdb/src/libduckdb_static.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/build/duckdb/extension/libduckdb_generated_extension_loader.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/build/duckdb/extension/core_functions/libcore_functions_extension.a"
    "-framework UIKit" "-framework Foundation")
set_target_properties(TPCHPhone PROPERTIES
    MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_SOURCE_DIR}/App/Info.plist"
    XCODE_ATTRIBUTE_PRODUCT_BUNDLE_IDENTIFIER "$ENV{BUNDLE_ID}"
    XCODE_ATTRIBUTE_DEVELOPMENT_TEAM "$ENV{APPLE_TEAM}"
    XCODE_ATTRIBUTE_CODE_SIGN_STYLE "Automatic"
    XCODE_ATTRIBUTE_CODE_SIGN_IDENTITY "Apple Development"
    XCODE_ATTRIBUTE_CODE_SIGN_ENTITLEMENTS "${CMAKE_CURRENT_SOURCE_DIR}/App/TPCHPhone.entitlements"
    XCODE_ATTRIBUTE_TARGETED_DEVICE_FAMILY "1"
    XCODE_ATTRIBUTE_ENABLE_BITCODE "NO"
    XCODE_ATTRIBUTE_CLANG_ENABLE_OBJC_ARC "YES"
    XCODE_ATTRIBUTE_ASSETCATALOG_COMPILER_GENERATE_SWIFT_ASSET_SYMBOL_EXTENSIONS "NO")
```

```xml file=.work/ios/App/Info.plist
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
<key>CFBundleExecutable</key><string>$(EXECUTABLE_NAME)</string>
<key>CFBundleName</key><string>TPCHPhone</string>
<key>CFBundleDisplayName</key><string>TPC-H DuckDB</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>1.0</string>
<key>CFBundleVersion</key><string>1</string>
<key>LSRequiresIPhoneOS</key><true/>
<key>UILaunchScreen</key><dict/>
<key>UIApplicationSceneManifest</key><dict>
  <key>UIApplicationSupportsMultipleScenes</key><false/>
  <key>UISceneConfigurations</key><dict>
    <key>UIWindowSceneSessionRoleApplication</key><array><dict>
      <key>UISceneConfigurationName</key><string>Default</string>
      <key>UISceneDelegateClassName</key><string>SceneDelegate</string>
    </dict></array>
  </dict>
</dict>
<key>UIFileSharingEnabled</key><true/>
<key>LSSupportsOpeningDocumentsInPlace</key><true/>
<key>UISupportedInterfaceOrientations</key><array><string>UIInterfaceOrientationPortrait</string></array>
</dict></plist>
```

```xml file=.work/ios/App/TPCHPhone.entitlements
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>com.apple.developer.kernel.increased-memory-limit</key><true/>
</dict></plist>
```

## Transfer, cool and measure

The preparer hashes each generated database and packages the unchanged SQL, query hashes and row counts. The sweep transfers one scale at a time in 1 GiB chunks, with resumable upload checkpoints. The app assembles the file, verifies its complete SHA-256 against the Mac, deletes consumed chunks and checks table counts before executing anything timed. This makes transfer time irrelevant to the chart.

```sh
.work/.venv/bin/python .work/ios/sweep.py
```

Leave the app open and externally cooled until all four scales finish. The host prints query progress and thermal state (`0` means nominal). Cooling can pause a run without adding to its query timings. Disconnects during polling can be recovered by reconnecting and unlocking the phone; the app saves a checkpoint after each completed execution. Rerunning the same host command uses the saved run IDs and skips completed executions. Do not change source databases, reinstall the app, or clear device storage during a resume. If app data or transfer chunks were manually removed, discard the matching host upload checkpoint before retransferring. Use a new output directory for a fresh experiment; never pool partially completed and fresh runs as repetitions.

```python file=.work/ios/prepare_inputs.py
"""Package exact saved SQL and hashes of the existing source databases."""
import argparse
import hashlib
import json
from pathlib import Path
import duckdb

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--scales', nargs='+', type=float, default=[200,100,50,25])
scales = parser.parse_args().scales
with duckdb.connect(str(root.parent/'results/results.duckdb'), read_only=True) as c:
    saved = c.execute('SELECT query,sql FROM queries ORDER BY query').fetchall()
queries = []
for number, sql in saved:
    assert (root/'queries'/f'q{number:02}.sql').read_text() == sql
    queries.append({'query':number, 'sql':sql, 'sha256':hashlib.sha256(sql.encode()).hexdigest()})
for sf in scales:
    assert sf in [25, 50, 100, 200]
    label = f'{sf:g}'
    path = root/'data'/f'tpch_sf{label}.duckdb'
    dest = root/'results/iphone_device'/f'sf{label}'
    dest.mkdir(parents=True, exist_ok=True)
    metadata = json.loads((root/f'results/sf{label}/metadata.json').read_text())
    stat = path.stat()
    cache = dest/'input.json'
    previous = json.loads(cache.read_text()) if cache.exists() else {}
    if previous.get('source_bytes') == stat.st_size and previous.get('source_mtime_ns') == stat.st_mtime_ns:
        sha = previous['database_sha256']
    else:
        print(f'Hashing SF{label}: {stat.st_size/2**30:.2f} GiB', flush=True)
        with path.open('rb') as f:
            sha = hashlib.file_digest(f, 'sha256').hexdigest()
    manifest = {'scale_factor':sf, 'database_sha256':sha, 'table_rows':metadata['table_rows'], 'queries':queries,
                'source_bytes':stat.st_size, 'source_mtime_ns':stat.st_mtime_ns}
    if previous.get('database_sha256') == sha and 'database_chunks' in previous:
        manifest['database_chunks'] = previous['database_chunks']
    cache.write_text(json.dumps(manifest, indent=2)+'\n')
    print(f'Prepared SF{label}: {sha}', flush=True)
```

```python file=.work/ios/sweep.py
"""Transfer and run the four original datasets on the connected physical iPhone."""
import argparse
import os
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT/'results/iphone_device'
DEVICE = os.environ['DEVICE']
APP = os.environ['BUNDLE_ID']


def save(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2)+'\n')
    temp.replace(path)


def command(arguments, log):
    with log.open('a') as f:
        subprocess.run(['xcrun', 'devicectl', *arguments], stdout=f, stderr=subprocess.STDOUT,
                       cwd=ROOT, check=True)


def copy(source, destination, direction, log, extra=None):
    command(['device', 'copy', direction, '--device', DEVICE, '--source', str(source),
             '--destination', str(destination), '--domain-type', 'appDataContainer',
             '--domain-identifier', APP, *(extra or [])], log)


def upload_chunks(source, folder, manifest):
    chunk_size = 1024**3
    chunks = []
    for index, offset in enumerate(range(0, source.stat().st_size, chunk_size)):
        chunks.append({'path':f'staging/sf{int(manifest["scale_factor"])}/part-{index:04}.bin',
                       'bytes':min(chunk_size, source.stat().st_size-offset)})
    manifest['database_chunks'] = chunks
    save(folder/'input.json', manifest)
    state_path = folder/'chunk_uploads.json'
    prior = json.loads(state_path.read_text()) if state_path.exists() else {}
    uploaded = prior.get('files',{}) if prior.get('source_sha256') == manifest['database_sha256'] else {}
    stage = ROOT/'data/.iphone_stage'
    stage.mkdir(parents=True,exist_ok=True)
    with source.open('rb') as reader:
        for index, part in enumerate(chunks):
            if str(index) in uploaded: continue
            local = stage/f'part-{index:04}.bin'
            reader.seek(index*chunk_size)
            digest = hashlib.sha256()
            remaining = part['bytes']
            with local.open('wb') as writer:
                while remaining:
                    data = reader.read(min(8*1024**2,remaining))
                    assert data, 'Unexpected source EOF'
                    writer.write(data); digest.update(data); remaining -= len(data)
            start = time.monotonic()
            for attempt in range(3):
                try:
                    copy(local, 'Documents/'+part['path'], 'to', folder/'upload.log',
                         ['--json-output',str(folder/f'chunk-{index:04}-transfer.json')])
                    break
                except subprocess.CalledProcessError:
                    if attempt == 2: raise
                    print(f'Chunk {index+1}: connection interrupted; retrying',flush=True)
                    time.sleep(5)
            result = json.loads((folder/f'chunk-{index:04}-transfer.json').read_text())
            assert result['info']['outcome'] == 'success'
            assert result['result']['file']['metadata']['size'] == part['bytes']
            uploaded[str(index)] = {**part,'sha256':digest.hexdigest(),'upload_seconds':time.monotonic()-start}
            save(state_path,{'source_sha256':manifest['database_sha256'],'files':uploaded})
            local.unlink()
            print(f'SF{manifest["scale_factor"]:g}: uploaded chunk {index+1}/{len(chunks)} '
                  f'({sum(v["bytes"] for v in uploaded.values())/2**30:.2f} GiB)',flush=True)


def run(sf, selection):
    folder = DEST/f'sf{sf}'
    manifest = json.loads((folder/'input.json').read_text())
    entry = selection['runs'].setdefault(str(sf), {'run_id':str(uuid.uuid4()).upper(), 'complete':False})
    save(DEST/'sweep_selection.json', selection)
    run_id = entry['run_id']
    exported = folder/'exported'/run_id
    if entry['complete']:
        assert (exported/'validation.json').exists()
        print(f'SF{sf}: already complete and validated', flush=True)
        return
    source = ROOT/'data'/f'tpch_sf{sf}.duckdb'
    assert source.stat().st_size == manifest['source_bytes']
    assert source.stat().st_mtime_ns == manifest['source_mtime_ns']
    # Read the actual device marker; a host checkpoint alone is not proof of transfer.
    ready_path=folder/'device_ready.json'
    try:
        copy('Documents/tpch_current.duckdb.ready.json',ready_path,'from',folder/'control.log')
        ready=json.loads(ready_path.read_text())
    except subprocess.CalledProcessError:
        ready={}
    if ready.get('sha256') != manifest['database_sha256']:
        print(f'SF{sf}: uploading {source.stat().st_size/2**30:.2f} GiB over USB',flush=True)
        upload_chunks(source,folder,manifest)
    copy(folder/'input.json', f'Documents/input_sf{sf}.json', 'to', folder/'control.log')
    print(f'SF{sf}: launching native run {run_id}', flush=True)
    command(['device','process','launch','--device',DEVICE,'--terminate-existing',APP,
             '--run','--scale',str(sf),'--run-id',run_id,'--memory-limit','6GB','--wait-for-nominal','--keep-awake'], folder/'control.log')
    started = time.monotonic()
    previous = None
    last_notice = 0
    while True:
        time.sleep(10)
        try:
            copy('Documents/status.json', folder/'status.json', 'from', folder/'control.log')
        except subprocess.CalledProcessError:
            if time.monotonic()-started >= 7200: raise
            print('Status read interrupted; reconnect and unlock the phone. Waiting.',flush=True)
            continue
        status = json.loads((folder/'status.json').read_text())
        if status.get('run_id') != run_id:
            assert time.monotonic()-started < 120, 'App did not start the requested run'
            continue
        progress = status['phase'], status['query'], status['repeat']
        if progress != previous or time.monotonic()-last_notice > 45:
            print(f'SF{sf}: {progress}; thermal={status["memory"]["thermal_state"]}; '
                  f'{time.monotonic()-started:.0f}s since launch', flush=True)
            previous, last_notice = progress, time.monotonic()
        if status['phase'] in ['complete','failed']:
            exported.parent.mkdir(parents=True, exist_ok=True)
            copy(f'Documents/results/{run_id}', exported, 'from', folder/'control.log')
            shutil.copy2(ROOT/'ios/build_manifest.json', exported/'build_manifest.json')
            assert status['phase'] == 'complete', (exported/'metadata.json').read_text()
            break
        assert time.monotonic()-started < 7200, 'Scale exceeded two hours; saved checkpoint retained'
    subprocess.run([sys.executable,str(ROOT/'ios/validate.py'),str(exported)],check=True,cwd=ROOT)
    entry['complete'] = True
    entry['completed_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save(DEST/'sweep_selection.json', selection)
    print(f'SF{sf}: complete; all 44 query results validated', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scales', nargs='+', type=int, default=[200,100,50,25])
    args = parser.parse_args()
    assert all(s in [200,100,50,25] for s in args.scales)
    path = DEST/'sweep_selection.json'
    selection = json.loads(path.read_text()) if path.exists() else {
        'scale_order':[200,100,50,25], 'threads':6, 'memory_limit':'6GB', 'wait_for_nominal':True, 'runs':{}}
    for sf in args.scales:
        run(sf, selection)
    # Restore normal idle locking after the sweep; this launch does not run queries.
    command(['device','process','launch','--device',DEVICE,'--terminate-existing',APP,
             '--scale',str(args.scales[-1])], DEST/'finish.log')


if __name__ == '__main__':
    main()
```

## Validate and retain

For every scale, the sweep exports all 44 measurements, profile JSON, complete query results and metadata, then runs the validator below. It checks exact SQL/database hashes, row counts, six threads, effective 6 GB buffer limit, nominal starts, Low Power Mode off and no debugger. Numeric/result validation uses the same reference and tolerances as [DATABRICKS.md](DATABRICKS.md). Results are saved in `.work/results/iphone_device/results.duckdb` and exported run folders. Do not replace the retained chart data unless the whole sweep passes.

```python file=.work/ios/validate.py
"""Validate an exported iPhone run and store its measurements in DuckDB."""
import argparse
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT/'results/iphone_device'


def normalized(result):
    types = result['types']
    assert all(len(row) == len(types) for row in result['rows'])
    numeric = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 16, 19, 28, 32}
    return [[{'number':v, 'kind':'float' if t in {10, 11} else 'Decimal'}
             if v is not None and t in numeric else v
             for v, t in zip(row, types)] for row in result['rows']]


def sortkey(row):
    return tuple((0, '') if v is None else (1, Decimal(v['number'])) if isinstance(v, dict)
                 else (2, v) for v in row)


def compare(actual, expected):
    assert len(actual) == len(expected)
    maximum = Decimal(0)
    for a, b in zip(sorted(actual, key=sortkey), sorted(expected, key=sortkey)):
        assert len(a) == len(b)
        for x, y in zip(a, b):
            if isinstance(x, dict) and isinstance(y, dict):
                error = abs(Decimal(x['number']) - Decimal(y['number']))
                tolerance = (max(Decimal('1e-6'), abs(Decimal(y['number']))*Decimal('1e-14'))
                             if 'float' in [x['kind'], y['kind']] else Decimal(0))
                assert error <= tolerance, (x, y, error)
                maximum = max(maximum, error)
            else:
                assert x == y, (x, y)
    return str(maximum)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    folder = parser.parse_args().run_directory.resolve()
    metadata = json.loads((folder/'metadata.json').read_text())
    measurements = json.loads((folder/'measurements.json').read_text())
    sf = metadata['scale_factor']
    label = f'{sf:g}'
    manifest_path = DEST/f'sf{label}/input.json'
    manifest = json.loads(manifest_path.read_text())
    references = json.loads((ROOT/'reference'/f'sf{label}.json').read_text())
    assert metadata['status'] == 'complete' and metadata['executions'] == 44
    assert sf in [25,50,100,200] and metadata['duckdb_version'] == 'v1.5.6'
    assert metadata['threads'] == 6 and metadata['memory_limit'] == '6GB'
    assert metadata['settings'][0][:2] == ['6', '5.5 GiB']
    assert metadata['debugger_attached'] is False
    assert all(x['debugger_attached'] is False for x in metadata.get('launches', []))
    assert metadata['database_sha256'] == manifest['database_sha256']
    assert metadata['table_rows'] == manifest['table_rows']
    source = ROOT/'data'/f'tpch_sf{label}.duckdb'
    if 'source_bytes' in manifest:
        assert source.stat().st_size == manifest['source_bytes']
        assert source.stat().st_mtime_ns == manifest['source_mtime_ns']
    else:
        assert hashlib.file_digest(source.open('rb'), 'sha256').hexdigest() == manifest['database_sha256']
    assert metadata['wait_for_nominal'] is True
    assert all(r['memory_before']['thermal_state']==0 for r in measurements)
    assert all(not r['memory_before']['low_power_mode'] for r in measurements)
    assert len(measurements) == 44
    assert {(r['query'], r['repeat']) for r in measurements} == {(q, r) for q in range(1, 23) for r in [1, 2]}
    queries = {q['query']:q for q in manifest['queries']}
    for q in queries.values():
        assert (ROOT/'queries'/f'q{q["query"]:02}.sql').read_text() == q['sql']
        assert hashlib.sha256(q['sql'].encode()).hexdigest() == q['sha256']
    profiles = {}
    for row in measurements:
        q, rep = row['query'], row['repeat']
        assert row['query_sha256'] == queries[q]['sha256']
        assert math.isfinite(row['wall_seconds']) and row['wall_seconds'] > 0
        result = json.loads((folder/f'q{q:02}_r{rep}_result.json').read_text())
        assert len(result['rows']) == row['rows_returned']
        row['maximum_numeric_error'] = compare(normalized(result), references[str(q)])
        profile = json.loads((folder/f'q{q:02}_r{rep}_profile.json').read_text())
        assert profile['query_name'] == queries[q]['sql']
        profiles[q, rep] = profile
    means = [sum(r['wall_seconds'] for r in measurements if r['query'] == q)/2 for q in range(1, 23)]
    geomean = math.exp(sum(map(math.log, means))/22)
    summary = {'status':'passed', 'run_id':metadata['run_id'], 'scale_factor':sf,
        'executions':44, 'geomean_seconds':geomean, 'mean_suite_seconds':sum(means),
        'maximum_numeric_error':str(max(Decimal(r['maximum_numeric_error']) for r in measurements)),
        'database_sha256':metadata['database_sha256'], 'memory_before':metadata['memory_before'],
        'memory_after':metadata['memory_after'],
        'thermal_states':sorted({r[k]['thermal_state'] for r in measurements for k in ['memory_before','memory_after']}),
        'maximum_profile_buffer_bytes':max(p['system_peak_buffer_memory'] for p in profiles.values()),
        'maximum_profile_temp_bytes':max(p['system_peak_temp_dir_size'] for p in profiles.values())}
    (folder/'validation.json').write_text(json.dumps(summary, indent=2)+'\n')
    with duckdb.connect(str(DEST/'results.duckdb')) as c:
        c.execute('CREATE TABLE IF NOT EXISTS runs (run_id VARCHAR PRIMARY KEY, scale_factor DOUBLE, metadata JSON, validation JSON)')
        c.execute('''CREATE TABLE IF NOT EXISTS measurements (run_id VARCHAR, query INTEGER, repeat INTEGER,
            wall_seconds DOUBLE, rows_returned BIGINT, details JSON, profile JSON, result JSON,
            PRIMARY KEY(run_id,query,repeat))''')
        c.execute('CREATE TABLE IF NOT EXISTS queries (query INTEGER PRIMARY KEY, sql VARCHAR, sha256 VARCHAR)')
        c.execute('BEGIN')
        c.execute('INSERT OR REPLACE INTO runs VALUES (?,?,?,?)', [metadata['run_id'],sf,json.dumps(metadata),json.dumps(summary)])
        for row in measurements:
            q, rep = row['query'], row['repeat']
            c.execute('INSERT OR REPLACE INTO measurements VALUES (?,?,?,?,?,?,?,?)',
                [metadata['run_id'],q,rep,row['wall_seconds'],row['rows_returned'],json.dumps(row),
                 json.dumps(profiles[q,rep]),(folder/f'q{q:02}_r{rep}_result.json').read_text()])
        c.executemany('INSERT OR REPLACE INTO queries VALUES (?,?,?)',[(q['query'],q['sql'],q['sha256']) for q in queries.values()])
        c.execute('''CREATE OR REPLACE VIEW query_summary AS SELECT run_id, query,
            avg(wall_seconds) mean_seconds FROM measurements GROUP BY ALL''')
        c.execute('''CREATE OR REPLACE VIEW scale_summary AS SELECT run_id, scale_factor, count(*) queries,
            exp(avg(ln(mean_seconds))) geomean_seconds, sum(mean_seconds) mean_suite_seconds
            FROM query_summary JOIN runs USING(run_id) GROUP BY ALL''')
        c.execute('COMMIT')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
```

The original selected runs had all 176 starts and all 176 post-query snapshots nominal, with all result sets passing validation. Expected aggregates and retained run IDs:

| Scale | Geomean seconds | Run ID |
|---:|---:|---|
| 25 | 0.463052 | 695351E1-B874-4D96-B48F-A55FDA05090D |
| 50 | 1.355626 | 6EAA4CF3-6218-4A63-A0D9-0FB7E4554FAB |
| 100 | 2.626181 | 055BFEF6-E253-4E0C-BCDE-5B9129D5B038 |
| 200 | 6.021557 | 11F932C6-A533-4552-84DD-AFED8A1C9345 |

Compute each point as `exp(avg(ln(mean_query_seconds)))` across 22 queries after averaging the two elapsed measurements for each query. These observed times can vary on another run. [CHARTS.md](CHARTS.md) describes importing a complete rerun and regenerating the PNGs.

## Native app source

The source below preserves the measured timer, DuckDB API calls, JSON profiling and thermal-gate behavior. Defaults are restricted to the final six-thread, 6 GB, nominal-start configuration. No Swift bridge or Python interpreter runs on the phone.

```objc file=.work/ios/App/main.mm
#import <UIKit/UIKit.h>
#import <Foundation/Foundation.h>
#import <CommonCrypto/CommonDigest.h>
#import <mach/mach.h>
#import <os/proc.h>
#include <sys/sysctl.h>
#include <unistd.h>
#include <chrono>
#include <stdexcept>
#include "duckdb.h"

static NSString *Docs() {
    return NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).firstObject;
}
static NSString *Argument(NSString *name, NSString *fallback) {
    NSArray *args = [NSProcessInfo processInfo].arguments;
    NSUInteger index = [args indexOfObject:name];
    return index != NSNotFound && index + 1 < args.count ? args[index+1] : fallback;
}
static NSString *SHA(NSData *data) {
    unsigned char digest[CC_SHA256_DIGEST_LENGTH];
    CC_SHA256(data.bytes, (CC_LONG)data.length, digest);
    NSMutableString *out = [NSMutableString string];
    for (unsigned char x : digest) [out appendFormat:@"%02x", x];
    return out;
}
static NSString *FileSHA(NSString *path) {
    NSFileHandle *file = [NSFileHandle fileHandleForReadingAtPath:path];
    if (!file) throw std::runtime_error("Input database is missing");
    CC_SHA256_CTX ctx; CC_SHA256_Init(&ctx);
    while (true) {
        @autoreleasepool {
            NSData *data = [file readDataOfLength:1024*1024];
            if (!data.length) break;
            CC_SHA256_Update(&ctx, data.bytes, (CC_LONG)data.length);
        }
    }
    [file closeFile];
    unsigned char digest[CC_SHA256_DIGEST_LENGTH]; CC_SHA256_Final(digest, &ctx);
    NSMutableString *out = [NSMutableString string];
    for (unsigned char x : digest) [out appendFormat:@"%02x", x];
    return out;
}
static void Save(NSString *path, id object) {
    NSError *error = nil;
    NSData *data = [NSJSONSerialization dataWithJSONObject:object options:NSJSONWritingPrettyPrinted error:&error];
    if (!data || ![data writeToFile:path options:NSDataWritingAtomic error:&error])
        throw std::runtime_error(error.localizedDescription.UTF8String ?: "Cannot save result");
}
static NSDictionary *Memory() {
    task_vm_info_data_t info = {};
    mach_msg_type_number_t count = TASK_VM_INFO_COUNT;
    kern_return_t status = task_info(mach_task_self(), TASK_VM_INFO, (task_info_t)&info, &count);
    uint64_t footprint = status == KERN_SUCCESS ? info.phys_footprint : 0;
    uint64_t available = os_proc_available_memory();
    return @{@"physical_footprint_bytes":@(footprint), @"available_bytes":@(available),
        @"estimated_process_budget_bytes":@(footprint + available), @"task_info_status":@(status),
        @"thermal_state":@([NSProcessInfo processInfo].thermalState),
        @"low_power_mode":@([NSProcessInfo processInfo].lowPowerModeEnabled)};
}
static NSDictionary *Storage() {
    NSDictionary *attributes = [[NSFileManager defaultManager] attributesOfFileSystemForPath:Docs() error:nil];
    return @{@"free_bytes":attributes[NSFileSystemFreeSize] ?: @0,
             @"total_bytes":attributes[NSFileSystemSize] ?: @0};
}
static void Status(NSString *runID, NSString *scale, NSString *phase, int query = 0, int repeat = 0) {
    Save([Docs() stringByAppendingPathComponent:@"status.json"],
         @{@"run_id":runID, @"scale_factor":@([scale doubleValue]), @"phase":phase,
           @"query":@(query), @"repeat":@(repeat), @"memory":Memory(), @"storage":Storage()});
}
static BOOL DebuggerAttached() {
    int mib[] = {CTL_KERN, KERN_PROC, KERN_PROC_PID, getpid()};
    struct kinfo_proc info = {}; size_t size = sizeof(info);
    return sysctl(mib, 4, &info, &size, nullptr, 0) == 0 && (info.kp_proc.p_flag & P_TRACED);
}
struct Connection {
    duckdb_database db = nullptr;
    duckdb_connection conn = nullptr;
    Connection(NSString *path, NSString *temp) {
        duckdb_config config = nullptr;
        if (duckdb_create_config(&config) == DuckDBError) throw std::runtime_error("Cannot create DuckDB config");
        if (duckdb_set_config(config, "access_mode", "READ_ONLY") == DuckDBError ||
            duckdb_set_config(config, "threads", "6") == DuckDBError ||
            duckdb_set_config(config, "memory_limit", Argument(@"--memory-limit", @"6GB").UTF8String) == DuckDBError ||
            duckdb_set_config(config, "temp_directory", temp.UTF8String) == DuckDBError) {
            duckdb_destroy_config(&config); throw std::runtime_error("Cannot apply DuckDB settings");
        }
        char *error = nullptr;
        auto state = duckdb_open_ext(path.UTF8String, &db, config, &error);
        duckdb_destroy_config(&config);
        if (state == DuckDBError) {
            std::string message = error ? error : "Cannot open database";
            duckdb_free(error); throw std::runtime_error(message);
        }
        if (duckdb_connect(db, &conn) == DuckDBError) {
            duckdb_close(&db); throw std::runtime_error("Cannot connect");
        }
    }
    ~Connection() { if (conn) duckdb_disconnect(&conn); if (db) duckdb_close(&db); }
};
static NSArray *Execute(duckdb_connection conn, NSString *statement, NSArray **types = nullptr) {
    duckdb_result result = {};
    if (duckdb_query(conn, statement.UTF8String, &result) == DuckDBError) {
        std::string message = duckdb_result_error(&result) ?: "SQL error";
        duckdb_destroy_result(&result); throw std::runtime_error(message);
    }
    NSMutableArray *columnTypes = [NSMutableArray array];
    for (idx_t c = 0; c < duckdb_column_count(&result); ++c)
        [columnTypes addObject:@(duckdb_column_type(&result, c))];
    NSMutableArray *rows = [NSMutableArray array];
    for (idx_t r = 0; r < duckdb_row_count(&result); ++r) {
        NSMutableArray *row = [NSMutableArray array];
        for (idx_t c = 0; c < duckdb_column_count(&result); ++c) {
            if (duckdb_value_is_null(&result, c, r)) [row addObject:[NSNull null]];
            else {
                char *value = duckdb_value_varchar(&result, c, r);
                [row addObject:value ? [NSString stringWithUTF8String:value] : [NSNull null]];
                duckdb_free(value);
            }
        }
        [rows addObject:row];
    }
    duckdb_destroy_result(&result);
    if (types) *types = columnTypes;
    return rows;
}

@interface RunnerController : UIViewController
@property(nonatomic, strong) UITextView *text;
@property(nonatomic, strong) UIButton *button;
@property(nonatomic) BOOL running;
@end

@implementation RunnerController
- (void)viewDidLoad {
    [super viewDidLoad]; self.view.backgroundColor = UIColor.systemBackgroundColor;
    self.button = [UIButton buttonWithType:UIButtonTypeSystem];
    [self.button setTitle:[NSString stringWithFormat:@"Run SF%@", Argument(@"--scale", @"200")] forState:UIControlStateNormal];
    [self.button addTarget:self action:@selector(startRun) forControlEvents:UIControlEventTouchUpInside];
    self.button.translatesAutoresizingMaskIntoConstraints = NO;
    self.text = [[UITextView alloc] init]; self.text.editable = NO;
    self.text.font = [UIFont monospacedSystemFontOfSize:13 weight:UIFontWeightRegular];
    self.text.translatesAutoresizingMaskIntoConstraints = NO;
    [self.view addSubview:self.button]; [self.view addSubview:self.text];
    UILayoutGuide *safe = self.view.safeAreaLayoutGuide;
    [NSLayoutConstraint activateConstraints:@[
        [self.button.topAnchor constraintEqualToAnchor:safe.topAnchor constant:12],
        [self.button.centerXAnchor constraintEqualToAnchor:safe.centerXAnchor],
        [self.text.topAnchor constraintEqualToAnchor:self.button.bottomAnchor constant:12],
        [self.text.leadingAnchor constraintEqualToAnchor:safe.leadingAnchor constant:12],
        [self.text.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor constant:-12],
        [self.text.bottomAnchor constraintEqualToAnchor:safe.bottomAnchor]]];
    [self log:@"DuckDB · native iPhone benchmark\n6 threads · 6 GB · spilling enabled\n"];
    [self log:[NSString stringWithFormat:@"Initial memory: %@", Memory()]];
    if ([[NSProcessInfo processInfo].arguments containsObject:@"--keep-awake"])
        UIApplication.sharedApplication.idleTimerDisabled = YES;
    for (NSString *scale in @[@"200", @"100", @"50", @"25"])
        [[NSFileManager defaultManager] createDirectoryAtPath:[Docs() stringByAppendingPathComponent:[@"staging/sf" stringByAppendingString:scale]]
            withIntermediateDirectories:YES attributes:nil error:nil];
    Save([Docs() stringByAppendingPathComponent:@"device_preflight.json"],
         @{@"memory":Memory(), @"storage":Storage(), @"duckdb_version":@(duckdb_library_version())});
    if ([[NSProcessInfo processInfo].arguments containsObject:@"--run"])
        dispatch_async(dispatch_get_main_queue(), ^{ [self startRun]; });
}
- (void)log:(NSString *)line {
    fprintf(stdout, "%s\n", line.UTF8String); fflush(stdout);
    dispatch_async(dispatch_get_main_queue(), ^{
        self.text.text = [self.text.text stringByAppendingFormat:@"%@\n", line];
        [self.text scrollRangeToVisible:NSMakeRange(self.text.text.length, 0)];
    });
}
- (void)startRun {
    if (self.running) return;
    self.running = YES; self.button.enabled = NO; UIApplication.sharedApplication.idleTimerDisabled = YES;
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
        @autoreleasepool { [self benchmark]; }
        dispatch_async(dispatch_get_main_queue(), ^{
            self.running = NO; self.button.enabled = YES;
            UIApplication.sharedApplication.idleTimerDisabled = [[NSProcessInfo processInfo].arguments containsObject:@"--keep-awake"];
        });
    });
}
- (void)benchmark {
    NSString *scale = Argument(@"--scale", @"200");
    NSString *memoryLimit = Argument(@"--memory-limit", @"6GB");
    BOOL waitForNominal = YES;
    NSString *runID = Argument(@"--run-id", NSUUID.UUID.UUIDString);
    NSString *output = [Docs() stringByAppendingPathComponent:[@"results/" stringByAppendingString:runID]];
    [[NSFileManager defaultManager] createDirectoryAtPath:output withIntermediateDirectories:YES attributes:nil error:nil];
    NSMutableDictionary *metadata = [@{@"run_id":runID, @"scale_factor":@([scale doubleValue]), @"threads":@6,
        @"memory_limit":memoryLimit, @"repeats":@2, @"build_configuration":@"Release",
        @"wait_for_nominal":@(waitForNominal), @"thermal_poll_seconds":@1,
        @"duckdb_version":@(duckdb_library_version()), @"os_version":[NSProcessInfo processInfo].operatingSystemVersionString,
        @"physical_memory_bytes":@([NSProcessInfo processInfo].physicalMemory),
        @"cpu_count":@([NSProcessInfo processInfo].processorCount), @"memory_before":Memory(),
        @"started_at":[[NSISO8601DateFormatter new] stringFromDate:[NSDate date]],
        @"timing_scope":@"duckdb_query plus complete result conversion to strings and result destruction; excludes connection setup and JSON serialization",
        @"profiling":@"json", @"debugger_attached":@(DebuggerAttached()), @"status":@"running"} mutableCopy];
    try {
        if (![memoryLimit isEqualToString:@"6GB"])
            throw std::runtime_error("Unsupported memory limit");
        if (![@[@"25", @"50", @"100", @"200"] containsObject:scale])
            throw std::runtime_error("Unsupported scale");
        if (![[NSUUID alloc] initWithUUIDString:runID]) throw std::runtime_error("Invalid run UUID");
        NSString *metadataPath = [output stringByAppendingPathComponent:@"metadata.json"];
        if ([[NSFileManager defaultManager] fileExistsAtPath:metadataPath]) {
            NSDictionary *prior = [NSJSONSerialization JSONObjectWithData:[NSData dataWithContentsOfFile:metadataPath] options:0 error:nil];
            if (![prior[@"scale_factor"] isEqual:metadata[@"scale_factor"]] ||
                ![prior[@"memory_limit"] isEqual:memoryLimit] || ![prior[@"threads"] isEqual:@6] ||
                [prior[@"wait_for_nominal"] boolValue] != waitForNominal)
                throw std::runtime_error("Resume configuration mismatch");
            metadata = [prior mutableCopy]; metadata[@"status"] = @"running";
        }
        NSMutableArray *launches = [metadata[@"launches"] mutableCopy] ?: [NSMutableArray array];
        [launches addObject:@{@"time":[[NSISO8601DateFormatter new] stringFromDate:[NSDate date]],
                             @"memory":Memory(), @"debugger_attached":@(DebuggerAttached())}];
        metadata[@"launches"] = launches;
        Save(metadataPath, metadata);
        Status(runID, scale, @"hashing");
        NSString *inputPath = [Docs() stringByAppendingPathComponent:[NSString stringWithFormat:@"input_sf%@.json", scale]];
        NSDictionary *input = [NSJSONSerialization JSONObjectWithData:[NSData dataWithContentsOfFile:inputPath] options:0 error:nil];
        if (!input) throw std::runtime_error("Missing input manifest");
        if (![input[@"scale_factor"] isEqual:metadata[@"scale_factor"]]) throw std::runtime_error("Input scale mismatch");
        if (strcmp(duckdb_library_version(), "v1.5.6")) throw std::runtime_error("Wrong DuckDB version");
        NSString *database = [Docs() stringByAppendingPathComponent:@"tpch_current.duckdb"];
        NSString *readyPath = [database stringByAppendingString:@".ready.json"];
        NSDictionary *ready = [NSJSONSerialization JSONObjectWithData:[NSData dataWithContentsOfFile:readyPath] ?: [NSData data] options:0 error:nil];
        if (input[@"database_chunks"] && ![ready[@"sha256"] isEqual:input[@"database_sha256"]]) {
            Status(runID, scale, @"assembling");
            NSString *incoming = [database stringByAppendingString:@".incoming"];
            FILE *out = fopen(incoming.fileSystemRepresentation, "wb");
            if (!out) throw std::runtime_error("Cannot create assembled database");
            char *buffer = (char *)malloc(1024*1024);
            if (!buffer) { fclose(out); throw std::runtime_error("Cannot allocate transfer buffer"); }
            for (NSDictionary *part in input[@"database_chunks"]) {
                NSString *path = [Docs() stringByAppendingPathComponent:part[@"path"]];
                FILE *in = fopen(path.fileSystemRepresentation, "rb");
                uint64_t total = 0; bool failed = !in;
                if (in) {
                    size_t count;
                    while ((count = fread(buffer, 1, 1024*1024, in))) {
                        if (fwrite(buffer, 1, count, out) != count) { failed = true; break; }
                        total += count;
                    }
                    failed = failed || ferror(in); fclose(in);
                }
                if (failed || total != [part[@"bytes"] unsignedLongLongValue]) {
                    free(buffer); fclose(out); throw std::runtime_error("Missing or incomplete database chunk");
                }
            }
            free(buffer);
            if (fclose(out)) throw std::runtime_error("Cannot flush assembled database");
            [[NSFileManager defaultManager] removeItemAtPath:database error:nil];
            NSError *moveError = nil;
            if (![[NSFileManager defaultManager] moveItemAtPath:incoming toPath:database error:&moveError])
                throw std::runtime_error(moveError.localizedDescription.UTF8String);
            Status(runID, scale, @"hashing");
        }
        NSString *temp = [Docs() stringByAppendingPathComponent:[@"spill/" stringByAppendingString:runID]];
        [[NSFileManager defaultManager] removeItemAtPath:temp error:nil];
        [[NSFileManager defaultManager] createDirectoryAtPath:temp withIntermediateDirectories:YES attributes:nil error:nil];
        NSString *sha = FileSHA(database); metadata[@"database_sha256"] = sha;
        if (![sha isEqualToString:input[@"database_sha256"]]) throw std::runtime_error("Database SHA-256 mismatch");
        Save(readyPath, @{@"sha256":sha, @"scale_factor":metadata[@"scale_factor"]});
        for (NSDictionary *part in input[@"database_chunks"])
            [[NSFileManager defaultManager] removeItemAtPath:[Docs() stringByAppendingPathComponent:part[@"path"]] error:nil];
        [self log:@"Database SHA-256 matches the Mac source."];
        Status(runID, scale, @"table_checks");
        {
            Connection check(database, temp);
            NSMutableDictionary *counts = [NSMutableDictionary dictionary];
            for (NSString *table in input[@"table_rows"]) {
                NSArray *r = Execute(check.conn, [NSString stringWithFormat:@"SELECT count(*) FROM %@", table]);
                NSNumber *count = @([r[0][0] longLongValue]);
                if (![count isEqual:input[@"table_rows"][table]]) throw std::runtime_error("Table count mismatch");
                counts[table] = count;
            }
            metadata[@"table_rows"] = counts;
            metadata[@"settings"] = Execute(check.conn, @"SELECT current_setting('threads'), current_setting('memory_limit'), current_setting('temp_directory')");
        }
        Save([output stringByAppendingPathComponent:@"metadata.json"], metadata);
        NSString *measurementsPath = [output stringByAppendingPathComponent:@"measurements.json"];
        NSData *saved = [NSData dataWithContentsOfFile:measurementsPath];
        NSMutableArray *measurements = saved ? [[NSJSONSerialization JSONObjectWithData:saved options:0 error:nil] mutableCopy] : [NSMutableArray array];
        if (!measurements) throw std::runtime_error("Invalid saved measurements");
        for (NSDictionary *query in input[@"queries"]) {
            int number = [query[@"query"] intValue]; NSString *statement = query[@"sql"];
            if (![SHA([statement dataUsingEncoding:NSUTF8StringEncoding]) isEqualToString:query[@"sha256"]])
                throw std::runtime_error("Query SHA-256 mismatch");
            for (int rep = 1; rep <= 2; rep++) {
                @autoreleasepool {
                    BOOL complete = NO;
                    for (NSDictionary *record in measurements) {
                        if ([record[@"query"] intValue] == number && [record[@"repeat"] intValue] == rep) {
                            if (![record[@"query_sha256"] isEqualToString:query[@"sha256"]])
                                throw std::runtime_error("Resume query mismatch");
                            complete = YES;
                        }
                    }
                    if (complete) continue;
                    Status(runID, scale, @"running", number, rep);
                    [self log:[NSString stringWithFormat:@"SF%@ Q%02d run %d starting", scale, number, rep]];
                    NSString *stem = [NSString stringWithFormat:@"q%02d_r%d", number, rep];
                    NSDictionary *before = Memory(); NSArray *rows, *types;
                    double elapsed, coolingSeconds = 0;
                    NSInteger thermalBeforeWait = [before[@"thermal_state"] integerValue];
                    {
                        Connection connection(database, temp);
                        Execute(connection.conn, @"PRAGMA enable_profiling='json'");
                        Execute(connection.conn, [NSString stringWithFormat:@"SET profiling_output='%@/%@_profile.json'", output, stem]);
                        if (waitForNominal) {
                            auto coolingStart = std::chrono::steady_clock::now();
                            thermalBeforeWait = [Memory()[@"thermal_state"] integerValue];
                            while (true) {
                                before = Memory();
                                if ([before[@"thermal_state"] integerValue] == NSProcessInfoThermalStateNominal) {
                                    Status(runID, scale, @"running", number, rep);
                                    // Final check after status I/O, immediately before starting the timer.
                                    before = Memory();
                                    if ([before[@"thermal_state"] integerValue] == NSProcessInfoThermalStateNominal) break;
                                }
                                Status(runID, scale, @"cooling", number, rep);
                                [NSThread sleepForTimeInterval:1.0];
                            }
                            coolingSeconds = std::chrono::duration<double>(std::chrono::steady_clock::now()-coolingStart).count();
                        }
                        auto start = std::chrono::steady_clock::now();
                        rows = Execute(connection.conn, statement, &types);
                        elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
                    }
                    NSDictionary *after = Memory();
                    Save([output stringByAppendingPathComponent:[stem stringByAppendingString:@"_result.json"]],
                         @{@"types":types, @"rows":rows});
                    [measurements addObject:@{@"query":@(number), @"repeat":@(rep), @"wall_seconds":@(elapsed),
                        @"query_sha256":query[@"sha256"], @"rows_returned":@(rows.count),
                        @"memory_before":before, @"memory_after":after}];
                    if (waitForNominal) {
                        NSMutableDictionary *record = [measurements.lastObject mutableCopy];
                        record[@"cooling_wait_seconds"] = @(coolingSeconds);
                        record[@"thermal_state_before_wait"] = @(thermalBeforeWait);
                        measurements[measurements.count-1] = record;
                    }
                    Save([output stringByAppendingPathComponent:@"measurements.json"], measurements);
                    [self log:[NSString stringWithFormat:@"Q%02d run %d: %.4f s · %lu rows", number, rep, elapsed, (unsigned long)rows.count]];
                }
            }
        }
        metadata[@"status"] = @"complete"; metadata[@"executions"] = @(measurements.count);
        metadata[@"memory_after"] = Memory();
        Save([output stringByAppendingPathComponent:@"metadata.json"], metadata);
        Save([Docs() stringByAppendingPathComponent:@"latest.json"], @{@"run_id":runID, @"status":@"complete"});
        Status(runID, scale, @"complete");
        [self log:@"COMPLETE: all 44 executions saved. Ready for Mac validation."];
    } catch (const std::exception &error) {
        metadata[@"status"] = @"failed"; metadata[@"error"] = @(error.what());
        try { Save([output stringByAppendingPathComponent:@"metadata.json"], metadata); } catch (...) {}
        try { Status(runID, scale, @"failed"); } catch (...) {}
        [self log:[NSString stringWithFormat:@"FAILED: %s", error.what()]];
    }
}
@end

@interface SceneDelegate : UIResponder <UIWindowSceneDelegate>
@property(nonatomic, strong) UIWindow *window;
@end
@implementation SceneDelegate
- (void)scene:(UIScene *)scene willConnectToSession:(UISceneSession *)session options:(UISceneConnectionOptions *)options {
    if (![scene isKindOfClass:UIWindowScene.class]) return;
    self.window = [[UIWindow alloc] initWithWindowScene:(UIWindowScene *)scene];
    self.window.rootViewController = [RunnerController new]; [self.window makeKeyAndVisible];
}
@end
@interface AppDelegate : UIResponder <UIApplicationDelegate>
@end
@implementation AppDelegate
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options { return YES; }
@end
int main(int argc, char *argv[]) {
    @autoreleasepool { return UIApplicationMain(argc, argv, nil, NSStringFromClass(AppDelegate.class)); }
}
```
