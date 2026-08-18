#!/usr/bin/env python3
"""Teste de mudanca de regime: treina ate o fim de 2019 e preve o periodo pandemico.

O backtesting por rolling origin do run_benchmark.py mede desempenho dentro de um
regime estavel. Este script mede outra coisa: quanto cada modelo erra quando o
regime muda debaixo dele. Origem unica, sem reestimacao, treino congelado em
dezembro de 2019.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from onco_timeseries.data import load_and_aggregate_series
from onco_timeseries.evaluate import mae, rmse, smape
from onco_timeseries.models import (
    CatBoostForecaster,
    LinearTrendForecaster,
    ProphetForecaster,
    SarimaForecaster,
    SeasonalNaiveForecaster,
    TimesFMForecaster,
    XGBoostForecaster,
)

MODELOS = {
    "seasonal_naive": SeasonalNaiveForecaster,
    "linear_trend": LinearTrendForecaster,
    "sarima": SarimaForecaster,
    "prophet": ProphetForecaster,
    "timesfm": TimesFMForecaster,
    "xgboost": XGBoostForecaster,
    "catboost": CatBoostForecaster,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Teste de mudanca de regime")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--train-end", default="2019-12-01")
    parser.add_argument("--models", default="seasonal_naive,linear_trend,sarima,prophet,timesfm,xgboost,catboost")
    parser.add_argument("--output-prefix", default="results/regime_test")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    serie = load_and_aggregate_series(args.input_csv, "date", "value", "MS")

    corte = pd.Timestamp(args.train_end)
    train = serie[serie.index <= corte]
    teste = serie[serie.index > corte]
    horizonte = len(teste)

    print(f"Treino: {train.index[0].date()} a {train.index[-1].date()} ({len(train)} meses)")
    print(f"Teste:  {teste.index[0].date()} a {teste.index[-1].date()} ({horizonte} meses)")
    print("Origem unica, sem reestimacao.\n")

    nomes = [m.strip() for m in args.models.split(",") if m.strip()]
    linhas = []
    preds = []

    for nome in nomes:
        try:
            modelo = MODELOS[nome]()
            y_pred = np.asarray(modelo.forecast(train, horizon=horizonte), dtype=float)
        except Exception as exc:
            print(f"[WARN] {nome} falhou: {exc}")
            continue

        y_true = teste.to_numpy(dtype=float)
        for dt, yt, yp in zip(teste.index, y_true, y_pred):
            preds.append({"model": nome, "date": dt, "y_true": yt, "y_pred": yp})

        linha = {"model": nome, "horizonte_total": horizonte}
        for rotulo, fatia in [
            ("total", slice(None)),
            ("2020", slice(0, 12)),
            ("2021", slice(12, 24)),
            ("2022", slice(24, 36)),
            ("2023", slice(36, 48)),
            ("primeiros_6m", slice(0, 6)),
        ]:
            yt, yp = y_true[fatia], y_pred[fatia]
            if len(yt) == 0:
                continue
            linha[f"smape_{rotulo}"] = smape(yt, yp)
            linha[f"vies_{rotulo}"] = float(np.mean(yp - yt))
        linha["mae_total"] = mae(y_true, y_pred)
        linha["rmse_total"] = rmse(y_true, y_pred)
        linhas.append(linha)

    res = pd.DataFrame(linhas).sort_values("smape_total")

    cols_smape = [c for c in res.columns if c.startswith("smape_")]
    print("sMAPE por periodo\n")
    print(res[["model"] + cols_smape].to_string(index=False, float_format=lambda v: f"{v:6.2f}"))

    cols_vies = [c for c in res.columns if c.startswith("vies_")]
    print("\nVies medio (previsto menos observado, em obitos/mes)\n")
    print(res[["model"] + cols_vies].to_string(index=False, float_format=lambda v: f"{v:7.0f}"))

    res.to_csv(f"{args.output_prefix}_metrics.csv", index=False)
    pd.DataFrame(preds).to_csv(f"{args.output_prefix}_predictions.csv", index=False)
    print(f"\nGravado: {args.output_prefix}_metrics.csv")
    print(f"Gravado: {args.output_prefix}_predictions.csv")


if __name__ == "__main__":
    main()
