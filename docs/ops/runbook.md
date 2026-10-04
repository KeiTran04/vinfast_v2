# Runbook — Vinfast Mage Wrapper (`full_daily`)

Phạm vi: vận hành pipeline Mage `full_daily` (blocks `b01`–`b07` + `b06_qc_gate`),
backfill theo ngày, và fallback chạy tay khi Mage down.

## 1. Yêu cầu môi trường

- Docker + Docker Compose v2.
- Python 3.11.
- PowerShell: bật UTF-8 cho mọi lệnh Python (tránh lỗi encoding tiếng Việt):

  ```powershell
  $env:PYTHONUTF8 = 1
  ```

## 2. Chuẩn bị lần đầu

1. Tải `clickhouse.metabase-driver.jar` (ClickHouse driver cho Metabase) vào
   `Vinfast_v1/metabase/plugins/` (mount vào `/plugins` của service `metabase` —
   xem `docker-compose.yml`). Không có file này thì Metabase không kết nối
   được ClickHouse.
2. Copy env mẫu và điền giá trị thật:

   ```powershell
   cp .env.example .env
   ```

   Biến chính: `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `CLICKHOUSE_USER`,
   `CLICKHOUSE_PASSWORD`, `CLICKHOUSE_DB`, `ALERT_WEBHOOK_URL`, `MAGE_PORT`.
3. Khởi động toàn bộ stack:

   ```powershell
   docker compose up -d
   ```

## 3. URLs sau khi `compose up`

| Service    | URL                   |
|------------|-----------------------|
| Mage       | http://localhost:6789 |
| MinIO UI   | http://localhost:9101 |
| ClickHouse | http://localhost:8123 |
| Metabase   | http://localhost:3000 |

Credentials MinIO/ClickHouse lấy từ `.env` (`vinfast` / `vinfast123` mặc định).
MinIO S3 API: `http://localhost:9100`. Buckets seed tự động:
`vinfast-bronze`, `vinfast-silver`, `vinfast-gold` (service `minio-init`).

## 4. Chạy tay 3 lệnh gốc khi Mage down

Chạy từ thư mục `Vinfast_v1/` (pipeline gốc, không qua Mage):

```powershell
$env:PYTHONUTF8 = 1
cd Vinfast_v1
python -m src.data_generator.cli generate --start-date 2026-08-10 --end-date 2026-08-10 --vehicles 5 --seed 42
python -m src.pipeline.cli run --all --date 2026-08-10
python -m dbt.cli.main run --full-refresh --profiles-dir .  # cd dbt_project trước
python -m dbt.cli.main test --profiles-dir .                # cd dbt_project trước
```

Lệnh 1 sinh dữ liệu mẫu, lệnh 2 chạy toàn bộ nguồn pipeline
(entities/telemetry/crm/dms/charging), lệnh 3–4 build + test dbt marts.
Tương đương các block Mage `b01` → `b04` → `b05`.

Kiểm tra nhanh từng nguồn:

```powershell
python -m src.pipeline.cli list
python -m src.pipeline.cli run --source crm --date 2026-08-10 --dry-run
python -m src.pipeline.cli run --source crm --date 2026-08-10
```

## 5. Trigger `full_daily` trên Mage (đường chính)

1. Mở Mage http://localhost:6789 → pipeline `full_daily`
   (schedule `0 1 * * *`, timezone `Asia/Ho_Chi_Minh` — xem
   `mage/pipelines/full_daily/metadata.yaml`).
2. Trigger thủ công với runtime variable `batch_date=YYYY-MM-DD`
   (ví dụ `2026-08-10`). Các block chạy tuần tự:
   `b01_generate` → `b02_entities` → `b03_telemetry` →
   `b04_crm_dms` → `b05_dbt_build` → `b06_qc_gate` → `b07_metabase_refresh`.
3. `b06_qc_gate` chặn pipeline nếu lệch count: entities tolerance 0%
   (`diff > 0` là đỏ), telemetry tolerance 1%.

## 6. Backfill một khoảng ngày

```powershell
python -m mage.pipelines.backfill.blocks.run_range --start-date 2026-08-10 --end-date 2026-08-12
```

`run_range.iter_dates(start, end)` sinh từng `batch_date` và gọi runner
tương ứng (mỗi ngày = 1 trigger `full_daily` với `batch_date` đó).

## 7. Xem log

Mỗi block ghi 1 dòng JSON vào `logs/{date}.jsonl` qua `blocks/_runner.py::run_cli`
(`block`, `batch_date`, `cmd`, `exit_code`, `duration_s`):

```powershell
Get-Content logs/2026-08-10.jsonl
```

`exit_code != 0` → `run_cli` raise `RuntimeError`, block fail, pipeline dừng
trước `b06_qc_gate` (không ghi Gold bẩn).

## 8. Onboard nguồn mới (6 bước)

5 bước gốc của pipeline metadata-driven + 1 bước template block Mage:

1. Tạo `Vinfast_v1/src/data_source/sources/<name>.yaml`
   (type `csv|parquet|api|kafka`, schedule, bronze/silver, mapping, dedup).
2. Tạo contract `contracts/<name>.contract.json`, bump `version` khi đổi schema.
3. `python -m src.pipeline.cli list` — nguồn mới hiện `valid=true`.
4. `python -m src.pipeline.cli run --source <name> --date 2026-08-10 --dry-run`
   (chỉ validate, không ghi).
5. `python -m src.pipeline.cli run --source <name> --date 2026-08-10` (ghi thật).
6. Copy template block Mage (ví dụ `b02_pipeline_entities.py`) thành
   `bXX_pipeline_<name>.py`, đổi `--source <name>`, đăng ký thứ tự chạy trong
   pipeline `full_daily` sau block phù hợp.

## 9. Sự cố thường gặp

- **MinIO đỏ / không kết nối:** kiểm tra `docker compose ps minio`,
  `MINIO_ENDPOINT` (`http://minio:9000` trong compose, `http://localhost:9100`
  từ host), user/pass trong `.env`; fallback local `data/bronze/` khi MinIO
  không khả dụng.
- **ClickHouse đỏ:** kiểm tra healthcheck `SELECT 1`, user/pass/db trong `.env`
  (`CLICKHOUSE_HOST=clickhouse` trong compose); dbt profile
  `Vinfast_v1/dbt_project/profiles.yml` phải khớp.
- **dbt đỏ:** chạy `python -m dbt.cli.main deps --profiles-dir .` rồi
  `compile` trước `run`; xem model lỗi trong `Vinfast_v1/dbt_project/models/`
  (staging → intermediate → marts).
- **Lệch count (QC gate đỏ):** `b06_qc_gate` raise `RuntimeError` khi entities
  lệch > 0% hoặc telemetry lệch > 1% (Silver MinIO vs Gold ClickHouse
  `mart_customer_360`). Kiểm tra `logs/{date}.jsonl` xem block nào fail,
  chạy lại `--dry-run` nguồn liên quan, rồi rerun `batch_date` đó.
