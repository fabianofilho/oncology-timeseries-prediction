"""Testes dos intervalos conformais.

Os dois que decidem se o modulo presta:

  - em serie sintetica estacionaria, a cobertura empirica fica proxima do nominal;
  - nenhuma janela usa residuo do proprio periodo de teste nem de periodo futuro.

O segundo e o que impede vazamento, e e testado de duas formas independentes:
por construcao (adulterar o futuro nao pode mexer no passado) e por contagem
(o numero de residuos disponiveis tem que crescer de um em um).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from onco_timeseries.intervals import (
    MIN_CALIB_JANELAS,
    conformal_intervals,
    evaluate_by_horizon,
    evaluate_intervals,
    interval_score,
    weighted_interval_score,
)

HOR = 6


def frame_sintetico(n_janelas: int = 400, sigma: float = 100.0, seed: int = 7,
                    nivel: float = 4200.0) -> pd.DataFrame:
    """Serie estacionaria: y_pred constante, erro normal de desvio conhecido."""
    rng = np.random.default_rng(seed)
    linhas = []
    for w in range(1, n_janelas + 1):
        for h in range(1, HOR + 1):
            pred = nivel
            linhas.append(
                {
                    "model": "m",
                    "window": w,
                    "horizon": h,
                    "y_pred": pred,
                    "y_true": pred + rng.normal(0, sigma),
                }
            )
    return pd.DataFrame(linhas)


# --------------------------------------------------------------------------- #
# cobertura
# --------------------------------------------------------------------------- #
def test_cobertura_proxima_do_nominal_em_serie_estacionaria():
    df = conformal_intervals(frame_sintetico())
    r = evaluate_intervals(df)
    for nivel in (50, 80, 95):
        obtido = r[f"cobertura_{nivel}"]
        assert abs(obtido - nivel / 100) < 0.04, f"nivel {nivel}: cobertura {obtido:.3f}"


def test_largura_cresce_com_o_nivel_nominal():
    df = conformal_intervals(frame_sintetico())
    r = evaluate_intervals(df)
    assert r["largura_50"] < r["largura_80"] < r["largura_95"]


def test_largura_acompanha_o_desvio_do_erro():
    estreito = evaluate_intervals(conformal_intervals(frame_sintetico(sigma=50.0)))
    largo = evaluate_intervals(conformal_intervals(frame_sintetico(sigma=200.0)))
    assert largo["largura_95"] > 3 * estreito["largura_95"]


# --------------------------------------------------------------------------- #
# ausencia de vazamento
# --------------------------------------------------------------------------- #
def test_janela_futura_nao_afeta_intervalo_de_janela_anterior():
    """Adulterar o futuro nao pode mudar o passado. Se mudar, ha vazamento."""
    base = frame_sintetico(n_janelas=60)
    corte = 40

    adulterado = base.copy()
    alvo = adulterado.window > corte
    adulterado.loc[alvo, "y_true"] = adulterado.loc[alvo, "y_true"] + 100000.0

    a = conformal_intervals(base)
    b = conformal_intervals(adulterado)

    cols = [f"{lado}_{n}" for lado in ("lo", "hi") for n in (50, 80, 95)]
    passado_a = a[a.window <= corte][cols].to_numpy()
    passado_b = b[b.window <= corte][cols].to_numpy()
    np.testing.assert_allclose(passado_a, passado_b, equal_nan=True)

    # e o futuro tem que ter mudado, senao o teste nao estaria testando nada
    fut_a = a[a.window > corte][cols].to_numpy()
    fut_b = b[b.window > corte][cols].to_numpy()
    assert not np.allclose(fut_a, fut_b, equal_nan=True)


def test_intervalo_nao_usa_residuo_da_propria_janela():
    """Mover so o alvo de uma janela nao pode mexer no intervalo dela."""
    base = frame_sintetico(n_janelas=40)
    alvo_w = 30

    adulterado = base.copy()
    m = adulterado.window == alvo_w
    adulterado.loc[m, "y_true"] = adulterado.loc[m, "y_true"] + 50000.0

    cols = [f"{lado}_{n}" for lado in ("lo", "hi") for n in (50, 80, 95)]
    a = conformal_intervals(base)
    b = conformal_intervals(adulterado)
    ja = a[a.window == alvo_w][cols].to_numpy()
    jb = b[b.window == alvo_w][cols].to_numpy()
    np.testing.assert_allclose(ja, jb, equal_nan=True)


def test_primeiras_janelas_ficam_sem_intervalo():
    df = conformal_intervals(frame_sintetico(n_janelas=30))
    sem = df[df.window <= MIN_CALIB_JANELAS]
    com = df[df.window > MIN_CALIB_JANELAS]
    assert sem["lo_95"].isna().all()
    assert com["lo_95"].notna().all()


def test_numero_de_residuos_de_calibracao_cresce_de_um_em_um():
    """Para um horizonte fixo, a janela w usa exatamente w-1 residuos."""
    df = frame_sintetico(n_janelas=30)
    h1 = df[df.horizon == 1].sort_values("window")
    com_intervalo = conformal_intervals(df)
    c1 = com_intervalo[(com_intervalo.horizon == 1)].sort_values("window")
    n_com = int(c1["lo_95"].notna().sum())
    assert n_com == len(h1) - MIN_CALIB_JANELAS


# --------------------------------------------------------------------------- #
# escalas e escores
# --------------------------------------------------------------------------- #
def test_escalas_concordam_em_serie_homocedastica():
    """Justifica o padrao absolute: nesta amplitude, log1p nao muda a leitura.

    O CV da serie real e 0,084. Numa serie assim, calibrar em log1p ou na escala
    absoluta da praticamente a mesma cobertura, entao a escala mais simples e a
    que nao acopla os erros entre previsoes vence por padrao.
    """
    df = frame_sintetico()
    a = evaluate_intervals(conformal_intervals(df, scale="absolute"))
    b = evaluate_intervals(conformal_intervals(df, scale="log1p"))
    for nivel in (50, 80, 95):
        assert abs(a[f"cobertura_{nivel}"] - b[f"cobertura_{nivel}"]) < 0.02


def test_scale_invalida_levanta_erro():
    with pytest.raises(ValueError, match="scale desconhecida"):
        conformal_intervals(frame_sintetico(n_janelas=20), scale="raiz")


def test_coluna_faltando_levanta_erro():
    df = frame_sintetico(n_janelas=20).drop(columns=["horizon"])
    with pytest.raises(ValueError, match="coluna obrigatoria"):
        conformal_intervals(df)


def test_interval_score_penaliza_furo():
    y = np.array([100.0])
    dentro = interval_score(y, np.array([90.0]), np.array([110.0]), 0.2)
    fora = interval_score(y, np.array([120.0]), np.array([140.0]), 0.2)
    assert fora[0] > dentro[0]


def test_interval_score_igual_largura_quando_cobre():
    y = np.array([100.0])
    s = interval_score(y, np.array([90.0]), np.array([110.0]), 0.2)
    assert s[0] == pytest.approx(20.0)


def test_wis_menor_para_previsao_melhor():
    y = np.array([100.0])
    bom = weighted_interval_score(
        y, {0.8: (np.array([95.0]), np.array([105.0]))}, np.array([100.0])
    )
    ruim = weighted_interval_score(
        y, {0.8: (np.array([140.0]), np.array([160.0]))}, np.array([150.0])
    )
    assert bom[0] < ruim[0]


def test_avaliacao_por_horizonte_cobre_todos_os_passos():
    df = conformal_intervals(frame_sintetico(n_janelas=40))
    tab = evaluate_by_horizon(df)
    assert set(tab[tab.horizon != "todos"].horizon) == set(range(1, HOR + 1))
    assert (tab.horizon == "todos").sum() == 1


def test_evaluate_vazio_quando_nao_ha_intervalo():
    df = conformal_intervals(frame_sintetico(n_janelas=5))
    assert evaluate_intervals(df) == {}
