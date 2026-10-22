"""Perturbacoes do estudo de simulacao (LAB-237).

Desenho registrado na issue antes de rodar (comentario de 19/10/2026, aprovado pelo
Fabiano em 22/10). Pergunta: em que condicoes os modelos novos se separam dos simples.
A serie e a real do OPT (2010-2019) e as janelas de teste sao as mesmas 55 do artigo.

Onde cada perturbacao entra (escolha registrada, nao muda depois de ver resultado):
- treino curto: janela deslizante com os ultimos k meses; nada e perturbado.
- faltantes: so no treino. A mascara e sorteada uma vez por replica sobre os meses do
  calendario; cada janela interpola o seu recorte de treino usando so o treino; a verdade
  do teste fica a original.
- quebra de nivel, mes atipico e ruido: na serie inteira, e a verdade muda junto.

Ver tests/test_simulacao.py.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

# Niveis registrados na LAB-237. A ordem importa so para a apresentacao.
CENARIOS: dict[str, list[float]] = {
    "treino_curto": [24, 36, 48],
    "faltantes": [0.05, 0.10, 0.20],
    "quebra": [0.05, -0.05, 0.10, -0.10],
    "atipico": [0.20],
    "ruido": [0.02, 0.05, 0.10],
}
# Cenarios sem sorteio rodam uma replica so.
DETERMINISTICOS = {"treino_curto"}
# Faixa de posicoes (0 = jan/2010) onde a quebra e o mes atipico podem cair.
POS_MIN, POS_MAX = 36, 108


def semente(cenario: str, nivel: float, replica: int) -> int:
    """Semente estavel entre maquinas e versoes do Python (hash() do Python nao e)."""
    chave = f"lab237|{cenario}|{nivel:g}|{replica}".encode()
    return int.from_bytes(hashlib.sha256(chave).digest()[:4], "big")


def mascara(index: pd.DatetimeIndex, frac: float, rng: np.random.Generator) -> pd.DatetimeIndex:
    """Meses mascarados (MCAR), sorteados uma vez por replica sobre o calendario todo."""
    n = int(round(frac * len(index)))
    pos = rng.choice(len(index), size=n, replace=False)
    return index[np.sort(pos)]


def aplica_faltantes(train: pd.Series, meses: pd.DatetimeIndex) -> pd.Series:
    """Apaga os meses mascarados do treino e interpola usando so o proprio treino.

    Interpolacao linear no tempo; nas pontas, repete o valor conhecido mais proximo.
    Nenhum valor fora do recorte de treino entra na conta.
    """
    t = train.astype(float).copy()
    t[t.index.isin(meses)] = np.nan
    if t.isna().all():
        raise ValueError("treino inteiro mascarado")
    return t.interpolate(method="time", limit_direction="both")


def quebra(serie: pd.Series, delta: float, rng: np.random.Generator) -> tuple[pd.Series, int]:
    """Mudanca de nivel permanente de `delta` (fracao) a partir de um mes sorteado."""
    t = int(rng.integers(POS_MIN, POS_MAX + 1))
    s = serie.astype(float).copy()
    s.iloc[t:] = s.iloc[t:] * (1.0 + delta)
    return s, t


def atipico(serie: pd.Series, frac: float, rng: np.random.Generator) -> tuple[pd.Series, int]:
    """Um mes isolado multiplicado por 1 + frac."""
    t = int(rng.integers(POS_MIN, POS_MAX + 1))
    s = serie.astype(float).copy()
    s.iloc[t] = s.iloc[t] * (1.0 + frac)
    return s, t


def ruido(serie: pd.Series, cv: float, rng: np.random.Generator) -> pd.Series:
    """Ruido multiplicativo log-normal com media 1 e coeficiente de variacao `cv`."""
    sigma = np.sqrt(np.log1p(cv**2))
    fator = rng.lognormal(mean=-(sigma**2) / 2.0, sigma=sigma, size=len(serie))
    return serie.astype(float) * fator


def prepara(serie: pd.Series, cenario: str, nivel: float, replica: int) -> dict:
    """Serie de trabalho e perturbacao de treino de uma replica.

    Devolve {"serie": serie que fornece treino E verdade, "faltantes": meses mascarados
    ou None, "max_train": k ou None, "posicao": mes da quebra ou do atipico ou None}.
    """
    if cenario not in CENARIOS and cenario != "controle":
        raise ValueError(f"cenario desconhecido: {cenario}")
    rng = np.random.default_rng(semente(cenario, nivel, replica))
    out = {"serie": serie.astype(float), "faltantes": None, "max_train": None, "posicao": None}
    if cenario == "treino_curto":
        out["max_train"] = int(nivel)
    elif cenario == "faltantes":
        out["faltantes"] = mascara(serie.index, nivel, rng)
    elif cenario == "quebra":
        out["serie"], out["posicao"] = quebra(serie, nivel, rng)
    elif cenario == "atipico":
        out["serie"], out["posicao"] = atipico(serie, nivel, rng)
    elif cenario == "ruido":
        out["serie"] = ruido(serie, nivel, rng)
    return out
