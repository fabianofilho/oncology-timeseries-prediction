#!/usr/bin/env python3
"""Constroi series mensais por sitio tumoral a partir do microdado ja extraido.

A condicao de parada da LAB-119 e verificada aqui, antes de qualquer modelagem:
sitio com media mensal abaixo do minimo nao gera serie, porque a variancia de
contagem baixa domina o sMAPE e a comparacao entre modelos vira ruido.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

# Sitios de maior volume. As faixas seguem a CID-10 e a definicao esta em
# docs/cid10_neoplasias_sim.md.
SITIOS = {
    "pulmao": {"rotulo": "Traqueia, bronquios e pulmao", "cid": ["C33", "C34"]},
    "colorretal": {"rotulo": "Colorretal", "cid": ["C18", "C19", "C20", "C21"]},
    "mama": {"rotulo": "Mama", "cid": ["C50"]},
    "prostata": {"rotulo": "Prostata", "cid": ["C61"]},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Series mensais por sitio tumoral")
    parser.add_argument("--raw-csv", required=True)
    parser.add_argument("--output-dir", default="results/series")
    parser.add_argument("--prefix", default="serie_onco_SP")
    parser.add_argument(
        "--min-media-mensal",
        type=float,
        default=30.0,
        help="Media mensal minima para o sitio entrar (condicao de parada da LAB-119)",
    )
    parser.add_argument("--report-output", default="results/site_series_report.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    raw = pd.read_csv(args.raw_csv, dtype={"CAUSABAS": str, "DTOBITO": str}, low_memory=False)
    cid = raw["CAUSABAS"].astype(str).str.upper().str.strip()
    data = pd.to_datetime(raw["DTOBITO"].astype(str).str.strip(), format="%d%m%Y", errors="coerce")

    n_sem_data = int(data.isna().sum())
    if n_sem_data:
        print(f"[WARN] {n_sem_data} registros sem data valida, descartados")
    ok = data.notna()
    cid, data = cid[ok], data[ok]

    mes = data.dt.to_period("M").dt.to_timestamp()
    prefixo3 = cid.str[:3]

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    linhas = []
    for chave, spec in SITIOS.items():
        mask = prefixo3.isin(spec["cid"])
        n = int(mask.sum())
        serie = (
            pd.DataFrame({"date": mes[mask]})
            .groupby("date")
            .size()
            .rename("value")
            .reset_index()
            .sort_values("date")
        )
        media = float(serie.value.mean()) if len(serie) else 0.0
        entra = media >= args.min_media_mensal

        registro = {
            "sitio": chave,
            "rotulo": spec["rotulo"],
            "cid": spec["cid"],
            "obitos": n,
            "pontos": int(len(serie)),
            "media_mensal": round(media, 1),
            "minimo_mensal": int(serie.value.min()) if len(serie) else 0,
            "maximo_mensal": int(serie.value.max()) if len(serie) else 0,
            "incluido": entra,
        }

        if entra:
            caminho = out_dir / f"{args.prefix}_{chave}_2010-2023.csv"
            serie.to_csv(caminho, index=False)
            registro["arquivo"] = str(caminho).replace("\\", "/")

            pre = serie[serie.date < "2020-01-01"]
            caminho_pre = out_dir / f"{args.prefix}_{chave}_2010-2019.csv"
            pre.to_csv(caminho_pre, index=False)
            registro["arquivo_pre"] = str(caminho_pre).replace("\\", "/")
            registro["pontos_pre"] = int(len(pre))
        linhas.append(registro)

    res = pd.DataFrame(linhas)
    print(
        res[
            ["sitio", "obitos", "pontos", "media_mensal", "minimo_mensal", "maximo_mensal", "incluido"]
        ].to_string(index=False)
    )

    excluidos = res[~res.incluido]
    if len(excluidos):
        print(f"\nExcluidos por media mensal abaixo de {args.min_media_mensal}:")
        for _, r in excluidos.iterrows():
            print(f"  - {r['sitio']}: media {r['media_mensal']}")
    else:
        print(f"\nNenhum sitio excluido pelo criterio de media mensal >= {args.min_media_mensal}.")

    p = Path(args.report_output)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            {"min_media_mensal": args.min_media_mensal, "sitios": linhas}, indent=2, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    print(f"\nGravado: {p}")


if __name__ == "__main__":
    main()
