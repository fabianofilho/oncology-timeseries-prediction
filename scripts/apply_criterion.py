#!/usr/bin/env python3
"""Aplica o criterio pre-declarado do projeto sobre a saida de run_uncertainty.py.

Criterio (fixado antes de qualquer numero existir, ver LAB-118 no Linear):
uma melhoria so conta como confirmada se o IC95% da diferenca exclui zero E o
Diebold-Mariano fica abaixo de 0,05 em 3 ou mais dos 6 horizontes.

As duas condicoes existem porque medem coisas diferentes. O bootstrap agregado
pergunta se a diferenca media e distinguivel de zero; o DM por horizonte pergunta
se ela se sustenta ao longo do horizonte ou vem de um ponto so.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ALPHA = 0.05
MIN_HORIZONS = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Veredito do criterio pre-declarado")
    parser.add_argument("--pairwise-csv", required=True)
    parser.add_argument("--metric", default="smape", help="Metrica do bootstrap agregado")
    parser.add_argument("--report-output", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = pd.read_csv(args.pairwise_csv)

    boot = df[(df.test == "bootstrap_pareado") & (df.metric == args.metric)]
    dm = df[df.test == "diebold_mariano_harvey"]

    linhas = []
    for _, row in boot.iterrows():
        par = row["pair"]
        dm_par = dm[dm.pair == par]
        n_sig = int((dm_par.p_value < ALPHA).sum())
        n_h = int(len(dm_par))
        ci_exclui_zero = not bool(row["ci_contains_zero"])
        confirmado = ci_exclui_zero and n_sig >= MIN_HORIZONS

        linhas.append(
            {
                "par": par,
                "diferenca": round(float(row["diff_point"]), 3),
                "ic95": f"[{row['ci_low']:.3f}, {row['ci_high']:.3f}]",
                "ic_exclui_zero": ci_exclui_zero,
                "dm_abaixo_alpha": f"{n_sig}/{n_h}",
                "confirmado": confirmado,
            }
        )

    out = pd.DataFrame(linhas)
    print(f"Criterio: IC95% exclui zero E DM < {ALPHA} em >= {MIN_HORIZONS} de 6 horizontes")
    print(f"Metrica do bootstrap: {args.metric}\n")
    print(out.to_string(index=False))

    n_conf = int(out.confirmado.sum())
    print(f"\nPares confirmados: {n_conf} de {len(out)}")
    if n_conf < len(out):
        print("Pares NAO confirmados (a diferenca observada nao se sustenta):")
        for _, r in out[~out.confirmado].iterrows():
            print(f"  - {r['par']}: DM abaixo de {ALPHA} em apenas {r['dm_abaixo_alpha']}")

    if args.report_output:
        p = Path(args.report_output)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(
                {
                    "criterio": {
                        "alpha": ALPHA,
                        "min_horizontes": MIN_HORIZONS,
                        "metrica_bootstrap": args.metric,
                    },
                    "pares": linhas,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"\nGravado: {p}")


if __name__ == "__main__":
    main()
