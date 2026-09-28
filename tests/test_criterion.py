"""Regra do criterio pre-declarado, v1 (LAB-118) e v2 (LAB-135).

A v2 foi escrita na LAB-135 antes de ser aplicada; estes testes fixam a redacao de la,
caso a caso, para que ninguem ajuste a regra depois de ver um veredito.
"""
from __future__ import annotations

from onco_timeseries.criterion import (
    CONFIRMADO,
    DISCORDANTE,
    NAO_CONFIRMADO,
    Intervalo,
    veredito_v1,
    veredito_v2,
)

NEG = Intervalo(-1.0, -1.5, -0.5)   # A melhor que B, IC exclui zero
POS = Intervalo(1.0, 0.5, 1.5)      # A pior que B, IC exclui zero
ZERO = Intervalo(-0.1, -0.6, 0.4)   # IC contem zero


def test_confirmado_exige_as_duas_metricas_no_mesmo_sentido_e_dm():
    assert veredito_v2(NEG, NEG, 3) == CONFIRMADO
    assert veredito_v2(POS, POS, 6) == CONFIRMADO


def test_sem_dm_nao_confirma_mesmo_com_as_duas_metricas():
    assert veredito_v2(NEG, NEG, 2) == NAO_CONFIRMADO


def test_so_uma_metrica_exclui_zero_e_discordante_com_ou_sem_dm():
    # o caso da dengue: sMAPE ve empate, MAE ve diferenca
    assert veredito_v2(ZERO, NEG, 5) == DISCORDANTE
    assert veredito_v2(NEG, ZERO, 5) == DISCORDANTE
    assert veredito_v2(NEG, ZERO, 0) == DISCORDANTE


def test_sinais_opostos_sao_discordantes():
    assert veredito_v2(NEG, POS, 6) == DISCORDANTE


def test_nenhuma_metrica_exclui_zero_e_nao_confirmado():
    assert veredito_v2(ZERO, ZERO, 6) == NAO_CONFIRMADO


def test_v1_ignora_o_mae():
    assert veredito_v1(NEG, 3) is True
    assert veredito_v1(NEG, 2) is False
    assert veredito_v1(ZERO, 6) is False
