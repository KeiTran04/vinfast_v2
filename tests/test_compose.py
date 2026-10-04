# tests/test_compose.py
import pathlib

import yaml


def test_compose():
    d = yaml.safe_load(pathlib.Path("docker-compose.yml").read_text(encoding="utf-8"))
    svcs = d.get("services", {})
    assert "minio" in svcs, "missing minio"
    assert "clickhouse" in svcs, "missing clickhouse"
    assert "metabase" in svcs, "missing metabase"
    assert "mageai" in svcs, "missing mageai"
    assert "6789:6789" in str(svcs["mageai"].get("ports", [])), "mage port wrong"
    cfg = pathlib.Path("mage/io_config.yaml").read_text(encoding="utf-8")
    assert "MINIO_ENDPOINT" in cfg and "CLICKHOUSE_HOST" in cfg
