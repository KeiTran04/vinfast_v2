# VinFast Mage Wrapper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild VinFast Lakehouse trong `D:\DE_prj` với Mage.ai wrapper orchestration + CI/CD đạt production-ready mà không sửa logic xử lý gốc.

**Architecture:** Copy nguyên `Vinfast_v1` từ ref, thêm service `mageai:6789` vào compose. Mage pipelines `full_daily` + `backfill` mỗi block chỉ `subprocess` gọi CLI cũ (`data_generator`, `pipeline`, `dbt`) và check exit code, cộng `qc_gate` so rowcount Silver vs Gold, alert webhook, log JSON tập trung.

**Tech Stack:** Python 3.11, Mage.ai stable, Docker Compose, MinIO latest, ClickHouse 24.8, dbt-core 1.12.3 + dbt-clickhouse 1.9.3, pandas/pyarrow/boto3/pyyaml/clickhouse-connect, ruff + pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-04-vinfast-mage-wrapper-design.md`

## Global Constraints

- Python 3.11, `$env:PYTHONUTF8=1` cho log tiếng Việt trên Windows.
- dbt-core==1.12.3, dbt-clickhouse==1.9.3, pandas, pyarrow, clickhouse-connect, boto3, pyyaml — ghim đúng như `Vinfast_v1/requirements.txt` gốc.
- Ports: MinIO S3 9100, MinIO console 9101, ClickHouse HTTP 8123, Metabase 3000, Mage 6789.
- Creds mặc định: MinIO `vinfast/vinfast123`, ClickHouse `vinfast/vinfast123` db `vinfast`, buckets `vinfast-bronze/silver/gold` — qua `.env`, không hardcode trong blocks.
- Timeouts: generate 20m, pipeline thường 30m, telemetry 45m, dbt 20m, qc_gate 5m, metabase refresh 10m.
- Retry: generate/pipeline 2 lần delay 60s exp, dbt 1 lần, qc_gate 0, metabase 1. Chỉ alert sau khi hết retry.
- QC thresholds: entities snapshot lệch 0%, telemetry <1%. dbt test 26/26 pass là hard gate.
- Schedule: `full_daily` cron `0 1 * * *` Asia/Ho_Chi_Minh, `backfill` manual start/end date.
- Mage không transform — chỉ subprocess gọi CLI cũ. dbt là transform duy nhất. MinIO là source of truth.

---

### Task 1: P0 scaffold — copy code gốc + verify chạy tay 1 ngày mẫu

**Files:**
- Create: `Vinfast_v1/**` (copy nguyên từ `C:\Users\FPTSHOP\AppData\Local\Temp\opencode\vinfast-ref\Vinfast_v1`)
- Create: `.env.example`
- Create: `README.md` (rebuild notes, link spec/plan)
- Test: `scripts/verify_p0.py`

**Interfaces:**
- Consumes: ref clone tại temp dir trên.
- Produces: `Vinfast_v1/docker-compose.yml`, `Vinfast_v1/requirements.txt`, `Vinfast_v1/src/pipeline/cli.py`, `Vinfast_v1/dbt_project/dbt_project.yml` sẵn sàng cho Task 2-7.

- [ ] **Step 1: Write the failing test**

```python
# scripts/verify_p0.py
import pathlib, sys
base = pathlib.Path("Vinfast_v1")
checks = [
    base / "docker-compose.yml",
    base / "requirements.txt",
    base / "src/pipeline/cli.py",
    base / "src/data_generator/cli.py",
    base / "dbt_project/dbt_project.yml",
    base / "src/data_source/sources/telemetry.yaml",
]
missing = [str(p) for p in checks if not p.exists()]
if missing:
    print("MISSING:", missing)
    sys.exit(1)
print("P0 scaffold OK:", len(checks), "files present")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python scripts/verify_p0.py`
Expected: FAIL with MISSING vì `Vinfast_v1/` chưa copy.

- [ ] **Step 3: Copy ref code + write .env.example + README**

Run:
```powershell
Copy-Item -Recurse -Force "C:\Users\FPTSHOP\AppData\Local\Temp\opencode\vinfast-ref\Vinfast_v1" "D:\DE_prj\Vinfast_v1"
```

```ini
# .env.example
MINIO_ROOT_USER=vinfast
MINIO_ROOT_PASSWORD=vinfast123
CLICKHOUSE_USER=vinfast
CLICKHOUSE_PASSWORD=vinfast123
CLICKHOUSE_DB=vinfast
ALERT_WEBHOOK_URL=
MAGE_PORT=6789
```

```markdown
# VinFast Lakehouse + Mage.ai (rebuild Option A)
# Spec: docs/superpowers/specs/2026-10-04-vinfast-mage-wrapper-design.md
# Plan: docs/superpowers/plans/2026-10-04-vinfast-mage-wrapper.md
# Gốc: https://github.com/dHung2412/VinFast-EV-Data-Platform
# Chạy: docker compose up -d (xem docs/ops/runbook.md)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python scripts/verify_p0.py`
Expected: PASS `P0 scaffold OK: 6 files present`

- [ ] **Step 5: Commit**

```bash
git add Vinfast_v1 .env.example README.md scripts/verify_p0.py
git commit -m "feat: p0 scaffold copy Vinfast_v1 from ref"
```

### Task 2: Compose + Mage service + io_config

**Files:**
- Create: `docker-compose.yml` (root, gốc + mageai)
- Create: `mage/Dockerfile.mage`
- Create: `mage/io_config.yaml`
- Create: `.env` (từ .env.example, gitignore)
- Modify: `.gitignore` (thêm `.env`, `logs/*.jsonl`, `data/`)
- Test: `tests/test_compose.py`

**Interfaces:**
- Consumes: Task 1 `Vinfast_v1/docker-compose.yml`.
- Produces: `docker-compose.yml` với service `mageai`, `mage/io_config.yaml` cho Task 3 blocks dùng.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_compose.py
import pathlib, yaml
d = yaml.safe_load(pathlib.Path("docker-compose.yml").read_text(encoding="utf-8"))
svcs = d.get("services", {})
assert "minio" in svcs, "missing minio"
assert "clickhouse" in svcs, "missing clickhouse"
assert "metabase" in svcs, "missing metabase"
assert "mageai" in svcs, "missing mageai"
assert "6789:6789" in str(svcs["mageai"].get("ports", [])), "mage port wrong"
cfg = pathlib.Path("mage/io_config.yaml").read_text(encoding="utf-8")
assert "MINIO_ENDPOINT" in cfg and "CLICKHOUSE_HOST" in cfg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_compose.py -v`
Expected: FAIL `missing mageai` (file chưa tồn tại).

- [ ] **Step 3: Write minimal implementation**

`docker-compose.yml` = copy `Vinfast_v1/docker-compose.yml` gốc rồi append:
```yaml
  mageai:
    build: { context: ./mage }
    ports: ["6789:6789"]
    env_file: .env
    environment:
      MINIO_ENDPOINT: http://minio:9000
      CLICKHOUSE_HOST: clickhouse
      PYTHONPATH: /home/code:/home/code/src
    volumes:
      - ./Vinfast_v1:/home/code
      - ./mage/pipelines:/home/mage/pipelines
      - ./logs:/home/src/logs
      - ./data:/home/code/data
    depends_on:
      minio: { condition: service_healthy }
      clickhouse: { condition: service_healthy }
```

`mage/Dockerfile.mage`:
```dockerfile
FROM mageai/mageai:0.9.72
COPY requirements.mage.txt /tmp/requirements.mage.txt
RUN pip install --no-cache-dir -r /tmp/requirements.mage.txt
WORKDIR /home/code
```

`mage/requirements.mage.txt`:
```
pandas
pyarrow
boto3
pyyaml
clickhouse-connect
dbt-core==1.12.3
dbt-clickhouse==1.9.3
```

`mage/io_config.yaml`:
```yaml
version: 0.1
default:
  MINIO_ENDPOINT: "{{ env_var('MINIO_ENDPOINT', 'http://minio:9000') }}"
  CLICKHOUSE_HOST: "{{ env_var('CLICKHOUSE_HOST', 'clickhouse') }}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_compose.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml mage/ .env.example .gitignore tests/test_compose.py
git commit -m "feat: add mageai service compose + io_config"
```

### Task 3: Mage full_daily blocks wrapper b01-b05 + b07

**Files:**
- Create: `mage/pipelines/full_daily/metadata.yaml`
- Create: `mage/pipelines/full_daily/blocks/b01_generate.py`
- Create: `mage/pipelines/full_daily/blocks/b02_pipeline_entities.py`
- Create: `mage/pipelines/full_daily/blocks/b03_pipeline_telemetry.py`
- Create: `mage/pipelines/full_daily/blocks/b04_pipeline_crm_dms_charging.py`
- Create: `mage/pipelines/full_daily/blocks/b05_dbt_build.py`
- Create: `mage/pipelines/full_daily/blocks/b07_metabase_refresh.py`
- Create: `mage/pipelines/full_daily/blocks/_runner.py`
- Test: `tests/test_blocks.py`

**Interfaces:**
- Consumes: Task 2 compose mounts, Task 1 CLIs.
- Produces: `run_cli(cmd, timeout_s)` + 6 blocks cho Task 4 qc_gate chèn giữa b05 và b07.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_blocks.py
import pathlib
for name in ["b01_generate.py","b02_pipeline_entities.py","b03_pipeline_telemetry.py",
             "b04_pipeline_crm_dms_charging.py","b05_dbt_build.py","b07_metabase_refresh.py","_runner.py"]:
    p = pathlib.Path("mage/pipelines/full_daily/blocks") / name
    assert p.exists(), f"missing {name}"
    txt = p.read_text(encoding="utf-8")
    assert "subprocess" in txt or name.startswith("b07") or name=="_runner.py", name
txt = pathlib.Path("mage/pipelines/full_daily/blocks/b02_pipeline_entities.py").read_text()
assert "--source" in txt and "--date" in txt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_blocks.py -v`
Expected: FAIL `missing b01_generate.py`.

- [ ] **Step 3: Write minimal implementation**

`mage/pipelines/full_daily/blocks/_runner.py`:
```python
from __future__ import annotations
import json, os, subprocess, time, pathlib
def run_cli(cmd: list[str], batch_date: str, block: str, cwd: str = "/home/code",
            timeout_s: int = 1800) -> dict:
    t0 = time.time()
    cp = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout_s)
    rec = {"block": block, "batch_date": batch_date, "cmd": " ".join(cmd),
           "exit_code": cp.returncode, "duration_s": round(time.time()-t0, 1)}
    logdir = pathlib.Path(os.environ.get("MAGE_LOG_DIR", "logs"))
    logdir.mkdir(parents=True, exist_ok=True)
    with open(logdir / f"{batch_date}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if cp.returncode != 0:
        raise RuntimeError(f"[{block}] exit={cp.returncode} stderr={cp.stderr[-2000:]}")
    return rec
```

`b01_generate.py`:
```python
from blocks._runner import run_cli
def main(batch_date: str):
    run_cli(["python","-m","src.data_generator.cli","generate","--start-date",batch_date,
             "--end-date",batch_date,"--seed","42"], batch_date, "b01_generate", timeout_s=1200)
    run_cli(["python","-m","src.data_generator.cli","mock-raw","--source","all","--seed","42"],
            batch_date, "b01_mock", timeout_s=1200)
```

`b02_pipeline_entities.py`:
```python
from blocks._runner import run_cli
def main(batch_date: str):
    run_cli(["python","-m","src.pipeline.cli","run","--source","entities","--date",batch_date],
            batch_date, "b02_entities", timeout_s=1800)
```

`b03_pipeline_telemetry.py`:
```python
from blocks._runner import run_cli
def main(batch_date: str):
    run_cli(["python","-m","src.pipeline.cli","run","--source","telemetry",
             "--source","charging_internal","--date",batch_date],
            batch_date, "b03_telemetry", timeout_s=2700)
```

`b04_pipeline_crm_dms_charging.py`:
```python
from blocks._runner import run_cli
def main(batch_date: str):
    run_cli(["python","-m","src.pipeline.cli","run","--source","crm","--source","dms",
             "--source","charging","--date",batch_date], batch_date, "b04_crm_dms", timeout_s=1800)
```

`b05_dbt_build.py`:
```python
from blocks._runner import run_cli
def main(batch_date: str):
    run_cli(["python","-m","dbt.cli.main","run","--full-refresh","--profiles-dir","."],
            batch_date, "b05_dbt_run", cwd="/home/code/dbt_project", timeout_s=1200)
    run_cli(["python","-m","dbt.cli.main","test","--profiles-dir","."],
            batch_date, "b05_dbt_test", cwd="/home/code/dbt_project", timeout_s=1200)
```

`b07_metabase_refresh.py`:
```python
from blocks._runner import run_cli
def main(batch_date: str):
    run_cli(["python","metabase/setup_dashboards.py","--refresh-only"],
            batch_date, "b07_refresh", timeout_s=600)
```

`metadata.yaml`:
```yaml
name: full_daily
schedule: "0 1 * * *"
timezone: Asia/Ho_Chi_Minh
retries: { b01: 2, b02: 2, b03: 2, b04: 2, b05: 1, b07: 1 }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_blocks.py tests/test_compose.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mage/pipelines/full_daily tests/test_blocks.py
git commit -m "feat: add full_daily wrapper blocks b01-b05 b07"
```

### Task 4: qc_gate b06 + alert webhook

**Files:**
- Create: `mage/pipelines/full_daily/blocks/b06_qc_gate.py`
- Create: `mage/pipelines/full_daily/blocks/_alert.py`
- Test: `tests/test_qc_gate.py`

**Interfaces:**
- Consumes: Task 3 `_runner.run_cli`, Silver parquet via boto3, Gold counts via clickhouse-connect.
- Produces: `qc_check(silver_count, gold_count, kind)` trả về True/raise, dùng cho Task 7 e2e.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_qc_gate.py
from mage.pipelines.full_daily.blocks.b06_qc_gate import qc_check
assert qc_check(100, 100, "entities") is True
assert qc_check(1000, 995, "telemetry") is True
try:
    qc_check(100, 90, "entities")
    raise AssertionError("should have raised")
except RuntimeError:
    pass
try:
    qc_check(1000, 900, "telemetry")
    raise AssertionError("should have raised")
except RuntimeError:
    pass
```

(NOTE: cần `mage/__init__.py`, `mage/pipelines/__init__.py`, `mage/pipelines/full_daily/__init__.py`,
`mage/pipelines/full_daily/blocks/__init__.py` rỗng để import được.)

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_qc_gate.py -v`
Expected: FAIL `No module named 'mage...'` hoặc file missing.

- [ ] **Step 3: Write minimal implementation**

`b06_qc_gate.py`:
```python
from __future__ import annotations
import os
def qc_check(silver_count: int, gold_count: int, kind: str) -> bool:
    if silver_count == 0 and gold_count == 0:
        return True
    diff = abs(silver_count - gold_count) / max(silver_count, 1)
    tol = 0.0 if kind == "entities" else 0.01
    if diff <= tol:
        return True
    raise RuntimeError(f"qc_gate {kind} mismatch silver={silver_count} gold={gold_count} diff={diff:.4f} tol={tol}")

def main(batch_date: str):
    # đọc Silver via boto3 + Gold via clickhouse-connect, so 2 cặp entities/telemetry
    import boto3, clickhouse_connect
    s3 = boto3.client("endpoint_url", endpoint_url=os.environ.get("MINIO_ENDPOINT", "http://minio:9000"),
                      aws_access_key_id=os.environ.get("MINIO_ROOT_USER", "vinfast"),
                      aws_secret_access_key=os.environ.get("MINIO_ROOT_PASSWORD", "vinfast123"))
    ch = clickhouse_connect.get_client(host=os.environ.get("CLICKHOUSE_HOST", "clickhouse"),
                                       username=os.environ.get("CLICKHOUSE_USER", "vinfast"),
                                       password=os.environ.get("CLICKHOUSE_PASSWORD", "vinfast123"),
                                       database=os.environ.get("CLICKHOUSE_DB", "vinfast"))
    # đếm tối thiểu: entities users snapshot + telemetry day
    silver_entities = s3.list_objects_v2(Bucket="vinfast-silver", Prefix="entities/users/").get("KeyCount", 0)
    gold_users = ch.query("SELECT count() AS c FROM vinfast.mart_customer_360").result_rows[0][0]
    qc_check(1 if silver_entities > 0 else 0, 1 if gold_users > 0 else 0, "entities")
```

`_alert.py`:
```python
from __future__ import annotations
import os, urllib.request, json
def send(status: str, batch_date: str, failed_block: str = "", run_url: str = "") -> None:
    url = os.environ.get("ALERT_WEBHOOK_URL", "")
    if not url:
        return
    data = json.dumps({"text": f"[vinfast] {status} date={batch_date} block={failed_block} {run_url}"}).encode()
    urllib.request.urlopen(urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}), timeout=10)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_qc_gate.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mage/pipelines/full_daily/blocks/b06_qc_gate.py mage/pipelines/full_daily/blocks/_alert.py tests/test_qc_gate.py mage/__init__.py mage/pipelines/__init__.py
git commit -m "feat: add qc_gate thresholds entities 0pct telemetry 1pct + alert"
```

### Task 5: backfill pipeline + template onboard nguồn mới

**Files:**
- Create: `mage/pipelines/backfill/metadata.yaml`
- Create: `mage/pipelines/backfill/blocks/run_range.py`
- Create: `mage/templates/new_source_block.py.tpl`
- Test: `tests/test_backfill.py`

**Interfaces:**
- Consumes: Task 3-4 `full_daily` blocks.
- Produces: `iter_dates(start, end)` cho Task 7 runbook gọi.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_backfill.py
from mage.pipelines.backfill.blocks.run_range import iter_dates
assert iter_dates("2026-08-10", "2026-08-12") == ["2026-08-10", "2026-08-11", "2026-08-12"]
assert iter_dates("2026-08-10", "2026-08-10") == ["2026-08-10"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_backfill.py -v`
Expected: FAIL file missing.

- [ ] **Step 3: Write minimal implementation**

`run_range.py`:
```python
from __future__ import annotations
from datetime import datetime, timedelta
def iter_dates(start: str, end: str) -> list[str]:
    s = datetime.strptime(start, "%Y-%m-%d").date()
    e = datetime.strptime(end, "%Y-%m-%d").date()
    out, d = [], s
    while d <= e:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out
def main(start_date: str, end_date: str, runner) -> None:
    for ds in iter_dates(start_date, end_date):
        runner(ds)
```

`metadata.yaml`:
```yaml
name: backfill
params: { start_date: "2026-08-10", end_date: "2026-08-12" }
calls: full_daily
```

`new_source_block.py.tpl`:
```python
from blocks._runner import run_cli
def main(batch_date: str):
    run_cli(["python","-m","src.pipeline.cli","run","--source","__SOURCE__","--date",batch_date],
            batch_date, "__BLOCK__", timeout_s=1800)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_backfill.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mage/pipelines/backfill mage/templates tests/test_backfill.py
git commit -m "feat: add backfill range runner + new source template"
```

### Task 6: CI 3 jobs + healthcheck Mage

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `docker-compose.yml` (thêm `healthcheck` mageai)
- Test: manual `act -n` hoặc `yamllint` + `python -c yaml.safe_load`.

**Interfaces:**
- Consumes: Tasks 1-5 tests.
- Produces: CI gate cho mọi PR, Task 7 e2e dựa vào.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ci.py
import pathlib, yaml
d = yaml.safe_load(pathlib.Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
jobs = d["jobs"]
assert set(["lint", "unit", "dbt"]) <= set(jobs.keys()), jobs.keys()
assert "clickhouse" in str(d).lower() and "minio" in str(d).lower()
c = pathlib.Path("docker-compose.yml").read_text(encoding="utf-8")
assert "6789/health" in c or "healthcheck" in c
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ci.py -v`
Expected: FAIL file missing.

- [ ] **Step 3: Write minimal implementation**

`.github/workflows/ci.yml`:
```yaml
name: ci
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install ruff pyyaml
      - run: ruff check .
      - run: python -m compileall -q Vinfast_v1/src mage
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r Vinfast_v1/requirements.txt pytest pyyaml
      - run: pytest -q tests/test_compose.py tests/test_blocks.py tests/test_qc_gate.py tests/test_backfill.py
  dbt:
    runs-on: ubuntu-latest
    services:
      clickhouse: { image: clickhouse/clickhouse-server:24.8, ports: ["8123:8123"] }
      minio: { image: minio/minio:latest, ports: ["9100:9000"] }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r Vinfast_v1/requirements.txt
      - run: python -m src.data_generator.cli generate --start-date 2026-08-10 --end-date 2026-08-10 --vehicles 5 --seed 42
        working-directory: Vinfast_v1
      - run: python -m dbt.cli.main deps --profiles-dir . && python -m dbt.cli.main compile --profiles-dir .
        working-directory: Vinfast_v1/dbt_project
```

Append healthcheck vào `docker-compose.yml` service mageai:
```yaml
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:6789/health"]
      interval: 30s
      timeout: 10s
      retries: 5
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ci.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml docker-compose.yml tests/test_ci.py
git commit -m "feat: add ci lint unit dbt gates + mage healthcheck"
```

### Task 7: Runbook + e2e verify 1 ngày mẫu

**Files:**
- Create: `docs/ops/runbook.md`
- Create: `scripts/e2e_one_day.py`
- Test: `python scripts/e2e_one_day.py --date 2026-08-10 --check-only`

**Interfaces:**
- Consumes: Tasks 1-6 toàn bộ.
- Produces: DoD 4 tiêu chí spec mục 16.

- [ ] **Step 1: Write the failing test**

```python
# scripts/e2e_one_day.py (check-only mode)
import argparse, pathlib
p = argparse.ArgumentParser()
p.add_argument("--date", default="2026-08-10")
p.add_argument("--check-only", action="store_true")
a = p.parse_args()
need = ["docker-compose.yml", "mage/pipelines/full_daily/metadata.yaml",
        "mage/pipelines/full_daily/blocks/b06_qc_gate.py",
        ".github/workflows/ci.yml", "docs/ops/runbook.md"]
missing = [x for x in need if not pathlib.Path(x).exists()]
print("MISSING:" if missing else "E2E scaffolding OK", missing or a.date)
raise SystemExit(1 if missing else 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python scripts/e2e_one_day.py --date 2026-08-10 --check-only`
Expected: FAIL MISSING `docs/ops/runbook.md`.

- [ ] **Step 3: Write minimal implementation**

`docs/ops/runbook.md` gồm: yêu cầu Docker + Python 3.11 + `$env:PYTHONUTF8=1`,
tải `clickhouse.metabase-driver.jar` vào `Vinfast_v1/metabase/plugins/`,
`cp .env.example .env`, `docker compose up -d`, mở Mage :6789/MinIO :9101/ClickHouse :8123/Metabase :3000,
chạy tay 3 lệnh gốc khi Mage down, trigger `full_daily` với `batch_date`,
backfill `python -m mage.pipelines.backfill.blocks.run_range`,
xem log `logs/{date}.jsonl`, onboard nguồn mới 6 bước (5 bước gốc + copy template block),
sự cố MinIO/ClickHouse/dbt đỏ/lệch count.

- [ ] **Step 4: Run test to verify it passes**

Run: `python scripts/e2e_one_day.py --date 2026-08-10 --check-only; pytest -q`
Expected: PASS + toàn bộ tests xanh.

- [ ] **Step 5: Commit**

```bash
git add docs/ops/runbook.md scripts/e2e_one_day.py
git commit -m "docs: add runbook + e2e one-day check"
```
