"""b05_dbt_build (transformer): dbt deps + run + test (retry 1, tranh double-write)."""
import json
import os
import subprocess
import time

if 'transformer' not in globals():  # GIU NGUYEN: Mage executor tu nap collector
    # decorator; ghi de se lam mat dang ky block (fail 'no decorated functions')
    try:
        from mage_ai.data_preparation.decorators import transformer
    except ImportError:  # plain pytest khong co mage_ai
        def transformer(fn):
            return fn


def _run(cmd, block, batch_date, cwd="/home/code/dbt_project", timeout_s=1200):
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
        raise RuntimeError(f"[{block}] exit={cp.returncode} stderr={cp.stderr[-2000:]} stdout={(cp.stdout or '')[-1000:]}")
    return {"block": block, "batch_date": batch_date, "exit_code": 0}


@transformer
def run_block(data=None, *args, **kwargs):
    batch_date = kwargs.get("batch_date") or os.environ.get("BATCH_DATE", "2026-08-10")
    profiles = ["--profiles-dir", "."]
    # --target docker: dung host tu env CLICKHOUSE_HOST (trong compose = clickhouse);
    # target dev mac dinh tro localhost -> refused trong container Mage.
    target = ["--target", "docker"]
    _run(["python", "-m", "dbt.cli.main", "deps"] + profiles,
         "b05_dbt_deps", batch_date)
    _run(["python", "-m", "dbt.cli.main", "run", "--full-refresh"] + profiles + target,
         "b05_dbt_run", batch_date)
    return _run(["python", "-m", "dbt.cli.main", "test"] + profiles + target,
                "b05_dbt_test", batch_date)
