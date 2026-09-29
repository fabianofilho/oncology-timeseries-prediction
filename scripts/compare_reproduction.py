#!/usr/bin/env python3
"""Compara uma reproducao do benchmark agregado com os resultados publicados.

A reproducao em results/reproducao/*_mac10_* foi gerada em 2026-09-29 num Apple M4
(arm64, 10 nucleos logicos), Python 3.13, xgboost 3.4.1, com:

    python scripts/run_benchmark.py \\
        --input-csv results/series/serie_onco_SP_sim_real_2010-2019.csv \\
        --horizon 6 --min-train-size 60 \\
        --models seasonal_naive,linear_trend,sarima,prophet,timesfm,xgboost,catboost \\
        --output-prefix results/reproducao/benchmark_mac10 --processo-por-modelo
    python scripts/run_uncertainty.py --predictions-csv results/reproducao/benchmark_mac10_predictions.csv \\
        --models (os mesmos sete) --n-boot 10000 --seed 20260818 \\
        --output-prefix results/reproducao/uncertainty_mac10
    python scripts/apply_criterion.py \\
        --pairwise-csv results/reproducao/uncertainty_mac10_pairwise_tests.csv \\
        --report-output results/reproducao/criterion_verdict_mac10.json

O que este script mede: diferenca de sMAPE e de previsao por modelo, e todo par cujo
veredito muda. O resultado vai para results/reproducao_benchmark.json, que o
manuscrito le. Ver docs/xgboost_reprodutibilidade.md.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compara reproducao com o publicado")
    p.add_argument("--rotulo", default="mac10")
    p.add_argument("--maquina", default="Apple M4, arm64, 10 nucleos logicos")
    p.add_argument("--output", default="results/reproducao_benchmark.json")
    return p.parse_args()


def pares(caminho: Path) -> dict:
    out = {}
    for p in json.loads(caminho.read_text(encoding="utf-8"))["pares"]:
        out[frozenset(p["par"].split("_menos_"))] = p
    return out


def dm_por_horizonte(caminho: Path, a: str, b: str) -> list[float]:
    d = pd.read_csv(caminho)
    d = d[(d.test == "diebold_mariano_harvey")
          & d.pair.isin([f"{a}_menos_{b}", f"{b}_menos_{a}"])].sort_values("horizon")
    return [round(float(x), 4) for x in d.p_value]


def main() -> None:
    args = parse_args()
    rd = R / "reproducao"
    pub_m = pd.read_csv(R / "benchmark_onco_SP_2010_2019_full_metrics.csv").set_index("model")
    rep_m = pd.read_csv(rd / f"benchmark_{args.rotulo}_metrics.csv").set_index("model")
    pub_p = pd.read_csv(R / "benchmark_onco_SP_2010_2019_full_predictions.csv")
    rep_p = pd.read_csv(rd / f"benchmark_{args.rotulo}_predictions.csv")
    m = pub_p.merge(rep_p, on=["model", "date", "window", "horizon"], suffixes=("_pub", "_rep"))
    if len(m) != len(pub_p):
        raise SystemExit("[ERRO] reproducao nao cobre as mesmas previsoes do publicado")
    max_dif = (m.y_pred_rep - m.y_pred_pub).abs().groupby(m.model).max()

    modelos = {}
    for mod in pub_m.index:
        modelos[mod] = {
            "smape_publicado": round(float(pub_m.loc[mod, "smape"]), 4),
            "smape_reproduzido": round(float(rep_m.loc[mod, "smape"]), 4),
            "dif_smape": float(rep_m.loc[mod, "smape"] - pub_m.loc[mod, "smape"]),
            "max_dif_previsao": float(max_dif[mod]),
        }

    A = pares(R / "criterion_verdict_2010_2019_full.json")
    B = pares(rd / f"criterion_verdict_{args.rotulo}.json")
    mudam = []
    for k, pa in A.items():
        pb = B[k]
        if pa["veredito"] != pb["veredito"]:
            a, b = sorted(k)
            mudam.append({
                "par": sorted(k), "veredito_publicado": pa["veredito"],
                "veredito_reproduzido": pb["veredito"],
                "dm_publicado": pa["dm_abaixo_alpha"], "dm_reproduzido": pb["dm_abaixo_alpha"],
                "p_dm_publicado": dm_por_horizonte(R / "uncertainty_onco_SP_2010_2019_full_pairwise_tests.csv", a, b),
                "p_dm_reproduzido": dm_por_horizonte(rd / f"uncertainty_{args.rotulo}_pairwise_tests.csv", a, b),
            })

    outros = [mod for mod in modelos if mod != "xgboost"]
    rel = {
        "maquina": args.maquina,
        "modelos": modelos,
        "max_abs_dif_smape_sem_xgboost": max(abs(modelos[x]["dif_smape"]) for x in outros),
        "confirmados_publicado": sum(p["confirmado"] for p in A.values()),
        "confirmados_reproduzido": sum(p["confirmado"] for p in B.values()),
        "pares_total": len(A),
        "pares_que_mudam": mudam,
    }
    Path(args.output).write_text(json.dumps(rel, indent=2, ensure_ascii=False), encoding="utf-8")
    for mod, d in modelos.items():
        print(f"{mod:<15} {d['smape_publicado']:>8.4f} {d['smape_reproduzido']:>8.4f} "
              f"dif {d['dif_smape']:+.2e}  max dif previsao {d['max_dif_previsao']:.3g}")
    print(f"confirmados: {rel['confirmados_publicado']} -> {rel['confirmados_reproduzido']} de {len(A)}")
    for p in mudam:
        print(f"MUDA: {' x '.join(p['par'])}: {p['veredito_publicado']} ({p['dm_publicado']}) -> "
              f"{p['veredito_reproduzido']} ({p['dm_reproduzido']})")
    print(f"Gravado: {args.output}")


if __name__ == "__main__":
    main()
