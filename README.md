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

### Por sítio tumoral

Mesmo protocolo aplicado às quatro séries de maior volume.

| Série | Média mensal | Melhor sMAPE | Pares confirmados |
|---|---:|---:|---|
| Agregado C00-C97 | 4.251 | 1,515 | 12 de 21 |
| Pulmão (C33-C34) | 533 | 3,492 | 13 de 21 |
| Colorretal (C18-C21) | 436 | 4,340 | 12 de 21 |
| Mama (C50) | 333 | 5,238 | 4 de 21 |
| Próstata (C61) | 246 | 6,513 | 2 de 21 |

Em próstata, nenhum modelo bate o ingênuo sazonal pelo critério.

**O sMAPE de 1,5% do agregado não é evidência de modelo bom, é evidência de série
grande.** Contagem maior tem menos ruído relativo por construção: para contagem Poisson o
desvio escala com 1/√N. A razão de sMAPE observada entre agregado e cada sítio fica entre
0,82 e 1,03 da razão esperada só pelo tamanho, então a vantagem do agregado é explicada
pela contagem, sem evidência de cancelamento de erro entre sítios. Cálculo em
`scripts/analyze_site_scale.py`.

### Comparação com os outros dois domínios da linha

As séries de cardiovascular (CPT) e dengue (DFP) foram rerodadas por este mesmo código, não
comparadas a partir dos números que cada projeto publicou. Janela comum 2010-02 a 2019-12,
119 pontos, 54 janelas, 324 previsões por modelo.

Relatório completo, com IC95% dos sete modelos nos três domínios e as diferenças de
protocolo linha a linha, em [`docs/relatorio_dominios.md`](docs/relatorio_dominios.md),
gerado por `scripts/write_domain_report.py`. Atenção ao recorte: câncer e cardiovascular
são o estado de São Paulo, e a dengue é o município, porque o DFP trabalha por capital.

| Domínio | Amplitude máx/mín | Razão sMAPE contra o baseline | Pares confirmados | Discordantes sMAPE x MAE | Batem o ingênuo sazonal |
|---|---:|---:|---|---|---|
| Câncer | 1,4 | 0,474 | 13 de 21 | 0 de 21 | sarima, prophet, timesfm |
| Cardiovascular | 1,5 | 0,795 | 9 de 21 | 0 de 21 | nenhum |
| Dengue | 140,8 | 0,935 | 1 de 21 | 8 de 21 | nenhum |

**Dos três domínios, só em câncer algum modelo bate o baseline trivial de forma
confirmada.** Em cardiovascular o SARIMA erra 20% menos e mesmo assim não passa: o DM fica
abaixo de 0,05 em apenas 2 dos 6 horizontes.

Em dengue o vencedor muda com a métrica (XGBoost por sMAPE, TimesFM por MAE e RMSE, com
razão 0,62 e 0,56). Com 52% dos meses abaixo de 1.000 casos, o sMAPE é dominado pelos
vales. Isso era limitação do critério, não do TimesFM, e foi resolvido na LAB-135: o
critério passou a exigir que sMAPE e MAE concordem, e os pares em que discordam viram
resultado próprio, "discordante". Em dengue são 8 de 21, entre eles TimesFM contra o
ingênuo sazonal. Mesmo assim o TimesFM não seria confirmado nem por um critério só de MAE:
o Diebold-Mariano, que já usa erro absoluto, passa em apenas 1 dos 6 horizontes. Em câncer
e cardiovascular a regra nova não muda nenhum dos pares.

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

Estratificar por sítio tumoral e rodar os quatro sítios:

```bash
make sites
```

Comparar os três domínios da linha sob protocolo idêntico (requer os repositórios
`cardiovascular-timeseries-prediction` e `dengue-time-series` clonados ao lado deste):

```bash
make domains
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
- **Critério pré-declarado** (v1, LAB-118): uma melhoria só conta como confirmada se o IC95%
  da diferença de sMAPE exclui zero e o DM, sobre erro absoluto, fica abaixo de 0,05 em 3 ou
  mais dos 6 horizontes
- **Critério v2** (LAB-135, registrado antes de ser aplicado): soma a exigência de que o
  IC95% da diferença de MAE também exclua zero, com o mesmo sinal. Se só uma das duas
  métricas vê diferença, o par é "discordante". Regra em `src/onco_timeseries/criterion.py`;
  os JSONs de veredito trazem a v2 em `confirmado` e a v1 em `confirmado_v1`

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

## Registro das decisões

O projeto foi conduzido num rastreador de issues privado (Linear, time Labdaps). As issues
que funcionaram como pré-registro, com o texto integral e os horários, estão copiadas em
[`docs/registro_decisoes.md`](docs/registro_decisoes.md): o que foi declarado antes de
rodar, o que foi decidido depois, e o limite do que a cópia prova.
