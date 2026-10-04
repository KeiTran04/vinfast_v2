# tests/test_blocks.py
import pathlib


def test_blocks():
    expected = {
        "mage/data_loaders/b01_generate.py": ["subprocess", "data_generator.cli", "generate"],
        "mage/transformers/b02_pipeline_entities.py": ["subprocess", "--source", "--date"],
        "mage/transformers/b03_pipeline_telemetry.py": ["subprocess", "charging_internal"],
        "mage/transformers/b04_pipeline_crm_dms_charging.py": ["subprocess", "--source", "dms"],
        "mage/transformers/b05_dbt_build.py": ["subprocess", "dbt.cli.main", "test"],
        "mage/transformers/b06_qc_gate.py": ["qc_check", "entities"],
        "mage/transformers/backfill_runner.py": ["subprocess", "iter_dates"],
        "mage/data_exporters/b07_metabase_refresh.py": ["subprocess", "setup_dashboards"],
    }
    for path, markers in expected.items():
        txt = pathlib.Path(path).read_text(encoding="utf-8")
        for m in markers:
            assert m in txt, f"{path} missing {m!r}"
    meta = pathlib.Path("mage/pipelines/full_daily/metadata.yaml").read_text(encoding="utf-8")
    for uuid in ["b01_generate", "b02_pipeline_entities", "b03_pipeline_telemetry",
                 "b04_pipeline_crm_dms_charging", "b05_dbt_build", "b06_qc_gate",
                 "b07_metabase_refresh"]:
        assert uuid in meta, f"full_daily metadata missing {uuid}"
