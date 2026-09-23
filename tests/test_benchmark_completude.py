"""O backtest precisa falhar na hora quando um modelo perde qualquer janela.

Antes destes testes, uma excecao numa janela virava aviso e o backtest seguia,
gravando metricas com menos previsoes que os outros modelos e terminando com
codigo zero. O run_uncertainty aborta depois nesse caso, entao nenhum numero
publicado corria risco, mas a falha ficava invisivel ate o passo seguinte.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent


def _carrega_run_benchmark():
    """scripts/ nao e pacote, entao o modulo entra pelo caminho do arquivo."""
    caminho = ROOT / "scripts" / "run_benchmark.py"
    spec = importlib.util.spec_from_file_location("run_benchmark", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rb = _carrega_run_benchmark()


def serie(n: int = 80) -> pd.Series:
    idx = pd.date_range("2010-01-01", periods=n, freq="MS")
    valores = 1000.0 + 10.0 * np.arange(n) + 50.0 * np.sin(np.arange(n) * np.pi / 6)
    return pd.Series(valores, index=idx)


class ModeloOk:
    name = "ok"
    supports_exog = False

    def forecast(self, train, horizon, exog_train=None, exog_future=None):
        return np.full(horizon, float(train.iloc[-1]))


class ModeloQuebraNaJanela:
    """Estoura excecao numa janela especifica, como um modelo real faria."""

    name = "quebra"
    supports_exog = False

    def __init__(self, janela_ruim: int):
        self.janela_ruim = janela_ruim
        self.chamadas = 0

    def forecast(self, train, horizon, exog_train=None, exog_future=None):
        self.chamadas += 1
        if self.chamadas == self.janela_ruim:
            raise RuntimeError("falha simulada de ajuste")
        return np.full(horizon, float(train.iloc[-1]))


class ModeloNaoFinito(ModeloOk):
    name = "nao_finito"

    def __init__(self, janela_ruim: int):
        self.janela_ruim = janela_ruim
        self.chamadas = 0

    def forecast(self, train, horizon, exog_train=None, exog_future=None):
        self.chamadas += 1
        if self.chamadas == self.janela_ruim:
            return np.full(horizon, np.nan)
        return np.full(horizon, float(train.iloc[-1]))


class ModeloTamanhoErrado(ModeloOk):
    name = "tamanho_errado"

    def forecast(self, train, horizon, exog_train=None, exog_future=None):
        return np.full(horizon - 1, float(train.iloc[-1]))


def roda(modelo, s=None, horizon=6, min_train_size=60):
    return rb.run_backtest(
        series=s if s is not None else serie(),
        model=modelo,
        horizon=horizon,
        min_train_size=min_train_size,
    )


def test_modelo_completo_devolve_todas_as_janelas():
    s = serie()
    n_esperado = len(s) - 60 - 6 + 1
    metric, preds = roda(ModeloOk(), s=s)
    assert metric["n_predictions"] == n_esperado * 6
    assert preds.window.nunique() == n_esperado


def test_excecao_em_uma_janela_interrompe_com_erro():
    with pytest.raises(rb.BacktestIncompleto) as e:
        roda(ModeloQuebraNaJanela(janela_ruim=3))
    msg = str(e.value)
    assert "Faltaram 1" in msg
    assert "janela 3" in msg
    assert "falha simulada" in msg


def test_previsao_nao_finita_interrompe_com_erro():
    with pytest.raises(rb.BacktestIncompleto) as e:
        roda(ModeloNaoFinito(janela_ruim=2))
    assert "nao-finita" in str(e.value)


def test_tamanho_errado_interrompe_com_erro():
    with pytest.raises(rb.BacktestIncompleto) as e:
        roda(ModeloTamanhoErrado())
    assert "tamanho" in str(e.value)


def test_serie_curta_demais_nao_passa_como_sucesso_vazio():
    with pytest.raises(rb.BacktestIncompleto) as e:
        roda(ModeloOk(), s=serie(40))
    assert "nenhuma janela" in str(e.value)


def test_mensagem_lista_no_maximo_cinco_janelas_e_conta_o_resto():
    class QuebraSempre(ModeloOk):
        name = "quebra_sempre"

        def forecast(self, train, horizon, exog_train=None, exog_future=None):
            raise RuntimeError("sempre falha")

    with pytest.raises(rb.BacktestIncompleto) as e:
        roda(QuebraSempre())
    msg = str(e.value)
    assert msg.count("janela ") == 5
    assert "e mais" in msg
