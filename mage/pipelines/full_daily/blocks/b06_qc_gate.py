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


def main(batch_date: str):
    # doc Silver via boto3 + Gold via clickhouse-connect, so 2 cap entities/telemetry
    import boto3, clickhouse_connect
    s3 = boto3.client("s3", endpoint_url=os.environ.get("MINIO_ENDPOINT", "http://minio:9000"),
                      aws_access_key_id=os.environ.get("MINIO_ROOT_USER", "vinfast"),
                      aws_secret_access_key=os.environ.get("MINIO_ROOT_PASSWORD", "vinfast123"))
    ch = clickhouse_connect.get_client(host=os.environ.get("CLICKHOUSE_HOST", "clickhouse"),
                                       username=os.environ.get("CLICKHOUSE_USER", "vinfast"),
                                       password=os.environ.get("CLICKHOUSE_PASSWORD", "vinfast123"),
                                       database=os.environ.get("CLICKHOUSE_DB", "vinfast"))
    # dem toi thieu: entities users snapshot + telemetry day
    silver_entities = s3.list_objects_v2(Bucket="vinfast-silver", Prefix="entities/users/").get("KeyCount", 0)
    gold_users = ch.query("SELECT count() AS c FROM vinfast.mart_customer_360").result_rows[0][0]
    qc_check(1 if silver_entities > 0 else 0, 1 if gold_users > 0 else 0, "entities")
