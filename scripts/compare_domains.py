#!/usr/bin/env python3
"""Compara previsibilidade entre os tres dominios da linha, sob protocolo identico.

Nao compara numeros ja publicados por cada projeto: reroda as tres series pelo
mesmo codigo, mesma janela de datas, mesmo horizonte, mesmo min_train, mesmos
modelos e mesma semente de bootstrap. Numero produzido por protocolo diferente
nao entra.

Alem do sMAPE bruto, reporta a razao contra o ingenuo sazonal do proprio dominio.
O sMAPE bruto mede o quanto o dominio e dificil; a razao mede o quanto modelar
adianta ali, e so a segunda e comparavel entre dominios com amplitude diferente.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

DOMINIOS = {
    "cancer": {
        "rotulo": "OPT cancer (obitos CID C, SIM)",
        "path": "results/series/serie_onco_SP_sim_real_2010-2023.csv",
    },
    "cardiovascular": {
        "rotulo": "CPT cardiovascular (obitos CID I, SIM)",
        "path": "../cardiovascular-timeseries-prediction/results/series/serie_eventos_sp_sim_real_2010_2023.csv",
    },
    "dengue": {
        "rotulo": "DFP dengue (casos notificados, InfoDengue)",
        "path": "../dengue-time-series/data/processed/dengue_monthly_sao.csv",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Comparacao entre dominios")
    parser.add_argument("--start", default="2010-02-01")
    parser.add_argument("--end", default="2019-12-01")
    parser.add_argument("--output-dir", default="results/series")
    parser.add_argument("--report-output", default="results/domain_comparison_inputs.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    esperado = pd.date_range(args.start, args.end, freq="MS")
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    linhas = []
    for chave, spec in DOMINIOS.items():
        origem = Path(spec["path"])
        if not origem.exists():
            raise FileNotFoundError(f"Serie ausente para {chave}: {origem}")

        d = pd.read_csv(origem, parse_dates=["date"]).sort_values("date")
        j = d[(d.date >= args.start) & (d.date <= args.end)][["date", "value"]]

        faltando = sorted(set(esperado) - set(j.date))
        if faltando:
            raise ValueError(f"{chave} tem {len(faltando)} meses faltando na janela comum")

        destino = out_dir / f"comp_{chave}_{args.start[:4]}_{args.end[:4]}.csv"
        j.to_csv(destino, index=False)

        v = j.value
        linhas.append(
            {
                "dominio": chave,
                "rotulo": spec["rotulo"],
                "origem": str(origem).replace("\\", "/"),
                "arquivo": str(destino).replace("\\", "/"),
                "pontos": int(len(j)),
                "media": round(float(v.mean()), 1),
                "minimo": int(v.min()),
                "maximo": int(v.max()),
                "amplitude_max_sobre_min": round(float(v.max() / v.min()), 1),
                "cv": round(float(v.std() / v.mean()), 3),
            }
        )

    res = pd.DataFrame(linhas)
    print(f"Janela comum: {args.start} a {args.end}, {len(esperado)} meses, sem buraco em nenhuma serie.\n")
    print(
        res[["dominio", "pontos", "media", "minimo", "maximo", "amplitude_max_sobre_min", "cv"]].to_string(
            index=False
        )
    )

    p = Path(args.report_output)
    p.write_text(
        json.dumps({"start": args.start, "end": args.end, "dominios": linhas}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nGravado: {p}")
    for r in linhas:
        print(f"  {r['arquivo']}")


if __name__ == "__main__":
    main()
