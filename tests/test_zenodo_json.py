"""O .zenodo.json repete os autores de paper/autoria.json: os dois não podem divergir."""
from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_autores_iguais_ao_autoria():
    zenodo = json.loads((RAIZ / ".zenodo.json").read_text(encoding="utf-8"))
    autoria = json.loads((RAIZ / "paper" / "autoria.json").read_text(encoding="utf-8"))
    esperado = [
        {
            "name": f"{a['sobrenome']}, {a['nome']}",
            "affiliation": a["afiliacao"],
            "orcid": a["orcid"],
        }
        for a in autoria["autores"]
    ]
    assert zenodo["creators"] == esperado
