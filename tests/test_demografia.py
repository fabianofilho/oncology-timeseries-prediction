"""Idade do SIM, padronizacao por Segi e Prais-Winsten (LAB-182)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from onco_timeseries.demografia import (
    FAIXAS,
    SEGI,
    faixa_etaria,
    idade_em_anos,
    prais_winsten,
    taxa_padronizada,
)


def test_segi_soma_cem_mil_e_cobre_as_faixas():
    assert sum(SEGI.values()) == 100_000
    assert list(SEGI) == FAIXAS


def test_idade_do_sim_em_texto_e_em_numero():
    cod = pd.Series(["465", "401", "400", "503", "312", "012", "999", None, "", 465])
    anos = idade_em_anos(cod)
    assert anos.tolist()[:6] == [65, 1, 0, 103, 0, 0]
    assert anos.iloc[6:9].isna().all()   # 999, None e vazio sao ignorados
    assert anos.iloc[9] == 65            # lido como numero


def test_faixa_etaria_nas_bordas():
    anos = pd.Series([0, 4, 5, 79, 80, 103, np.nan])
    assert faixa_etaria(anos).tolist()[:6] == ["0-4", "0-4", "5-9", "75-79", "80+", "80+"]
    assert pd.isna(faixa_etaria(anos).iloc[6])


def test_taxa_padronizada_de_taxa_constante_e_a_propria_taxa():
    # mesma taxa em todas as faixas: a padronizada tem de ser ela, qualquer que seja o peso
    pop = pd.Series(1_000_000, index=FAIXAS)
    obitos = pd.Series(50, index=FAIXAS)
    assert taxa_padronizada(obitos, pop) == pytest.approx(5.0)


def test_taxa_padronizada_recusa_faixa_sem_populacao():
    pop = pd.Series(1_000_000, index=FAIXAS).drop("80+")
    with pytest.raises(ValueError):
        taxa_padronizada(pd.Series(1, index=FAIXAS), pop)


def test_prais_winsten_recupera_apc_conhecido():
    anos = np.arange(2010, 2020)
    y = 10 * 1.03 ** (anos - 2010)          # +3% ao ano, sem ruido
    t = prais_winsten(anos, y)
    assert t.apc == pytest.approx(3.0, abs=1e-6)
    assert t.sentido == "aumento"


def test_prais_winsten_serie_com_ruido_e_ar1():
    rng = np.random.default_rng(1)
    anos = np.arange(2010, 2024)
    e = np.zeros(len(anos))
    for i in range(1, len(anos)):
        e[i] = 0.5 * e[i - 1] + rng.normal(0, 0.01)
    y = 10 ** (1 - 0.01 * (anos - 2010) + e)  # log10 cai 0,01 por ano: APC ~ -2,3%
    t = prais_winsten(anos, y)
    assert t.ic_low < -2.276 < t.ic_high
    assert t.sentido == "queda"
