"""Idade do SIM, taxa padronizada por idade e tendencia por Prais-Winsten (LAB-182).

Tudo aqui foi declarado na LAB-182 antes de rodar:

- idade decodificada do campo IDADE do SIM, que tem tres digitos: o primeiro e a
  unidade (0 a 3 = menos de um ano, 4 = anos, 5 = cem anos ou mais, com o resto somado
  a 100, 9 = ignorado) e os dois ultimos, o valor;
- padronizacao direta pela populacao mundial de Segi modificada por Doll, a mesma do
  INCA e de Reis 2026, em 17 faixas de 5 anos com 80+ fechando (80-84 e 85+ somados);
- tendencia por regressao de Prais-Winsten do log10 da taxa contra o ano, com
  APC = (10^b - 1) x 100 e IC95% pela t com n - 2 graus de liberdade.

Ver tests/test_demografia.py.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

FAIXAS = [
    "0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44",
    "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80+",
]

# Populacao padrao mundial (Segi 1960, modificada por Doll 1966), por 100.000.
# As faixas 80-84 e 85+ (500 cada) somam 1.000 em 80+, porque o denominador do
# DataSUS fecha em 80 anos ou mais.
SEGI = dict(zip(FAIXAS, [
    12000, 10000, 9000, 9000, 8000, 8000, 6000, 6000, 6000,
    6000, 5000, 4000, 4000, 3000, 2000, 1000, 1000,
]))


def idade_em_anos(codigo: pd.Series) -> pd.Series:
    """Converte o campo IDADE do SIM em anos completos; ignorado vira NaN.

    Aceita o codigo como texto ou numero. Lido como numero, "012" vira 12: por isso
    qualquer valor abaixo de 400 e tratado como menos de um ano.
    """
    num = pd.to_numeric(codigo, errors="coerce")
    anos = pd.Series(np.nan, index=codigo.index, dtype=float)
    anos[(num >= 0) & (num < 400)] = 0.0
    em_anos = (num >= 400) & (num < 500)
    anos[em_anos] = num[em_anos] - 400
    cem_mais = (num >= 500) & (num < 600)
    anos[cem_mais] = num[cem_mais] - 400
    return anos


def faixa_etaria(anos: pd.Series) -> pd.Series:
    """Faixa de 5 anos de FAIXAS; NaN continua NaN."""
    idx = np.minimum(np.floor(anos / 5), len(FAIXAS) - 1)
    out = pd.Series(pd.NA, index=anos.index, dtype="object")
    ok = anos.notna()
    out[ok] = [FAIXAS[int(i)] for i in idx[ok]]
    return out


def taxa_padronizada(obitos: pd.Series, populacao: pd.Series) -> float:
    """Taxa por 100.000 padronizada pelo metodo direto, pesos de SEGI.

    `obitos` e `populacao` indexados por faixa de FAIXAS. Faixa sem obito conta zero;
    faixa sem populacao derruba, porque a taxa daquela faixa nao existe.
    """
    pop = populacao.reindex(FAIXAS)
    if pop.isna().any() or (pop <= 0).any():
        raise ValueError(f"populacao ausente ou zero em {list(pop[pop.isna() | (pop <= 0)].index)}")
    obs = obitos.reindex(FAIXAS).fillna(0)
    pesos = pd.Series(SEGI)
    return float(((obs / pop) * pesos).sum() / pesos.sum() * 100_000)


@dataclass(frozen=True)
class Tendencia:
    """Resultado de Prais-Winsten sobre log10(y) contra o ano."""

    apc: float
    ic_low: float
    ic_high: float
    b: float
    se: float
    rho: float
    n: int

    @property
    def sentido(self) -> str:
        """'aumento', 'queda' ou 'estavel', pelo IC95% do APC."""
        if self.ic_low > 0:
            return "aumento"
        if self.ic_high < 0:
            return "queda"
        return "estavel"


def prais_winsten(anos: np.ndarray, y: np.ndarray, max_iter: int = 100, tol: float = 1e-8) -> Tendencia:
    """Regressao de Prais-Winsten de log10(y) contra o ano, AR(1) iterado.

    Diferente de Cochrane-Orcutt, mantem a primeira observacao, escalada por
    sqrt(1 - rho^2); com 10 a 14 pontos anuais, perder um ponto pesa.
    """
    anos = np.asarray(anos, dtype=float)
    y = np.log10(np.asarray(y, dtype=float))
    n = len(y)
    if n < 4:
        raise ValueError("Prais-Winsten precisa de pelo menos 4 pontos")
    x = anos - anos.mean()
    X = np.column_stack([np.ones(n), x])

    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    rho = 0.0
    for _ in range(max_iter):
        e = y - X @ beta
        novo = float(np.sum(e[1:] * e[:-1]) / np.sum(e[:-1] ** 2))
        novo = float(np.clip(novo, -0.99, 0.99))
        f = np.sqrt(1 - novo ** 2)
        Xs = np.vstack([f * X[0], X[1:] - novo * X[:-1]])
        ys = np.concatenate([[f * y[0]], y[1:] - novo * y[:-1]])
        beta = np.linalg.lstsq(Xs, ys, rcond=None)[0]
        convergiu = abs(novo - rho) < tol
        rho = novo
        if convergiu:
            break

    res = ys - Xs @ beta
    gl = n - 2
    s2 = float(res @ res / gl)
    cov = s2 * np.linalg.inv(Xs.T @ Xs)
    b, se = float(beta[1]), float(np.sqrt(cov[1, 1]))
    t = stats.t.ppf(0.975, gl)
    apc = lambda v: (10 ** v - 1) * 100  # noqa: E731
    return Tendencia(apc(b), apc(b - t * se), apc(b + t * se), b, se, rho, n)
