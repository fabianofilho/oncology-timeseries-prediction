#!/usr/bin/env python3
"""Choque ou poder? Analise exploratoria da LAB-204, registrada na issue antes de rodar.

Nas 103 janelas da serie inteira o Prophet se separou de SARIMA e TimesFM. Este script
pergunta se isso vem do choque de 2020-2023 ou so do poder extra de 103 janelas contra 55.

0. Controle: as 55 janelas estaveis, filtradas das previsoes da serie inteira e
   renumeradas, tem de reproduzir par a par o veredito da analise principal nesta maquina
   (results/reproducao/criterion_verdict_mac10.json). Se nao reproduzir, para.
1. Teste principal: criterio v2 so nas 48 janelas de choque. Prophet confirmado (e com
   erro maior) contra SARIMA ou TimesFM: o poder sozinho nao explica.
2. Diferenca em diferencas da perda do Prophet contra cada um, choque menos estavel,
   bootstrap estratificado (B = 10.000, semente 20260818), em sMAPE e em MAE.
3. Descritivo: 6 janelas treinadas antes de 2020 contra 42 que treinam com a pandemia.

Veredito por par: "choque", "inconsistente" ou "indeterminado". Nunca "poder": o desenho
nao tem como mostrar isso diretamente. As 48 janelas sao um unico choque visto por janelas
sobrepostas; o resultado descreve esta pandemia nesta serie.

Saidas: results/choque_poder/ e docs/relatorio_choque_poder.md.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"
OUT = R / "choque_poder"
MODELOS = "seasonal_naive,linear_trend,sarima,prophet,timesfm,xgboost,catboost"
B, SEMENTE = 10_000, 20260818
RIVAIS = ["sarima", "timesfm"]
NOME = {"sarima": "SARIMA", "timesfm": "TimesFM", "prophet": "Prophet"}


def br(x: float, dec: int = 2) -> str:
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pares(caminho: Path) -> dict:
    return {frozenset(p["par"].split("_menos_")): p
            for p in json.loads(caminho.read_text(encoding="utf-8"))["pares"]}


def roda_criterio(pred: pd.DataFrame, nome: str) -> dict:
    """Renumera as janelas de 1 a n e roda incerteza e criterio sobre o subconjunto."""
    mapa = {w: i + 1 for i, w in enumerate(sorted(pred.window.unique()))}
    sub = pred.assign(window=pred.window.map(mapa))
    csv = OUT / f"{nome}_predictions.csv"
    sub.to_csv(csv, index=False)
    env = {"PYTHONPATH": str(ROOT / "src"), "PATH": ""}
    subprocess.run([sys.executable, "scripts/run_uncertainty.py", "--predictions-csv", str(csv),
                    "--models", MODELOS, "--n-boot", str(B), "--seed", str(SEMENTE),
                    "--output-prefix", str(OUT / f"uncertainty_{nome}")],
                   cwd=ROOT, check=True, capture_output=True, env=env)
    subprocess.run([sys.executable, "scripts/apply_criterion.py", "--pairwise-csv",
                    str(OUT / f"uncertainty_{nome}_pairwise_tests.csv"),
                    "--report-output", str(OUT / f"criterion_verdict_{nome}.json")],
                   cwd=ROOT, check=True, capture_output=True, env=env)
    return pares(OUT / f"criterion_verdict_{nome}.json")


def perdas_por_janela(pred: pd.DataFrame, modelo: str) -> pd.DataFrame:
    g = pred[pred.model == modelo].copy()
    g["smape"] = 200 * (g.y_pred - g.y_true).abs() / (g.y_true.abs() + g.y_pred.abs())
    g["ae"] = (g.y_pred - g.y_true).abs()
    return g.groupby("window")[["smape", "ae"]].mean()


def dif_em_dif(pred: pd.DataFrame, choque: set, estaveis: set, rival: str) -> dict:
    """(perda Prophet - perda rival) no choque menos o mesmo nas estaveis."""
    d = perdas_por_janela(pred, "prophet") - perdas_por_janela(pred, rival)
    dc, de = d.loc[sorted(choque)], d.loc[sorted(estaveis)]
    rng = np.random.default_rng(SEMENTE)
    ic, cc = rng.integers(0, len(dc), (B, len(dc))), rng.integers(0, len(de), (B, len(de)))
    out = {}
    for m in ("smape", "ae"):
        a, b = dc[m].to_numpy(), de[m].to_numpy()
        boot = a[ic].mean(axis=1) - b[cc].mean(axis=1)
        lo, hi = np.percentile(boot, [2.5, 97.5])
        out[m] = {"choque": float(a.mean()), "estavel": float(b.mean()),
                  "did": float(a.mean() - b.mean()), "ic95": [float(lo), float(hi)]}
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pred = pd.read_csv(R / "benchmark_onco_SP_2010_2023_full_predictions.csv", parse_dates=["date"])
    pred["train_end"] = pd.to_datetime(pred.train_end)
    choque = set(pred[pred.date >= "2020-01-01"].window.unique())
    estaveis = set(pred.window.unique()) - choque

    # 0. controle
    V_est = roda_criterio(pred[pred.window.isin(estaveis)], "estaveis")
    M = pares(R / "reproducao" / "criterion_verdict_mac10.json")
    difs = [sorted(k) for k in M if (M[k]["veredito"], M[k]["dm_abaixo_alpha"], M[k]["ic95"])
            != (V_est[k]["veredito"], V_est[k]["dm_abaixo_alpha"], V_est[k]["ic95"])]
    if difs:
        raise SystemExit(f"[ERRO] controle falhou, pares diferentes: {difs}")

    # 1. teste principal
    V_ch = roda_criterio(pred[pred.window.isin(choque)], "choque")
    # 2. diferenca em diferencas, 3. descritivo
    pre = set(pred[(pred.window.isin(choque)) & (pred.train_end < "2020-01-01")].window.unique())
    pos = choque - pre
    desc = {}
    for nome, ws in (("treino_pre_2020", pre), ("treino_com_pandemia", pos)):
        sub = pred[pred.window.isin(ws)]
        desc[nome] = {"janelas": len(ws),
                      "previsoes": int(sub[sub.model == "prophet"].shape[0]),
                      "previsoes_em_2020_ou_depois": int(sub[(sub.model == "prophet")
                                                             & (sub.date >= "2020-01-01")].shape[0]),
                      "smape": {
            m: float((200 * (g.y_pred - g.y_true).abs() / (g.y_true.abs() + g.y_pred.abs())).mean())
            for m, g in sub.groupby("model") if m in ("prophet", *RIVAIS)}}

    resultado = {"janelas": {"estaveis": len(estaveis), "choque": len(choque)},
                 "controle": "reproduz criterion_verdict_mac10 par a par", "pares": {},
                 "descritivo": desc}
    for rival in RIVAIS:
        p = V_ch[frozenset({"prophet", rival})]
        prophet_pior = (p["diferenca"] > 0) == p["par"].startswith("prophet_")
        principal = p["confirmado"] and prophet_pior
        did = dif_em_dif(pred, choque, estaveis, rival)
        did_pos = all(did[m]["ic95"][0] > 0 for m in ("smape", "ae"))
        did_neg = all(did[m]["ic95"][1] < 0 for m in ("smape", "ae"))
        if principal and did_pos:
            ver = "choque"
        elif principal and did_neg:
            ver = "inconsistente"
        else:
            ver = "indeterminado"
        resultado["pares"][rival] = {
            "estavel": {"veredito": V_est[frozenset({"prophet", rival})]["veredito"],
                        "dm": V_est[frozenset({"prophet", rival})]["dm_abaixo_alpha"]},
            "choque": {"veredito": p["veredito"], "dm": p["dm_abaixo_alpha"],
                       "prophet_pior": bool(prophet_pior)},
            "dif_em_dif": did, "veredito": ver}
    (R / "choque_poder_resumo.json").write_text(json.dumps(resultado, indent=2, ensure_ascii=False),
                                                encoding="utf-8")
    escreve_relatorio(resultado)
    for rival, r in resultado["pares"].items():
        print(f"Prophet x {rival}: estavel {r['estavel']} | choque {r['choque']} | "
              f"DiD sMAPE {r['dif_em_dif']['smape']['did']:.3f} {r['dif_em_dif']['smape']['ic95']} "
              f"| MAE {r['dif_em_dif']['ae']['did']:.1f} {r['dif_em_dif']['ae']['ic95']} -> {r['veredito']}")
    print("descritivo:", json.dumps(desc))


def escreve_relatorio(res: dict) -> None:
    rot = {"confirmado": "confirmado", "nao_confirmado": "não confirmado", "discordante": "discordante"}
    L = ["# Choque ou poder? Separação do Prophet na série inteira", "",
         "Análise **exploratória** da LAB-204, registrada na issue antes de rodar. Gerado por "
         "`scripts/choque_poder.py`; não editar à mão.", "",
         f"As {res['janelas']['choque']} janelas que preveem algum mês de 2020-2023 são um único "
         "choque visto por janelas sobrepostas: o resultado descreve esta pandemia nesta série, "
         "não uma regra geral.", "",
         "## Controle", "",
         f"As {res['janelas']['estaveis']} janelas estáveis, filtradas das previsões da série "
         "inteira, reproduzem par a par os 21 vereditos da análise principal nesta máquina.", "",
         "## Resultado por par", "",
         "| Par | Estáveis | Choque | Prophet erra mais no choque? | Dif. em dif. sMAPE [IC95%] | "
         "Dif. em dif. MAE [IC95%] | Veredito |",
         "|---|---|---|---|---|---|---|"]
    for rival, r in res["pares"].items():
        s, a = r["dif_em_dif"]["smape"], r["dif_em_dif"]["ae"]
        L.append(f"| Prophet x {NOME[rival]} | {rot[r['estavel']['veredito']]} ({r['estavel']['dm']}) | "
                 f"{rot[r['choque']['veredito']]} ({r['choque']['dm']}) | "
                 f"{'sim' if r['choque']['prophet_pior'] else 'não'} | "
                 f"{br(s['did'])} [{br(s['ic95'][0])}; {br(s['ic95'][1])}] | "
                 f"{br(a['did'], 1)} [{br(a['ic95'][0], 1)}; {br(a['ic95'][1], 1)}] | **{r['veredito']}** |")
    L += ["", "Entre parênteses, os horizontes com Diebold-Mariano abaixo de 0,05. A diferença em "
          "diferenças é a perda do Prophet menos a do rival nas janelas de choque, menos a mesma "
          "diferença nas estáveis, em pontos de sMAPE e em óbitos por mês.", "",
          "**Regra registrada:** choque se o Prophet é confirmado como pior nas 48 janelas *e* a "
          "diferença em diferenças tem IC positivo em sMAPE e em MAE; inconsistente se um aponta "
          "para o choque e o outro contradiz; indeterminado nos demais casos. \"Poder\" não é "
          "veredito possível.", "",
          "Para Prophet × SARIMA, a diferença em diferenças positiva é evidência secundária e não "
          "muda o veredito: nas 103 janelas esse par só se confirma juntando os dois grupos, então "
          "a separação dele não pode ser atribuída ao choque sozinho.", "",
          "## Descritivo, sem veredito", "",
          "| Janelas | n | Prophet | SARIMA | TimesFM |", "|---|---:|---:|---:|---:|"]
    for nome, rot_ in (("treino_pre_2020", "Treino até 2019"),
                       ("treino_com_pandemia", "Treino com meses de 2020 ou depois")):
        d = res["descritivo"][nome]
        rot_ += (f" ({d['previsoes_em_2020_ou_depois']} de {d['previsoes']} previsões em 2020 ou "
                 f"depois)")
        L.append(f"| {rot_} | {d['janelas']} | " + " | ".join(br(d["smape"][m]) for m in
                                                             ("prophet", "sarima", "timesfm")) + " |")
    pre = res["descritivo"]["treino_pre_2020"]
    L += ["", "sMAPE (%). **Este recorte não separa as duas explicações e não sustenta conclusão "
          "nenhuma.** No primeiro grupo, só "
          f"{pre['previsoes_em_2020_ou_depois']} das {pre['previsoes']} previsões caem em 2020; "
          "as demais são meses estáveis de 2019, o que explica erros bem abaixo dos medidos no "
          "primeiro semestre de 2020. O segundo grupo mistura duas coisas: treinar com meses da "
          "pandemia e prever a recuperação de 2021 a 2023. Com 6 janelas, nenhum teste se aplica.",
          "",
          "## Limitações", "",
          "- **Um único choque.** As janelas de 2020-2023 veem o mesmo evento; o resultado "
          "descreve esta pandemia nesta série.",
          "- **Janelas sobrepostas.** O bootstrap da diferença em diferenças reamostra janelas "
          "como independentes dentro de cada grupo, mas janelas vizinhas compartilham meses "
          "previstos. Os IC tendem a ser estreitos demais. É a mesma premissa da análise "
          "principal, mantida aqui por coerência e não alterada depois de ver o resultado.",
          "- **Exploratória.** Fora do plano original da LAB-204, registrada na issue antes de "
          "rodar. Não entra no manuscrito sem decisão do Fabiano.", ""]
    (ROOT / "docs" / "relatorio_choque_poder.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
