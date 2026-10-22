"""Perturbacoes do estudo de simulacao (LAB-237): o que entra onde, e nada vaza do teste."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from onco_timeseries.evaluate import rolling_origin_splits
from onco_timeseries.simulacao import (
    CENARIOS,
    aplica_faltantes,
    mascara,
    prepara,
    ruido,
    semente,
)


@pytest.fixture
def serie() -> pd.Series:
    idx = pd.date_range("2010-01-01", periods=120, freq="MS")
    return pd.Series(np.linspace(3700, 4600, 120) + 50 * np.sin(np.arange(120)), index=idx)


def test_semente_estavel_e_distinta():
    assert semente("ruido", 0.05, 1) == semente("ruido", 0.05, 1)
    assert semente("ruido", 0.05, 1) != semente("ruido", 0.05, 2)
    assert semente("ruido", 0.05, 1) != semente("ruido", 0.10, 1)


def test_mascara_fixa_por_replica(serie):
    a = prepara(serie, "faltantes", 0.10, 3)["faltantes"]
    b = prepara(serie, "faltantes", 0.10, 3)["faltantes"]
    assert a.equals(b)
    assert len(a) == 12


def test_faltantes_sem_nan_e_sem_ver_o_teste(serie):
    meses = mascara(serie.index, 0.20, np.random.default_rng(0))
    for train, test in rolling_origin_splits(serie, horizon=6, min_train_size=60):
        t = aplica_faltantes(train, meses)
        assert not t.isna().any()
        assert t.index.equals(train.index)
        # meses nao mascarados ficam intactos
        livres = ~train.index.isin(meses)
        assert np.allclose(t[livres], train[livres])
        # trocar o futuro nao muda a interpolacao do treino
        outra = serie.copy()
        outra.loc[test.index] = 0.0
        assert np.allclose(aplica_faltantes(outra.loc[train.index], meses), t)


def test_faltantes_preserva_a_verdade(serie):
    p = prepara(serie, "faltantes", 0.20, 1)
    assert p["serie"].equals(serie.astype(float))


def test_quebra_muda_nivel_a_partir_do_mes(serie):
    p = prepara(serie, "quebra", 0.10, 1)
    t = p["posicao"]
    assert 36 <= t <= 108
    assert np.allclose(p["serie"].iloc[:t], serie.iloc[:t])
    assert np.allclose(p["serie"].iloc[t:], serie.iloc[t:] * 1.10)


def test_atipico_so_um_mes(serie):
    p = prepara(serie, "atipico", 0.20, 1)
    dif = ~np.isclose(p["serie"], serie)
    assert dif.sum() == 1 and dif[p["posicao"]]


def test_ruido_com_cv_aproximado():
    s = pd.Series(np.full(200_000, 1000.0))
    r = ruido(s, 0.05, np.random.default_rng(1)) / 1000.0
    assert abs(r.mean() - 1) < 0.002 and abs(r.std() - 0.05) < 0.002


def test_treino_curto_sem_sorteio(serie):
    p = prepara(serie, "treino_curto", 24, 1)
    assert p["max_train"] == 24 and p["serie"].equals(serie.astype(float))


def test_niveis_registrados():
    assert CENARIOS["treino_curto"] == [24, 36, 48]
    assert CENARIOS["faltantes"] == [0.05, 0.10, 0.20]
    assert CENARIOS["ruido"] == [0.02, 0.05, 0.10]
