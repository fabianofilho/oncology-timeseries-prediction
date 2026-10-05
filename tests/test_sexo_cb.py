"""A Comunicacao Breve por sexo (LAB-182) sai inteira de results/ e cabe nos limites da CSP."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

docx = pytest.importorskip("docx")
pytest.importorskip("matplotlib")

ROOT = Path(__file__).resolve().parent.parent


def test_comunicacao_breve_gera_dentro_dos_limites(tmp_path):
    r = subprocess.run([sys.executable, "scripts/build_sexo_cb.py", "--out", str(tmp_path)],
                       cwd=ROOT, capture_output=True, text=True,
                       env={"PYTHONPATH": "src", "PATH": ""})
    assert r.returncode == 0, r.stderr
    assert "EXCEDE" not in r.stdout
    doc = docx.Document(str(tmp_path / "CB_texto.docx"))
    nums = [int(x) for p in doc.paragraphs for run in p.runs if run.font.superscript
            for x in run.text.split(",")]
    maior = 0
    for n in nums:
        assert n <= maior + 1
        maior = max(maior, n)
    assert (tmp_path / "figures" / "Figure1.png").exists()
