#!/usr/bin/env python3
"""Separa 'o agregado e mais previsivel' de 'o agregado tem menos ruido de contagem'.

O sMAPE do agregado C00-C97 e varias vezes menor que o de qualquer sitio isolado.
Ler isso como previsibilidade estrutural seria erro: contagem mensal maior tem
menos ruido relativo por construcao. Para contagem aproximadamente Poisson, o
desvio relativo escala com 1/sqrt(N), entao a razao esperada de sMAPE entre duas
series so pelo tamanho e sqrt(N_agregado / N_sitio).

Se a razao observada bater com a esperada, o agregado nao e mais previsivel, so e
maior. Se ficar acima, o sitio e genuinamente mais dificil, e ai sim ha estrutura
que o agregado esconde.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Escala de contagem vs previsibilidade")
    parser.add_argument("--series-dir", default="results/series")
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--prefix", default="serie_onco_SP")
    parser.add_argument("--periodo", default="2010-2019")
    parser.add_argument("--report-output", default="results/site_scale_analysis.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sd, rd = Path(args.series_dir), Path(args.results_dir)

    fontes = {
        "agregado": (
            sd / f"{args.prefix}_sim_real_{args.periodo}.csv",
            rd / "benchmark_onco_SP_2010_2019_full_metrics.csv",
        )
    }
    for s in ["pulmao", "colorretal", "mama", "prostata"]:
        fontes[s] = (
            sd / f"{args.prefix}_{s}_{args.periodo}.csv",
            rd / f"benchmark_onco_SP_{s}_2010_2019_metrics.csv",
        )

    base_n = pd.read_csv(fontes["agregado"][0]).value.mean()
    base_s = pd.read_csv(fontes["agregado"][1]).smape.min()

    linhas = []
    for nome, (p_serie, p_bench) in fontes.items():
        n = float(pd.read_csv(p_serie).value.mean())
        m = pd.read_csv(p_bench)
        melhor = m.loc[m.smape.idxmin()]
        razao_obs = float(melhor.smape) / base_s
        razao_poisson = float(np.sqrt(base_n / n))
        linhas.append(
            {
                "serie": nome,
                "media_mensal": round(n, 0),
                "melhor_modelo": melhor.model,
                "smape": round(float(melhor.smape), 3),
                "razao_observada": round(razao_obs, 2),
                "razao_esperada_poisson": round(razao_poisson, 2),
                "obs_sobre_poisson": round(razao_obs / razao_poisson, 2),
            }
        )

    res = pd.DataFrame(linhas)
    print("Razao de sMAPE contra o agregado, observada e esperada so pelo tamanho da contagem\n")
    print(res.to_string(index=False))

    sitios = res[res.serie != "agregado"]
    lo, hi = sitios.obs_sobre_poisson.min(), sitios.obs_sobre_poisson.max()
    print(f"\nobs/Poisson nos sitios: {lo} a {hi}")
    if hi <= 1.25 and lo >= 0.75:
        print(
            "Conclusao: a vantagem do agregado e explicada pelo ruido de contagem.\n"
            "Nao ha evidencia de que agregar torne a serie estruturalmente mais previsivel,\n"
            "nem de cancelamento de erro entre sitios."
        )
    else:
        print("Conclusao: ha desvio relevante do esperado por contagem; investigar sitio a sitio.")

    p = Path(args.report_output)
    p.write_text(json.dumps({"series": linhas}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nGravado: {p}")


if __name__ == "__main__":
    main()
