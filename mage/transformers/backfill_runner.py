"""backfill_runner (transformer): lap lai chuoi full_daily cho tung ngay.

Nhan runtime variables start_date/end_date (YYYY-MM-DD). Moi ngay chay lai
toan bo chuoi lenh generate -> pipeline -> dbt (khong gom qc_gate/refresh,
giong trigger full_daily tung ngay). Self-contained, khong import block khac.
"""
import json
import os
import subprocess
import time
from datetime import datetime, timedelta

if 'transformer' not in globals():  # GIU NGUYEN: Mage executor tu nap collector
    # decorator; ghi de se lam mat dang ky block (fail 'no decorated functions')
    try:
        from mage_ai.data_preparation.decorators import transformer
    except ImportError:  # plain pytest khong co mage_ai
        def transformer(fn):
            return fn


def iter_dates(start, end):
    s = datetime.strptime(start, "%Y-%m-%d").date()  # noqa: DTZ007 - date-only batch param
    e = datetime.strptime(end, "%Y-%m-%d").date()  # noqa: DTZ007 - date-only batch param
    out, d = [], s
    while d <= e:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _run(cmd, block, batch_date, cwd="/home/code", timeout_s=1800):
    t0 = time.time()
    cp = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                        timeout=timeout_s, check=False)
    logdir = os.environ.get("MAGE_LOG_DIR", "logs")
    os.makedirs(logdir, exist_ok=True)
    rec = {"block": block, "batch_date": batch_date, "cmd": " ".join(cmd),
           "exit_code": cp.returncode, "duration_s": round(time.time() - t0, 1)}
    with open(os.path.join(logdir, f"{batch_date}.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if cp.returncode != 0:
        raise RuntimeError(f"[{block}@{batch_date}] exit={cp.returncode} "
                           f"stderr={cp.stderr[-2000:]} stdout={(cp.stdout or '')[-1000:]}")


@transformer
def run_block(*args, **kwargs):
    # khong upstream -> khong nhan data (tranh loi "missing upstream dependencies" cua Mage)
    start_date = kwargs.get("start_date") or os.environ.get("START_DATE", "2026-08-10")
    end_date = kwargs.get("end_date") or os.environ.get("END_DATE", start_date)
    for ds in iter_dates(start_date, end_date):
        _run(["python", "-m", "src.data_generator.cli", "generate",
              "--start-date", ds, "--end-date", ds, "--seed", "42"],
             "backfill_generate", ds, timeout_s=1200)
        _run(["python", "-m", "src.pipeline.cli", "run", "--source", "entities",
              "--date", ds], "backfill_entities", ds)
        _run(["python", "-m", "src.pipeline.cli", "run", "--source", "telemetry",
              "--source", "charging_internal", "--date", ds],
             "backfill_telemetry", ds, timeout_s=2700)
        _run(["python", "-m", "src.pipeline.cli", "run", "--source", "crm",
              "--source", "dms", "--source", "charging", "--date", ds],
             "backfill_crm_dms", ds)
    profiles = ["--profiles-dir", "."]
    target = ["--target", "docker"]  # nhu b05: tranh localhost trong container Mage
    _run(["python", "-m", "dbt.cli.main", "deps"] + profiles,
         "backfill_dbt_deps", end_date, cwd="/home/code/dbt_project")
    _run(["python", "-m", "dbt.cli.main", "run", "--full-refresh"] + profiles + target,
         "backfill_dbt_run", end_date, cwd="/home/code/dbt_project")
    _run(["python", "-m", "dbt.cli.main", "test"] + profiles + target,
         "backfill_dbt_test", end_date, cwd="/home/code/dbt_project")
    return {"block": "backfill_runner", "start_date": start_date,
            "end_date": end_date, "exit_code": 0}
