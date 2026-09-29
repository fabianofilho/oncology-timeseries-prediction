#!/usr/bin/env python3
"""Populacao residente do Estado de SP por ano, sexo e faixa de 5 anos (LAB-182).

Fonte: Estudo de Estimativas Populacionais por Municipio, Idade e Sexo 2000-2025,
DataSUS/RIPSA com dados basicos do IBGE, no TabNet (ibge/cnv/popsvs2024br.def). A
versao anterior (popsvsbr.def) para em 2021; esta cobre 2010-2023 inteiro com uma
fonte so, que e o que a LAB-182 declarou.

Uma consulta por ano, faixa etaria nas linhas e sexo nas colunas. As faixas precisam
somar o TOTAL que o proprio TabNet devolve, senao o script aborta: e a checagem de que
a tabela foi lida inteira.

Uso:
    python scripts/fetch_population_tabnet.py
"""
from __future__ import annotations

import argparse
import html as H
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from onco_timeseries.demografia import FAIXAS

URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?ibge/cnv/popsvs2024br.def"
UF_SAO_PAULO = "25"  # codigo do TabNet, nao o do IBGE


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Populacao de SP por sexo e faixa, TabNet")
    p.add_argument("--ano-inicio", type=int, default=2010)
    p.add_argument("--ano-fim", type=int, default=2023)
    p.add_argument("--output", default="results/populacao_sp_sexo_faixa_2010_2023.csv")
    p.add_argument("--timeout", type=int, default=180)
    return p.parse_args()


def rotulo_para_faixa(rotulo: str) -> str:
    """'De 0 a 4 anos' -> '0-4'; 'De 80 anos ou mais' -> '80+'."""
    nums = [int(x) for x in re.findall(r"\d+", rotulo)]
    return "80+" if "mais" in rotulo else f"{nums[0]}-{nums[1]}"


def consulta(ano: int, timeout: int) -> pd.DataFrame:
    campos = [
        ("Linha", "Faixa_Etária_2"), ("Coluna", "Sexo"), ("Incremento", "População_residente"),
        ("Arquivos", f"pop{ano % 100:02d}.dbf"), ("SUnidade_da_Federação", UF_SAO_PAULO),
        ("formato", "table"), ("mostre", "Mostra"),
    ]
    data = urllib.parse.urlencode(campos, encoding="latin-1").encode("latin-1")
    req = urllib.request.Request(URL, data=data, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        bruto = r.read().decode("latin-1")
    texto = re.sub(r"<script.*?</script>", " ", bruto, flags=re.S | re.I)
    texto = H.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", texto)))
    if "TOTAL" not in texto:
        raise SystemExit(f"[ERRO] {ano}: resposta do TabNet sem tabela; o formulario mudou?")

    num = r"([\d\.]+)"
    tot = re.search(rf"TOTAL {num} {num} {num}", texto)
    linhas = re.findall(rf"(De \d+ a \d+ anos|De 80 anos ou mais) {num} {num} {num}", texto)
    if not tot or len(linhas) != len(FAIXAS):
        raise SystemExit(f"[ERRO] {ano}: esperava {len(FAIXAS)} faixas, li {len(linhas)}")
    i = lambda s: int(s.replace(".", ""))  # noqa: E731
    reg = []
    for rot, masc, fem, _ in linhas:
        f = rotulo_para_faixa(rot)
        reg += [(ano, "masc", f, i(masc)), (ano, "fem", f, i(fem))]
    df = pd.DataFrame(reg, columns=["ano", "sexo", "faixa", "populacao"])
    for sexo, col in (("masc", 1), ("fem", 2)):
        if df[df.sexo == sexo].populacao.sum() != i(tot.group(col)):
            raise SystemExit(f"[ERRO] {ano} {sexo}: faixas nao somam o TOTAL do TabNet")
    if sorted(df.faixa.unique(), key=FAIXAS.index) != FAIXAS:
        raise SystemExit(f"[ERRO] {ano}: faixas lidas nao batem com FAIXAS")
    return df


def main() -> None:
    args = parse_args()
    partes = []
    for ano in range(args.ano_inicio, args.ano_fim + 1):
        df = consulta(ano, args.timeout)
        tot = df.groupby("sexo").populacao.sum()
        print(f"{ano}: masc {tot['masc']:,} | fem {tot['fem']:,}")
        partes.append(df)
        time.sleep(1)
    out = Path(args.output)
    pd.concat(partes).to_csv(out, index=False)
    print(f"Gravado: {out}")


if __name__ == "__main__":
    main()
