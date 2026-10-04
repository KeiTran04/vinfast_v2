"""b01_generate (data_loader): sinh du lieu + mock-raw cho 1 batch_date.

Self-contained: khong import module noi bo nao khac ngoai stdlib (chay duoc
ca trong Mage lan plain pytest). batch_date lay tu runtime variables cua Mage.
"""
import json
import os
import subprocess
import time

if 'data_loader' not in globals():  # GIU NGUYEN: Mage executor tu nap collector
    # decorator; ghi de se lam mat dang ky block (fail 'no decorated functions')
    try:
        from mage_ai.data_preparation.decorators import data_loader
    except ImportError:  # plain pytest khong co mage_ai
        def data_loader(fn):
            return fn


def _log(block, batch_date, cmd, exit_code, duration_s):
    logdir = os.environ.get("MAGE_LOG_DIR", "logs")
    os.makedirs(logdir, exist_ok=True)
    rec = {"block": block, "batch_date": batch_date, "cmd": " ".join(cmd),
           "exit_code": exit_code, "duration_s": round(duration_s, 1)}
    with open(os.path.join(logdir, f"{batch_date}.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _run(cmd, block, batch_date, cwd="/home/code", timeout_s=1200):
    t0 = time.time()
    cp = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                        timeout=timeout_s, check=False)
    _log(block, batch_date, cmd, cp.returncode, time.time() - t0)
    if cp.returncode != 0:
        raise RuntimeError(f"[{block}] exit={cp.returncode} stderr={cp.stderr[-2000:]} stdout={(cp.stdout or '')[-1000:]}")
    return {"block": block, "batch_date": batch_date, "exit_code": 0}


@data_loader
def run_block(*args, **kwargs):
    batch_date = kwargs.get("batch_date") or os.environ.get("BATCH_DATE", "2026-08-10")
    _run(["python", "-m", "src.data_generator.cli", "generate",
          "--start-date", batch_date, "--end-date", batch_date, "--seed", "42"],
         "b01_generate", batch_date)
    _run(["python", "-m", "src.data_generator.cli", "mock-raw",
          "--source", "all", "--seed", "42"],
         "b01_mock", batch_date, timeout_s=1200)
    return {"block": "b01_generate", "batch_date": batch_date, "exit_code": 0}
