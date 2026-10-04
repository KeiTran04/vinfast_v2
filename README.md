# VinFast EV Data Platform v2 — Lakehouse + Mage.ai Orchestration + CI/CD

Rebuild từ [VinFast-EV-Data-Platform](https://github.com/dHung2412/VinFast-EV-Data-Platform)
theo kiến trúc **Lakehouse**: S3 là source of truth (Bronze + Silver Parquet),
ClickHouse chỉ giữ tầng Gold serving, dbt là transform layer duy nhất —
cộng thêm **Mage.ai điều phối** và **CI/CD tự động**, đạt production-ready tối thiểu.

Điểm khác lớn nhất so với bản gốc: mọi bước chạy tay (`generate` → pipeline 6 nguồn →
`dbt run/test` → refresh dashboard) được đóng gói thành 2 pipelines Mage
(`full_daily`, `backfill`) trigger bằng 1 nút bấm, có retry, logging JSON,
QC gate chặn Gold bẩn và alert webhook. Toàn bộ đã chạy xanh end-to-end
(local + CI GitHub Actions).

## Kiến trúc

```
Synthetic sources (Python, seed cố định — không API ngoài)
  telemetry vật lý xe (~11-12k rows/ngày) · entities · CRM/DMS/Charging CSV
        │
        ▼  Mage full_daily (7 blocks, variables: batch_date)
  b01_generate → b02_entities → b03_telemetry → b04_crm_dms
        → b05_dbt_build → b06_qc_gate → b07_metabase_refresh
        │
        ▼  S3 [Bronze raw → Silver chuẩn hóa]  ← source of truth
               (staging dbt đọc s3() trực tiếp, không bảng raw_*)
        ▼  ClickHouse [Gold: 8 stg views → 2 int → 6 marts, 26 tests]
        ▼  Metabase (7 dashboards = 7 persona)
```

## Services (`docker compose up -d`)

| Service | URL | Tài khoản | Ghi chú |
|---|---|---|---|
| Mage.ai | http://localhost:6789 | (không cần login) | UI orchestration, pipelines `full_daily`/`backfill` |
| S3 (Moto) | http://localhost:9100 | `vinfast` / `vinfast123` | API S3, **không có console UI** |
| ClickHouse | http://localhost:8123 | `vinfast` / `vinfast123`, db `vinfast` | Gold serving |
| Metabase | http://localhost:3000 | `admin@vinfast.vn` / `Vinfast123!` | 7 dashboards dựng sẵn |

> **Tại sao Moto mà không phải MinIO?** `minio/minio` bị gỡ khỏi Docker Hub,
> `quay.io` chặn pull ẩn danh, `dl.min.io` trả 410 — Moto (`motoserver/moto`,
> S3 mock Python) tương thích đầy đủ với pipeline boto3 + ClickHouse `s3()`
> (đã kiểm chứng 16 models + 26 tests). Moto lưu in-memory: restart container
> là mất data S3 → trigger lại pipeline là có. Buckets tự tạo bởi pipeline,
> không còn `minio-init`/`mc`.

## Chạy nhanh

```powershell
cd D:\DE_prj
docker compose up -d            # ~1 phút cho 4 services healthy
```

Rồi 1 trong 2 cách:

**A. Qua Mage UI (khuyến nghị):** mở http://localhost:6789 → Pipelines →
`full_daily` → Trigger với variable `batch_date=2026-08-10` → xem từng block
chạy. Fail block nào thì retry từ block đó.

**B. Chạy tay** (chi tiết trong `docs/ops/runbook.md`):
```powershell
$env:PYTHONUTF8 = 1; $env:S3_ADDRESSING_STYLE = "path"
cd Vinfast_v1
python -m src.data_generator.cli generate --start-date 2026-08-10 --end-date 2026-08-12 --seed 42
python -m src.data_generator.cli mock-raw --source all --seed 42
python -m src.pipeline.cli run --source entities --date 2026-08-29
foreach ($d in @("2026-08-10","2026-08-11","2026-08-12")) {
  python -m src.pipeline.cli run --source telemetry --source charging_internal --date $d
}
python -m src.pipeline.cli run --source crm --source dms --source charging --date 2026-08-29
cd dbt_project
$env:CLICKHOUSE_HOST = "localhost"
python -m dbt.cli.main deps --profiles-dir .                  # lần đầu
python -m dbt.cli.main run --profiles-dir . --target docker   # 16 models
python -m dbt.cli.main test --profiles-dir . --target docker  # 26 tests
```

> Quy ước batch: telemetry/charging_internal chạy theo từng ngày 10–12,
> entities/crm/dms/charging chạy đúng **1 batch duy nhất** (staging đọc glob
> `*`, 2 partitions sẽ gây duplicate → rớt test unique `customer_id`).

## CI/CD (GitHub Actions, chạy mỗi push)

| Job | Làm gì |
|---|---|
| `lint` | `ruff check mage tests scripts` + `compileall` |
| `unit` | `pytest` — CLI args wrapper, ngưỡng qc_gate, `iter_dates`, parse yaml |
| `dbt` | Dựng Moto S3 + ClickHouse thật → seed 1 ngày (`--vehicles 5`) → chạy **nguyên pipeline** generate → pipeline → `dbt run/test` |

## Cấu trúc repo

```
D:\DE_prj\
├── docker-compose.yml        # minio(Moto) + clickhouse + metabase + mageai
├── mage/                     # Mage project: metadata, io_config, Dockerfile
│   ├── data_loaders/b01_generate.py
│   ├── transformers/b02..b06_*.py + backfill_runner.py
│   ├── data_exporters/b07_metabase_refresh.py
│   └── pipelines/{full_daily,backfill}/metadata.yaml
├── Vinfast_v1/               # code gốc: src/{pipeline,data_generator},
│                             # dbt_project (16 models/26 tests), metabase setup
├── .github/workflows/ci.yml  # lint → unit → dbt
├── tests/                    # pytest wrapper (6 tests)
├── docs/ops/runbook.md       # vận hành: trigger, backfill, onboard nguồn mới, sự cố
└── docs/superpowers/{specs,plans}/  # design spec + implementation plan
```

## Tài liệu

- Vận hành chi tiết: `docs/ops/runbook.md` (trigger Mage qua API/UI, backfill,
  onboard nguồn mới 6 bước, bẫy partition/BOM/decorator, troubleshooting)
- Design spec: `docs/superpowers/specs/2026-10-04-vinfast-mage-wrapper-design.md`
- Implementation plan: `docs/superpowers/plans/2026-10-04-vinfast-mage-wrapper.md`
