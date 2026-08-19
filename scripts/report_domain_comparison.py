#!/usr/bin/env python3
"""Relatorio comparativo entre os tres dominios da linha, sob protocolo identico.

Reporta tres coisas separadas, porque elas respondem perguntas diferentes:

1. sMAPE bruto: quao dificil e o dominio. Nao e comparavel entre dominios com
   amplitude muito diferente, e esta aqui so para contexto.
2. Razao contra o ingenuo sazonal do proprio dominio: quanto modelar adianta ali.
   Essa e a comparacao valida entre dominios.
3. Quantos pares o criterio pre-declarado confirma: se ha estrutura suficiente
   para distinguir modelo nenhum.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

DOMINIOS = ["cancer", "cardiovascular", "dengue"]
BASELINE = "seasonal_naive"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Relatorio comparativo entre dominios")
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--periodo", default="2010_2019")
    parser.add_argument("--inputs-json", default="results/domain_comparison_inputs.json")
    parser.add_argument("--report-output", default="results/domain_comparison_report.json")
    return parser.parse_args()


def confirmados(path: Path, smape_por_modelo: pd.Series) -> tuple[int, int, list[str]]:
    """Modelos que batem o baseline: diferenca confirmada E sMAPE menor.

    Um par confirmado so diz que a diferenca existe, nao em que direcao. Checar a
    direcao pelo sMAPE e obrigatorio: sem isso, um modelo pior que o baseline
    apareceria como se o tivesse batido.
    """
    v = json.loads(path.read_text(encoding="utf-8"))
    pares = v["pares"]
    conf = [p for p in pares if p["confirmado"]]
    batem = []
    for p in conf:
        if BASELINE not in p["par"]:
            continue
        partes = p["par"].split("_menos_")
        outro = partes[0] if partes[1] == BASELINE else partes[1]
        if smape_por_modelo[outro] < smape_por_modelo[BASELINE]:
            batem.append(outro)
    return len(conf), len(pares), sorted(set(batem))


def main() -> None:
    args = parse_args()
    rd = Path(args.results_dir)
    entradas = {d["dominio"]: d for d in json.loads(Path(args.inputs_json).read_text(encoding="utf-8"))["dominios"]}

    linhas = []
    for dom in DOMINIOS:
        m = pd.read_csv(rd / f"benchmark_dominio_{dom}_{args.periodo}_metrics.csv").set_index("model")
        n_conf, n_par, batem = confirmados(
            rd / f"criterion_verdict_dominio_{dom}_{args.periodo}.json", m.smape
        )

        base_smape = float(m.loc[BASELINE, "smape"])
        base_mae = float(m.loc[BASELINE, "mae"])
        melhor_smape = m.smape.idxmin()
        melhor_mae = m.mae.idxmin()

        linhas.append(
            {
                "dominio": dom,
                "amplitude": entradas[dom]["amplitude_max_sobre_min"],
                "cv": entradas[dom]["cv"],
                "melhor_por_smape": melhor_smape,
                "smape": round(float(m.smape.min()), 2),
                "smape_baseline": round(base_smape, 2),
                "razao_smape": round(float(m.smape.min()) / base_smape, 3),
                "melhor_por_mae": melhor_mae,
                "razao_mae": round(float(m.mae.min()) / base_mae, 3),
                "metrica_concorda": melhor_smape == melhor_mae,
                "pares_confirmados": f"{n_conf}/{n_par}",
                "batem_o_baseline": batem,
            }
        )

    res = pd.DataFrame(linhas)

    print("Protocolo identico nos tres: 2010-02 a 2019-12, 119 pontos, horizonte 6,")
    print("min_train 60, 54 janelas, 324 previsoes por modelo, semente 20260818.\n")

    print("1. Dificuldade do dominio (nao comparavel entre dominios, so contexto)\n")
    print(res[["dominio", "amplitude", "cv", "melhor_por_smape", "smape", "smape_baseline"]].to_string(index=False))

    print("\n2. Quanto modelar adianta (razao contra o ingenuo sazonal do proprio dominio)\n")
    print("   razao < 1 = o melhor modelo erra menos que o baseline trivial\n")
    print(res[["dominio", "razao_smape", "razao_mae", "melhor_por_smape", "melhor_por_mae", "metrica_concorda"]].to_string(index=False))

    print("\n3. Ha estrutura para distinguir modelos?\n")
    for _, r in res.iterrows():
        b = ", ".join(r["batem_o_baseline"]) if r["batem_o_baseline"] else "NENHUM"
        print(f"   {r['dominio']:<16} {r['pares_confirmados']:>6} pares confirmados | batem o ingenuo sazonal: {b}")

    disc = res[~res.metrica_concorda]
    if len(disc):
        print("\nATENCAO: em " + ", ".join(disc.dominio) + " o melhor modelo muda conforme a metrica.")
        print("Reportar so o sMAPE ali seria escolher o vencedor pela metrica.")

    p = Path(args.report_output)
    p.write_text(json.dumps({"dominios": linhas}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nGravado: {p}")


if __name__ == "__main__":
    main()
