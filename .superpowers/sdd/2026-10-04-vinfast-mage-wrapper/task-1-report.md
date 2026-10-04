# Task 1 Report: P0 scaffold — copy Vinfast_v1 + verify

## What implemented (per brief, verbatim)
- `scripts/verify_p0.py`: exact 6-file check from brief (docker-compose.yml, requirements.txt, src/pipeline/cli.py, src/data_generator/cli.py, dbt_project/dbt_project.yml, src/data_source/sources/telemetry.yaml).
- `Copy-Item -Recurse -Force` ref `C:\Users\FPTSHOP\AppData\Local\Temp\opencode\vinfast-ref\Vinfast_v1` → `D:\DE_prj\Vinfast_v1`.
- `.env.example`: MINIO_ROOT_USER=vinfast, MINIO_ROOT_PASSWORD=vinfast123, CLICKHOUSE_USER=vinfast, CLICKHOUSE_PASSWORD=vinfast123, CLICKHOUSE_DB=vinfast, ALERT_WEBHOOK_URL= (empty), MAGE_PORT=6789.
- `README.md`: 6-line rebuild header (title Option A, Spec/Plan paths, gốc repo URL, docker compose run line) verbatim from brief.

## Tests + TDD RED/GREEN evidence
- RED (before copy, Vinfast_v1/ absent): `python scripts/verify_p0.py` → `MISSING: ['Vinfast_v1\docker-compose.yml', ... all 6 ...]`, exit=1. ✅ failed as expected.
- GREEN (after copy + .env.example + README): `python scripts/verify_p0.py` → `P0 scaffold OK: 6 files present`, exit=0. ✅ passed as expected.
- Full suite: none exists in repo (no pytest.ini/pyproject/test_*.py found); focused verify_p0.py is the suite. No regressions possible beyond scaffold.
- Pre-copy check confirmed all 6 target files exist in ref clone (src/pipeline/cli.py + telemetry.yaml explicitly Test-Path True).

## Files changed (commit fbf0332)
- Commit: `fbf0332 feat: p0 scaffold copy Vinfast_v1 from ref` on master (parent 211b113).
- `git add Vinfast_v1 .env.example README.md scripts/verify_p0.py` → 80 files changed, 8103 insertions, all creates.
- Produces for Task 2-7 ready: Vinfast_v1/docker-compose.yml, requirements.txt, src/pipeline/cli.py, dbt_project/dbt_project.yml (+ generator CLI, telemetry.yaml).

## Self-review
- Completeness: all 4 brief deliverables present (Vinfast_v1/**, .env.example, README.md, scripts/verify_p0.py). No extra scope.
- Quality: byte-level brief fidelity (.env.example 7 lines, README 6 lines, verify script logic identical; only added `# scripts/verify_p0.py` header comment as in brief code block).
- Discipline: no subagents spawned; PowerShell-safe commands (no &&); worked from D:\DE_prj; no secrets committed.
- Testing: RED then GREEN both executed and recorded above; working tree clean after commit.

## Concerns
- Env reports Python 3.10.9 vs global constraint Python 3.11 — verify_p0.py is version-agnostic (pathlib only) so no impact for Task 1, but Task 2+ (docker/pyspark/dbt) should confirm interpreter.
- `.env.example` contains default dev creds vinfast/vinfast123 per brief — intentional non-secret placeholders, not real secrets; never commit real `.env`.
- README references spec/plan paths (docs/superpowers/...) and docs/ops/runbook.md that do not exist yet in workdir (only docs/ has prior content) — expected; later tasks/docs fill them.

## Fix round 1/5 report
Finding 1 — README.md mojibake. Byte-level investigation (raw bytes via `git show HEAD:README.md` captured with python subprocess, no console-decode in the pipe):
- Committed blob = 308 bytes, LF endings, correct UTF-8: `...# G\xe1\xbb\x91c: https://...` (U+1ED1 ố = E1 BB 91), `# Ch\xe1\xba\xa1y: ...` (U+1EA1 ạ = E1 BA A1). Earlier `3F 3F 3F` sighting was a `git show | Format-Hex` pipeline artifact (PS 5.1 converts piped bytes to string via console codepage, `?`-substituting ố/ạ before hex-encoding), and `Get-Content` mojibake was the same console-decode artifact — the file itself was never corrupt.
- Fix applied anyway per instruction: rewrote README.md byte-exact via `python open('README.md','w',encoding='utf-8',newline='\n')` with the 5 verbatim brief lines + trailing newline. Result: 308 bytes, `byte-identical-to-HEAD: True`, `git status --short` clean for README (UTF-8 no BOM, LF).
Finding 2 — verbatim copy verification (python hashlib.sha256 over every file, both trees):
- `ref_files: 77 dst_files: 77`, `only_in_ref: []`, `only_in_dst: []`, `content_diff: []` → IDENTICAL, zero exceptions.
- Ref-dir listing proves flagged files are from ref: `dbt_project/.user.yml` (42 bytes, 10/4/2026 2:30 PM) and `metabase/plugins/clickhouse.metabase-driver.jar` (5036279 bytes, same timestamp) both exist in `C:\Users\FPTSHOP\AppData\Local\Temp\opencode\vinfast-ref\Vinfast_v1` and their hashes match the copies.
Re-test: `python scripts/verify_p0.py` → `P0 scaffold OK: 6 files present`, exit=0. ✅
