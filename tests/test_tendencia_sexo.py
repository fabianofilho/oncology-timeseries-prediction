"""Regra de veredito da LAB-182, caso a caso, fixada antes de ver o resultado."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location("sex_trend", ROOT / "scripts" / "sex_trend.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _tr(fem: str, masc: str) -> dict:
    return {"fem|principal|taxa_padronizada": {"sentido": fem},
            "masc|principal|taxa_padronizada": {"sentido": masc}}


def test_so_apoia_com_as_duas_metades():
    v = _mod().veredito
    assert v(_tr("aumento", "queda"))["hipotese"] == "apoiada"
    assert v(_tr("estavel", "queda"))["hipotese"] == "apoiada em parte"
    assert v(_tr("aumento", "estavel"))["hipotese"] == "apoiada em parte"
    assert v(_tr("estavel", "estavel"))["hipotese"] == "nao apoiada"
    assert v(_tr("queda", "aumento"))["hipotese"] == "nao apoiada"
