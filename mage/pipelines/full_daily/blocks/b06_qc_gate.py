from __future__ import annotations

import os


def qc_check(silver_count: int, gold_count: int, kind: str) -> bool:
    if silver_count == 0 and gold_count == 0:
        return True
    diff = abs(silver_count - gold_count) / max(silver_count, 1)
    tol = 0.0 if kind == "entities" else 0.01
    if diff <= tol:
        return True
    raise RuntimeError(f"qc_gate {kind} mismatch silver={silver_count} gold={gold_count} diff={diff:.4f} tol={tol}")


def _silver_parquet_rowcount(s3, bucket: str, key: str) -> int:
    import io
    obj = s3.get_object(Bucket=bucket, Key=key)
    data = obj["Body"].read()
    try:
        import pyarrow.parquet as pq
        return pq.read_table(io.BytesIO(data)).num_rows
    except ImportError:
        import pandas as pd
        return len(pd.read_parquet(io.BytesIO(data)))


def main(batch_date: str):
    # doc Silver via boto3 + Gold via clickhouse-connect, so 2 cap entities/telemetry
    import boto3
    import clickhouse_connect
    s3 = boto3.client("s3", endpoint_url=os.environ.get("MINIO_ENDPOINT", "http://minio:9000"),
                      aws_access_key_id=os.environ.get("MINIO_ROOT_USER", "vinfast"),
                      aws_secret_access_key=os.environ.get("MINIO_ROOT_PASSWORD", "vinfast123"))
    ch = clickhouse_connect.get_client(host=os.environ.get("CLICKHOUSE_HOST", "clickhouse"),
                                       username=os.environ.get("CLICKHOUSE_USER", "vinfast"),
                                       password=os.environ.get("CLICKHOUSE_PASSWORD", "vinfast123"),
                                       database=os.environ.get("CLICKHOUSE_DB", "vinfast"))
    bucket = os.environ.get("SILVER_BUCKET", "vinfast-silver")
    # cap 1 entities snapshot 0%: Silver vehicles parquet vs Gold mart_vehicle_360
    silver_entities = _silver_parquet_rowcount(s3, bucket, "entities/vehicles/data.parquet")
    gold_vehicles = ch.query("SELECT count() AS c FROM vinfast.mart_vehicle_360").result_rows[0][0]
    qc_check(silver_entities, int(gold_vehicles), "entities")
    # cap 2 telemetry <1% (spec §6): Silver telemetry {date} parquet vs Gold mart count (same-day slice)
    silver_telemetry = _silver_parquet_rowcount(s3, bucket, f"telemetry/{batch_date}/data.parquet")
    gold_telemetry = ch.query(
        f"SELECT count() AS c FROM vinfast.mart_charging_analytics WHERE toDate(started_at) = toDate('{batch_date}')").result_rows[0][0]
    qc_check(silver_telemetry, int(gold_telemetry), "telemetry")
