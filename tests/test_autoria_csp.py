"""O bloco de autoria sai de paper/autoria.json: campo vazio vira [PENDING], campo cheio vira texto.

A CSP pede autores, ORCID e contribuicoes no formulario de submissao; o texto e a ficha
(build/csp/CSP_formulario_submissao.md) saem da mesma fonte.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("docx")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_csp_submission as csp  # noqa: E402

V = json.loads((ROOT / "paper" / "verified_numbers.json").read_text(encoding="utf-8"))
MODELO = csp.carrega_autoria()


def pendencias(autoria: dict) -> str:
    doc, _ = csp.build_texto(V, autoria)
    return "\n".join(p.text for p in doc.paragraphs)


def preenchida() -> dict:
    a = copy.deepcopy(MODELO)
    a["lista_fechada"] = True
    a["autores"][0]["contribuicao"] = "conceived the study, ran the analysis and wrote the text"
    a["financiamento"] = "This study received no specific funding."
    a["conflitos"] = "The authors declare no conflict of interest."
    a["agradecimentos"] = "We thank a colleague for reading the manuscript."
    return a


def test_modelo_versionado_mantem_os_cinco_pending():
    assert pendencias(MODELO).count("[PENDING:") == 5


def test_autoria_completa_zera_os_pending_e_entra_no_texto():
    txt = pendencias(preenchida())
    assert "[PENDING:" not in txt
    assert "Fabiano Novaes Barcellos Filho" in txt
    assert "conceived the study, ran the analysis and wrote the text." in txt
    assert "This study received no specific funding." in txt


def test_autor_sem_orcid_volta_a_pendencia():
    a = preenchida()
    a["autores"].append({"nome": "Ana", "sobrenome": "Teste", "afiliacao": "X", "pais": "Brazil",
                         "orcid": "", "contribuicao": "reviewed the text"})
    assert "author 2: orcid" in pendencias(a)


def test_ficha_nao_carrega_email_sem_o_arquivo_privado():
    ficha = csp.ficha_formulario(preenchida(), None, csp.TITULO, "abstract", "a; b; c", "ethics")
    assert "[PENDING: e-mail]" in ficha
    assert "@" not in ficha.split("## Passo 4")[0]
