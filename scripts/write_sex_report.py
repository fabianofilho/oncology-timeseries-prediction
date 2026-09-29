#!/usr/bin/env python3
"""Escreve docs/relatorio_sexo.md, o relatorio da estratificacao por sexo (LAB-182).

Nenhum numero e digitado: tudo sai de results/, gerado por `make sex`. As frases de
conclusao tem um ramo para cada resultado possivel, inclusive o de a hipotese nao se
sustentar, porque o plano foi registrado na LAB-182 antes de rodar.

Uso:
    python scripts/write_sex_report.py [--output docs/relatorio_sexo.md]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"
SERIES = ["total_masc", "total_fem", "pulmao_masc", "pulmao_fem"]
TITULO = {"total_masc": "Câncer, masculino", "total_fem": "Câncer, feminino",
          "pulmao_masc": "Pulmão, masculino", "pulmao_fem": "Pulmão, feminino"}
BASELINE = "seasonal_naive"
ORDEM = ["seasonal_naive", "linear_trend", "sarima", "prophet", "timesfm", "xgboost", "catboost"]
NOME = {"seasonal_naive": "Ingênuo sazonal", "linear_trend": "Tendência linear", "sarima": "SARIMA",
        "prophet": "Prophet", "timesfm": "TimesFM", "xgboost": "XGBoost", "catboost": "CatBoost"}
SEXO = {"fem": "feminino", "masc": "masculino"}


def br(x: float, dec: int = 2) -> str:
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def lista(nomes: list[str]) -> str:
    nomes = [NOME[n] for n in nomes]
    if not nomes:
        return "nenhum"
    return nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]


def outro(par: str, modelo: str) -> str | None:
    a, b = par.split("_menos_")
    return b if a == modelo else a if b == modelo else None


def carrega_benchmark(serie: str) -> dict:
    boot = pd.read_csv(R / f"uncertainty_onco_SP_sexo_{serie}_2010_2019_bootstrap_metrics.csv")
    met = pd.read_csv(R / f"benchmark_onco_SP_sexo_{serie}_2010_2019_metrics.csv").set_index("model")
    vd = json.loads((R / f"criterion_verdict_sexo_{serie}_2010_2019.json").read_text(encoding="utf-8"))
    if vd["criterio"].get("versao") != 2:
        raise ValueError(f"veredito de {serie} fora da regra v2")
    pares = {p["par"]: p for p in vd["pares"]}
    batem = sorted(
        [o for par, p in pares.items() if (o := outro(par, BASELINE)) and p["confirmado"]
         and met.loc[o, "smape"] < met.loc[BASELINE, "smape"]], key=ORDEM.index)
    return {"smape": boot[boot.metric == "smape"].set_index("model"), "met": met, "pares": pares,
            "batem": batem, "n_janelas": int(boot.n_windows.iloc[0]),
            "serie": pd.read_csv(R / "series" / f"serie_onco_SP_{serie}_2010-2019.csv")}


def main() -> None:
    ap = argparse.ArgumentParser(description="Relatorio da estratificacao por sexo")
    ap.add_argument("--output", default="docs/relatorio_sexo.md")
    args = ap.parse_args()

    ser = json.loads((R / "sex_series_report.json").read_text(encoding="utf-8"))
    tend = json.loads((R / "sexo_tendencia_pulmao.json").read_text(encoding="utf-8"))
    taxas = pd.read_csv(R / "sexo_taxas_pulmao.csv")
    B = {s: carrega_benchmark(s) for s in SERIES}
    agr_boot = pd.read_csv(R / "uncertainty_onco_SP_2010_2019_full_bootstrap_metrics.csv")
    agr_smape = agr_boot[agr_boot.metric == "smape"].set_index("model")
    agr_n = float(pd.read_csv(R / "series" / "serie_onco_SP_sim_real_2010-2019.csv").value.mean())

    tr = {(t["sexo"], t["janela"], t["medida"]): t for t in tend["tendencias"]}
    ver = tend["veredito"]

    L: list[str] = []
    w = L.append
    w("# Estratificação por sexo: previsão e tendência da mortalidade por câncer de pulmão")
    w("")
    w("Relatório da LAB-182. Gerado por `scripts/write_sex_report.py` a partir de `results/`; "
      "não editar à mão. O plano (séries, protocolo, população padrão, método de tendência e "
      "o que conta como apoio à hipótese) foi registrado na issue antes de rodar.")
    w("")

    # ------------------------------------------------------------ resposta curta
    fem = tr[("fem", "2010-2019", "taxa_padronizada")]
    masc = tr[("masc", "2010-2019", "taxa_padronizada")]
    w("## Resposta curta")
    w("")
    frase = {"apoiada": "se sustenta", "apoiada em parte": "se sustenta só em parte",
             "nao apoiada": "não se sustenta"}[ver["hipotese"]]
    w(f"**A hipótese de que a mortalidade por câncer de pulmão sobe em mulheres e cai em homens "
      f"{frase}** na taxa padronizada por idade, de 2010 a 2019: variação percentual anual (APC) de "
      f"{br(fem['apc'])}% [{br(fem['ic95'][0])}; {br(fem['ic95'][1])}] no sexo feminino e "
      f"{br(masc['apc'])}% [{br(masc['ic95'][0])}; {br(masc['ic95'][1])}] no masculino.")
    w("")
    fc = tr[("fem", "2010-2019", "obitos")]
    mc = tr[("masc", "2010-2019", "obitos")]
    w(f"Em contagem bruta, o número de óbitos variou {br(fc['apc'])}% ao ano no feminino e "
      f"{br(mc['apc'])}% no masculino. A distância entre contagem e taxa padronizada é o "
      "envelhecimento da população: é por isso que a hipótese foi testada na taxa.")
    w("")
    todas_batem = [s for s in SERIES if B[s]["batem"]]
    boost_bate = [s for s in SERIES if {"xgboost", "catboost"} & set(B[s]["batem"])]
    if len(todas_batem) == len(SERIES):
        comuns = sorted(set.intersection(*(set(B[s]["batem"]) for s in SERIES)), key=ORDEM.index)
        parciais = sorted({m for s in SERIES for m in B[s]["batem"]} - set(comuns), key=ORDEM.index)
        w("Na previsão, algum modelo bate o ingênuo sazonal de forma confirmada nas quatro séries. "
          + (f"{lista(comuns)} {'bate' if len(comuns) == 1 else 'batem'} em todas"
             if comuns else "Nenhum modelo bate em todas")
          + "".join(f"; {NOME[m] if m not in ('linear_trend', 'seasonal_naive') else NOME[m].lower()}"
                    f" em {sum(m in B[s]['batem'] for s in SERIES)} de 4" for m in parciais)
          + ("; XGBoost e CatBoost não batem em nenhuma." if not boost_bate else "."))
    elif todas_batem:
        w("Na previsão, algum modelo bate o ingênuo sazonal de forma confirmada em "
          + ", ".join(TITULO[s].lower() for s in todas_batem) + "; nas demais séries, nenhum.")
    else:
        w("Na previsão, nenhum modelo bate o ingênuo sazonal de forma confirmada em nenhuma das "
          "quatro séries.")
    w("")

    # ------------------------------------------------------------ series
    w("## 1. Séries")
    w("")
    w("Mesma extração do manuscrito: SIM por residência, Estado de São Paulo, 2010-2023.")
    w("")
    w("| Desfecho | Óbitos | Masculino | Feminino | Sexo ignorado | Idade ignorada |")
    w("|---|---:|---:|---:|---:|---:|")
    for chave, d in ser["desfechos"].items():
        w(f"| {d['rotulo']} | {br(d['obitos'], 0)} | {br(d['series']['masc']['obitos'], 0)} | "
          f"{br(d['series']['fem']['obitos'], 0)} | {br(d['sexo_ignorado'], 0)} | "
          f"{br(d['idade_ignorada'], 0)} ({br(d['idade_ignorada_pct'], 2)}%) |")
    w("")
    w(f"Masculino, feminino e sexo ignorado somam o total do manuscrito "
      f"({br(ser['total_microdado'], 0)} óbitos); o script aborta se não somarem.")
    w("")

    # ------------------------------------------------------------ previsao
    w("## 2. Previsão por sexo")
    w("")
    n_jan = B[SERIES[0]]["n_janelas"]
    w(f"Protocolo idêntico ao do manuscrito: 2010-2019, horizonte de 6 meses, treino mínimo de "
      f"60, {n_jan} janelas, os sete modelos, bootstrap de janelas inteiras e critério v2 "
      "(sMAPE e MAE concordando, e Diebold-Mariano em ≥ 3 de 6 horizontes).")
    w("")
    w("sMAPE (%) com IC95%. Em negrito, a menor estimativa pontual de cada série.")
    w("")
    w("| Modelo | " + " | ".join(TITULO[s] for s in SERIES) + " |")
    w("|---|" + "---|" * len(SERIES))
    for m in ORDEM:
        cel = []
        for s in SERIES:
            r = B[s]["smape"].loc[m]
            t = f"{br(r.point)} [{br(r.ci_low)}; {br(r.ci_high)}]"
            cel.append(f"**{t}**" if B[s]["smape"].point.idxmin() == m else t)
        w(f"| {NOME[m]} | " + " | ".join(cel) + " |")
    w("")
    w("| Série | Óbitos por mês | Pares confirmados | Discordantes sMAPE x MAE | Batem o ingênuo sazonal | "
      "sMAPE observado / esperado por Poisson |")
    w("|---|---:|---|---|---|---:|")
    razoes = {}
    base_s = float(agr_smape.point.min())
    for s in SERIES:
        n = float(B[s]["serie"].value.mean())
        obs = float(B[s]["smape"].point.min()) / base_s
        esp = float(np.sqrt(agr_n / n))
        razoes[s] = obs / esp
        pares = B[s]["pares"].values()
        w(f"| {TITULO[s]} | {br(n, 0)} | {sum(p['confirmado'] for p in pares)} de {len(pares)} | "
          f"{sum(p['veredito'] == 'discordante' for p in pares)} de {len(pares)} | "
          f"{lista(B[s]['batem'])} | {br(razoes[s], 2)} |")
    w("")
    fora = [s for s in SERIES if not 0.8 <= razoes[s] <= 1.25]
    w("A última coluna compara o erro do melhor modelo em cada série com o do agregado, "
      "descontado o que o tamanho da contagem explica (raiz da razão das médias mensais, "
      "como nos sítios). Perto de 1, a série não é mais difícil do que sua contagem implica. "
      + ("Todas as quatro ficam entre 0,8 e 1,25." if not fora else
         "Fora da faixa de 0,8 a 1,25: " + ", ".join(
             f"{TITULO[s].lower()} ({br(razoes[s], 2)})" for s in fora) + "."))
    w("")

    # ------------------------------------------------------------ tendencia
    w("## 3. Tendência da taxa de pulmão padronizada por idade")
    w("")
    w(f"Padronização {tend['padronizacao']}. Denominador: {tend['denominador']}. Taxas por "
      "100.000 habitantes.")
    w("")
    piv = taxas.pivot(index="ano", columns="sexo", values="taxa_padronizada")
    pivb = taxas.pivot(index="ano", columns="sexo", values="obitos")
    w("| Ano | Feminino, taxa | Masculino, taxa | Feminino, óbitos | Masculino, óbitos |")
    w("|---|---:|---:|---:|---:|")
    for ano in piv.index:
        w(f"| {ano} | {br(piv.loc[ano, 'fem'])} | {br(piv.loc[ano, 'masc'])} | "
          f"{br(pivb.loc[ano, 'fem'], 0)} | {br(pivb.loc[ano, 'masc'], 0)} |")
    w("")
    w("Prais-Winsten do log10 contra o ano. APC em % ao ano, com IC95%.")
    w("")
    w("| Sexo | Janela | Medida | APC [IC95%] | Sentido |")
    w("|---|---|---|---|---|")
    for t in tend["tendencias"]:
        med = "taxa padronizada" if t["medida"] == "taxa_padronizada" else "contagem bruta"
        sent = {"aumento": "aumento", "queda": "queda", "estavel": "estável"}[t["sentido"]]
        w(f"| {SEXO[t['sexo']]} | {t['janela']} | {med} | {br(t['apc'])} "
          f"[{br(t['ic95'][0])}; {br(t['ic95'][1])}] | {sent} |")
    w("")
    w(f"**Veredito pela regra da LAB-182:** hipótese {ver['hipotese'].replace('nao', 'não')}. "
      f"Queda no masculino: {'sim' if ver['masculino_cai'] else 'não'}; aumento no feminino: "
      f"{'sim' if ver['feminino_sobe'] else 'não'}.")
    sens = {t["sexo"]: t for t in tend["tendencias"]
            if t["janela"] == "2010-2023" and t["medida"] == "taxa_padronizada"}
    w("")
    w(f"Na sensibilidade com 2010-2023, o APC é {br(sens['fem']['apc'])}% no feminino e "
      f"{br(sens['masc']['apc'])}% no masculino.")
    if "sensibilidade_redistribuicao" in tend:
        vr = tend["sensibilidade_redistribuicao"]["veredito"]["hipotese"].replace("nao", "não")
        L[-1] += f" Com a idade ignorada redistribuída proporcionalmente, o veredito é: {vr}."
    else:
        L[-1] += (f" A idade ignorada ficou em {br(tend['idade_ignorada_pct'], 2)}% dos óbitos de "
          "pulmão, abaixo do limiar de 1% declarado; a sensibilidade de redistribuição não se "
          "aplica.")
    w("")

    # ------------------------------------------------------------ limitacoes
    w("## 4. Limitações")
    w("")
    w("- **Denominador revisado.** As estimativas de 2024 do DataSUS/RIPSA substituem as de "
      "2000-2021; os números de população diferem da série antiga. Usar uma fonte só, de 2010 a "
      "2023, foi a escolha declarada.")
    w("- **Faixa aberta em 80 anos.** O denominador fecha em 80+, então os pesos de Segi de "
      "80-84 e 85+ foram somados. Em pulmão, com óbitos concentrados em idade alta, isso pesa "
      "mais do que em cânceres de idade menor.")
    w("- **Um estado.** A tendência é de São Paulo; Reis 2026 projeta por região.")
    w("- **XGBoost depende da máquina.** O benchmark por sexo rodou num Apple M4; o XGBoost não "
      "reproduz entre máquinas (ver `docs/xgboost_reprodutibilidade.md`), então os números dele "
      "nesta tabela podem diferir em outro computador. Os outros seis modelos reproduzem.")
    w("- **Taxa padronizada só para pulmão**, como declarado. A previsão por sexo usa contagem, "
      "como o resto do projeto.")
    w("- **Manuscrito da CSP inalterado.** Estes resultados não entram no texto submetido.")
    w("")
    w("## 5. Reprodução")
    w("")
    w("```")
    w("make extract-sim   # microdado do SIM, fora do git")
    w("make sex           # séries, população, benchmark, critério, tendência e este relatório")
    w("```")

    out = ROOT / args.output
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Gravado: {out}")


if __name__ == "__main__":
    main()
