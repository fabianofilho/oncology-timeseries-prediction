"""Intervalos de predicao conformais para o backtest de origem rolante.

Portado de dengue-time-series/src/dengue_forecast/intervals.py, com as mudancas
que esta serie exige. A ideia e a mesma: a previsao pontual de cada modelo ja
existe, e o intervalo sai da distribuicao empirica dos erros que aquele modelo
cometeu, no mesmo passo de horizonte, em janelas ANTERIORES a que esta sendo
prevista. Nenhum residuo da propria janela nem de janela futura entra na
calibracao, pelo mesmo motivo que o backtest nao treina em dado futuro.

O que muda em relacao ao dengue, e por que:

1. Horizonte 6 em vez de 12, seguindo o protocolo deste projeto.

2. Escala absoluta como padrao, em vez de log1p. No dengue a contagem varia
   quatro ordens de grandeza entre vale e pico, o residuo aditivo e fortemente
   heterocedastico e o log1p resolve isso. Aqui o coeficiente de variacao da
   serie mensal e 0,084 e a razao entre maximo e minimo e 1,4, entao o residuo
   aditivo ja e aproximadamente homocedastico e a transformacao nao compra nada.
   Pior: log1p acopla os erros, porque um residuo grande infla o quantil de
   todas as previsoes daquele horizonte. A escala log1p continua disponivel em
   scale="log1p" para sensibilidade, e o teste test_escalas_concordam_em_serie_
   homocedastica documenta que nesta escala de variacao as duas concordam.

3. MIN_CALIB_JANELAS = 12 em vez de 20. O dengue tem muito mais folds; aqui sao
   55 janelas por modelo. Exigir 20 deixaria 35 janelas avaliaveis por horizonte;
   exigir 12 deixa 43. O numero esta declarado aqui, antes de rodar, e nao foi
   escolhido olhando a cobertura resultante.

A cobertura e medida, nao assumida: ver evaluate_intervals().
"""
from __future__ import annotations

import numpy as np
import pandas as pd

HORIZON = 6
MIN_CALIB_JANELAS = 12
NIVEIS = (0.50, 0.80, 0.95)


def _conformal_quantile(residuos: np.ndarray, level: float) -> float:
    """Quantil conformal de amostra finita.

    level e a probabilidade acumulada desejada. Para n residuos, usa o k-esimo
    menor com k = ceil((n+1)*level), limitado a n. Sem a correcao de amostra
    finita a cobertura fica sistematicamente abaixo do nominal com n pequeno.
    """
    n = residuos.size
    if n == 0:
        return float("nan")
    k = int(np.ceil((n + 1) * level))
    if k < 1:
        return float(np.min(residuos))
    if k > n:
        return float(np.max(residuos))
    return float(np.partition(residuos, k - 1)[k - 1])


def conformal_intervals(
    df: pd.DataFrame,
    levels: tuple[float, ...] = NIVEIS,
    min_calib_janelas: int = MIN_CALIB_JANELAS,
    scale: str = "absolute",
    horizon: int = HORIZON,
) -> pd.DataFrame:
    """Anexa limites inferior e superior por nivel nominal.

    Espera as colunas model, window, horizon, y_true e y_pred, que sao as que o
    run_benchmark.py ja grava. Linhas sem janelas anteriores suficientes recebem
    NaN nos limites e ficam fora da avaliacao de cobertura.
    """
    if scale not in ("absolute", "log1p"):
        raise ValueError(f"scale desconhecida: {scale}")
    for col in ("model", "window", "horizon", "y_true", "y_pred"):
        if col not in df.columns:
            raise ValueError(f"coluna obrigatoria ausente: {col}")

    df = df.copy().reset_index(drop=True)
    for lv in levels:
        df[f"lo_{int(lv * 100)}"] = np.nan
        df[f"hi_{int(lv * 100)}"] = np.nan

    y_true = df["y_true"].to_numpy(dtype=float)
    y_pred = df["y_pred"].to_numpy(dtype=float)
    if scale == "log1p":
        df["_res"] = np.log1p(y_true) - np.log1p(y_pred)
        df["_ancora"] = np.log1p(y_pred)
        volta = np.expm1
    else:
        df["_res"] = y_true - y_pred
        df["_ancora"] = y_pred

        def volta(v):
            return v

    for _, sub in df.groupby("model", sort=False):
        for h in range(1, horizon + 1):
            m = sub[sub["horizon"] == h].sort_values("window")
            idx = m.index.to_numpy()
            res = m["_res"].to_numpy()
            ancora = m["_ancora"].to_numpy()

            for pos in range(len(idx)):
                if pos < min_calib_janelas:
                    continue
                calib = res[:pos]  # so janelas estritamente anteriores
                for lv in levels:
                    a = 1.0 - lv
                    q_lo = _conformal_quantile(calib, a / 2)
                    q_hi = _conformal_quantile(calib, 1 - a / 2)
                    p = int(lv * 100)
                    df.at[idx[pos], f"lo_{p}"] = max(0.0, volta(ancora[pos] + q_lo))
                    df.at[idx[pos], f"hi_{p}"] = max(0.0, volta(ancora[pos] + q_hi))

    return df.drop(columns=["_res", "_ancora"])


def interval_score(y: np.ndarray, lo: np.ndarray, hi: np.ndarray, alpha: float) -> np.ndarray:
    """Interval score de Gneiting e Raftery: largura mais penalidade por furo."""
    return (
        (hi - lo)
        + (2.0 / alpha) * np.clip(lo - y, 0, None)
        + (2.0 / alpha) * np.clip(y - hi, 0, None)
    )


def weighted_interval_score(
    y: np.ndarray, bounds: dict[float, tuple[np.ndarray, np.ndarray]], mediana: np.ndarray
) -> np.ndarray:
    """WIS de Bracher et al., o escore padrao dos forecast hubs epidemiologicos.

    Combina calibracao e nitidez num unico numero na escala do desfecho. Menor e
    melhor. bounds mapeia nivel nominal para (lo, hi).
    """
    k = len(bounds)
    total = 0.5 * np.abs(y - mediana)
    for lv, (lo, hi) in bounds.items():
        alpha = 1.0 - lv
        total = total + (alpha / 2.0) * interval_score(y, lo, hi, alpha)
    return total / (k + 0.5)


def evaluate_intervals(df: pd.DataFrame, levels: tuple[float, ...] = NIVEIS) -> dict:
    """Cobertura empirica, nitidez e WIS sobre as linhas que tem intervalo."""
    cols = [f"lo_{int(lv * 100)}" for lv in levels]
    ev = df.dropna(subset=cols).copy()
    if ev.empty:
        return {}

    y = ev["y_true"].to_numpy(dtype=float)
    out: dict = {"n_avaliado": int(len(ev))}
    bounds = {}
    for lv in levels:
        p = int(lv * 100)
        lo = ev[f"lo_{p}"].to_numpy(dtype=float)
        hi = ev[f"hi_{p}"].to_numpy(dtype=float)
        bounds[lv] = (lo, hi)
        out[f"cobertura_{p}"] = float(np.mean((y >= lo) & (y <= hi)))
        out[f"largura_{p}"] = float(np.mean(hi - lo))
        out[f"largura_mediana_{p}"] = float(np.median(hi - lo))
    out["WIS"] = float(
        np.mean(weighted_interval_score(y, bounds, ev["y_pred"].to_numpy(dtype=float)))
    )
    return out


def evaluate_by_horizon(
    df: pd.DataFrame, levels: tuple[float, ...] = NIVEIS, horizon: int = HORIZON
) -> pd.DataFrame:
    """Mesma avaliacao, quebrada por modelo e por passo de horizonte."""
    linhas = []
    for modelo, sub in df.groupby("model", sort=False):
        for h in range(1, horizon + 1):
            r = evaluate_intervals(sub[sub["horizon"] == h], levels)
            if r:
                linhas.append({"model": modelo, "horizon": h, **r})
        r_tot = evaluate_intervals(sub, levels)
        if r_tot:
            linhas.append({"model": modelo, "horizon": "todos", **r_tot})
    return pd.DataFrame(linhas)
