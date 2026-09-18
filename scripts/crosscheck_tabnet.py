#!/usr/bin/env python3
"""Confere a serie extraida contra o TabNet do DataSUS, a fonte oficial.

Esta e a unica checagem que valida a FONTE, e nao so a nossa leitura dela. As
demais validacoes do projeto conferem se o arquivo foi lido corretamente; esta
confere se o total que obtivemos e o mesmo que o Ministerio da Saude publica.

Detalhe que decide o resultado: os arquivos DO<UF><ANO>.dbc ficam na pasta
DORES do FTP, que e "DO por RESidencia". Logo o comparador correto no TabNet e
"Obitos p/Residenc", nao "Obitos p/Ocorrenc". Comparar contra ocorrencia produz
uma diferenca sistematica de cerca de 1,7%, que nao e erro de extracao e sim
duas definicoes diferentes de populacao.

Recorte usado no TabNet, equivalente ao filtro de prefixo C da extracao:
Grupo CID-10 de 22 a 36, que sao as neoplasias malignas C00-C97. Os grupos 37,
38 e 39 (in situ, benignas e de comportamento incerto, D00-D48) ficam de fora.

Uso:
    python scripts/crosscheck_tabnet.py
"""
from __future__ import annotations

import argparse
import html as H
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sim/cnv/obt10uf.def"

UF_SAO_PAULO = "25"          # codigo do TabNet, nao o do IBGE
GRUPOS_C00_C97 = [str(g) for g in range(22, 37)]
VISOES = {"residencia": "Óbitos_p/Residênc", "ocorrencia": "Óbitos_p/Ocorrênc"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Confere a serie contra o TabNet")
    p.add_argument("--ano-inicio", type=int, default=2010)
    p.add_argument("--ano-fim", type=int, default=2023)
    p.add_argument("--uf", default=UF_SAO_PAULO)
    p.add_argument("--verified-json", default="paper/verified_numbers.json")
    p.add_argument("--report-output", default="results/tabnet_crosscheck.json")
    p.add_argument("--timeout", type=int, default=180)
    return p.parse_args()


def consulta(conteudo: str, anos: range, uf: str, timeout: int) -> dict[int, int]:
    campos = [
        ("Linha", "Ano_do_Óbito"),
        ("Coluna", "--Não-Ativa--"),
        ("Incremento", conteudo),
        ("SUnidade_da_Federação", uf),
        ("formato", "table"),
        ("mostre", "Mostra"),
    ]
    campos += [("Arquivos", f"obtuf{a % 100:02d}.dbf") for a in anos]
    campos += [("SGrupo_CID-10", g) for g in GRUPOS_C00_C97]

    data = urllib.parse.urlencode(campos, encoding="latin-1").encode("latin-1")
    req = urllib.request.Request(URL, data=data, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        bruto = r.read().decode("latin-1")

    texto = re.sub(r"<script.*?</script>", " ", bruto, flags=re.S | re.I)
    texto = H.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", texto)))
    if "TOTAL" not in texto:
        raise SystemExit("[ERRO] resposta do TabNet sem tabela; o formulario mudou?")

    corpo = texto[texto.index("TOTAL"):]
    pares = re.findall(r"\b(20[0-9]\d)\s+([\d\.]+)", corpo)
    fora = {int(a): int(v.replace(".", "")) for a, v in pares}
    return {a: fora[a] for a in anos if a in fora}


def main() -> None:
    args = parse_args()
    anos = range(args.ano_inicio, args.ano_fim + 1)

    nosso_raw = json.loads((ROOT / args.verified_json).read_text(encoding="utf-8"))
    nosso = {int(k): int(v) for k, v in nosso_raw["coorte"]["obitos_por_ano"].items()}

    tabnet: dict[str, dict[int, int]] = {}
    for rotulo, conteudo in VISOES.items():
        tabnet[rotulo] = consulta(conteudo, anos, args.uf, args.timeout)
        if len(tabnet[rotulo]) != len(anos):
            raise SystemExit(f"[ERRO] TabNet devolveu {len(tabnet[rotulo])} anos para {rotulo}")
        time.sleep(1)

    print("Fonte: MS/SVSA/CGIAE, Sistema de Informacoes sobre Mortalidade (SIM), via TabNet.")
    print("Recorte: Sao Paulo, Grupo CID-10 22 a 36 (neoplasias malignas C00-C97).\n")
    print(f"{'ano':<6}{'nosso':>9}{'TabNet resid':>14}{'dif':>7}{'dif%':>8}"
          f"{'TabNet ocorr':>14}{'dif%':>8}")

    somas = {"nosso": 0, "residencia": 0, "ocorrencia": 0}
    divergentes = []
    for a in anos:
        m, r, o = nosso[a], tabnet["residencia"][a], tabnet["ocorrencia"][a]
        somas["nosso"] += m
        somas["residencia"] += r
        somas["ocorrencia"] += o
        if m != r:
            divergentes.append((a, m, r))
        print(f"{a:<6}{m:>9,}{r:>14,}{m - r:>7,}{100 * (m - r) / r:>7.2f}%"
              f"{o:>14,}{100 * (m - o) / o:>7.2f}%")

    sm, sr, so = somas["nosso"], somas["residencia"], somas["ocorrencia"]
    print(f"{'TOTAL':<6}{sm:>9,}{sr:>14,}{sm - sr:>7,}{100 * (sm - sr) / sr:>7.2f}%"
          f"{so:>14,}{100 * (sm - so) / so:>7.2f}%")

    print()
    if divergentes:
        print(f"DIVERGENCIA em {len(divergentes)} de {len(anos)} anos contra a visao de residencia:")
        for a, m, r in divergentes:
            print(f"  {a}: nosso {m:,}, TabNet {r:,}, diferenca {m - r:+,}")
    else:
        print(f"Bate exatamente com a visao de RESIDENCIA nos {len(anos)} anos, diferenca zero.")
        print(f"Contra a visao de OCORRENCIA a diferenca e de {100 * (sm - so) / so:.2f}%, "
              f"sistematica e esperada: sao definicoes diferentes de populacao.")

    saida = {
        "fonte": "MS/SVSA/CGIAE - SIM, via TabNet (tabnet.datasus.gov.br)",
        "recorte": {"uf_tabnet": args.uf, "grupos_cid10": GRUPOS_C00_C97,
                    "equivale_a": "C00-C97"},
        "nosso": nosso,
        "tabnet_residencia": tabnet["residencia"],
        "tabnet_ocorrencia": tabnet["ocorrencia"],
        "anos_divergentes_vs_residencia": [a for a, _, _ in divergentes],
        "confere": not divergentes,
        "dif_pct_vs_ocorrencia": round(100 * (sm - so) / so, 2),
    }
    p = ROOT / args.report_output
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(saida, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nGravado: {p}")
    raise SystemExit(0 if not divergentes else 1)


if __name__ == "__main__":
    main()
