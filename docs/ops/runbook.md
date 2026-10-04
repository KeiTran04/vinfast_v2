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

| Service    | URL                   | Ghi chú |
|------------|-----------------------|---------|
| Mage       | http://localhost:6789 | UI orchestration (200 = sống) |
| S3 (Moto)  | http://localhost:9100 | API S3, **không có console UI** |
| ClickHouse | http://localhost:8123 | |
| Metabase   | http://localhost:3000 | setup lần đầu, driver jar đã kèm sẵn |

Credentials MinIO/ClickHouse lấy từ `.env` (`vinfast` / `vinfast123` mặc định).

> **Lưu ý S3:** service `minio` trong compose là **Moto server**
> (`motoserver/moto`), không phải MinIO thật — vì `minio/minio` đã bị gỡ
> khỏi Docker Hub, `quay.io` chặn pull ẩn danh, `dl.min.io` trả 410.
> Buckets (`vinfast-bronze/silver/gold`) **tự tạo bởi pipeline**
> (`lander.py`/`conformer.py` ensure-bucket), không còn service `minio-init`/`mc`.
> Moto lưu in-memory (restart container là mất data S3 → chạy lại pipeline).
> Kiểm tra data bằng boto3/python thay vì console UI. SQL `s3('http://minio:9000/...')`
> của dbt giữ nguyên vì tên service + port trong compose không đổi.

## 4. Chạy tay khi Mage down (đường chính local)

Chạy từ thư mục `Vinfast_v1/` (pipeline gốc, không qua Mage).
Mọi lệnh Python cần 2 env (tránh lỗi encoding + để boto3 nói chuyện với Moto):

```powershell
$env:PYTHONUTF8 = 1
$env:S3_ADDRESSING_STYLE = "path"
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
python -m dbt.cli.main deps --profiles-dir .
python -m dbt.cli.main run --profiles-dir . --target docker
python -m dbt.cli.main test --profiles-dir . --target docker
cd ..\..
python metabase/setup_dashboards.py --base-url http://localhost:3000  # ở Vinfast_v1/
```

> **Bẫy partition đã gặp:** staging đọc glob `*` nên mỗi nguồn phi-telemetry
> chỉ được ghi đúng **1 batch_date** (29). Đừng chạy `--all` thêm ngày khác
> cho crm/dms/charging (đã từng gây duplicate `customer_id` → rớt test
> `unique_mart_customer_360_customer_id`). Lỡ ghi thừa thì xóa partition thừa
> bằng boto3 `delete_object` rồi chạy lại `dbt run/test`.

Kiểm tra nhanh từng nguồn:

```powershell
python -m src.pipeline.cli list
python -m src.pipeline.cli run --source crm --date 2026-08-10 --dry-run
python -m src.pipeline.cli run --source crm --date 2026-08-10
```

## 5. Trigger `full_daily` trên Mage (đường chính)

`mage/` là Mage project thật (`metadata.yaml` project + `pipelines/*/metadata.yaml`
đúng schema + blocks trong `data_loaders/`, `transformers/`, `data_exporters/`).
Mage đọc code trực tiếp từ mount `./mage` nên sửa file là có hiệu lực ngay,
không cần rebuild (chỉ rebuild khi đổi `Dockerfile.mage`/`requirements.mage.txt`).

1. Mở Mage http://localhost:6789 → Pipelines → `full_daily` (7 blocks) và `backfill`.
2. Tạo schedule 1 lần: POST `/api/pipelines/full_daily/pipeline_schedules`
   `{"pipeline_schedule": {"name": "manual", "schedule_type": "api"}}`
   → PUT `/api/pipeline_schedules/{id}` `{"pipeline_schedule": {"status": "active"}}`.
   (POST thẳng `/api/pipeline_schedules` sẽ 500 — schedule lồng dưới pipeline.)
3. Trigger run: POST `/api/pipeline_schedules/{id}/pipeline_runs`
   `{"pipeline_run": {"variables": {"batch_date": "2026-08-10"}}}`
   — chú ý key số ít `pipeline_run` (dùng `pipeline_runs` sẽ bị lặng lẽ bỏ variables).
   Biến `batch_date` tới từng block qua `kwargs` (fallback env `BATCH_DATE`).
4. Retry từ block giữa chừng: PUT `/api/pipeline_runs/{id}`
   `{"pipeline_run": {"pipeline_run_action": "retry_blocks",
   "from_block_uuid": "b06_qc_gate"}}`.
5. Theo dõi: GET `/api/pipeline_runs/{id}` (status) và
   `/api/pipeline_runs/{id}/block_runs` (từng block); log chi tiết trong
   `docker logs de_prj-mageai-1`.
6. `b06_qc_gate` chặn pipeline nếu lệch count: entities (snapshot vehicles
   vs `mart_vehicle_360`) tolerance 0%, telemetry tolerance 1% — nhánh
   telemetry so Silver `charging_internal/{date}` (sessions/ngày, cùng đơn vị
   với mart) vs `mart_charging_analytics` slice cùng ngày, KHÔNG so Silver
   telemetry raw events với mart sessions (khác đơn vị, từng gây fail oan
   `diff=0.9983`). Cảnh báo: `full_daily` viết crm/dms/charging theo đúng
   1 `batch_date` — đừng trộn nhiều batch thủ công (staging đọc glob `*`,
   2 partitions → rớt test unique `customer_id`; xem bẫy partition ở §4).

> Bài học đã gặp: file block sửa xong phải **không BOM** (PowerShell
> `Set-Content -Encoding utf8` thêm BOM → Mage `exec` SyntaxError
> `U+FEFF`). Decorator phải giữ mẫu `if 'x' not in globals()` (ghi đè
> collector của executor → fail `no decorated functions`). Block không
> upstream thì signature chỉ `(*args, **kwargs)` (kẻo fail
> `missing upstream dependencies`).

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

- **S3 (Moto) đỏ / không kết nối:** `docker compose ps minio`,
  `docker logs de_prj-minio-1`; endpoint trong compose `http://minio:9000`,
  từ host `http://localhost:9100`; boto3 cần `S3_ADDRESSING_STYLE=path`.
  Moto in-memory → restart là mất data, chạy lại pipeline là có.
- **Mage build/start fail (`Secondary flag...`):** image `mageai` kèm
  `typer 0.9.0`, `pip install` dbt nâng `click>=8.2` gây vỡ. Đã fix bằng
  `typer==0.16.0` trong `mage/requirements.mage.txt` — đừng xóa dòng đó.
  Build lại: `docker compose build mageai && docker compose up -d mageai`.
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
