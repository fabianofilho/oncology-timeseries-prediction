#!/usr/bin/env python3
"""Aplica o criterio pre-declarado do projeto sobre a saida de run_uncertainty.py.

A regra mora em src/onco_timeseries/criterion.py, com as duas versoes:

- v1 (LAB-118): IC95% do sMAPE exclui zero E Diebold-Mariano, sobre erro absoluto,
  abaixo de 0,05 em 3 ou mais dos 6 horizontes;
- v2 (LAB-135): a v1 mais o IC95% do MAE excluindo zero com o mesmo sinal. Quando as
  duas metricas discordam, o par e "discordante".

O campo `confirmado` segue a v2. A v1 fica em `confirmado_v1`, para reproduzir os
numeros publicados antes da LAB-135.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from onco_timeseries.criterion import (
    ALPHA,
    CONFIRMADO,
    DISCORDANTE,
    MIN_HORIZONS,
    Intervalo,
    veredito_v1,
    veredito_v2,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Veredito do criterio pre-declarado")
    parser.add_argument("--pairwise-csv", required=True)
    parser.add_argument("--report-output", default="")
    return parser.parse_args()


def _intervalo(row: pd.Series, par: str, metrica: str) -> Intervalo:
    iv = Intervalo(float(row["diff_point"]), float(row["ci_low"]), float(row["ci_high"]))
    # o CSV traz a flag calculada no run_uncertainty; as duas contas precisam bater
    if iv.exclui_zero == bool(row["ci_contains_zero"]):
        raise ValueError(f"IC incoerente com ci_contains_zero em {par} ({metrica})")
    return iv


def main() -> None:
    args = parse_args()
    df = pd.read_csv(args.pairwise_csv)

    boot = df[df.test == "bootstrap_pareado"]
    smape = boot[boot.metric == "smape"].set_index("pair")
    mae = boot[boot.metric == "mae"].set_index("pair")
    dm = df[df.test == "diebold_mariano_harvey"]
    if set(smape.index) != set(mae.index):
        raise ValueError("pares de sMAPE e MAE nao coincidem no pairwise CSV")

    linhas = []
    for par in smape.index:
        s_iv = _intervalo(smape.loc[par], par, "smape")
        m_iv = _intervalo(mae.loc[par], par, "mae")
        dm_par = dm[dm.pair == par]
        n_sig = int((dm_par.p_value < ALPHA).sum())
        v2 = veredito_v2(s_iv, m_iv, n_sig)
        linhas.append(
            {
                "par": par,
                "diferenca": round(s_iv.diff, 3),
                "ic95": f"[{s_iv.low:.3f}, {s_iv.high:.3f}]",
                "ic_exclui_zero": s_iv.exclui_zero,
                "diferenca_mae": round(m_iv.diff, 3),
                "ic95_mae": f"[{m_iv.low:.3f}, {m_iv.high:.3f}]",
                "ic_mae_exclui_zero": m_iv.exclui_zero,
                "dm_abaixo_alpha": f"{n_sig}/{len(dm_par)}",
                "veredito": v2,
                "confirmado": v2 == CONFIRMADO,
                "confirmado_v1": veredito_v1(s_iv, n_sig),
            }
        )

    out = pd.DataFrame(linhas)
    print(f"Criterio v2 (LAB-135): IC95% de sMAPE e de MAE excluem zero, mesmo sinal, "
          f"E DM < {ALPHA} em >= {MIN_HORIZONS} de 6 horizontes\n")
    print(out[["par", "ic95", "ic95_mae", "dm_abaixo_alpha", "veredito", "confirmado_v1"]]
          .to_string(index=False))

    n_v2 = int(out.confirmado.sum())
    n_v1 = int(out.confirmado_v1.sum())
    disc = out[out.veredito == DISCORDANTE]
    print(f"\nConfirmados v2: {n_v2} de {len(out)}  |  v1: {n_v1} de {len(out)}  |  "
          f"discordantes: {len(disc)}")
    mudou = out[out.confirmado != out.confirmado_v1]
    for _, r in mudou.iterrows():
        print(f"  MUDOU de v1 para v2: {r['par']} -> {r['veredito']}")

    if args.report_output:
        p = Path(args.report_output)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(
                {
                    "criterio": {
                        "versao": 2,
                        "alpha": ALPHA,
                        "min_horizontes": MIN_HORIZONS,
                        "metricas_bootstrap": ["smape", "mae"],
                        "perda_dm": "erro absoluto",
                        "decisao": "LAB-135, registrada em 2026-09-28 antes de ser aplicada",
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
