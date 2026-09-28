"""Criterio pre-declarado de diferenca confirmada entre dois modelos.

Versao 1 (LAB-118, fixada antes de qualquer numero): IC95% bootstrap da diferenca de
sMAPE exclui zero E Diebold-Mariano com correcao de Harvey, sobre erro absoluto,
abaixo de 0,05 em 3 ou mais dos 6 horizontes.

Versao 2 (LAB-135, registrada na issue em 2026-09-28 antes de ser aplicada): soma a
exigencia de que o IC95% da diferenca de MAE tambem exclua zero, com o mesmo sinal.
O motivo e a dengue: com 52% dos meses abaixo de 1.000 casos, o denominador do sMAPE
e dominado pelos vales e a metrica declara empate onde o MAE ve a maior diferenca da
tabela. Quando as duas metricas discordam, o par e "discordante", que e resultado a
reportar e nunca vitoria nem empate.

A versao 1 continua calculada ao lado, para reproduzir os numeros ja publicados.

Ver tests/test_criterion.py.
"""
from __future__ import annotations

from dataclasses import dataclass

ALPHA = 0.05
MIN_HORIZONS = 3

CONFIRMADO = "confirmado"
DISCORDANTE = "discordante"
NAO_CONFIRMADO = "nao_confirmado"


@dataclass(frozen=True)
class Intervalo:
    """Diferenca pontual e IC95% bootstrap de uma metrica, modelo A menos modelo B."""

    diff: float
    low: float
    high: float

    @property
    def exclui_zero(self) -> bool:
        return self.low > 0 or self.high < 0

    @property
    def sinal(self) -> int:
        """Sinal do IC quando ele exclui zero; 0 quando contem zero."""
        if self.high < 0:
            return -1
        if self.low > 0:
            return 1
        return 0


def veredito_v1(smape: Intervalo, n_dm_sig: int) -> bool:
    """Regra da LAB-118: IC do sMAPE exclui zero e DM em >= 3 horizontes."""
    return smape.exclui_zero and n_dm_sig >= MIN_HORIZONS


def veredito_v2(smape: Intervalo, mae: Intervalo, n_dm_sig: int) -> str:
    """Regra da LAB-135, na redacao registrada na issue.

    confirmado: IC de sMAPE e de MAE excluem zero, com o mesmo sinal, e DM passa.
    discordante: so um dos dois IC exclui zero, ou os dois excluem com sinais opostos.
    nao_confirmado: nenhum IC exclui zero, ou os dois excluem no mesmo sentido sem DM.
    """
    a, c = smape.exclui_zero, mae.exclui_zero
    if a != c or (a and c and smape.sinal != mae.sinal):
        return DISCORDANTE
    if a and c and n_dm_sig >= MIN_HORIZONS:
        return CONFIRMADO
    return NAO_CONFIRMADO
