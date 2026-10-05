#!/usr/bin/env python3
"""Relatorio da sensibilidade com a serie inteira 2010-2023 (LAB-204).

Plano registrado na LAB-204 antes de rodar. Le o benchmark das 103 janelas
(results/benchmark_onco_SP_2010_2023_full_*), o veredito do criterio v2 e compara com a
reproducao da analise principal nesta mesma maquina (results/reproducao/, porque o XGBoost
nao reproduz entre maquinas) e com a execucao publicada.

Checagem de consistencia: com janela expansiva, as janelas cujo horizonte inteiro cai antes
de 2020 usam o mesmo treino da analise principal, entao as previsoes delas tem de bater com
a reproducao. O script reporta a maior diferenca.

Saidas: results/serie_inteira_resumo.json e docs/relatorio_serie_inteira.md. Nenhum numero
e digitado.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from onco_timeseries.evaluate import smape

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"
CIMA = ["sarima", "timesfm", "prophet"]
BAIXO = ["linear_trend", "catboost", "xgboost", "seasonal_naive"]
ORDEM = CIMA + BAIXO
NOME = {"seasonal_naive": "Ingênuo sazonal", "linear_trend": "Tendência linear", "sarima": "SARIMA",
        "prophet": "Prophet", "timesfm": "TimesFM", "xgboost": "XGBoost", "catboost": "CatBoost"}


def br(x: float, dec: int = 2) -> str:
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pares(caminho: Path) -> dict:
    return {frozenset(p["par"].split("_menos_")): p
            for p in json.loads(caminho.read_text(encoding="utf-8"))["pares"]}


def main() -> None:
    ap = argparse.ArgumentParser(description="Relatorio da serie inteira (LAB-204)")
    ap.add_argument("--output", default="docs/relatorio_serie_inteira.md")
    ap.add_argument("--resumo", default="results/serie_inteira_resumo.json")
    args = ap.parse_args()

    pred = pd.read_csv(R / "benchmark_onco_SP_2010_2023_full_predictions.csv", parse_dates=["date"])
    n_jan = int(pred.window.nunique())
    choque = set(pred[pred.date >= "2020-01-01"].window.unique())
    estaveis = set(pred.window.unique()) - choque

    # consistencia: janelas estaveis contra a reproducao da analise principal nesta maquina
    rep = pd.read_csv(R / "reproducao" / "benchmark_mac10_predictions.csv", parse_dates=["date"])
    m = pred[pred.window.isin(estaveis)].merge(rep, on=["model", "date", "horizon"],
                                                suffixes=("", "_rep"))
    if len(m) != len(rep):
        raise SystemExit("[ERRO] janelas estaveis nao cobrem as previsoes da analise principal")
    max_dif = (m.y_pred - m.y_pred_rep).abs().groupby(m.model).max()

    def s(df: pd.DataFrame) -> pd.Series:
        return df.groupby("model").apply(lambda g: smape(g.y_true.to_numpy(), g.y_pred.to_numpy()),
                                         include_groups=False)

    total = s(pred)
    so_choque = s(pred[pred.window.isin(choque)])
    so_estavel = s(pred[pred.window.isin(estaveis)])
    pred["ano"] = pred.date.dt.year
    por_ano = pred.groupby(["ano", "model"]).apply(
        lambda g: smape(g.y_true.to_numpy(), g.y_pred.to_numpy()), include_groups=False).unstack()

    V = pares(R / "criterion_verdict_2010_2023_full.json")
    M = pares(R / "reproducao" / "criterion_verdict_mac10.json")
    P = pares(R / "criterion_verdict_2010_2019_full.json")
    entre = [k for k in V if len(k & set(CIMA)) == 1]
    dentro_cima = [k for k in V if k <= set(CIMA)]
    dentro_baixo = [k for k in V if k <= set(BAIXO)]
    a = all(V[k]["confirmado"] for k in entre)
    b = not any(V[k]["confirmado"] for k in dentro_cima)
    mudam_vs_mac = sorted([sorted(k) for k in V if V[k]["veredito"] != M[k]["veredito"]])

    resumo = {
        "janelas": n_jan, "janelas_estaveis": len(estaveis), "janelas_choque": len(choque),
        "max_dif_previsao_estaveis": {k: float(v) for k, v in max_dif.items()},
        "smape_total": total.round(4).to_dict(), "smape_choque": so_choque.round(4).to_dict(),
        "smape_estavel": so_estavel.round(4).to_dict(),
        "confirmados": sum(p["confirmado"] for p in V.values()), "pares": len(V),
        "discordantes": sum(p["veredito"] == "discordante" for p in V.values()),
        "condicao_a_entre_grupos": a, "condicao_b_dentro_cima": b,
        "conclusao_sobrevive": a and b,
        "pares_que_mudam_vs_principal_mesma_maquina": mudam_vs_mac,
    }
    Path(args.resumo).write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")

    L: list[str] = []
    w = L.append
    w("# Sensibilidade: benchmark com a série inteira 2010-2023")
    w("")
    w("Relatório da LAB-204. Gerado por `scripts/write_full_series_report.py` a partir de "
      "`results/`; não editar à mão. Plano registrado na issue antes de rodar.")
    w("")
    w("## Resposta curta")
    w("")
    ok = a and b
    w(f"**A conclusão do manuscrito {'sobrevive' if ok else 'não sobrevive'} à série inteira.** "
      f"Nas {n_jan} janelas, {resumo['confirmados']} dos {len(V)} pares são confirmados. "
      + ("Todos os pares entre o grupo que representa a série e o que não representa seguem "
         "confirmados" if a else "Nem todos os pares entre os dois grupos seguem confirmados")
      + (", e nenhum par dentro do grupo de cima é confirmado." if b else
         ", mas o grupo de cima não fica empatado."))
    if not b:
        sep = [k for k in dentro_cima if V[k]["confirmado"]]
        emp = [k for k in dentro_cima if not V[k]["confirmado"]]
        nome_par = lambda k: " x ".join(NOME[x] for x in sorted(k, key=ORDEM.index))  # noqa: E731
        w("")
        w("Dentro do grupo de cima, passam a ser confirmados: "
          + "; ".join(f"{nome_par(k)} ({V[k]['dm_abaixo_alpha']} horizontes)" for k in sep)
          + ". " + ("Continuam empatados: " + "; ".join(nome_par(k) for k in emp) + ". "
                    if emp else "")
          + "O degrau entre representar e não representar a série se mantém; o que deixa de "
            "valer é o empate dentro do grupo de cima. Pela regra registrada na LAB-204, isso "
            "conta como a conclusão não sobreviver.")
    w("")
    melhor_choque = so_choque.idxmin()
    w(f"Nas {len(choque)} janelas que preveem algum mês de 2020-2023, o erro de todos os modelos "
      f"sobe (o menor é {NOME[melhor_choque]}, {br(so_choque.min())}%, contra "
      f"{br(so_estavel.min())}% do melhor no período estável).")
    w("")

    w("## 1. Desenho")
    w("")
    w(f"Série de 168 meses, o mesmo protocolo da análise principal (horizonte 6, treino mínimo "
      f"60, janela expansiva, passo 1), os mesmos sete modelos, bootstrap de janelas inteiras e "
      f"critério v2. São {n_jan} janelas: {len(estaveis)} com o horizonte inteiro antes de 2020, "
      f"que são as mesmas da análise principal, e {len(choque)} que preveem algum mês de "
      f"2020-2023. A pandemia entra sem dummy nem tratamento.")
    w("")
    w(f"**Consistência:** nas {len(estaveis)} janelas estáveis, as previsões batem com a "
      f"reprodução da análise principal nesta máquina; a maior diferença é de "
      f"{br(max(max_dif), 3)} óbitos ({NOME[max_dif.idxmax()]}).")
    w("")

    w("## 2. sMAPE (%) por modelo")
    w("")
    w(f"| Modelo | {n_jan} janelas | {len(estaveis)} estáveis | {len(choque)} com 2020-2023 |")
    w("|---|---:|---:|---:|")
    for mod in ORDEM:
        w(f"| {NOME[mod]} | {br(total[mod])} | {br(so_estavel[mod])} | {br(so_choque[mod])} |")
    w("")

    w("## 3. sMAPE (%) por ano do mês previsto")
    w("")
    w("| Ano | " + " | ".join(NOME[x] for x in ORDEM) + " |")
    w("|---|" + "---:|" * len(ORDEM))
    for ano, row in por_ano.iterrows():
        mn = row[ORDEM].idxmin()
        w(f"| {ano} | " + " | ".join(f"**{br(row[x])}**" if x == mn else br(row[x]) for x in ORDEM) + " |")
    w("")
    w("Em negrito, o menor erro de cada ano.")
    w("")

    w("## 4. Vereditos (critério v2)")
    w("")
    w("| Par | Série inteira | Principal, esta máquina | Principal, publicado |")
    w("|---|---|---|---|")
    rot = {"confirmado": "confirmado", "nao_confirmado": "não confirmado", "discordante": "discordante"}
    for grupo, ks in (("entre os grupos", entre), ("dentro do grupo de cima", dentro_cima),
                      ("dentro do grupo de baixo", dentro_baixo)):
        for k in sorted(ks, key=lambda k: sorted(k)):
            x, y = sorted(k, key=ORDEM.index)
            w(f"| {NOME[x]} x {NOME[y]} ({grupo}) | {rot[V[k]['veredito']]} ({V[k]['dm_abaixo_alpha']}) | "
              f"{rot[M[k]['veredito']]} ({M[k]['dm_abaixo_alpha']}) | {rot[P[k]['veredito']]} |")
    w("")
    w("Entre parênteses, os horizontes com Diebold-Mariano abaixo de 0,05.")
    w("")
    w(f"**Condição (a)**, todos os pares entre grupos confirmados: {'sim' if a else 'não'}. "
      f"**Condição (b)**, nenhum par dentro do grupo de cima confirmado: {'sim' if b else 'não'}.")
    if mudam_vs_mac:
        w("")
        w("Pares cujo veredito difere da análise principal nesta máquina: "
          + "; ".join(" x ".join(NOME[x] for x in sorted(p, key=ORDEM.index)) for p in mudam_vs_mac) + ".")
    w("")
    w("## 5. Limitações")
    w("")
    w("- Mais janelas dão mais poder ao teste por horizonte; parte da diferença de vereditos "
      "contra a análise principal pode vir só disso, e não do choque.")
    w("- O XGBoost não reproduz entre máquinas; esta execução e o comparador rodaram no mesmo "
      "computador.")
    w("- Este resultado não entra no manuscrito da CSP sem decisão do Fabiano.")
    w("")
    w("## 6. Reprodução")
    w("")
    w("```")
    w("python scripts/run_benchmark.py --input-csv results/series/serie_onco_SP_sim_real_2010-2023.csv \\")
    w("    --horizon 6 --min-train-size 60 --models seasonal_naive,linear_trend,sarima,prophet,timesfm,xgboost,catboost \\")
    w("    --output-prefix results/benchmark_onco_SP_2010_2023_full --processo-por-modelo")
    w("python scripts/run_uncertainty.py --predictions-csv results/benchmark_onco_SP_2010_2023_full_predictions.csv \\")
    w("    --models (os mesmos sete) --n-boot 10000 --seed 20260818 --output-prefix results/uncertainty_onco_SP_2010_2023_full")
    w("python scripts/apply_criterion.py --pairwise-csv results/uncertainty_onco_SP_2010_2023_full_pairwise_tests.csv \\")
    w("    --report-output results/criterion_verdict_2010_2023_full.json")
    w("python scripts/write_full_series_report.py")
    w("```")

    (ROOT / args.output).write_text("\n".join(L) + "\n", encoding="utf-8")
    print(json.dumps({k: resumo[k] for k in ("janelas", "confirmados", "discordantes",
                                              "condicao_a_entre_grupos", "condicao_b_dentro_cima",
                                              "pares_que_mudam_vs_principal_mesma_maquina")},
                     ensure_ascii=False))
    print(f"Gravado: {args.output} e {args.resumo}")


if __name__ == "__main__":
    main()
