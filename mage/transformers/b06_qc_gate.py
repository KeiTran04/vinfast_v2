"""b06_qc_gate (transformer): so rowcount Silver vs Gold + alert webhook khi fail.

Cap 1 entities snapshot 0%, cap 2 telemetry <1%. Self-contained (stdlib o top-level;
boto3/clickhouse_connect import trong ham de plain pytest van import duoc).
"""
import os

if 'transformer' not in globals():  # GIU NGUYEN: Mage executor tu nap collector
    # decorator; ghi de se lam mat dang ky block (fail 'no decorated functions')
    try:
        from mage_ai.data_preparation.decorators import transformer
    except ImportError:  # plain pytest khong co mage_ai
        def transformer(fn):
            return fn


def qc_check(silver_count, gold_count, kind):
    if silver_count == 0 and gold_count == 0:
        return True
    diff = abs(silver_count - gold_count) / max(silver_count, 1)
    tol = 0.0 if kind == "entities" else 0.01
    if diff <= tol:
        return True
    raise RuntimeError(
        f"qc_gate {kind} mismatch silver={silver_count} gold={gold_count} "
        f"diff={diff:.4f} tol={tol}")


def _parquet_rowcount(s3, bucket, key):
    import io
    try:
        data = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    except Exception as e:  # noqa: BLE001 - wrap thanh RuntimeError kem key context
        raise RuntimeError(f"qc_gate missing silver s3://{bucket}/{key}: {e}")
    try:
        import pyarrow.parquet as pq
        return pq.read_table(io.BytesIO(data)).num_rows
    except ImportError:
        import pandas as pd
        return len(pd.read_parquet(io.BytesIO(data)))


def _alert(status, batch_date, failed_block="", run_url=""):
    import json
    import urllib.request
    url = os.environ.get("ALERT_WEBHOOK_URL", "")
    if not url:
        return
    data = json.dumps(
        {"text": f"[vinfast] {status} date={batch_date} block={failed_block} {run_url}"}
    ).encode()
    try:
        urllib.request.urlopen(
            urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}),
            timeout=10)
    except Exception:  # noqa: BLE001, S110 - alert khong bao gio duoc lam fail pipeline
        pass


@transformer
def run_block(data=None, *args, **kwargs):
    import boto3
    import clickhouse_connect
    from botocore.config import Config

    batch_date = kwargs.get("batch_date") or os.environ.get("BATCH_DATE", "2026-08-10")
    addressing = os.environ.get("S3_ADDRESSING_STYLE", "auto")
    s3 = boto3.client("s3", endpoint_url=os.environ.get("MINIO_ENDPOINT", "http://minio:9000"),
                      aws_access_key_id=os.environ.get("MINIO_ROOT_USER", "vinfast"),
                      aws_secret_access_key=os.environ.get("MINIO_ROOT_PASSWORD", "vinfast123"),
                      config=Config(connect_timeout=5, read_timeout=10,
                                    s3={"addressing_style": addressing}))
    ch = clickhouse_connect.get_client(host=os.environ.get("CLICKHOUSE_HOST", "clickhouse"),
                                       username=os.environ.get("CLICKHOUSE_USER", "vinfast"),
                                       password=os.environ.get("CLICKHOUSE_PASSWORD", "vinfast123"),
                                       database=os.environ.get("CLICKHOUSE_DB", "vinfast"))
    bucket = os.environ.get("SILVER_BUCKET", "vinfast-silver")
    try:
        silver_entities = _parquet_rowcount(s3, bucket, "entities/vehicles/data.parquet")
        gold_vehicles = ch.query(
            "SELECT count() AS c FROM vinfast.mart_vehicle_360").result_rows[0][0]
        qc_check(silver_entities, int(gold_vehicles), "entities")
        # cap 2 telemetry <1%: dung Silver charging_internal (sessions/ngay, cung don vi
        # voi mart), KHONG dung Silver telemetry raw events (11329 rows vs 19 sessions).
        silver_sessions = _parquet_rowcount(s3, bucket, f"charging_internal/{batch_date}/data.parquet")
        gold_telemetry = ch.query(
            "SELECT count() AS c FROM vinfast.mart_charging_analytics "
            f"WHERE toDate(started_at) = toDate('{batch_date}')").result_rows[0][0]
        qc_check(silver_sessions, int(gold_telemetry), "telemetry")
    except Exception:
        _alert("failed", batch_date, failed_block="b06_qc_gate")
        raise
    _alert("success", batch_date)
    return {"block": "b06_qc_gate", "batch_date": batch_date, "exit_code": 0}
