"""As referencias da CSP saem numeradas na ordem em que aparecem no texto.

Antes, os numeros eram digitados no texto e a lista seguia outra ordem (o texto
citava 5, 7, 6, 4, 1, 2, 3), o que a CSP nao aceita. Agora o texto cita por
chave e o numero vem da primeira aparicao.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

docx = pytest.importorskip("docx")

ROOT = Path(__file__).resolve().parent.parent


def _carrega_csp():
    spec = importlib.util.spec_from_file_location(
        "build_csp_submission", ROOT / "scripts" / "build_csp_submission.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sobrescritos(p):
    return [r.text for r in p.runs if r.font.superscript]


def test_numero_segue_primeira_aparicao_e_repete_na_volta():
    csp = _carrega_csp()
    p = docx.Document().add_paragraph()
    ordem: list[str] = []
    csp.cite_runs(p, "a [@hyndman2006], b [@collins2024], c [@hyndman2006].", ordem)
    assert ordem == ["hyndman2006", "collins2024"]
    assert _sobrescritos(p) == ["1", "2", "1"]
    assert p.text == "a1, b2, c1."


def test_chave_desconhecida_derruba_o_build():
    csp = _carrega_csp()
    p = docx.Document().add_paragraph()
    with pytest.raises(KeyError):
        csp.cite_runs(p, "texto [@inexistente2099].", [])


def test_pacote_real_cita_todas_as_referencias_em_ordem():
    csp = _carrega_csp()
    import json

    v = json.loads((ROOT / "paper" / "verified_numbers.json").read_text(encoding="utf-8"))
    doc, _ = csp.build_texto(v)
    assert sorted(csp.CITADAS) == sorted(csp.REFERENCES)
    numeros = [
        int(x)
        for par in doc.paragraphs
        for r in par.runs
        if r.font.superscript
        for x in r.text.split(",")
    ]
    # cada numero novo e exatamente o proximo; repeticoes podem voltar a qualquer um anterior
    maior = 0
    for n in numeros:
        assert n <= maior + 1
        maior = max(maior, n)
    assert maior == len(csp.REFERENCES)


def test_citacao_multipla_numera_cada_chave():
    csp = _carrega_csp()
    p = docx.Document().add_paragraph()
    ordem: list[str] = []
    csp.cite_runs(p, "x [@hyndman2006]. y [@collins2024,@hyndman2006].", ordem)
    assert _sobrescritos(p) == ["1", "2,1"]
