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
