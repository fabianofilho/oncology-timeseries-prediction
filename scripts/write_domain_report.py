#!/usr/bin/env python3
"""Escreve o relatorio final da comparacao entre dominios (LAB-120) em Markdown.

Nenhum numero e digitado aqui: tudo sai dos CSVs e JSONs de results/ gerados por
`make domains`. O que e digitado sao fatos de desenho de cada serie (desfecho, fonte,
recorte geografico) e o protocolo que cada projeto publicou, com a origem anotada em
PUBLICADO e SERIES, conferidos nos READMEs e no codigo de cada repositorio em
2026-09-28.

As frases de conclusao sao montadas a partir do resultado, com um ramo para cada
desfecho possivel, inclusive empate. Se um numero mudar, a frase muda junto.

Uso:
    python scripts/write_domain_report.py [--output docs/relatorio_dominios.md]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
PERIODO = "2010_2019"
DOMINIOS = ["cancer", "cardiovascular", "dengue"]
BASELINE = "seasonal_naive"
ORDEM = ["seasonal_naive", "linear_trend", "sarima", "prophet", "timesfm", "xgboost", "catboost"]
NOME = {
    "seasonal_naive": "Ingênuo sazonal",
    "linear_trend": "Tendência linear",
    "sarima": "SARIMA",
    "prophet": "Prophet",
    "timesfm": "TimesFM",
    "xgboost": "XGBoost",
    "catboost": "CatBoost",
}
TITULO = {"cancer": "Câncer", "cardiovascular": "Cardiovascular", "dengue": "Dengue"}

# Desenho de cada serie. A geografia da dengue e o municipio (geocodigo IBGE 3550308 em
# scripts/fetch_infodengue.py do DFP), nao o estado: e a unica diferenca de recorte
# entre as tres, e ela nao aparecia na comparacao de agosto.
SERIES = {
    "cancer": ("OPT", "óbitos, causa básica CID-10 C00-C97", "SIM/DataSUS, por residência",
               "Estado de São Paulo"),
    "cardiovascular": ("CPT", "óbitos, causa básica CID-10 I00-I99", "SIM/DataSUS",
                       "Estado de São Paulo"),
    "dengue": ("DFP", "casos notificados", "InfoDengue",
               "Município de São Paulo (IBGE 3550308)"),
}

# Protocolo que cada projeto publicou, conferido no README de cada um em 2026-09-28.
# Nenhum numero publicado por eles entra nas tabelas deste relatorio.
PUBLICADO = [
    ("OPT, manuscrito da CSP", "2010-01 a 2019-12 (120 meses); 2020-2023 só como teste de regime",
     "Estado de SP", "6", "60",
     "sMAPE, com MAE e RMSE", "IC exclui zero e DM em ≥ 3 de 6"),
    ("CPT, README", "2010-01 a 2023-12 (168 meses)", "Estado de SP", "6", "60",
     "MAE, RMSE e sMAPE", "IC exclui zero e DM em ≥ 3 de 6"),
    ("DFP, README", "2010-02 a 2024-11 (178 meses)", "8 capitais", "12", "48",
     "MAE relativo ao ingênuo; sMAPE exploratório", "IC exclui zero e DM em ≥ 6 de 12"),
]


def br(x: float, dec: int = 2) -> str:
    """Numero no padrao brasileiro: ponto no milhar, virgula no decimal."""
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def ic(row: pd.Series, dec: int = 2) -> str:
    return f"{br(row['point'], dec)} [{br(row['ci_low'], dec)}; {br(row['ci_high'], dec)}]"


def lista(nomes: list[str]) -> str:
    nomes = [NOME[n] for n in nomes]
    if not nomes:
        return "nenhum"
    return nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]


def outro_do_par(par: str, modelo: str) -> str | None:
    a, b = par.split("_menos_")
    if modelo == a:
        return b
    if modelo == b:
        return a
    return None


def carrega(dom: str) -> dict:
    met = pd.read_csv(RESULTS / f"benchmark_dominio_{dom}_{PERIODO}_metrics.csv").set_index("model")
    boot = pd.read_csv(RESULTS / f"uncertainty_dominio_{dom}_{PERIODO}_bootstrap_metrics.csv")
    vd = json.loads((RESULTS / f"criterion_verdict_dominio_{dom}_{PERIODO}.json").read_text(encoding="utf-8"))
    pred = pd.read_csv(RESULTS / f"benchmark_dominio_{dom}_{PERIODO}_predictions.csv")
    serie = pd.read_csv(RESULTS / "series" / f"comp_{dom}_{PERIODO}.csv")
    hor = pd.read_csv(RESULTS / f"uncertainty_dominio_{dom}_{PERIODO}_error_by_horizon.csv")
    if vd["criterio"].get("versao") != 2:
        raise ValueError(f"veredito de {dom} nao esta na regra v2 (LAB-135); rode make domains")

    pares = {p["par"]: p for p in vd["pares"]}
    # quem bate o baseline: par confirmado E erro menor nas duas metricas
    batem = []
    for par, p in pares.items():
        outro = outro_do_par(par, BASELINE)
        if outro and p["confirmado"] and met.loc[outro, "smape"] < met.loc[BASELINE, "smape"]:
            batem.append(outro)
    return {
        "met": met,
        "smape": boot[boot.metric == "smape"].set_index("model"),
        "mae": boot[boot.metric == "mae"].set_index("model"),
        "pares": pares,
        "batem": sorted(batem, key=ORDEM.index),
        "pred": pred,
        "serie": serie,
        "horizonte": int(hor.horizon.max()),
        "n_janelas": int(boot.n_windows.iloc[0]),
        "n_prev": int(boot.n_predictions.iloc[0]),
        "B": int(boot.B.iloc[0]),
    }


def par_contra_baseline(d: dict, modelo: str) -> dict:
    for par, p in d["pares"].items():
        if outro_do_par(par, BASELINE) == modelo:
            return p
    raise KeyError(modelo)


def main() -> None:
    ap = argparse.ArgumentParser(description="Relatorio final da comparacao entre dominios")
    ap.add_argument("--output", default="docs/relatorio_dominios.md")
    args = ap.parse_args()

    entradas = json.loads((RESULTS / "domain_comparison_inputs.json").read_text(encoding="utf-8"))
    perfil = {d["dominio"]: d for d in entradas["dominios"]}
    D = {dom: carrega(dom) for dom in DOMINIOS}
    semente = re.search(r"--seed (\d+)", (ROOT / "Makefile").read_text(encoding="utf-8")).group(1)

    ref = D["cancer"]
    for dom in DOMINIOS:
        for k in ("horizonte", "n_janelas", "n_prev", "B"):
            if D[dom][k] != ref[k]:
                raise ValueError(f"protocolo difere em {k} entre cancer e {dom}")
    pontos = {perfil[d]["pontos"] for d in DOMINIOS}
    if len(pontos) != 1:
        raise ValueError(f"numero de pontos difere entre dominios: {pontos}")
    n_pontos = pontos.pop()
    min_train = n_pontos - ref["horizonte"] + 1 - ref["n_janelas"]

    L: list[str] = []
    w = L.append

    w("# Previsibilidade de câncer, cardiovascular e dengue sob protocolo idêntico")
    w("")
    w("Relatório final da LAB-120. Gerado por `scripts/write_domain_report.py` a partir de "
      "`results/`; não editar à mão. Critério na versão 2 (LAB-135): sMAPE e MAE precisam "
      "concordar.")
    w("")

    # ---------------------------------------------------------------- resposta curta
    batem_dom = [d for d in DOMINIOS if D[d]["batem"]]
    w("## Resposta curta")
    w("")
    if not batem_dom:
        w("Em nenhum dos três domínios algum modelo bate o ingênuo sazonal de forma confirmada. "
          "Os três empatam com o baseline trivial, e esse é o achado.")
    else:
        partes = [f"{TITULO[d].lower()} ({lista(D[d]['batem'])})" for d in batem_dom]
        resto = [TITULO[d].lower() for d in DOMINIOS if d not in batem_dom]
        w(f"Só em {' e '.join(partes)} algum modelo bate o ingênuo sazonal de forma confirmada. "
          + (f"Em {' e '.join(resto)}, nenhum modelo passa no critério contra o baseline trivial."
             if resto else ""))
    disc_dom = {d: sum(p["veredito"] == "discordante" for p in D[d]["pares"].values()) for d in DOMINIOS}
    com_disc = [d for d in DOMINIOS if disc_dom[d]]
    if com_disc:
        w("")
        w("sMAPE e MAE discordam em " + ", ".join(
            f"{disc_dom[d]} dos {len(D[d]['pares'])} pares de {TITULO[d].lower()}" for d in com_disc)
          + ("; nos outros domínios, em nenhum." if len(com_disc) < len(DOMINIOS) else "."))
    w("")

    # ---------------------------------------------------------------- protocolo
    w("## 1. Protocolo comum")
    w("")
    w("As três séries foram rerodadas pelo mesmo código. Nenhum número publicado por CPT ou "
      "DFP foi reaproveitado.")
    w("")
    w("| Item | Valor |")
    w("|---|---|")
    w(f"| Janela comum | {entradas['start'][:7]} a {entradas['end'][:7]}, {n_pontos} meses |")
    w(f"| Horizonte | {ref['horizonte']} meses |")
    w(f"| Treino mínimo | {min_train} meses, janela expansiva, passo de 1 mês |")
    w(f"| Janelas de origem rolante | {ref['n_janelas']} |")
    w(f"| Previsões por modelo e domínio | {ref['n_prev']} |")
    w(f"| Modelos | os mesmos {len(ORDEM)}, mesma configuração: {lista(ORDEM)} |")
    w(f"| Bootstrap | janelas inteiras, B = {br(ref['B'], 0)}, semente {semente} |")
    w("| Critério | v2: IC95% de sMAPE e de MAE excluem zero no mesmo sentido, e "
      "Diebold-Mariano (erro absoluto, correção de Harvey) < 0,05 em ≥ 3 de 6 horizontes |")
    w("")

    # ---------------------------------------------------------------- series
    w("## 2. O que difere entre as séries")
    w("")
    w("O protocolo é idêntico; as séries não. A diferença de recorte geográfico da dengue "
      "vem do DFP, que trabalha por capital.")
    w("")
    w("| | " + " | ".join(TITULO[d] for d in DOMINIOS) + " |")
    w("|---|" + "---|" * len(DOMINIOS))
    w("| Projeto de origem | " + " | ".join(SERIES[d][0] for d in DOMINIOS) + " |")
    w("| Desfecho | " + " | ".join(SERIES[d][1] for d in DOMINIOS) + " |")
    w("| Fonte | " + " | ".join(SERIES[d][2] for d in DOMINIOS) + " |")
    w("| Recorte | " + " | ".join(SERIES[d][3] for d in DOMINIOS) + " |")
    w("| Média mensal | " + " | ".join(br(perfil[d]["media"], 0) for d in DOMINIOS) + " |")
    w("| Mínimo e máximo | " + " | ".join(
        f"{br(perfil[d]['minimo'], 0)} a {br(perfil[d]['maximo'], 0)}" for d in DOMINIOS) + " |")
    w("| Amplitude máx/mín | " + " | ".join(br(perfil[d]["amplitude_max_sobre_min"], 1) for d in DOMINIOS) + " |")
    w("| Coeficiente de variação | " + " | ".join(br(perfil[d]["cv"], 3) for d in DOMINIOS) + " |")
    w("")

    # ---------------------------------------------------------------- tabela unica
    for metrica, rot, dec in (("smape", "sMAPE (%)", 2), ("mae", "MAE (casos ou óbitos por mês)", 0)):
        w(f"## {3 if metrica == 'smape' else 4}. {rot} com IC95%, os sete modelos nos três domínios")
        w("")
        w("| Modelo | " + " | ".join(TITULO[d] for d in DOMINIOS) + " |")
        w("|---|" + "---|" * len(DOMINIOS))
        for m in ORDEM:
            celulas = []
            for d in DOMINIOS:
                t = ic(D[d][metrica].loc[m], dec)
                melhor = D[d][metrica].point.idxmin() == m
                celulas.append(f"**{t}**" if melhor else t)
            w(f"| {NOME[m]} | " + " | ".join(celulas) + " |")
        w("")
        if metrica == "smape":
            w("Em negrito, a menor estimativa pontual de cada domínio, que não é o mesmo que o "
              "melhor modelo (seção 6). O sMAPE bruto mede a dificuldade da série e não se "
              "compara entre domínios: com amplitude de "
              f"{br(perfil['dengue']['amplitude_max_sobre_min'], 1)} vezes na dengue contra "
              f"{br(perfil['cancer']['amplitude_max_sobre_min'], 1)} no câncer, a diferença de "
              "nível é da série, não do modelo.")
            w("")

    # ---------------------------------------------------------------- razao
    w("## 5. Quanto modelar adianta, contra o baseline do próprio domínio")
    w("")
    w("Razão abaixo de 1 significa que o melhor modelo erra menos que repetir o ano anterior.")
    w("")
    w("| Domínio | Razão sMAPE | Melhor por sMAPE | Razão MAE | Melhor por MAE |")
    w("|---|---:|---|---:|---|")
    razao = {}
    for d in DOMINIOS:
        met = D[d]["met"]
        ms, mm = met.smape.idxmin(), met.mae.idxmin()
        rs = met.smape.min() / met.loc[BASELINE, "smape"]
        rm = met.mae.min() / met.loc[BASELINE, "mae"]
        razao[d] = (rs, rm, ms, mm)
        w(f"| {TITULO[d]} | {br(rs, 3)} | {NOME[ms]} | {br(rm, 3)} | {NOME[mm]} |")
    w("")
    muda = [d for d in DOMINIOS if razao[d][2] != razao[d][3]]
    if muda:
        w("O melhor modelo muda com a métrica em " + " e ".join(TITULO[d].lower() for d in muda)
          + ". Reportar só uma das duas ali seria escolher o vencedor pela métrica.")
        w("")

    # ---------------------------------------------------------------- criterio
    w("## 6. O que sobrevive ao critério")
    w("")
    w("| Domínio | Pares confirmados | Discordantes sMAPE x MAE | Batem o ingênuo sazonal |")
    w("|---|---|---|---|")
    for d in DOMINIOS:
        n = len(D[d]["pares"])
        c = sum(p["confirmado"] for p in D[d]["pares"].values())
        w(f"| {TITULO[d]} | {c} de {n} | {disc_dom[d]} de {n} | {lista(D[d]['batem'])} |")
    w("")
    w("Cada modelo contra o ingênuo sazonal, com as três condições do critério. Diferença = "
      "ingênuo menos modelo, então positivo significa que o modelo erra menos.")
    w("")
    w("| Domínio | Modelo | Dif. sMAPE [IC95%] | Dif. MAE [IC95%] | DM < 0,05 | Veredito |")
    w("|---|---|---|---|---|---|")
    for d in DOMINIOS:
        for m in ORDEM[1:]:
            p = par_contra_baseline(D[d], m)
            # os pares vem como a_menos_b; normaliza para ingenuo menos modelo
            sinal = 1 if p["par"].startswith(BASELINE) else -1
            ds = [sinal * float(x) for x in p["ic95"].strip("[]").split(",")]
            dm = [sinal * float(x) for x in p["ic95_mae"].strip("[]").split(",")]
            lo_s, hi_s = sorted(ds)
            lo_m, hi_m = sorted(dm)
            ver = p["veredito"].replace("nao_confirmado", "não confirmado")
            w(f"| {TITULO[d]} | {NOME[m]} | {br(sinal * p['diferenca'])} "
              f"[{br(lo_s)}; {br(hi_s)}] | {br(sinal * p['diferenca_mae'], 0)} "
              f"[{br(lo_m, 0)}; {br(hi_m, 0)}] | {p['dm_abaixo_alpha']} | {ver} |")
    w("")

    # ---------------------------------------------------------------- hipotese
    w("## 7. A hipótese da issue")
    w("")
    w("A LAB-120 partiu da hipótese de que câncer é dominado por tendência, cardiovascular por "
      "sazonalidade e dengue por surto, e de que foundation model só compensa onde há surto.")
    w("")
    rt = {d: D[d]["met"].loc["linear_trend", "smape"] / D[d]["met"].loc[BASELINE, "smape"] for d in DOMINIOS}
    estrutura_ok = rt["cancer"] < 1 < rt["cardiovascular"]
    w(f"**Estrutura, câncer contra cardiovascular: {'se sustenta' if estrutura_ok else 'não se sustenta'}.** "
      "A tendência linear "
      f"tem razão {br(rt['cancer'], 2)} contra o ingênuo sazonal em câncer e "
      f"{br(rt['cardiovascular'], 2)} em cardiovascular"
      + (": extrapolar uma reta é competitivo onde a tendência domina e é o pior modelo onde "
         "domina o ciclo anual." if estrutura_ok else "."))
    w("")
    tf = {d: par_contra_baseline(D[d], "timesfm")["veredito"] for d in DOMINIOS}
    tf_bate = [d for d in DOMINIOS if "timesfm" in D[d]["batem"]]
    so_surto = tf_bate == ["dengue"]
    p_tf_den = par_contra_baseline(D["dengue"], "timesfm")
    w(f"**Foundation model só onde há surto: {'se sustenta' if so_surto else 'não se sustenta'}.** "
      + ("O TimesFM bate o ingênuo sazonal de forma confirmada em "
         + " e ".join(TITULO[d].lower() for d in tf_bate)
         if tf_bate else "O TimesFM não bate o ingênuo sazonal de forma confirmada em nenhum domínio")
      + f", e na dengue o par é {tf['dengue'].replace('nao_confirmado', 'não confirmado')}: "
      f"o IC de MAE {'exclui' if p_tf_den['ic_mae_exclui_zero'] else 'contém'} zero, o de sMAPE "
      f"{'exclui' if p_tf_den['ic_exclui_zero'] else 'contém'}, e o Diebold-Mariano fica abaixo "
      f"de 0,05 em {p_tf_den['dm_abaixo_alpha'].replace('/', ' de ')} horizontes."
      + (" Há um efeito na dengue, visível no erro absoluto, mas o teste por horizonte não o "
         "sustenta." if p_tf_den["ic_mae_exclui_zero"] and not p_tf_den["confirmado"] else "")
      + (" E o mesmo modelo tem ganho confirmado numa série sem surto."
         if [d for d in tf_bate if d != "dengue"] else ""))
    w("")

    # ---------------------------------------------------------------- conclusao OPT
    w("## 8. Conclusão do OPT")
    w("")
    top = D["cancer"]["batem"]
    entre = [p for par, p in D["cancer"]["pares"].items()
             if all(x in top for x in par.split("_menos_"))]
    conf_entre = sum(p["confirmado"] for p in entre)
    if not top:
        w("Em câncer, nenhum modelo bate o ingênuo sazonal de forma confirmada: os sete empatam "
          "com o baseline trivial.")
    else:
        w(f"Em câncer, {lista(top)} batem o ingênuo sazonal de forma confirmada, com o melhor "
          f"errando {br(100 * (1 - razao['cancer'][0]), 0)}% menos por sMAPE. "
          + (f"Entre esses {len(top)}, nenhum dos {len(entre)} pares é confirmado: eles empatam "
             "entre si, e o que os dados sustentam é um degrau entre quem representa a série e "
             "quem não representa, não um vencedor."
             if conf_entre == 0 else
             f"Entre esses {len(top)}, {conf_entre} dos {len(entre)} pares são confirmados."))
    w("")
    w("Nesta janela comum (a partir de fevereiro de 2010, por causa da dengue) o câncer tem "
      f"{sum(p['confirmado'] for p in D['cancer']['pares'].values())} de {len(D['cancer']['pares'])} "
      "pares confirmados. O manuscrito do OPT usa a série a partir de janeiro, com uma janela a "
      "mais, e reporta a própria contagem; os dois números não se misturam.")
    w("")

    # ---------------------------------------------------------------- publicado
    w("## 9. Diferenças contra o que cada projeto publicou")
    w("")
    w("| Fonte | Período | Recorte | Horizonte | Treino mínimo | Métrica principal | Critério |")
    w("|---|---|---|---|---|---|---|")
    for linha in PUBLICADO:
        w("| " + " | ".join(linha) + " |")
    w(f"| **Esta comparação** | {entradas['start'][:7]} a {entradas['end'][:7]} ({n_pontos} meses) | "
      f"Estado de SP; dengue no município | {ref['horizonte']} | {min_train} | sMAPE e MAE | "
      "v2, sMAPE e MAE concordando e DM em ≥ 3 de 6 |")
    w("")
    w("Esta comparação responde outra pergunta que a de cada projeto e não substitui nenhum "
      "resultado publicado.")
    w("")

    # ---------------------------------------------------------------- limitacoes
    w("## 10. Limitações")
    w("")
    w("- **Recorte geográfico**: câncer e cardiovascular são o estado de São Paulo; dengue é o "
      "município. A comparação vale como razão contra o baseline de cada série, não como "
      "comparação entre populações.")
    pr = D["dengue"]["pred"]
    mx = D["dengue"]["serie"].value.max()
    neg = pr[pr.y_pred < 0].groupby("model").size()
    acima = pr[pr.y_pred > mx].groupby("model").size()
    for m in ORDEM:
        if neg.get(m, 0) or acima.get(m, 0):
            w(f"- **{NOME[m]} na dengue**: {neg.get(m, 0)} previsões negativas de casos e "
              f"{acima.get(m, 0)} acima do máximo da série ({br(mx, 0)}), a maior em "
              f"{br(pr[pr.model == m].y_pred.max(), 0)}. Mantidas sem corte, como o protocolo "
              f"manda; pesam no MAE dele ({br(D['dengue']['met'].loc[m, 'mae'], 0)}).")
    w("- **Poder do Diebold-Mariano em série com surto**: com "
      f"{ref['n_janelas']} janelas e cauda pesada, o teste por horizonte quase nunca passa na "
      "dengue, inclusive onde os dois IC excluem zero.")
    w("- **Sem teste de mudança de regime** em cardiovascular e dengue. A comparação é toda "
      "dentro do período estável; só o OPT tem teste fora do regime, no manuscrito.")
    w("")

    # ---------------------------------------------------------------- reproducao
    w("## 11. Reprodução")
    w("")
    w("As séries agregadas estão versionadas em `results/series/comp_*_2010_2019.csv`, sem "
      "identificação.")
    w("")
    w("```")
    w("make domains                          # benchmark, incerteza, critério e relatório")
    w("python scripts/write_domain_report.py # só este documento, a partir de results/")
    w("```")
    w("")
    w("`make domains` começa por `scripts/compare_domains.py`, que relê as séries de origem "
      "nos repositórios irmãos (`../cardiovascular-timeseries-prediction` e "
      "`../dengue-time-series`) e aborta se faltar mês na janela comum. Sem eles, os CSVs "
      "versionados bastam para rodar o resto.")

    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Gravado: {out}")


if __name__ == "__main__":
    main()
