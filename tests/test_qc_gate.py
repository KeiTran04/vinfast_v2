# tests/test_qc_gate.py
from mage.transformers.b06_qc_gate import qc_check


def test_qc_gate():
    assert qc_check(100, 100, "entities") is True
    assert qc_check(1000, 995, "telemetry") is True
    try:
        qc_check(100, 90, "entities")
        raise AssertionError("should have raised")
    except RuntimeError:
        pass
    try:
        qc_check(1000, 900, "telemetry")
        raise AssertionError("should have raised")
    except RuntimeError:
        pass
