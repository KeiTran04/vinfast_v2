# tests/test_ci.py
import pathlib

import yaml

d = yaml.safe_load(pathlib.Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
jobs = d["jobs"]
assert {"lint", "unit", "dbt"} <= set(jobs.keys()), jobs.keys()
assert "clickhouse" in str(d).lower() and "minio" in str(d).lower()
c = pathlib.Path("docker-compose.yml").read_text(encoding="utf-8")
assert "6789/health" in c or "healthcheck" in c


def test_ci():
    assert {"lint", "unit", "dbt"} <= set(jobs.keys()), jobs.keys()
    assert "clickhouse" in str(d).lower() and "minio" in str(d).lower()
    assert "6789/health" in c or "healthcheck" in c
