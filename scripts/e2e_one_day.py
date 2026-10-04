# scripts/e2e_one_day.py (check-only mode)
import argparse
import pathlib

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
