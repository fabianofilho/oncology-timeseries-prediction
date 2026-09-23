#!/usr/bin/env python3
"""Intervalos de predicao conformais sobre o backtest ja rodado.

Nao treina nada e nao altera previsao pontual nenhuma: le as previsoes que o
run_benchmark.py gravou e anexa limites calibrados so com residuos de janelas
anteriores.

Duas avaliacoes, que respondem perguntas diferentes:

  dentro do regime   as 55 janelas de 2010-2019. Mede se o intervalo esta
                     calibrado quando o mundo se comporta como no treino.

  fora do regime     os primeiros 6 meses de 2020, previstos com treino
                     congelado em dez/2019 e intervalo calibrado com TODOS os
                     residuos de 2010-2019. Responde se o intervalo avisa quando
                     o regime muda. Se a cobertura desabar, ele nao avisa.

Só os 6 primeiros meses entram na segunda avaliacao porque a calibracao existe
para os horizontes 1 a 6. Estender para 48 meses exigiria extrapolar o quantil
para horizontes nunca calibrados, o que seria inventar incerteza.

Uso:
    python scripts/run_intervals.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from onco_timeseries.intervals import (
    MIN_CALIB_JANELAS,
    NIVEIS,
    _conformal_quantile,
    conformal_intervals,
    evaluate_by_horizon,
    evaluate_intervals,
    weighted_interval_score,
)

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
HORIZON = 6


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Intervalos conformais do backtest")
    p.add_argument(
        "--predictions-csv",
        default="results/benchmark_onco_SP_2010_2019_full_predictions.csv",
    )
    p.add_argument(
        "--regime-csv", default="results/regime_test_2020_2023_full_predictions.csv"
    )
    p.add_argument("--scale", default="absolute", choices=["absolute", "log1p"])
    p.add_argument("--output-prefix", default="results/intervals_2010_2019")
    return p.parse_args()


def intervalos_fora_do_regime(
    dentro: pd.DataFrame, regime: pd.DataFrame, scale: str
) -> pd.DataFrame:
    """Calibra com todo o periodo estavel e aplica aos 6 primeiros meses de 2020.

    A calibracao usa os residuos do horizonte correspondente, entao o mes 1 de
    2020 e comparado contra a distribuicao de erro de h=1, e assim por diante.
    """
    reg = regime.sort_values(["model", "date"]).copy()
    reg["horizon"] = reg.groupby("model").cumcount() + 1
    reg = reg[reg.horizon <= HORIZON].copy()

    for lv in NIVEIS:
        reg[f"lo_{int(lv * 100)}"] = np.nan
        reg[f"hi_{int(lv * 100)}"] = np.nan

    for modelo, sub in reg.groupby("model", sort=False):
        calib_modelo = dentro[dentro.model == modelo]
        for h in range(1, HORIZON + 1):
            res = (
                calib_modelo[calib_modelo.horizon == h]
                .pipe(lambda d: d.y_true - d.y_pred)
                .to_numpy(dtype=float)
            )
            if res.size == 0:
                continue
            linha = sub[sub.horizon == h]
            if linha.empty:
                continue
            i = linha.index[0]
            ancora = float(reg.at[i, "y_pred"])
            for lv in NIVEIS:
                a = 1.0 - lv
                p = int(lv * 100)
                reg.at[i, f"lo_{p}"] = max(
                    0.0, ancora + _conformal_quantile(res, a / 2)
                )
                reg.at[i, f"hi_{p}"] = max(
                    0.0, ancora + _conformal_quantile(res, 1 - a / 2)
                )
    return reg


def tabela_resumo(tab: pd.DataFrame) -> pd.DataFrame:
    t = tab[tab.horizon == "todos"].copy()
    cols = ["model", "n_avaliado", "cobertura_50", "cobertura_80", "cobertura_95",
            "largura_50", "largura_80", "largura_95", "WIS"]
    return t[cols].sort_values("WIS").reset_index(drop=True)


def main() -> None:
    args = parse_args()
    dentro = pd.read_csv(ROOT / args.predictions_csv, parse_dates=["date"])

    com_int = conformal_intervals(dentro, scale=args.scale)
    por_h = evaluate_by_horizon(com_int)
    resumo = tabela_resumo(por_h)

    print(f"Calibracao: so janelas anteriores, minimo de {MIN_CALIB_JANELAS}, "
          f"escala {args.scale}.")
    print(f"Avaliadas {int(resumo.n_avaliado.iloc[0])} previsoes por modelo, "
          f"de {len(dentro) // dentro.model.nunique()}.\n")

    print("DENTRO DO REGIME (2010-2019), cobertura empirica e largura media\n")
    print(
        resumo.to_string(
            index=False,
            float_format=lambda v: f"{v:8.3f}",
            columns=["model", "cobertura_50", "cobertura_80", "cobertura_95",
                     "largura_50", "largura_80", "largura_95", "WIS"],
        )
    )
    print("\nNominal: 0,500 / 0,800 / 0,950. Largura e WIS em obitos por mes.")

    p_int = ROOT / f"{args.output_prefix}_predictions.csv"
    p_h = ROOT / f"{args.output_prefix}_by_horizon.csv"
    p_res = ROOT / f"{args.output_prefix}_summary.csv"
    com_int.to_csv(p_int, index=False)
    por_h.to_csv(p_h, index=False)
    resumo.to_csv(p_res, index=False)

    saida: dict = {
        "escala": args.scale,
        "min_calib_janelas": MIN_CALIB_JANELAS,
        "niveis": list(NIVEIS),
        "dentro_do_regime": resumo.to_dict(orient="records"),
    }

    # fora do regime
    p_regime = ROOT / args.regime_csv
    if p_regime.exists() and args.scale == "absolute":
        regime = pd.read_csv(p_regime, parse_dates=["date"])
        reg_int = intervalos_fora_do_regime(dentro, regime, args.scale)
        linhas = []
        for modelo, sub in reg_int.groupby("model", sort=False):
            r = evaluate_intervals(sub)
            if r:
                linhas.append({"model": modelo, **r})
        fora = pd.DataFrame(linhas).sort_values("WIS").reset_index(drop=True)

        print("\n\nFORA DO REGIME (primeiros 6 meses de 2020), mesmo intervalo\n")
        print(
            fora.to_string(
                index=False,
                float_format=lambda v: f"{v:8.3f}",
                columns=["model", "cobertura_50", "cobertura_80", "cobertura_95", "WIS"],
            )
        )
        cob95 = fora.cobertura_95.mean()
        print(
            f"\nCobertura media a 95% fora do regime: {cob95:.3f}, contra "
            f"{resumo.cobertura_95.mean():.3f} dentro."
        )
        print(
            "Leitura: o intervalo "
            + ("AVISA" if cob95 >= 0.80 else "NAO AVISA")
            + " a mudanca de regime, no sentido de "
            + ("continuar cobrindo o observado." if cob95 >= 0.80
               else "o observado cair fora do intervalo com frequencia muito maior que o nominal.")
        )
        reg_int.to_csv(ROOT / f"{args.output_prefix}_regime_predictions.csv", index=False)
        saida["fora_do_regime"] = fora.to_dict(orient="records")
        saida["cobertura_95_media"] = {
            "dentro": float(resumo.cobertura_95.mean()),
            "fora": float(cob95),
        }

    p_json = ROOT / f"{args.output_prefix}_report.json"
    p_json.write_text(json.dumps(saida, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nGravado: {p_res}")
    print(f"Gravado: {p_h}")
    print(f"Gravado: {p_json}")


if __name__ == "__main__":
    main()
