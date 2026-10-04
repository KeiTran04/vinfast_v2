# tests/test_blocks.py
import pathlib


def test_blocks():
    for name in ["b01_generate.py","b02_pipeline_entities.py","b03_pipeline_telemetry.py",
                 "b04_pipeline_crm_dms_charging.py","b05_dbt_build.py","b07_metabase_refresh.py"]:
        p = pathlib.Path("mage/pipelines/full_daily/blocks") / name
        assert p.exists(), f"missing {name}"
        txt = p.read_text(encoding="utf-8")
        assert "run_cli" in txt, name
    txt = pathlib.Path("mage/pipelines/full_daily/blocks/_runner.py").read_text(encoding="utf-8")
    assert "subprocess" in txt, "_runner.py"
    txt = pathlib.Path("mage/pipelines/full_daily/blocks/b02_pipeline_entities.py").read_text()
    assert "--source" in txt and "--date" in txt
