# Predição de Mortalidade por Câncer em Séries Temporais (DataSUS)

Análise de séries temporais de mortalidade por neoplasias malignas usando dados reais do
**Sistema de Informações sobre Mortalidade (SIM/DataSUS)**.

Terceiro projeto da linha de forecast epidemiológico do laboratório, junto de
[cardiovascular-timeseries-prediction](https://github.com/fabianofilho/cardiovascular-timeseries-prediction)
(CID-10 capítulo I) e [dengue-imdc-2026](https://github.com/fabianofilho/dengue-imdc-2026).
O método de backtesting e de medida de incerteza é o mesmo, o que permite comparar o quanto
cada domínio é previsível sob o mesmo protocolo.

## Objetivo

Avaliar a capacidade de modelos de forecasting em prever a série mensal de óbitos por
neoplasia maligna (CID-10 C00-C97), com backtesting temporal por rolling origin e incerteza
medida em toda comparação entre modelos.

Modelos a comparar:

1. **SARIMA**: baseline estatístico com sazonalidade multiplicativa
2. **Prophet**: decomposição de tendência e sazonalidade
3. **TimesFM**: foundation model para séries temporais, zero-shot
4. **XGBoost** e **CatBoost**: boosting com defasagens, via skforecast

## Estado atual

Sete modelos rodados sobre a série real, com incerteza medida e critério pré-declarado
aplicado. O desenho segue a decisão registrada no Linear: treino restrito a 2010-2019, e
2020-2023 usado apenas como teste de mudança de regime.

### Dentro do regime, 2010-2019

Rolling origin, 55 janelas, 330 previsões por modelo, mesmas janelas para os sete.

| Modelo | sMAPE | IC95% | MAE |
|---|---:|---|---:|
| SARIMA | 1,515 | [1,381, 1,652] | 68,6 |
| TimesFM | 1,668 | [1,504, 1,845] | 75,2 |
| Prophet | 1,701 | [1,537, 1,868] | 76,7 |
| Tendência linear | 2,757 | [2,543, 2,985] | 124,5 |
| CatBoost | 3,029 | [2,774, 3,296] | 136,0 |
| XGBoost | 3,113 | [2,855, 3,386] | 139,4 |
| Ingênuo sazonal | 3,226 | [2,903, 3,556] | 143,4 |

### Nenhum modelo é o melhor, e isso é o resultado

O critério pré-declarado confirma 12 dos 21 pares, e os 9 que sobram desenham dois grupos:

- **Grupo de cima**: SARIMA, TimesFM e Prophet. Nenhum par entre eles é confirmado. SARIMA
  tem o menor sMAPE pontual e ainda assim é indistinguível dos outros dois.
- **Grupo de baixo**: tendência linear, CatBoost, XGBoost e ingênuo sazonal. Nenhum par
  entre eles é confirmado.
- **Entre os grupos**: os 12 pares são confirmados, todos com DM abaixo de 0,05 em 6 de 6
  horizontes.

O achado é o degrau entre modelar e não modelar a série, não um ranking de sete posições.
Veredito completo em `results/criterion_verdict_2010_2019_full.json`.

### Por que o boosting ficou no grupo de baixo

| Modelo | Previsões acima do máximo do treino | Viés médio |
|---|---:|---:|
| CatBoost | 0 de 330 | -89,8 |
| XGBoost | 0 de 330 | -90,4 |
| Prophet | 63 de 330 | -15,3 |
| SARIMA | 59 de 330 | -21,5 |
| TimesFM | 51 de 330 | -28,5 |

26,7% das observações de teste estão acima do máximo da janela de treino. A previsão de uma
árvore é uma média de folhas ajustadas no treino, então é limitada ao intervalo já
observado. Não é falha de tuning, é limite estrutural, e a saída seria modelar a diferença
em vez do nível.

### Fora do regime, 2020-2023

Origem única, treino congelado em dezembro de 2019, horizonte de 48 meses.

| Modelo | sMAPE | Viés médio (óbitos/mês) |
|---|---:|---:|
| Ingênuo sazonal | 4,28 | +6 |
| XGBoost | 4,77 | +131 |
| Tendência linear | 5,09 | +221 |
| CatBoost | 5,26 | +197 |
| TimesFM | 5,55 | +268 |
| SARIMA | 6,40 | +313 |
| Prophet | 7,62 | +375 |

A ordem praticamente inverte, e a explicação é única: todos superestimam, e quanto mais o
modelo extrapola a tendência pré-2020, mais ele erra quando o crescimento para. A mesma
incapacidade de extrapolar que prejudicou o boosting dentro do regime é o que o protege
fora dele.

Duas ressalvas. As duas tabelas têm desenhos diferentes (horizonte 6 com 55 origens contra
horizonte 48 com uma origem) e não se comparam número a número; na fatia comparável, os
primeiros 6 meses de 2020, os sete ficam entre 7,3 e 8,2 e praticamente empatam. E origem
única não tem incerteza: com n = 1, a ordem fora do regime é descritiva.

## Diferença em relação ao projeto cardiovascular

Mortalidade por câncer tem tendência secular mais forte e sazonalidade mais fraca que
mortalidade cardiovascular, que responde a onda de frio. Isso muda o que esperar do
baseline: a parte fácil de prever aqui é a tendência, não o ciclo anual. Um SARIMA que
ganhe só por capturar tendência linear não é evidência de que o modelo complexo falhou,
é evidência de que a série é fácil. O protocolo de incerteza existe justamente para essa
distinção não virar afirmação sem número.

## Setup

```bash
make setup-base
```

Para TimesFM, Prophet e boosting, que têm dependências pesadas:

```bash
make setup-full
```

## Uso

Extrair a série real do SIM (São Paulo, 2010-2023, neoplasias malignas):

```bash
make extract-sim
```

Validar o dado extraído antes de qualquer modelagem:

```bash
make validate
```

Rodar o benchmark com backtesting por rolling origin:

```bash
make benchmark
```

Medir a incerteza das diferenças entre modelos:

```bash
make uncertainty
```

Testes:

```bash
make test
```

## Metodologia

- **Backtesting**: rolling origin com janela expanding, passo 1
- **Horizonte**: 6 meses
- **Janela mínima de treino**: 60 meses
- **Métricas**: MAE, RMSE, sMAPE
- **Incerteza**: bootstrap por bloco reamostrando janelas inteiras (B = 10.000), mais
  Diebold-Mariano por horizonte com correção de Harvey
- **Critério pré-declarado**: uma melhoria só conta como confirmada se o IC95% da diferença
  exclui zero e o DM fica abaixo de 0,05 em 3 ou mais dos 6 horizontes

Esse critério é declarado antes de rodar, de propósito. No projeto cardiovascular, a
primeira leitura dos resultados afirmou vitória de um modelo que o intervalo de confiança
não sustentava, e isso só apareceu depois de medir.

## Estrutura

```
oncology-timeseries-prediction/
  data/raw/            microdado baixado, não versionado
  data/processed/      série agregada intermediária
  docs/                definição de desfecho e CID-10
  results/series/      série agregada final, versionada
  scripts/             extração, validação, benchmark, incerteza
  src/onco_timeseries/ data, evaluate, models, uncertainty, exog
  tests/               testes das métricas e do bootstrap
```

## Projeto no Linear

[Oncology Prediction Timeseries (OPT)](https://linear.app/labdaps/project/oncology-prediction-timeseries-opt-dd6e9c8f37c7), time Labdaps.

O board tem o pipeline em seis issues, da definição de desfecho (LAB-114) ao relatório
comparativo entre os três projetos da linha (LAB-120). A ordem de dependência está
declarada lá, não aqui.
