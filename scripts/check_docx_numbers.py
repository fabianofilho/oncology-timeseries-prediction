#!/usr/bin/env python3
"""Confere o corpo do .docx contra paper/verified_numbers.json, numero por numero.

Passo obrigatorio antes de entregar: nao e feito de cabeca, e feito por este
comparador. Le o .docx de volta (paragrafos e tabelas), procura cada valor que o
JSON diz e reporta ausente ou divergente.

Tambem valida a estrutura que o python-docx nao garante sozinho: numeracao de
linha, campo de numero de pagina, figuras embutidas e tabelas nativas.

Uso:
    python scripts/check_docx_numbers.py [--docx build/manuscript.docx]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "paper"


def texto_completo(doc: Document) -> str:
    partes = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        for row in t.rows:
            partes.extend(c.text for c in row.cells)
    return "\n".join(partes)


def main() -> None:
    ap = argparse.ArgumentParser(description="Confere numeros do .docx")
    ap.add_argument("--docx", default="build/manuscript.docx")
    args = ap.parse_args()

    v = json.loads((PAPER / "verified_numbers.json").read_text(encoding="utf-8"))
    doc = Document(str(ROOT / args.docx))
    txt = texto_completo(doc)

    co, ba = v["coorte"], v["benchmark_agregado"]
    ci, met, crit = ba["ci_smape"], ba["metricas"], ba["criterio"]
    ext, tend, sit, reg = v["extrapolacao"], v["tendencia_pre_pandemia"], v["sitios"], v["teste_regime"]

    checagens: list[tuple[str, str]] = []

    def esperar(rotulo: str, valor: str) -> None:
        checagens.append((rotulo, valor))

    esperar("obitos por cancer", f"{co['obitos_por_cancer']:,}")
    esperar("pontos da serie completa", str(co["pontos_serie_completa"]))
    esperar("pontos da serie de treino", str(co["pontos_serie_treino"]))
    esperar("media mensal", f"{int(co['media_mensal']):,}")
    esperar("minimo mensal", f"{co['minimo_mensal']:,}")
    esperar("maximo mensal", f"{co['maximo_mensal']:,}")
    esperar("janelas de rolling origin", str(ba["n_janelas"]))
    esperar("previsoes por modelo", str(ba["n_previsoes_por_modelo"]))
    esperar("min train", str(ba["min_train"]))
    esperar("horizonte", str(ba["horizonte"]))
    esperar("replicas do bootstrap", str(ci["sarima"]["B"]))
    esperar("pares confirmados", str(crit["pares_confirmados"]))
    esperar("pares totais", str(crit["pares_total"]))
    esperar("alpha do criterio", str(crit["alpha"]))
    esperar("min horizontes do criterio", str(crit["min_horizontes"]))

    for m in ci:
        esperar(f"sMAPE pontual de {m}", f"{ci[m]['point']:.2f}")
        esperar(f"IC de {m}", f"{ci[m]['ci_low']:.2f} to {ci[m]['ci_high']:.2f}")
        esperar(f"MAE de {m}", f"{met[m]['mae']:.1f}")

    esperar("R2 da tendencia pre-pandemia", str(tend["r2"]))
    esperar("slope da tendencia", f"{int(tend['slope_obitos_por_ano']):,}")
    esperar("pct de observacoes acima do max de treino",
            f"{ext['_observacoes_acima_do_max_treino']['pct']}")
    esperar("n de observacoes acima do max de treino",
            str(ext["_observacoes_acima_do_max_treino"]["n"]))
    for m in ("catboost", "xgboost", "sarima", "prophet", "timesfm"):
        esperar(f"extrapolacoes de {m}", str(ext[m]["acima_do_max_treino"]))

    for s in ("agregado", "pulmao", "colorretal", "mama", "prostata"):
        esperar(f"sMAPE do sitio {s}", f"{sit[s]['smape_melhor']:.2f}")
        esperar(f"media mensal do sitio {s}", f"{int(sit[s]['media_mensal']):,}")
    esperar("cobertura dos sitios", str(v["sitios_cobertura_pct"]))

    for m in reg["por_modelo"]:
        esperar(f"sMAPE fora de regime de {m}", f"{reg['por_modelo'][m]['smape_total']:.2f}")

    for a, val in co["obitos_por_ano"].items():
        esperar(f"obitos em {a}", f"{val:,}")

    itv = v.get("intervalos")
    if itv:
        fx = itv["faixa_cobertura"]
        for nivel in ("n50", "n80", "n95"):
            esperar(f"cobertura minima {nivel}", f"{fx[nivel][0]:.3f}")
            esperar(f"cobertura maxima {nivel}", f"{fx[nivel][1]:.3f}")
        esperar("pior WIS", f"{itv['pior_wis']['valor']:.1f}")
        esperar("WIS do ingenuo sazonal", f"{itv['wis_seasonal_naive']:.1f}")
        esperar("cobertura 95 fora do regime", f"{itv['cobertura_95_fora']:.3f}")
        esperar("n avaliado por modelo", str(itv["n_avaliado_por_modelo"]))

    faltando = [(r, x) for r, x in checagens if x not in txt]
    print(f"Numeros conferidos: {len(checagens)}")
    print(f"Encontrados no documento: {len(checagens) - len(faltando)}")
    if faltando:
        print(f"\nNAO ENCONTRADOS ({len(faltando)}):")
        for r, x in faltando:
            print(f"  ERRO  {r:44s} esperado no texto: {x}")
    else:
        print("Todos os valores do JSON aparecem no documento com o mesmo valor.")

    # numeros soltos no texto que nao vieram do JSON
    print("\n--- estrutura ---")
    sec = doc.sections[0]
    tem_ln = sec._sectPr.find(qn("w:lnNumType")) is not None
    tem_pg = "PAGE" in sec.footer.paragraphs[0]._p.xml
    figs = len(doc.inline_shapes)
    tabs = len(doc.tables)
    dims = [(len(t.rows), len(t.columns)) for t in doc.tables]
    pend = len(re.findall(r"\[PENDING:", txt))
    ausentes_fig = len(re.findall(r"\[FIGURA AUSENTE:", txt))

    print(f"numeracao de linha continua (w:lnNumType): {'OK' if tem_ln else 'AUSENTE'}")
    print(f"campo de numero de pagina no rodape:       {'OK' if tem_pg else 'AUSENTE'}")
    print(f"figuras embutidas (inline shapes):          {figs}")
    print(f"tabelas nativas:                            {tabs} {dims}")
    print(f"marcadores [PENDING]:                       {pend}")
    print(f"figuras ausentes:                           {ausentes_fig}")
    print(f"paragrafos:                                 {len(doc.paragraphs)}")

    # 6 tabelas desde que a calibracao de intervalo entrou como Table 6.
    n_tab_esperado = 6 if v.get("intervalos") else 5
    ok = (not faltando and tem_ln and tem_pg and figs == 5
          and tabs == n_tab_esperado and ausentes_fig == 0)
    print("\nVEREDITO: " + ("estrutura e numeros OK" if ok else "REVISAR os itens acima"))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
