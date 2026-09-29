# Previsibilidade de câncer, cardiovascular e dengue sob protocolo idêntico

Relatório final da LAB-120. Gerado por `scripts/write_domain_report.py` a partir de `results/`; não editar à mão. Critério na versão 2 (LAB-135): sMAPE e MAE precisam concordar.

## Resposta curta

Só em câncer (SARIMA, Prophet e TimesFM) algum modelo bate o ingênuo sazonal de forma confirmada. Em cardiovascular e dengue, nenhum modelo passa no critério contra o baseline trivial.

sMAPE e MAE discordam em 8 dos 21 pares de dengue; nos outros domínios, em nenhum.

## 1. Protocolo comum

As três séries foram rerodadas pelo mesmo código. Nenhum número publicado por CPT ou DFP foi reaproveitado.

| Item | Valor |
|---|---|
| Janela comum | 2010-02 a 2019-12, 119 meses |
| Horizonte | 6 meses |
| Treino mínimo | 60 meses, janela expansiva, passo de 1 mês |
| Janelas de origem rolante | 54 |
| Previsões por modelo e domínio | 324 |
| Modelos | os mesmos 7, mesma configuração: Ingênuo sazonal, Tendência linear, SARIMA, Prophet, TimesFM, XGBoost e CatBoost |
| Bootstrap | janelas inteiras, B = 10.000, semente 20260818 |
| Critério | v2: IC95% de sMAPE e de MAE excluem zero no mesmo sentido, e Diebold-Mariano (erro absoluto, correção de Harvey) < 0,05 em ≥ 3 de 6 horizontes |

## 2. O que difere entre as séries

O protocolo é idêntico; as séries não. A diferença de recorte geográfico da dengue vem do DFP, que trabalha por capital.

| | Câncer | Cardiovascular | Dengue |
|---|---|---|---|
| Projeto de origem | OPT | CPT | DFP |
| Desfecho | óbitos, causa básica CID-10 C00-C97 | óbitos, causa básica CID-10 I00-I99 | casos notificados |
| Fonte | SIM/DataSUS, por residência | SIM/DataSUS | InfoDengue |
| Recorte | Estado de São Paulo | Estado de São Paulo | Município de São Paulo (IBGE 3550308) |
| Média mensal | 4.256 | 7.049 | 2.497 |
| Mínimo e máximo | 3.513 a 5.085 | 5.811 a 8.919 | 262 a 36.897 |
| Amplitude máx/mín | 1,4 | 1,5 | 140,8 |
| Coeficiente de variação | 0,084 | 0,098 | 2,023 |

## 3. sMAPE (%) com IC95%, os sete modelos nos três domínios

| Modelo | Câncer | Cardiovascular | Dengue |
|---|---|---|---|
| Ingênuo sazonal | 3,18 [2,87; 3,51] | 4,15 [3,76; 4,57] | 75,50 [66,13; 85,70] |
| Tendência linear | 2,72 [2,52; 2,94] | 7,87 [7,41; 8,33] | 117,53 [110,26; 124,53] |
| SARIMA | **1,51 [1,38; 1,65]** | **3,30 [2,99; 3,62]** | 95,35 [83,82; 106,88] |
| Prophet | 1,68 [1,52; 1,85] | 3,40 [3,08; 3,75] | 92,74 [81,10; 104,33] |
| TimesFM | 1,63 [1,48; 1,80] | 3,46 [3,15; 3,78] | 75,75 [67,12; 84,49] |
| XGBoost | 3,13 [2,89; 3,38] | 4,62 [4,18; 5,09] | **70,62 [61,35; 80,12]** |
| CatBoost | 2,99 [2,74; 3,26] | 4,35 [3,96; 4,77] | 73,38 [65,07; 82,23] |

Em negrito, a menor estimativa pontual de cada domínio, que não é o mesmo que o melhor modelo (seção 6). O sMAPE bruto mede a dificuldade da série e não se compara entre domínios: com amplitude de 140,8 vezes na dengue contra 1,4 no câncer, a diferença de nível é da série, não do modelo.

## 4. MAE (casos ou óbitos por mês) com IC95%, os sete modelos nos três domínios

| Modelo | Câncer | Cardiovascular | Dengue |
|---|---|---|---|
| Ingênuo sazonal | 142 [128; 156] | 305 [276; 337] | 2.891 [1.967; 3.903] |
| Tendência linear | 123 [114; 134] | 579 [544; 616] | 3.782 [3.282; 4.344] |
| SARIMA | **68 [62; 75]** | **242 [219; 265]** | 4.188 [2.834; 6.002] |
| Prophet | 76 [69; 84] | 248 [225; 274] | 3.491 [2.904; 4.086] |
| TimesFM | 74 [67; 81] | 255 [231; 278] | **1.797 [1.290; 2.379]** |
| XGBoost | 141 [130; 151] | 339 [306; 375] | 2.763 [1.868; 3.756] |
| CatBoost | 134 [123; 146] | 320 [290; 353] | 2.696 [1.854; 3.632] |

## 5. Quanto modelar adianta, contra o baseline do próprio domínio

Razão abaixo de 1 significa que o melhor modelo erra menos que repetir o ano anterior.

| Domínio | Razão sMAPE | Melhor por sMAPE | Razão MAE | Melhor por MAE |
|---|---:|---|---:|---|
| Câncer | 0,474 | SARIMA | 0,483 | SARIMA |
| Cardiovascular | 0,795 | SARIMA | 0,793 | SARIMA |
| Dengue | 0,935 | XGBoost | 0,622 | TimesFM |

O melhor modelo muda com a métrica em dengue. Reportar só uma das duas ali seria escolher o vencedor pela métrica.

## 6. O que sobrevive ao critério

| Domínio | Pares confirmados | Discordantes sMAPE x MAE | Batem o ingênuo sazonal |
|---|---|---|---|
| Câncer | 13 de 21 | 0 de 21 | SARIMA, Prophet e TimesFM |
| Cardiovascular | 9 de 21 | 0 de 21 | nenhum |
| Dengue | 1 de 21 | 8 de 21 | nenhum |

Cada modelo contra o ingênuo sazonal, com as três condições do critério. Diferença = ingênuo menos modelo, então positivo significa que o modelo erra menos.

| Domínio | Modelo | Dif. sMAPE [IC95%] | Dif. MAE [IC95%] | DM < 0,05 | Veredito |
|---|---|---|---|---|---|
| Câncer | Tendência linear | 0,46 [0,19; 0,74] | 19 [7; 31] | 0/6 | não confirmado |
| Câncer | SARIMA | 1,68 [1,42; 1,93] | 73 [63; 84] | 6/6 | confirmado |
| Câncer | Prophet | 1,50 [1,20; 1,79] | 66 [53; 78] | 6/6 | confirmado |
| Câncer | TimesFM | 1,55 [1,29; 1,82] | 68 [57; 79] | 6/6 | confirmado |
| Câncer | XGBoost | 0,05 [-0,18; 0,29] | 1 [-9; 12] | 0/6 | não confirmado |
| Câncer | CatBoost | 0,19 [-0,09; 0,48] | 7 [-5; 20] | 0/6 | não confirmado |
| Cardiovascular | Tendência linear | -3,72 [-4,21; -3,21] | -274 [-309; -238] | 5/6 | confirmado |
| Cardiovascular | SARIMA | 0,85 [0,46; 1,26] | 63 [35; 93] | 2/6 | não confirmado |
| Cardiovascular | Prophet | 0,75 [0,32; 1,18] | 57 [26; 87] | 1/6 | não confirmado |
| Cardiovascular | TimesFM | 0,69 [0,29; 1,08] | 50 [22; 79] | 2/6 | não confirmado |
| Cardiovascular | XGBoost | -0,47 [-0,80; -0,15] | -34 [-57; -11] | 1/6 | não confirmado |
| Cardiovascular | CatBoost | -0,20 [-0,53; 0,12] | -15 [-38; 7] | 0/6 | não confirmado |
| Dengue | Tendência linear | -42,03 [-55,00; -28,54] | -891 [-1.641; -82] | 0/6 | não confirmado |
| Dengue | SARIMA | -19,85 [-34,50; -4,94] | -1.297 [-2.954; -154] | 0/6 | não confirmado |
| Dengue | Prophet | -17,23 [-29,85; -4,45] | -600 [-1.419; 223] | 0/6 | discordante |
| Dengue | TimesFM | -0,25 [-9,32; 8,70] | 1.094 [433; 1.845] | 1/6 | discordante |
| Dengue | XGBoost | 4,88 [-1,50; 10,97] | 128 [-597; 830] | 1/6 | não confirmado |
| Dengue | CatBoost | 2,12 [-5,57; 9,59] | 195 [-266; 698] | 0/6 | não confirmado |

## 7. A hipótese da issue

A LAB-120 partiu da hipótese de que câncer é dominado por tendência, cardiovascular por sazonalidade e dengue por surto, e de que foundation model só compensa onde há surto.

**Estrutura, câncer contra cardiovascular: se sustenta.** A tendência linear tem razão 0,86 contra o ingênuo sazonal em câncer e 1,90 em cardiovascular: extrapolar uma reta é competitivo onde a tendência domina e é o pior modelo onde domina o ciclo anual.

**Foundation model só onde há surto: não se sustenta.** O TimesFM bate o ingênuo sazonal de forma confirmada em câncer, e na dengue o par é discordante: o IC de MAE exclui zero, o de sMAPE contém, e o Diebold-Mariano fica abaixo de 0,05 em 1 de 6 horizontes. Há um efeito na dengue, visível no erro absoluto, mas o teste por horizonte não o sustenta. E o mesmo modelo tem ganho confirmado numa série sem surto.

## 8. Conclusão do OPT

Em câncer, SARIMA, Prophet e TimesFM batem o ingênuo sazonal de forma confirmada, com o melhor errando 53% menos por sMAPE. Entre esses 3, nenhum dos 3 pares é confirmado: eles empatam entre si, e o que os dados sustentam é um degrau entre quem representa a série e quem não representa, não um vencedor.

Nesta janela comum (a partir de fevereiro de 2010, por causa da dengue) o câncer tem 13 de 21 pares confirmados. O manuscrito do OPT usa a série a partir de janeiro, com uma janela a mais, e reporta a própria contagem; os dois números não se misturam.

## 9. Diferenças contra o que cada projeto publicou

| Fonte | Período | Recorte | Horizonte | Treino mínimo | Métrica principal | Critério |
|---|---|---|---|---|---|---|
| OPT, manuscrito da CSP | 2010-01 a 2019-12 (120 meses); 2020-2023 só como teste de regime | Estado de SP | 6 | 60 | sMAPE, com MAE e RMSE | IC exclui zero e DM em ≥ 3 de 6 |
| CPT, README | 2010-01 a 2023-12 (168 meses) | Estado de SP | 6 | 60 | MAE, RMSE e sMAPE | IC exclui zero e DM em ≥ 3 de 6 |
| DFP, README | 2010-02 a 2024-11 (178 meses) | 8 capitais | 12 | 48 | MAE relativo ao ingênuo; sMAPE exploratório | IC exclui zero e DM em ≥ 6 de 12 |
| **Esta comparação** | 2010-02 a 2019-12 (119 meses) | Estado de SP; dengue no município | 6 | 60 | sMAPE e MAE | v2, sMAPE e MAE concordando e DM em ≥ 3 de 6 |

Esta comparação responde outra pergunta que a de cada projeto e não substitui nenhum resultado publicado.

## 10. Limitações

- **Recorte geográfico**: câncer e cardiovascular são o estado de São Paulo; dengue é o município. A comparação vale como razão contra o baseline de cada série, não como comparação entre populações.
- **SARIMA na dengue**: 16 previsões negativas de casos e 5 acima do máximo da série (36.897), a maior em 73.643. Mantidas sem corte, como o protocolo manda; pesam no MAE dele (4.188).
- **Poder do Diebold-Mariano em série com surto**: com 54 janelas e cauda pesada, o teste por horizonte quase nunca passa na dengue, inclusive onde os dois IC excluem zero.
- **Sem teste de mudança de regime** em cardiovascular e dengue. A comparação é toda dentro do período estável; só o OPT tem teste fora do regime, no manuscrito.

## 11. Reprodução

As séries agregadas estão versionadas em `results/series/comp_*_2010_2019.csv`, sem identificação.

```
make domains                          # benchmark, incerteza, critério e relatório
python scripts/write_domain_report.py # só este documento, a partir de results/
```

`make domains` começa por `scripts/compare_domains.py`, que relê as séries de origem nos repositórios irmãos (`../cardiovascular-timeseries-prediction` e `../dengue-time-series`) e aborta se faltar mês na janela comum. Sem eles, os CSVs versionados bastam para rodar o resto.
