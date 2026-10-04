# Spec: Rebuild VinFast Lakehouse với Mage.ai Wrapper (Option A) — Production-ready Orchestration + CI/CD

- Date: 2026-10-04 (updated v2)
- Status: Draft v2 — chờ bạn review file này trước khi lập implementation plan
- Reference: https://github.com/dHung2412/VinFast-EV-Data-Platform
- Workspace: `D:\DE_prj` (trống lúc brainstorm, sẽ chứa code rebuild)
- Quyết định đã chốt trong chat: Option A Wrapper + orchestrator Mage.ai + mục tiêu production-ready
- Personas phục vụ: DE owner (bạn), reviewer portfolio, operator chạy daily

## 1. Tóm tắt điều hành

Rebuild lại Lakehouse VinFast EV (MinIO Bronze/Silver là source of truth, ClickHouse chỉ Gold,
dbt là transform duy nhất) nhưng thay cách chạy tay bằng Mage.ai điều phối + CI tự động.

Nguyên tắc bất biến: **không sửa logic xử lý dữ liệu cũ, chỉ thêm lớp tự động hóa + giám sát bên trên.**
Mỗi block Mage chỉ `subprocess` gọi đúng CLI đã được kiểm chứng (`src.data_generator.cli`,
`src.pipeline.cli`, `dbt run/test`) và kiểm tra exit code. Nhờ vậy tái dùng toàn bộ 26 dbt tests,
QC 4 lớp trong `validator.py`, và quy trình onboard nguồn mới 5 bước mà không tốn công rewrite.

Khi xong, một lệnh `docker compose up -d` dựng đủ 5 services, Mage tự chạy daily 01:00,
lỗi tự retry + alert webhook, push code tự chạy lint/test/dbt gate.

## 2. Mục tiêu & tiêu chí thành công

G1. Tự động hóa end-to-end local: `generate -> pipeline 6 nguồn -> dbt run/test -> qc_gate`
chạy bằng 1 trigger Mage, không cần chạy tay từng lệnh như README gốc.
G2. Production-ready tối thiểu: retry có giới hạn, timeout rõ ràng, log JSON tập trung,
alert success/failed, healthcheck cho mọi service, runbook vận hành.
G3. CI chặn lỗi sớm: mọi PR phải qua `ruff + pytest + dbt compile/test`, fail thì block merge.
G4. Dễ onboard nguồn mới: thêm nguồn mới vẫn chỉ sửa `contracts/*.json` + `sources/*.yaml`
(+ plugin optional) + thêm 1 block wrapper, có template mẫu.

Tiêu chí nghiệm thu đo được:
- `docker compose up -d` lên đủ MinIO :9100/:9101, ClickHouse :8123, Metabase :3000, Mage :6789.
- Pipeline `full_daily` với `batch_date=2026-08-10` chạy xanh từ generate tới qc_gate,
  Silver có `telemetry/{date}/data.parquet`, Gold có đủ 6 marts, `dbt test` 26/26 pass.
- Giả lập fail (sai `--date` hoặc kill ClickHouse giữa `dbt run`): block fail, retry đúng số lần,
  downstream skip, alert webhook bắn đúng 1 tin có `batch_date + failed_block + run_url`.
- CI xanh trên push mới, và đỏ khi cố tình phá 1 dbt test.

## 3. Bối cảnh & ràng buộc

Code gốc đã mổ thực tế từ temp clone:
- `docker-compose.yml`: clickhouse 24.8 (`vinfast/vinfast123`, db `vinfast`), minio latest
  (`vinfast/vinfast123`, buckets bronze/silver/gold via minio-init), metabase latest + mount
  `./metabase/plugins/clickhouse.metabase-driver.jar`. Đoạn Airflow 3 đang comment — bỏ, thay bằng Mage.
- `src/pipeline/cli.py`: `list` + `run --source (repeatable) | --all --date YYYY-MM-DD [--dry-run]`,
  `--date` bắt buộc, chạy vòng lặp từng source, fail 1 source vẫn chạy tiếp rồi exit 1 cuối cùng.
- `src/data_generator/cli.py`: `generate --start-date --end-date --vehicles 20 --seed 42
  --output data/raw --datasets all` (hive parquet year=/month=/day=) + `mock-raw --source all/crm/dms/charging`.
- `dbt_project.yml`: staging materialized view, intermediate/marts table, profile `vinfast`.
  8 staging views đọc `s3()` trực tiếp từ MinIO, 2 intermediate, 6 marts.
- `requirements.txt`: dbt-core 1.12.3, dbt-clickhouse 1.9.3, pandas, pyarrow,
  clickhouse-connect, boto3, pyyaml.

Ràng buộc:
- Windows + Docker Desktop, Python 3.11, `$env:PYTHONUTF8=1` cho log tiếng Việt.
- Local-first, single-node, không HA, không streaming, không auto-deploy CD.
- Creds mặc định giữ như gốc để tương thích docs, nhưng phải qua env file, không hardcode trong Mage blocks.

## 4. Phương án đã cân nhắc

| Phương án | Mô tả | Trade-off | Kết luận |
|---|---|---|---|
| A. Wrapper (chọn) | Mage block = subprocess gọi CLI cũ | + Ít rủi ro, dùng lại tests/QC, xong nhanh 2-3 ngày. - Quan sát chưa tới từng bước EXTRACT→CONFORM | Chốt A, đúng YAGNI |
| B. Mage-native | Tách 6 bước thành block riêng | + Monitor granular. - Rewrite identity SQLite + plugin + tests, effort 3-4x, dễ break | Để V2 |
| C. Schedule-lite | Chỉ schedule script, CI lint | + <1 ngày. - Không retry/alert/monitoring, trượt mục tiêu production-ready | Loại |

## 5. Kiến trúc tổng thể

```
SOURCES (synthetic, giữ nguyên)
  telemetry hive parquet | crm csv | dms csv | charging csv + charging_internal
        |
        v
MAGE.AI :6789 (NEW - chỉ điều phối, không transform)
  trigger daily 01:00 Asia/Ho_Chi_Minh + manual backfill(date range)
  full_daily: generate -> pipeline(entities -> telemetry/charging_internal -> crm/dms/charging)
              -> dbt_build -> qc_gate -> metabase_refresh
  backfill:   param start/end date, gọi lại full_daily theo từng ngày
        |
        v
MinIO :9100 SOURCE OF TRUTH (giữ nguyên)
  vinfast-bronze raw landed parquet (partition ingest_date)
  vinfast-silver chuẩn hóa + phái sinh (snapshot entities ghi đè)
        |
        v  dbt stg_* đọc s3() trực tiếp, không raw_* trung gian
ClickHouse :8123 GOLD ONLY dbt-managed (giữ nguyên)
  stg 8 views -> int 2 tables -> mart 6 tables (26 tests)
        |
        v
Metabase :3000 (giữ nguyên, 7 dashboards = 7 persona)
CI GitHub Actions (NEW): lint -> unit -> dbt gate
Logs + Alert webhook (NEW)
```

Cây thư mục mục tiêu:
```
D:\DE_prj\
├── Vinfast_v1\                      # copy nguyên ref (src, dbt_project, metabase, warehouse)
├── mage\
│   ├── Dockerfile.mage              # mageai/mageai + copy requirements + dbt
│   ├── io_config.yaml               # minio(clickhouse creds qua env, không commit secret thật)
│   └── pipelines\
│       ├── full_daily/
│       │   ├── metadata.yaml        # schedule daily, retry policy, alert hook
│       │   └── blocks/
│       │       ├── b01_generate.py          # subprocess generate + mock-raw
│       │       ├── b02_pipeline_entities.py
│       │       ├── b03_pipeline_telemetry.py
│       │       ├── b04_pipeline_crm_dms_charging.py
│       │       ├── b05_dbt_build.py         # dbt deps + run + test, fail -> dừng
│       │       ├── b06_qc_gate.py           # so rowcount Silver vs Gold
│       │       └── b07_metabase_refresh.py  # gọi setup_dashboards.py --refresh-only
│       └── backfill/
│           └── metadata.yaml        # params start_date/end_date, loop theo ngày
├── .github/workflows/ci.yml
├── docker-compose.yml               # gốc + service mageai
├── .env.example                     # MINIO_*, CLICKHOUSE_*, ALERT_WEBHOOK_URL, MAGE_PORT
├── logs/                            # mount chung, JSON lines
└── docs/ops/runbook.md              # lệnh tay, backfill, xem log, onboard nguồn mới
```

`docker-compose` thêm:
```yaml
mageai:
  build: { context: ./mage }
  ports: ["6789:6789"]
  env_file: .env
  environment:
    MINIO_ENDPOINT: http://minio:9000
    CLICKHOUSE_HOST: clickhouse
    PYTHONPATH: /home/code:/home/code/src
  volumes:
    - ./Vinfast_v1:/home/code
    - ./mage/pipelines:/home/mage/pipelines
    - ./logs:/home/src/logs
    - ./data:/home/code/data
  depends_on: { minio: {condition: service_healthy}, clickhouse: {condition: service_healthy} }
```

## 6. Chi tiết Mage blocks (wrapper thuần túy)

Mọi block tuân cùng khung: `subprocess.run([...], check=False) -> parse stdout tìm rows/duration
-> ghi 1 dòng JSON log -> return exit_code`. Không import `src.pipeline` trực tiếp để tránh
kẹt dependency và để giữ ranh giới “Mage không transform”.

- `b01_generate`: `python -m src.data_generator.cli generate --start-date {ds} --end-date {ds}
  --seed 42` + `mock-raw --source all --seed 42`. Idempotent theo `ds` vì ghi đè partition ngày.
- `b02..b04 pipeline`: gọi `python -m src.pipeline.cli run --source ... --date {ds}`
  theo thứ tự bắt buộc entities trước (để identity match_or_create có VIN/user trước),
  sau đó telemetry + charging_internal song song được, cuối cùng crm/dms/charging.
  `--dry-run` dùng cho onboard test, không ghi MinIO.
- `b05_dbt_build`: `dbt deps && dbt run --full-refresh --profiles-dir . && dbt test --profiles-dir .`
  chạy trong `/home/code/dbt_project`. Retry chỉ 1 lần để tránh double-write mart.
- `b06_qc_gate` (block mới duy nhất có logic): đọc Silver parquet rowcount qua `boto3`
  + query `SELECT count() FROM vinfast.mart_*` qua `clickhouse-connect`, so sánh ngưỡng
  entities 0%, telemetry <1%. Fail -> raise để Mage mark failed và skip refresh.
- `b07_metabase_refresh`: gọi `python metabase/setup_dashboards.py` ở chế độ refresh
  (không tạo duplicate dashboard /39-45).

`io_config.yaml` chỉ lưu endpoint + user, password lấy từ env. Không commit `.env` thật.

## 7. Data flow & tính幂 đẳng

Daily `{ds}`: trigger 01:00 -> generate ghi `data/raw/{dataset}/year=/month=/day=` ->
pipeline land Bronze `ingest_date={ds}` -> conform Silver `{prefix}/{ds}/data.parquet`
(snapshot entities ghi đè key cố định) -> dbt stg views đọc `s3()` Silver -> marts Gold ->
qc_gate -> refresh Metabase.

Backfill `[start,end]`: loop từng ngày gọi lại full_daily, ngày nào fail thì dừng và báo ngày đó,
không chạy lấn ngày sau. Mọi bước ghi đè theo partition nên chạy lại an toàn.

## 8. Error handling / Retry / Logging / Alert

| Block | Timeout | Retry | Fail thì sao |
|---|---|---|---|
| generate | 20 phút | 2, delay 60s exp | pipeline downstream skip, alert |
| pipeline entities/crm/dms/charging | 30 phút | 2, delay 60s exp | dừng chuỗi, không chạy dbt, alert |
| pipeline telemetry | 45 phút | 2, delay 60s exp | như trên |
| dbt run/test | 20 phút | 1 | skip qc_gate + refresh, alert kèm `dbt test` failures |
| qc_gate | 5 phút | 0 | skip refresh, alert data mismatch |
| metabase refresh | 10 phút | 1 | pipeline mark partial-success, alert warning |

Gates fail-fast theo thứ tự: QC 4 lớp trong `validator.py` (exit 1) -> Mage block fail ->
`dbt test` 26 tests hard gate -> `qc_gate` rowcount gate -> mới refresh BI.

Log: giữ file log gốc + mỗi block ghi 1 dòng JSON
`{ts, pipeline, block, source, batch_date, rows_in, rows_out, duration_s, exit_code, run_url}`.
Xem realtime trên Mage UI, tra cứu sau trong `./logs/*.jsonl` bằng `rg`.

Alert V1: 1 webhook chung (`ALERT_WEBHOOK_URL`) bắn 2 sự kiện pipeline success/failed
nội dung gồm `batch_date, failed_block, exit_code, run_url, 5 dòng log cuối`.
Không hardcode URL, không spam từng retry — chỉ bắn khi hết retry.

## 9. Testing strategy

- Tái dùng: 26 `dbt test` + QC 4 lớp gốc, không viết lại.
- Thêm `pytest` wrapper (nhẹ, <10 tests): block build đúng CLI args, parser `--date` bắt buộc,
  `qc_gate` comparator đúng ngưỡng 0%/1%, loader `sources/*.yaml` + `contracts/*.json` hợp lệ.
- `dbt compile` trong CI để bắt lỗi SQL/jinja sớm không cần data thật.
- Manual checklist trước merge: `full_daily` xanh với 1 ngày mẫu, backfill 2 ngày liên tiếp xanh,
  kill ClickHouse giữa `dbt run` để kiểm tra retry + alert đúng 1 tin.

## 10. CI/CD

`.github/workflows/ci.yml` 3 jobs chạy song song sau checkout:
1. `lint`: `ruff check .` + `python -m compileall -q src mage`.
2. `unit`: `pip install -r Vinfast_v1/requirements.txt + pytest -q`.
3. `dbt`: dựng `clickhouse/clickhouse-server:24.8` + `minio/minio` service containers,
   seed 1 ngày (`generate --start-date X --end-date X --vehicles 5`), rồi
   `dbt deps && dbt compile && dbt run && dbt test --profiles-dir .`.
Fail job nào block merge job đó. Chưa làm CD auto-deploy, giữ `docker compose up -d` tay (YAGNI).

## 11. Monitoring & vận hành

- Healthcheck: giữ minio/clickhouse gốc, thêm `mageai` curl `/health`, metabase depends clickhouse healthy.
- Lịch: `full_daily` cron `0 1 * * *` timezone Asia/Ho_Chi_Minh, `backfill` manual nhập start/end.
- Runbook `docs/ops/runbook.md` phải có: lệnh dựng services + tải driver jar Metabase,
  lệnh chạy tay full 3 bước gốc khi Mage down, cách mở Mage UI xem log từng block,
  backfill 1 ngày/many ngày, onboard nguồn mới 5 bước cũ + bước 6 thêm block wrapper + ví dụ YAML,
  checklist sự cố (MinIO down, ClickHouse down, dbt test đỏ, Silver/Gold lệch count).
- Onboarding nguồn mới ví dụ: copy `sources/telemetry.yaml` -> `sources/newsrc.yaml`,
  thêm contract JSON, chạy `run --source newsrc --date X --dry-run`, rồi copy
  `b04_pipeline_crm_dms_charging.py` đổi `--source newsrc` là xong.

## 12. Bảo mật & cấu hình

`.env.example` liệt kê `MINIO_ROOT_USER/PASSWORD, CLICKHOUSE_USER/PASSWORD/DB,
ALERT_WEBHOOK_URL, MAGE_PORT=6789`. `.env` thật gitignore. Mage blocks đọc qua `os.environ`,
không paste secret vào YAML/log. Ports mặc định giữ như gốc để docs cũ vẫn đúng.

## 13. Non-goals

Không Mage-native refactor, không Kafka/Flink streaming, không multi-node HA,
không thêm nguồn/mart/dashboard mới, không PagerDuty/email phức tạp, không auto-deploy CD.

## 14. Rủi ro & giảm thiểu

- Mage image nặng + Windows mount chậm -> ghim `mageai/mageai:<stable>`, mount tối thiểu,
  đưa `requirements` vào Dockerfile để khỏi pip mỗi lần up.
- dbt-clickhouse version lệch -> ghim đúng 1.12.3/1.9.3 như gốc, CI dùng cùng image.
- Metabase driver jar phải tải tay -> đưa vào runbook + check `Test-Path` trong CI lint.
- Backfill đè partition -> tất cả writes đều overwrite theo ngày, qc_gate chạy sau cùng để phát hiện lệch.

## 15. Kế hoạch rollout (để writing-plans chi tiết hóa)

P0: copy `Vinfast_v1` nguyên + compose chạy tay xanh 1 ngày mẫu.
P1: thêm service Mage + `full_daily` 7 blocks wrapper + qc_gate + alert webhook stub.
P2: CI 3 jobs + runbook + backfill pipeline + template onboard nguồn mới.
P3: demo nghiệm thu theo 4 tiêu chí mục 2.

## 16. Acceptance criteria (Definition of Done)

1. Compose 5 services healthy, Mage UI mở được :6789.
2. `full_daily` ngày mẫu xanh tới refresh, đủ Silver + 6 marts, 26/26 dbt pass.
3. Fail injection đúng retry/skip/1 alert như mục 2.
4. CI xanh/red đúng kỳ vọng, runbook đủ để người mới chạy lại từ zero.

## 17. Self-review v2

- [x] Không còn TBD/TODO, mọi số (port, timeout, retry, ngưỡng %, cron, version) đều cụ thể.
- [x] Nhất quán: Mage không transform, dbt là transform duy nhất, MinIO là source of truth.
- [x] Đủ nhỏ cho 1 implementation plan (P0-P3), không lẫn streaming/HA.
- [x] Không mập mờ: thứ tự nguồn, idempotency overwrite, alert 1 tin sau hết retry, CD manual đều explicit.
