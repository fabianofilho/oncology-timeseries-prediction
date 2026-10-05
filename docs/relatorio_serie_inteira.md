# Sensibilidade: benchmark com a série inteira 2010-2023

Relatório da LAB-204. Gerado por `scripts/write_full_series_report.py` a partir de `results/`; não editar à mão. Plano registrado na issue antes de rodar.

## Resposta curta

**A conclusão do manuscrito não sobrevive à série inteira.** Nas 103 janelas, 15 dos 21 pares são confirmados. Todos os pares entre o grupo que representa a série e o que não representa seguem confirmados, mas o grupo de cima não fica empatado.

Dentro do grupo de cima, passam a ser confirmados: SARIMA x Prophet (3/6 horizontes); TimesFM x Prophet (6/6 horizontes). Continuam empatados: SARIMA x TimesFM. O degrau entre representar e não representar a série se mantém; o que deixa de valer é o empate dentro do grupo de cima. Pela regra registrada na LAB-204, isso conta como a conclusão não sobreviver.

Nas 48 janelas que preveem algum mês de 2020-2023, o erro de todos os modelos sobe (o menor é TimesFM, 3,13%, contra 1,51% do melhor no período estável).

## 1. Desenho

Série de 168 meses, o mesmo protocolo da análise principal (horizonte 6, treino mínimo 60, janela expansiva, passo 1), os mesmos sete modelos, bootstrap de janelas inteiras e critério v2. São 103 janelas: 55 com o horizonte inteiro antes de 2020, que são as mesmas da análise principal, e 48 que preveem algum mês de 2020-2023. A pandemia entra sem dummy nem tratamento.

**Consistência:** nas 55 janelas estáveis, as previsões batem com a reprodução da análise principal nesta máquina; a maior diferença é de 0,000 óbitos (CatBoost).

## 2. sMAPE (%) por modelo

| Modelo | 103 janelas | 55 estáveis | 48 com 2020-2023 |
|---|---:|---:|---:|
| SARIMA | 2,41 | 1,51 | 3,43 |
| TimesFM | 2,35 | 1,67 | 3,13 |
| Prophet | 2,77 | 1,70 | 3,99 |
| Tendência linear | 3,37 | 2,76 | 4,08 |
| CatBoost | 3,81 | 3,03 | 4,71 |
| XGBoost | 3,94 | 3,15 | 4,85 |
| Ingênuo sazonal | 4,17 | 3,23 | 5,24 |

## 3. sMAPE (%) por ano do mês previsto

| Ano | SARIMA | TimesFM | Prophet | Tendência linear | CatBoost | XGBoost | Ingênuo sazonal |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2015 | **1,73** | 1,98 | 2,10 | 2,76 | 3,72 | 4,37 | 4,75 |
| 2016 | **1,37** | 1,59 | 1,94 | 2,65 | 2,55 | 2,56 | 2,50 |
| 2017 | **1,09** | 1,27 | 1,17 | 2,18 | 2,64 | 2,61 | 2,67 |
| 2018 | **1,45** | 1,54 | 1,49 | 2,62 | 3,09 | 2,86 | 2,42 |
| 2019 | 2,11 | 1,94 | **1,85** | 3,57 | 3,02 | 3,51 | 4,42 |
| 2020 | 6,55 | 5,74 | 6,81 | 7,02 | 5,76 | **5,58** | 7,43 |
| 2021 | 2,46 | **2,27** | 3,11 | 3,11 | 3,37 | 3,41 | 6,02 |
| 2022 | 2,70 | **2,64** | 3,30 | 3,07 | 4,16 | 4,77 | 3,61 |
| 2023 | **1,98** | 2,04 | 3,10 | 3,24 | 6,55 | 6,41 | 3,70 |

Em negrito, o menor erro de cada ano.

## 4. Vereditos (critério v2)

| Par | Série inteira | Principal, esta máquina | Principal, publicado |
|---|---|---|---|
| Prophet x CatBoost (entre os grupos) | confirmado (6/6) | confirmado (6/6) | confirmado |
| SARIMA x CatBoost (entre os grupos) | confirmado (6/6) | confirmado (6/6) | confirmado |
| TimesFM x CatBoost (entre os grupos) | confirmado (6/6) | confirmado (6/6) | confirmado |
| Prophet x Tendência linear (entre os grupos) | confirmado (3/6) | confirmado (6/6) | confirmado |
| SARIMA x Tendência linear (entre os grupos) | confirmado (6/6) | confirmado (6/6) | confirmado |
| TimesFM x Tendência linear (entre os grupos) | confirmado (6/6) | confirmado (6/6) | confirmado |
| Prophet x Ingênuo sazonal (entre os grupos) | confirmado (6/6) | confirmado (6/6) | confirmado |
| Prophet x XGBoost (entre os grupos) | confirmado (6/6) | confirmado (6/6) | confirmado |
| SARIMA x Ingênuo sazonal (entre os grupos) | confirmado (6/6) | confirmado (6/6) | confirmado |
| SARIMA x XGBoost (entre os grupos) | confirmado (6/6) | confirmado (6/6) | confirmado |
| TimesFM x Ingênuo sazonal (entre os grupos) | confirmado (6/6) | confirmado (6/6) | confirmado |
| TimesFM x XGBoost (entre os grupos) | confirmado (6/6) | confirmado (6/6) | confirmado |
| SARIMA x Prophet (dentro do grupo de cima) | confirmado (3/6) | não confirmado (1/6) | não confirmado |
| TimesFM x Prophet (dentro do grupo de cima) | confirmado (6/6) | não confirmado (0/6) | não confirmado |
| SARIMA x TimesFM (dentro do grupo de cima) | não confirmado (0/6) | não confirmado (0/6) | não confirmado |
| Tendência linear x CatBoost (dentro do grupo de baixo) | não confirmado (0/6) | não confirmado (1/6) | não confirmado |
| CatBoost x Ingênuo sazonal (dentro do grupo de baixo) | não confirmado (2/6) | não confirmado (0/6) | não confirmado |
| CatBoost x XGBoost (dentro do grupo de baixo) | discordante (2/6) | não confirmado (1/6) | não confirmado |
| Tendência linear x Ingênuo sazonal (dentro do grupo de baixo) | confirmado (5/6) | não confirmado (0/6) | não confirmado |
| Tendência linear x XGBoost (dentro do grupo de baixo) | não confirmado (2/6) | confirmado (3/6) | não confirmado |
| XGBoost x Ingênuo sazonal (dentro do grupo de baixo) | não confirmado (1/6) | não confirmado (0/6) | não confirmado |

Entre parênteses, os horizontes com Diebold-Mariano abaixo de 0,05.

**Condição (a)**, todos os pares entre grupos confirmados: sim. **Condição (b)**, nenhum par dentro do grupo de cima confirmado: não.

Pares cujo veredito difere da análise principal nesta máquina: CatBoost x XGBoost; Tendência linear x Ingênuo sazonal; Tendência linear x XGBoost; SARIMA x Prophet; TimesFM x Prophet.

## 5. Limitações

- Mais janelas dão mais poder ao teste por horizonte; parte da diferença de vereditos contra a análise principal pode vir só disso, e não do choque.
- O XGBoost não reproduz entre máquinas; esta execução e o comparador rodaram no mesmo computador.
- Este resultado não entra no manuscrito da CSP sem decisão do Fabiano.

## 6. Reprodução

```
python scripts/run_benchmark.py --input-csv results/series/serie_onco_SP_sim_real_2010-2023.csv \
    --horizon 6 --min-train-size 60 --models seasonal_naive,linear_trend,sarima,prophet,timesfm,xgboost,catboost \
    --output-prefix results/benchmark_onco_SP_2010_2023_full --processo-por-modelo
python scripts/run_uncertainty.py --predictions-csv results/benchmark_onco_SP_2010_2023_full_predictions.csv \
    --models (os mesmos sete) --n-boot 10000 --seed 20260818 --output-prefix results/uncertainty_onco_SP_2010_2023_full
python scripts/apply_criterion.py --pairwise-csv results/uncertainty_onco_SP_2010_2023_full_pairwise_tests.csv \
    --report-output results/criterion_verdict_2010_2023_full.json
python scripts/write_full_series_report.py
```
