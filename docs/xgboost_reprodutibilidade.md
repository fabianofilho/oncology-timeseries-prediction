# O XGBoost depende do ambiente, mas o valor publicado reproduz

Estado: resolvido para este projeto, com uma ressalva registrada.

Auditoria feita em 2026-09-23, depois que o projeto cardiovascular encontrou sete valores
distintos de sMAPE para o mesmo código e a mesma série, só trocando versão de biblioteca e
número de threads, sem conseguir reproduzir o número que estava publicado lá.

## O valor publicado reproduz

Rodando só o XGBoost na configuração exata do benchmark full (série de 2010-2019, 55
janelas, horizonte 6, treino mínimo 60):

| | sMAPE |
|---|---:|
| Valor em `results/benchmark_onco_SP_2010_2019_full_metrics.csv` | 3.112688870260289 |
| Reproduzido em 2026-09-23 | 3.112688870260289 |

Diferença absoluta `0.000e+00`, e as 330 previsões batem ponto a ponto com diferença
máxima `0.000e+00`. Diferente do cardiovascular, aqui o número publicado é reproduzível.

## Mas ele depende do número de threads

Com a versão fixa em 3.4.1, nesta máquina, variando apenas `n_jobs`:

| `n_jobs` | sMAPE | Diferença vs publicado |
|---|---:|---:|
| 1 | 3.120290 | +0.0076 |
| 2 | 3.092740 | -0.0199 |
| 4 | 3.124732 | +0.0120 |
| 8 | 3.107879 | -0.0048 |
| 12 | 3.112689 | 0 |
| default (-1) | 3.112689 | 0 |

Amplitude de **0.032 pp**. O valor publicado corresponde a `n_jobs=-1` numa máquina de 12
núcleos lógicos, que é onde `-1` resolve para 12. Numa máquina com outro número de núcleos,
o mesmo código com a mesma versão dá outro número.

O CatBoost não tem esse comportamento e não foi alterado.

## Por que isso não muda nenhuma conclusão

A amplitude de 0.032 pp precisa ser lida contra a incerteza já medida, não contra zero:

- O IC95% do XGBoost é [2.855, 3.386], largura de 0.53 pp. A variação por thread é 6% dessa
  largura.
- O XGBoost está no grupo de baixo, e nenhuma comparação dele contra CatBoost
  (diferença -0.084, IC [-0.219, 0.041]) ou contra o ingênuo sazonal (diferença -0.113,
  IC [-0.342, 0.113]) é confirmada pelo critério pré-declarado. Deslocar o XGBoost em
  0.032 pp em qualquer direção não aproxima nenhum desses pares do limiar.
- A comparação que o critério confirma, SARIMA contra XGBoost, tem diferença de -1.598 com
  DM abaixo de 0,05 em 6 de 6 horizontes. Está a cinquenta vezes a amplitude observada.

Ou seja, o achado do manuscrito, de que o boosting não se distingue do baseline trivial,
não depende de qual máquina rodou.

## O que foi feito

- `requirements-optional.txt` fixa `xgboost==3.4.1` em vez de `>=2.0.0`.
- Este documento registra que fixar a versão **não basta**: a contagem de núcleos move o
  resultado sozinha, e quem reproduzir numa máquina com outro número de núcleos deve esperar
  diferença da ordem de 0.03 pp no XGBoost.

## Ambiente que produziu o valor publicado

```json
{
  "xgboost": "3.4.1",
  "numpy": "2.5.2",
  "pandas": "2.3.3",
  "skforecast": "0.23.0",
  "python": "3.12.10",
  "so": "Windows 11",
  "cpu_count": 12
}
```

## O que continua em aberto

Não testamos outras versões do XGBoost nesta série. O cardiovascular mostrou amplitude de
cerca de 0.15 pp entre versões, maior que a amplitude por threads, então a comparação entre
versões aqui provavelmente daria um espalhamento maior que os 0.032 pp medidos. Como o valor
publicado reproduz na versão fixada, isso não bloqueia nada, mas também não está medido.
