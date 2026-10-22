"""Regra de repeticao da LAB-237 (22/10) e juncao dos lotes de replicas."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_simulacao as rs  # noqa: E402


def resumo(confirmados: dict[str, int], r: int = 20) -> dict:
    reps = []
    for i in range(r):
        reps.append({"replica": i + 1, "pares": [
            {"par": par, "confirmado": i < n} for par, n in confirmados.items()]})
    return {"replicas": r, "por_replica": reps}


def test_proporcoes_so_novo_contra_simples():
    p = rs.proporcoes(resumo({"timesfm_menos_sarima": 10, "sarima_menos_linear_trend": 20,
                              "timesfm_menos_prophet": 20}))
    assert p == {"timesfm_menos_sarima": 0.5}


@pytest.mark.parametrize("n,no_limite", [(7, False), (8, True), (12, True), (13, False)])
def test_faixa_do_limite_exclusiva(n, no_limite):
    v = rs.proporcoes(resumo({"prophet_menos_seasonal_naive": n}))["prophet_menos_seasonal_naive"]
    assert (rs.LIMITE[0] < v < rs.LIMITE[1]) is no_limite


def test_le_previsoes_junta_lotes_e_recusa_duplicata(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "OUT", tmp_path)
    p = rs.pasta("ruido", 0.05)
    p.mkdir(parents=True)
    linha = {"model": "x", "date": "2015-01-01", "y_true": 1.0, "y_pred": 1.0, "window": 1, "horizon": 1}
    falha = pd.DataFrame(columns=["replica", "window", "model", "erro"])
    for m in rs.MODELOS:
        pd.DataFrame([{**linha, "model": m, "replica": 1}]).to_csv(p / f"pred_{m}.csv", index=False)
        falha.to_csv(p / f"pred_{m}_falhas.csv", index=False)
        pd.DataFrame([{**linha, "model": m, "replica": 2}]).to_csv(p / f"pred_{m}_r2-2.csv", index=False)
        falha.to_csv(p / f"pred_{m}_r2-2_falhas.csv", index=False)
    pred, _ = rs.le_previsoes("ruido", 0.05)
    assert sorted(pred.replica.unique()) == [1, 2] and len(pred) == 2 * len(rs.MODELOS)
    pd.DataFrame([{**linha, "model": "sarima", "replica": 2}]).to_csv(p / "pred_sarima_r2-2b.csv", index=False)
    falha.to_csv(p / "pred_sarima_r2-2b_falhas.csv", index=False)
    with pytest.raises(SystemExit):
        rs.le_previsoes("ruido", 0.05)
