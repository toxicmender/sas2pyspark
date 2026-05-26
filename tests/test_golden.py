from pathlib import Path

from translator.pipeline import translate_sas_to_pyspark


def normalize(text: str) -> str:
    normalized = "".join(text.replace("\r\n", "\n").split())
    return normalized.replace(",)", ")")


def test_golden_data_step_if_else():
    sas_source = Path("tests/sas/data_step_if.sas").read_text(encoding="utf-8")
    expected = Path("tests/pyspark/data_step_if.py").read_text(encoding="utf-8")

    result = translate_sas_to_pyspark(sas_source)
    assert normalize(result.pyspark) == normalize(expected)
