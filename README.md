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

Série extraída e validada. Nenhum modelo treinado ainda, e portanto nenhum número de
desempenho aparece aqui. O benchmark e o módulo de incerteza vieram do projeto
cardiovascular, onde já rodaram sobre dado real, mas ainda não foram executados sobre a
série oncológica.

## Dados

- **Fonte**: SIM/DataSUS, registros reais de óbito (`DO<UF><ANO>.dbc`)
- **Filtro**: causa básica com CID-10 prefixo `C`, ver [docs/cid10_neoplasias_sim.md](docs/cid10_neoplasias_sim.md)
- **Recorte**: estado de São Paulo, janeiro/2010 a dezembro/2023 (168 meses)
- **Extração**: `scripts/extract_sim_real.py`
- **Validação**: `scripts/validate_real_dataset.py`, 9 de 9 checagens aprovadas em
  `results/data_reality_report_2010-2023.json`

### Resumo dos dados

| Indicador | Valor |
|---|---:|
| Registros brutos do SIM | 4.317.224 |
| Óbitos por neoplasia maligna (CID C) | 741.313 |
| Fração do total de óbitos | 17,2% |
| Pontos na série mensal | 168 |
| Média mensal | 4.413 |
| Mínimo mensal | 3.513 (fev/2010) |
| Máximo mensal | 5.296 (mai/2022) |
| Óbitos em 2010 | 45.263 |
| Óbitos em 2023 | 60.827 |
| Códigos CID distintos | 447 |

Distribuição por sítio: pulmão (C33-C34) 12,5%, colorretal (C18-C21) 10,6%, mama (C50) 8,0%
e próstata (C61) 5,8%, somando 36,9% dos óbitos. Sem localização especificada (C80): 3,1%.

O total de 4.317.224 registros brutos bate exatamente com o extraído pelo projeto
cardiovascular a partir dos mesmos arquivos, o que valida o caminho de download e
decodificação. A conferência contra o Atlas do INCA continua pendente.

A série agregada está versionada em `results/series/serie_onco_SP_sim_real_2010-2023.csv`.
O microdado não é versionado.

### Ruptura de 2020

A tendência de 2010 a 2019 é quase perfeitamente linear: +1.352 óbitos por ano, R² = 0,992.
Projetada para diante, ela erra 2020 por -6,6% e ainda erra 2023 por -2,7%. 2020 foi o único
ano de queda absoluta da série, -5,6% sobre 2019. A série não retornou ao patamar anterior.

Qual tratamento dar a esse período é decisão aberta, registrada na LAB-114 do Linear. O
default do `Makefile` usa a série inteira sem tratamento, e essa escolha precisa estar
declarada em qualquer resultado publicado.

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
