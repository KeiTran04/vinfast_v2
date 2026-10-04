"""b07_metabase_refresh (data_exporter): refresh dashboards Metabase."""
import json
import os
import subprocess
import time

if 'data_exporter' not in globals():  # GIU NGUYEN: Mage executor tu nap collector
    # decorator; ghi de se lam mat dang ky block (fail 'no decorated functions')
    try:
        from mage_ai.data_preparation.decorators import data_exporter
    except ImportError:  # plain pytest khong co mage_ai
        def data_exporter(fn):
            return fn


@data_exporter
def run_block(data=None, *args, **kwargs):
    batch_date = kwargs.get("batch_date") or os.environ.get("BATCH_DATE", "2026-08-10")
    base_url = os.environ.get("MB_BASE_URL", "http://metabase:3000")
    cmd = ["python", "metabase/setup_dashboards.py", "--base-url", base_url]
    t0 = time.time()
    cp = subprocess.run(cmd, cwd="/home/code", capture_output=True, text=True,
                        timeout=600, check=False)
    logdir = os.environ.get("MAGE_LOG_DIR", "logs")
    os.makedirs(logdir, exist_ok=True)
    rec = {"block": "b07_refresh", "batch_date": batch_date, "cmd": " ".join(cmd),
           "exit_code": cp.returncode, "duration_s": round(time.time() - t0, 1)}
    with open(os.path.join(logdir, f"{batch_date}.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if cp.returncode != 0:
        raise RuntimeError(f"[b07_refresh] exit={cp.returncode} stderr={cp.stderr[-2000:]} stdout={(cp.stdout or '')[-1000:]}")
    return {"block": "b07_refresh", "batch_date": batch_date, "exit_code": 0}
