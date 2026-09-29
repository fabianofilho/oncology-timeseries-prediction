"""O relatorio da LAB-120 sai inteiro de results/, sem numero digitado e sem buraco."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_relatorio_gera_sem_nan_e_com_as_onze_secoes(tmp_path):
    saida = tmp_path / "relatorio.md"
    subprocess.run(
        [sys.executable, "scripts/write_domain_report.py", "--output", str(saida)],
        cwd=ROOT, check=True, capture_output=True,
    )
    txt = saida.read_text(encoding="utf-8")
    assert not re.search(r"\bnan\b", txt, re.IGNORECASE)
    for n in range(1, 12):
        assert f"## {n}. " in txt
    # a geografia da dengue precisa estar declarada: era a diferenca que faltava
    assert "Município de São Paulo" in txt
