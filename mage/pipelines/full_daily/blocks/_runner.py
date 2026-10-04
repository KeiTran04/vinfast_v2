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
