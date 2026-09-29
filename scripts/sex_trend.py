#!/usr/bin/env python3
"""Tendencia da taxa de mortalidade por cancer de pulmao padronizada por idade, por sexo.

Aplica o plano registrado na LAB-182 antes de rodar:

- taxa padronizada pelo metodo direto, populacao mundial de Segi modificada por Doll;
- regressao de Prais-Winsten do log10 da taxa contra o ano, APC com IC95%;
- janela principal 2010-2019, sensibilidade 2010-2023;
- contraste: a mesma regressao sobre a contagem bruta;
- idade ignorada fora do numerador; se passar de 1%, sensibilidade com redistribuicao
  proporcional entre as faixas do mesmo ano e sexo;
- apoio a hipotese so se, na janela principal, APC feminino > 0 com IC excluindo zero
  E APC masculino < 0 com IC excluindo zero.

Entradas: results/sexo_obitos_anuais_faixa.csv (build_sex_series.py) e
results/populacao_sp_sexo_faixa_2010_2023.csv (fetch_population_tabnet.py).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from onco_timeseries.demografia import FAIXAS, prais_winsten, taxa_padronizada

JANELAS = {"principal": (2010, 2019), "sensibilidade": (2010, 2023)}
LIMIAR_IDADE_IGNORADA_PCT = 1.0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tendencia da taxa padronizada por sexo")
    p.add_argument("--obitos-csv", default="results/sexo_obitos_anuais_faixa.csv")
    p.add_argument("--pop-csv", default="results/populacao_sp_sexo_faixa_2010_2023.csv")
    p.add_argument("--desfecho", default="pulmao")
    p.add_argument("--taxas-output", default="results/sexo_taxas_pulmao.csv")
    p.add_argument("--report-output", default="results/sexo_tendencia_pulmao.json")
    return p.parse_args()


def taxas(ob: pd.DataFrame, pop: pd.DataFrame, redistribuir: bool) -> pd.DataFrame:
    linhas = []
    for (sexo, ano), g in ob.groupby(["sexo", "ano"]):
        por_faixa = g.set_index("faixa").obitos
        ign = int(por_faixa.get("ignorada", 0))
        conhecidos = por_faixa.reindex(FAIXAS).fillna(0)
        if redistribuir and ign:
            conhecidos = conhecidos * (conhecidos.sum() + ign) / conhecidos.sum()
        p = pop[(pop.sexo == sexo) & (pop.ano == ano)].set_index("faixa").populacao
        linhas.append({
            "sexo": sexo, "ano": int(ano),
            "obitos": int(por_faixa.sum()), "idade_ignorada": ign,
            "taxa_bruta": float(por_faixa.sum() / p.sum() * 100_000),
            "taxa_padronizada": taxa_padronizada(conhecidos, p),
        })
    return pd.DataFrame(linhas).sort_values(["sexo", "ano"])


def tendencias(tx: pd.DataFrame) -> dict:
    out = {}
    for sexo in ("fem", "masc"):
        for janela, (a, b) in JANELAS.items():
            d = tx[(tx.sexo == sexo) & tx.ano.between(a, b)]
            for medida in ("taxa_padronizada", "obitos"):
                t = prais_winsten(d.ano.to_numpy(), d[medida].to_numpy())
                out[f"{sexo}|{janela}|{medida}"] = {
                    "sexo": sexo, "janela": f"{a}-{b}", "medida": medida, "n": t.n,
                    "apc": round(t.apc, 3), "ic95": [round(t.ic_low, 3), round(t.ic_high, 3)],
                    "rho": round(t.rho, 3), "sentido": t.sentido,
                }
    return out


def veredito(tr: dict) -> dict:
    fem = tr["fem|principal|taxa_padronizada"]
    masc = tr["masc|principal|taxa_padronizada"]
    fem_sobe, masc_cai = fem["sentido"] == "aumento", masc["sentido"] == "queda"
    if fem_sobe and masc_cai:
        texto = "apoiada"
    elif fem_sobe or masc_cai:
        texto = "apoiada em parte"
    else:
        texto = "nao apoiada"
    return {"hipotese": texto, "feminino_sobe": fem_sobe, "masculino_cai": masc_cai,
            "regra": "LAB-182: janela 2010-2019, APC fem > 0 e APC masc < 0, ambos com IC95% "
                     "excluindo zero"}


def main() -> None:
    args = parse_args()
    ob = pd.read_csv(args.obitos_csv)
    ob = ob[ob.desfecho == args.desfecho]
    pop = pd.read_csv(args.pop_csv)

    tx = taxas(ob, pop, redistribuir=False)
    ign_pct = 100 * tx.idade_ignorada.sum() / tx.obitos.sum()
    tr = tendencias(tx)
    rel = {
        "desfecho": args.desfecho,
        "padronizacao": "direta, população mundial de Segi modificada por Doll, 17 faixas (80+)",
        "denominador": "DataSUS/RIPSA, estimativas por município, idade e sexo 2000-2025",
        "idade_ignorada_pct": round(float(ign_pct), 3),
        "tendencias": list(tr.values()),
        "veredito": veredito(tr),
    }
    if ign_pct > LIMIAR_IDADE_IGNORADA_PCT:
        tr_r = tendencias(taxas(ob, pop, redistribuir=True))
        rel["sensibilidade_redistribuicao"] = {"tendencias": list(tr_r.values()),
                                               "veredito": veredito(tr_r)}

    tx.round(4).to_csv(args.taxas_output, index=False)
    Path(args.report_output).write_text(json.dumps(rel, indent=2, ensure_ascii=False), encoding="utf-8")

    print(tx.pivot(index="ano", columns="sexo", values="taxa_padronizada").round(2).to_string())
    print(f"\nidade ignorada: {ign_pct:.3f}% dos obitos")
    for t in tr.values():
        print(f"{t['sexo']:<5}{t['janela']:<11}{t['medida']:<18} APC {t['apc']:>7.2f}% "
              f"[{t['ic95'][0]:.2f}; {t['ic95'][1]:.2f}]  {t['sentido']}")
    print(f"\nHipotese: {rel['veredito']['hipotese']}")
    print(f"Gravado: {args.report_output} e {args.taxas_output}")


if __name__ == "__main__":
    main()
