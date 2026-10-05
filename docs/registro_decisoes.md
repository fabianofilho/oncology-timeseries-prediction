# Registro das decisões tomadas antes de rodar

Cópia das issues do Linear que funcionaram como pré-registro do projeto. O rastreador
fica num workspace privado; este arquivo existe para quem não tem acesso conferir o que
foi declarado, e quando.

Exportado em 2026-10-04 pela API do Linear. O texto das issues e dos comentários está
reproduzido sem edição; a única mudança é que os links internos do Linear viraram o
identificador da issue (por exemplo, LAB-118). Horários em UTC. Os comentários estão na
conta do primeiro autor e foram escritos com o assistente de IA declarado no manuscrito.

**Limite desta cópia.** A API registra quando cada issue foi criada e quando foi alterada
pela última vez, mas não guarda versões anteriores da descrição. Ela não prova, sozinha,
que o texto de uma issue não foi editado depois de criado. O histórico de edição fica
visível na interface do Linear.

## Cronologia de 18 de agosto de 2026

| Horário (UTC) | Fonte | Evento |
|---|---|---|
| 09:33:39 | git `312c6eb` | Scaffold do projeto |
| 09:33:56 | LAB-114 criada | Lista três tratamentos possíveis para a pandemia, sem escolher |
| 09:34:28 | LAB-116 criada | Protocolo de backtesting, SARIMA e Prophet, e os dois baselines triviais |
| 09:34:43 | LAB-117 criada | TimesFM, XGBoost e CatBoost no mesmo protocolo |
| 09:35:00 | LAB-118 criada | Critério de diferença confirmada, escrito por extenso |
| 10:10:41 | git `3000709` | Série de SP 2010-2023 extraída e versionada |
| 10:11:40 | LAB-114, comentário | Recomenda treinar até 2019, com base só na tendência anual da série |
| **10:42:06** | **git `0e39333`** | **Primeiro benchmark, treinando até 2019, com os quatro primeiros modelos** |
| **10:42:15** | **LAB-114, comentário** | **"Decisão tomada: opção 1", escrito depois de o benchmark ter rodado** |
| 10:54:57 | git `9b49871` | TimesFM, XGBoost e CatBoost entram, nas mesmas 55 janelas |

Decisões posteriores, registradas da mesma forma:

| Horário (UTC) | Fonte | Evento |
|---|---|---|
| 2026-08-19 15:26:30 | LAB-135 criada | Critério cego em série com surto; três opções |
| 2026-09-28 22:25:49 | LAB-135, comentário | Regra v2 escolhida e escrita antes de ser aplicada |
| 2026-09-28 22:29:30 | LAB-135, comentário | Resultado da v2 |
| 2026-09-29 09:55:54 | LAB-182 criada | Plano da estratificação por sexo, antes de qualquer análise |

## O que a cronologia sustenta, e o que não sustenta

- **Conjunto de modelos:** declarado antes do benchmark (LAB-116 e LAB-117, 09:34). Sustenta.
- **Critério de diferença confirmada:** declarado antes do benchmark (LAB-118, 09:35).
  Sustenta, com o limite acima sobre edições posteriores da descrição.
- **Corte do treino em 2019:** proposto como opção (09:33) e **recomendado** (10:11) antes
  do benchmark, com base só na tendência anual, sem resultado de modelo. A **decisão**
  explícita foi registrada às 10:42:15, nove segundos depois do commit do primeiro
  benchmark, que já usava esse corte. Dizer que a decisão foi registrada antes de rodar
  vai além do que o registro mostra.
- **Critério v2 (LAB-135):** escrito às 22:25, antes do resultado (22:29).
- **Estratificação por sexo (LAB-182):** plano escrito antes de qualquer análise.

---

## LAB-114 — Definir desfecho, recorte geográfico e período da série oncológica

Criada em 2026-08-18 09:33:56. Concluída em 2026-08-18 10:42:32.

### Descrição

## O que decidir

O scaffold assumiu um default para poder rodar, mas a decisão de desfecho ainda não foi tomada. Ela define tudo que vem depois e não pode ser mudada no meio do benchmark sem invalidar comparação.

| Item | Default no scaffold | Alternativas |
| -- | -- | -- |
| Desfecho | óbito com causa básica CID-10 prefixo C | incluir D37-D48 (comportamento incerto) como sensibilidade |
| Fonte | SIM (mortalidade) | SIH (internação oncológica), APAC/Painel-Oncologia (tratamento) |
| Recorte | São Paulo | Brasil, ou macrorregião |
| Período | 2010 a 2023, mensal | estender para 2000, ou parar em 2019 para excluir a pandemia |
| Agregação | C00-C97 somados | estratificar por sítio |

## Por que importa

O período é a decisão mais sensível. A COVID-19 deslocou a mortalidade por câncer por duas vias distintas: excesso de óbito em pacientes oncológicos e queda de diagnóstico em 2020-2021, que empurra óbito para os anos seguintes. Uma série 2010-2023 sem tratamento explícito disso mistura o sinal epidemiológico com a ruptura assistencial, e todo modelo vai errar exatamente ali. Três saídas possíveis, e a escolha precisa ser declarada antes de rodar:

1. treinar até 2019 e usar 2020-2023 só como teste de robustez a choque
2. manter a série inteira e incluir dummy de pandemia como exógena
3. manter a série inteira sem tratamento, e reportar o erro por ano

## Checklist de verificação

- [ ] Definição de desfecho escrita em `docs/cid10_neoplasias_sim.md` com o que entra e o que fica de fora
- [ ] Decisão sobre o período pandêmico registrada nesta issue, com a justificativa
- [ ] `make extract-sim` e `make validate` refletem o recorte escolhido
- [ ] Comparabilidade com o CPT verificada: mesmo recorte geográfico e mesmo período, ou a diferença declarada

## Contexto

O CPT (LAB-29) fez essa mesma definição para CID-10 capítulo I, em SP, 2010-2023. Manter o mesmo recorte é o caminho de menor esforço e o que permite comparar previsibilidade entre domínios. Qualquer desvio disso precisa ser deliberado.

### Comentário de 2026-08-18 10:11:40

## A série extraída mostra que a ruptura de 2020 é real e não se fecha até 2023

Isto não decide a issue, mas tira a decisão do campo da hipótese. Números da série de SP 2010-2023 já extraída (LAB-115).

### Tendência pré-pandemia

Regressão linear nos totais anuais de 2010 a 2019: **+1.352 óbitos por ano, R² = 0,992**. A série pré-pandemia é quase uma reta. O maior desvio em dez anos foi de 1,3%.

### O que acontece quando essa reta é projetada para 2020-2023

| Ano | Observado | Esperado pela reta | Diferença |
|---|---:|---:|---:|
| 2020 | 54.616 | 58.450 | **-6,6%** |
| 2021 | 57.128 | 59.801 | -4,5% |
| 2022 | 58.595 | 61.153 | -4,2% |
| 2023 | 60.827 | 62.505 | -2,7% |

2020 foi o único ano de queda absoluta da série inteira: -3.242 óbitos, -5,6% sobre 2019, contra crescimento de +1,7% a +4,5% em todos os outros treze anos.

### Como ler isso

A série não voltou para o patamar antigo. Quatro anos depois ainda está 2,7% abaixo da projeção, fechando o intervalo devagar. Isso é compatível com queda de diagnóstico em 2020-2021 empurrando óbito para frente, mas o dado de mortalidade sozinho não separa essa explicação de uma mudança real de nível. Para separar seria preciso o dado de incidência ou de procedimento (SIH ou APAC), que está fora do recorte atual.

### O que isso muda em cada opção

**Opção 1, treinar até 2019 e testar em 2020-2023.** Ficou mais atraente do que parecia. Com R² de 0,992 no pré-pandemia, o treino é limpo, e o teste vira uma pergunta bem posta: quanto um modelo erra quando o regime muda. A desvantagem é que sobram só 120 meses de treino, contra os 60 mínimos, o que deixa poucas janelas de rolling origin.

**Opção 2, dummy de pandemia como exógena.** Precisa definir quando a dummy termina, e o dado mostra que não há um fim óbvio: o efeito ainda estava presente em 2023. Uma dummy 2020-2021 deixaria o resíduo de 2022 e 2023 sem explicação.

**Opção 3, série inteira sem tratamento.** É o que está extraído. O custo é conhecido: todo modelo vai errar em 2020 e o sMAPE médio vai carregar esse erro. Como todos os modelos erram no mesmo ponto, a comparação entre eles ainda é justa, mas o número absoluto fica pior do que a série merece.

### Recomendação

Opção 1 como análise principal e opção 3 como sensibilidade, reportando as duas. É o desenho que responde a pergunta mais interessante do projeto sem esconder o choque. Mas a decisão é sua, e ela precisa ser registrada aqui antes da LAB-116 rodar, porque muda a definição das janelas de backtesting.

### Comentário de 2026-08-18 10:42:15

## Decisão tomada: opção 1, treinar até 2019

Registrando a decisão para não ficar implícita no código. O benchmark da LAB-116 rodou com rolling origin inteiramente dentro de 2010-2019, e 2020-2023 virou teste de mudança de regime com origem única e treino congelado em dez/2019.

O que ficou fora: a opção 3 como sensibilidade, que eu tinha recomendado junto. Só a opção 1 foi executada. Rodar a série inteira é uma linha de comando, mas não foi feito e não deve ser reportado como se tivesse sido.

(O restante deste comentário traz os resultados do teste de regime; está omitido aqui por ser resultado, não decisão.)

---

## LAB-116 — Baseline estatístico com backtesting por rolling origin

Criada em 2026-08-18 09:34:28. Concluída em 2026-08-18 10:41:50.

## O que fazer

Rodar SARIMA e Prophet sobre a série validada, com rolling origin, janela expanding, passo 1, horizonte de 6 meses e janela mínima de treino de 60 meses.

```bash
make benchmark
```

Antes disso, incluir um baseline trivial de referência: previsão ingênua sazonal (valor do mesmo mês do ano anterior) e tendência linear simples.

## Por que o baseline trivial não é opcional

Mortalidade por câncer cresce de forma quase monótona, puxada por envelhecimento populacional. Uma reta ajustada nos últimos cinco anos provavelmente acerta a tendência com erro baixo. Se o SARIMA não bater a reta, o problema não é o SARIMA, é a série não ter estrutura para modelar. Sem esse piso, qualquer sMAPE de um dígito vai ser lido como bom desempenho quando pode ser só a facilidade do problema.

## Checklist de verificação

- [ ] `results/benchmark_onco_*_metrics.csv` gerado, com número de previsões por modelo registrado
- [ ] Baseline ingênuo sazonal e tendência linear na mesma tabela que SARIMA e Prophet
- [ ] Número de janelas do rolling origin conferido: deve ser (n_pontos - min_train - horizonte + 1)
- [ ] Nenhum modelo com acesso a dado posterior ao fim da janela de treino

---

## LAB-117 — TimesFM e boosting no mesmo protocolo do baseline

Criada em 2026-08-18 09:34:43. Concluída em 2026-08-18 10:54:45.

## O que fazer

Rodar TimesFM zero-shot, XGBoost e CatBoost com defasagens sobre a mesma série, nas mesmas janelas de rolling origin usadas pelo baseline.

```bash
make setup-full
make benchmark   # com --models sarima,prophet,timesfm,xgboost,catboost
```

## Condição de aceite que não pode ser afrouxada

Os cinco modelos precisam ser avaliados nas **mesmas janelas**. Um modelo avaliado em subconjunto diferente não entra na tabela comparativa, entra numa tabela separada com a diferença de amostra declarada.

No CPT, XGBoost e CatBoost foram implementados e testados só na série tiny de 48 pontos, e por isso ficaram fora do benchmark real por um tempo sem que a tabela dissesse isso (LAB-63). Aqui, modelo que não rodou na série real não aparece na tabela.

## Checklist de verificação

- [ ] Coluna `n_predictions` idêntica entre todos os modelos da tabela principal
- [ ] TimesFM confirmado como zero-shot, sem ajuste na série alvo
- [ ] Defasagens do boosting geradas só com dado até o fim do treino de cada janela
- [ ] Tempo de execução por modelo registrado, para saber o custo de cada um

---

## LAB-118 — Medir incerteza e aplicar o critério pré-declarado antes de afirmar qualquer vitória

Criada em 2026-08-18 09:35:00. Concluída em 2026-08-18 10:55:16.

## O que fazer

```bash
make uncertainty
```

Bootstrap por bloco reamostrando janelas inteiras, não previsões isoladas, B = 10.000, mesmas janelas para todos os modelos em cada réplica para preservar o pareamento. Diebold-Mariano por horizonte com correção de Harvey.

## Critério pré-declarado

Uma melhoria só conta como confirmada se as duas condições valerem:

1. o IC95% da diferença de sMAPE exclui zero
2. o DM fica abaixo de 0,05 em 3 ou mais dos 6 horizontes

Se nenhum modelo passar, o achado do projeto é que os modelos empatam nesta série. Isso é resultado publicável e vai para o README e para o status update exatamente assim, sem eufemismo.

## Por que o critério está escrito antes de rodar

No CPT, o README e o `paper.md` afirmaram vitória do TimesFM com amplitude de 0,38 pp entre o melhor e o pior modelo, e o IC95% de todos se sobrepunha inteiramente (LAB-64). O critério só vale se for fixado antes de ver o número.

## Checklist de verificação

- [ ] `*_bootstrap_metrics.csv` e `*_pairwise_tests.csv` gerados
- [ ] Tabela final com sMAPE, IC95% e largura do intervalo por modelo
- [ ] Para cada par comparado, o veredito segundo o critério, incluindo os que não passam
- [ ] Semente do bootstrap registrada no relatório

---

## LAB-135 — Critério pré-declarado usa só sMAPE e fica cego em série com surto

Criada em 2026-08-19 15:26:30. Concluída em 2026-09-28 22:29:33. A descrição expõe o
problema e as três opções; a regra escolhida está no comentário de 2026-09-28 22:25:49,
reproduzido abaixo.

### Comentário de 2026-09-28 22:25:49

## Decisão, registrada antes de aplicar a regra (28/09)

**Opção 3: concordância entre duas métricas.** Decidido sem ter aberto os IC de MAE de nenhum domínio.

Por que não as outras: a opção 1 declararia a métrica da dengue depois de saber que o MAE favorece o TimesFM, que é o que o critério existe para impedir. A opção 2 (MASE) troca a métrica principal e reescreve vereditos já publicados de câncer e cardiovascular.

**Fato que muda o desenho:** o Diebold-Mariano já usa erro absoluto como perda (`run_uncertainty.py`, `metric="mae"`). Só a condição do bootstrap usa sMAPE. Então o critério atual já mistura as duas métricas, e o ponto cego está só no IC.

### Regra, por par de modelos

- **A** (inalterada): IC95% bootstrap da diferença de **sMAPE** exclui zero
- **B** (inalterada): DM-Harvey sobre erro absoluto, p < 0,05 em ≥ 3 de 6 horizontes
- **C** (nova): IC95% bootstrap da diferença de **MAE** exclui zero

Veredito:
- **confirmado**: A e C, com o mesmo sinal, e B
- **discordante**: só uma entre A e C vale, ou as duas valem com sinais opostos. É resultado a reportar, nunca vitória nem empate
- **não confirmado**: nem A nem C; ou A e C sem B

A regra antiga (A e B) continua calculada e gravada ao lado, para reproduzir os números já publicados.

### O que conta como problema

Se algum par de câncer ou cardiovascular mudar de veredito, quem se ajusta é o manuscrito do OPT antes da submissão (LAB-169), não a regra. A regra fica como está escrita aqui.

---

## LAB-182 — Estratificação por sexo: previsão por sexo e tendência da taxa padronizada de pulmão

Criada em 2026-09-29 09:55:54. Concluída em 2026-09-29 11:36:49. O plano completo está
na descrição da issue; a parte que define o teste da hipótese:

> **O que conta como apoio à hipótese:** na janela principal, APC feminino > 0 com IC
> excluindo zero **e** APC masculino < 0 com IC excluindo zero. Qualquer outro resultado
> é reportado como ele é: só uma metade, nenhuma, ou o contrário.

Taxa por padronização direta (população mundial de Segi modificada por Doll), denominador
das estimativas populacionais 2000-2025 do DataSUS/RIPSA, tendência por Prais-Winsten do
log10 da taxa, janela principal 2010-2019 e sensibilidade 2010-2023. A regra está
implementada e testada em `scripts/sex_trend.py` e `tests/test_tendencia_sexo.py`.
