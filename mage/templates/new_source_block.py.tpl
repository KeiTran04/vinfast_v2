"""Template block pipeline moi: copy vao mage/transformers/bXX_pipeline___SOURCE__.py,
doi __SOURCE__/__BLOCK__, khai bao trong mage/pipelines/full_daily/metadata.yaml.
Self-contained theo quy uoc blocks (khong import module noi bo, batch_date tu kwargs).
"""
import json
import os
import subprocess
import time

try:
    from mage_ai.data_preparation.decorators import transformer
except ImportError:  # plain pytest khong co mage_ai
    def transformer(fn):
        return fn


@transformer
def run_block(data=None, *args, **kwargs):
    batch_date = kwargs.get("batch_date") or os.environ.get("BATCH_DATE", "2026-08-10")
    cmd = ["python", "-m", "src.pipeline.cli", "run",
           "--source", "__SOURCE__", "--date", batch_date]
    t0 = time.time()
    cp = subprocess.run(cmd, cwd="/home/code", capture_output=True, text=True,
                        timeout=1800, check=False)
    logdir = os.environ.get("MAGE_LOG_DIR", "logs")
    os.makedirs(logdir, exist_ok=True)
    rec = {"block": "__BLOCK__", "batch_date": batch_date, "cmd": " ".join(cmd),
           "exit_code": cp.returncode, "duration_s": round(time.time() - t0, 1)}
    with open(os.path.join(logdir, f"{batch_date}.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if cp.returncode != 0:
        raise RuntimeError(f"[__BLOCK__] exit={cp.returncode} stderr={cp.stderr[-2000:]} stdout={(cp.stdout or '')[-1000:]}")
    return {"block": "__BLOCK__", "batch_date": batch_date, "exit_code": 0}
