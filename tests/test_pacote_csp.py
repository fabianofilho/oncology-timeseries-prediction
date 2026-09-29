"""O pacote da CSP sai inteiro do JSON e passa no conferidor de numeros e estrutura.

Desde a aposentadoria do build_docx.py (2026-09-28), o pacote da CSP e a unica versao
do texto, e o check_docx_numbers.py confere ele.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("docx")
pytest.importorskip("PIL")

ROOT = Path(__file__).resolve().parent.parent


def test_pacote_gera_e_passa_no_conferidor(tmp_path):
    pasta = tmp_path / "csp"
    subprocess.run([sys.executable, "scripts/build_csp_submission.py", "--out", str(pasta)],
                   cwd=ROOT, check=True, capture_output=True)
    r = subprocess.run([sys.executable, "scripts/check_docx_numbers.py", "--dir", str(pasta)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
    assert "Todos os valores exigidos aparecem no pacote" in r.stdout
