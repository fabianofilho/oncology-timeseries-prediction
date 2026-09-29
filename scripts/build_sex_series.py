#!/usr/bin/env python3
"""Series mensais por sexo e contagens anuais por sexo e faixa etaria (LAB-182).

A partir do microdado ja extraido (make extract-sim), gera:

- results/series/serie_onco_SP_{total,pulmao}_{masc,fem}_{2010-2023,2010-2019}.csv,
  no mesmo formato das series por sitio, para o benchmark;
- results/sexo_obitos_anuais_faixa.csv, obitos por ano, sexo, faixa etaria e
  desfecho, agregados e sem identificacao, para a taxa padronizada;
- results/sex_series_report.json, com a conciliacao: masculino + feminino +
  ignorado tem de dar o total do manuscrito, senao o script aborta.

A condicao de parada da LAB-119 vale aqui: serie com media mensal abaixo de 30 obitos
nao gera arquivo de benchmark.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from onco_timeseries.demografia import faixa_etaria, idade_em_anos

DESFECHOS = {
    "total": {"rotulo": "Neoplasias malignas", "cid": None},
    "pulmao": {"rotulo": "Traqueia, brônquios e pulmão", "cid": ["C33", "C34"]},
}
SEXOS = {"1": "masc", "2": "fem"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Series por sexo")
    p.add_argument("--raw-csv", default="data/raw/sim_onco_SP_2010-2023.csv")
    p.add_argument("--output-dir", default="results/series")
    p.add_argument("--prefix", default="serie_onco_SP")
    p.add_argument("--min-media-mensal", type=float, default=30.0)
    p.add_argument("--total-esperado", type=int, default=741_313,
                   help="Total de obitos do manuscrito; a soma por sexo tem de bater")
    p.add_argument("--anual-output", default="results/sexo_obitos_anuais_faixa.csv")
    p.add_argument("--report-output", default="results/sex_series_report.json")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    raw = pd.read_csv(args.raw_csv, dtype={"CAUSABAS": str, "DTOBITO": str, "SEXO": str,
                                            "IDADE": str}, low_memory=False)
    data = pd.to_datetime(raw["DTOBITO"].astype(str).str.strip(), format="%d%m%Y", errors="coerce")
    if data.isna().any():
        raise SystemExit(f"[ERRO] {int(data.isna().sum())} registros sem data valida")
    if len(raw) != args.total_esperado:
        raise SystemExit(f"[ERRO] microdado com {len(raw)} registros, esperado {args.total_esperado}")

    sexo = raw["SEXO"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    sexo = sexo.map(SEXOS)  # 0, 9 e vazio viram NaN: ignorado
    prefixo3 = raw["CAUSABAS"].astype(str).str.upper().str.strip().str[:3]
    mes = data.dt.to_period("M").dt.to_timestamp()
    anos = idade_em_anos(raw["IDADE"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True))
    faixa = faixa_etaria(anos)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rel: dict = {"total_microdado": int(len(raw)), "desfechos": {}}

    anual = []
    for chave, spec in DESFECHOS.items():
        no_desfecho = (pd.Series(True, index=raw.index) if spec["cid"] is None
                       else prefixo3.isin(spec["cid"]))
        n_des = int(no_desfecho.sum())
        n_ign_sexo = int((no_desfecho & sexo.isna()).sum())
        n_ign_idade = int((no_desfecho & anos.isna()).sum())
        d = {"rotulo": spec["rotulo"], "cid": spec["cid"], "obitos": n_des,
             "sexo_ignorado": n_ign_sexo, "idade_ignorada": n_ign_idade,
             "idade_ignorada_pct": round(100 * n_ign_idade / n_des, 3), "series": {}}
        soma_sexos = 0
        for cod, nome in SEXOS.items():
            m = no_desfecho & (sexo == nome)
            soma_sexos += int(m.sum())
            serie = (pd.DataFrame({"date": mes[m]}).groupby("date").size()
                     .rename("value").reset_index().sort_values("date"))
            media = float(serie.value.mean())
            s = {"obitos": int(m.sum()), "pontos": int(len(serie)), "media_mensal": round(media, 1),
                 "minimo_mensal": int(serie.value.min()), "maximo_mensal": int(serie.value.max()),
                 "incluido": media >= args.min_media_mensal}
            if s["incluido"]:
                base = f"{args.prefix}_{chave}_{nome}"
                serie.to_csv(out_dir / f"{base}_2010-2023.csv", index=False)
                pre = serie[serie.date < "2020-01-01"]
                pre.to_csv(out_dir / f"{base}_2010-2019.csv", index=False)
                s["pontos_pre"] = int(len(pre))
                s["media_mensal_pre"] = round(float(pre.value.mean()), 1)
            d["series"][nome] = s

            # idade ignorada fica como faixa propria: a taxa padronizada a exclui, e a
            # sensibilidade com redistribuicao proporcional precisa saber quantos sao
            por_faixa = (pd.DataFrame({"ano": data[m].dt.year, "faixa": faixa[m].fillna("ignorada")})
                         .groupby(["ano", "faixa"]).size().rename("obitos").reset_index())
            por_faixa["sexo"], por_faixa["desfecho"] = nome, chave
            anual.append(por_faixa)

        if soma_sexos + n_ign_sexo != n_des:
            raise SystemExit(f"[ERRO] {chave}: masc + fem + ignorado != total")
        rel["desfechos"][chave] = d

    if rel["desfechos"]["total"]["obitos"] != args.total_esperado:
        raise SystemExit("[ERRO] total por desfecho nao reproduz o manuscrito")

    pd.concat(anual)[["desfecho", "sexo", "ano", "faixa", "obitos"]].sort_values(
        ["desfecho", "sexo", "ano", "faixa"]).to_csv(args.anual_output, index=False)

    Path(args.report_output).write_text(json.dumps(rel, indent=2, ensure_ascii=False), encoding="utf-8")
    for chave, d in rel["desfechos"].items():
        print(f"{chave}: {d['obitos']} obitos | sexo ignorado {d['sexo_ignorado']} | "
              f"idade ignorada {d['idade_ignorada']} ({d['idade_ignorada_pct']}%)")
        for nome, s in d["series"].items():
            print(f"   {nome}: {s['obitos']} obitos, media mensal {s['media_mensal']}, "
                  f"incluido={s['incluido']}")
    print(f"Gravado: {args.report_output} e {args.anual_output}")


if __name__ == "__main__":
    main()
