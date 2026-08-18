import numpy as np
import pandas as pd
import pytest

from onco_timeseries.models import LinearTrendForecaster, SeasonalNaiveForecaster


def serie(valores, inicio="2010-01-01"):
    idx = pd.date_range(inicio, periods=len(valores), freq="MS")
    return pd.Series(valores, index=idx, dtype=float)


def test_seasonal_naive_repete_o_mesmo_mes_do_ano_anterior():
    train = serie(list(range(1, 25)))  # 24 meses, 1..24
    pred = SeasonalNaiveForecaster().forecast(train, horizon=6)
    # Os ultimos 12 pontos sao 13..24; a previsao repete a partir de 13.
    np.testing.assert_allclose(pred, [13, 14, 15, 16, 17, 18])


def test_seasonal_naive_cicla_quando_o_horizonte_passa_de_um_ano():
    train = serie(list(range(1, 13)))
    pred = SeasonalNaiveForecaster().forecast(train, horizon=14)
    np.testing.assert_allclose(pred[:12], list(range(1, 13)))
    np.testing.assert_allclose(pred[12:], [1, 2])


def test_seasonal_naive_sem_ciclo_completo_usa_ultimo_valor():
    train = serie([10.0, 20.0, 30.0])
    pred = SeasonalNaiveForecaster().forecast(train, horizon=3)
    np.testing.assert_allclose(pred, [30.0, 30.0, 30.0])


def test_linear_trend_extrapola_reta_exata():
    train = serie([2.0 * i + 5.0 for i in range(24)])
    pred = LinearTrendForecaster().forecast(train, horizon=3)
    np.testing.assert_allclose(pred, [2.0 * 24 + 5.0, 2.0 * 25 + 5.0, 2.0 * 26 + 5.0])


def test_linear_trend_com_janela_ignora_o_passado_distante():
    # Patamar 100 por 12 meses, depois reta subindo 1 por mes por 12 meses.
    valores = [100.0] * 12 + [100.0 + i for i in range(1, 13)]
    train = serie(valores)
    pred = LinearTrendForecaster(window=12).forecast(train, horizon=1)
    # So a parte crescente entra: reta 101..112, proximo ponto 113.
    np.testing.assert_allclose(pred, [113.0])


def test_linear_trend_com_um_ponto_nao_quebra():
    train = serie([42.0])
    pred = LinearTrendForecaster().forecast(train, horizon=2)
    np.testing.assert_allclose(pred, [42.0, 42.0])


@pytest.mark.parametrize("modelo", [SeasonalNaiveForecaster(), LinearTrendForecaster()])
def test_baselines_nao_olham_o_futuro(modelo):
    train = serie(list(range(1, 37)))
    pred_curto = modelo.forecast(train, horizon=3)
    pred_longo = modelo.forecast(train, horizon=6)
    # As tres primeiras previsoes nao podem mudar por pedir mais horizonte.
    np.testing.assert_allclose(pred_curto, pred_longo[:3])
