# PROGRESS

Última atualização: 2026-09-28. Sessão de fechamento da submissão (LAB-169).

## Objetivo

Medir se modelos de forecasting preveem mortalidade mensal por neoplasia maligna
(CID-10 C00-C97) em São Paulo melhor que baselines triviais, com incerteza medida e
critério de diferença declarado antes de ver resultado. Terceiro projeto da linha, junto
do CPT (cardiovascular) e do DFP (dengue).

## Estado atual

Análise concluída e manuscrito montado. Alvo escolhido: Cadernos de Saúde Pública.

| Etapa | Estado |
|---|---|
| Extração e validação da série (SIM, SP, 2010-2023) | feita, 741.313 óbitos, 168 pontos |
| Benchmark dos 7 modelos, 55 janelas, 330 previsões cada | feito |
| Incerteza e critério pré-declarado | feito, 12 de 21 pares confirmados |
| Estratificação por 4 sítios tumorais | feita |
| Comparação CPT vs DFP vs OPT sob protocolo idêntico | feita |
| Manuscrito .docx de revisão (18 páginas) | feito, `build/manuscript.docx` |
| Pacote de submissão da CSP (4 arquivos) | feito, `build/csp/` |
| Conferência contra o TabNet | feita, bate exato nos 14 anos |
| Revisão de robustez (4 etapas) | feita em 2026-09-23 |
| Intervalos de predição conformais | feitos, cobertura 0,911 a 0,961 a 95% |
| Referências e checklist TRIPOD+AI | feitos em 2026-09-28, sobram 5 `[PENDING]`, todos de autoria |

Achado principal: não há vencedor. Existe um degrau entre os modelos que representam a
série (SARIMA, TimesFM, Prophet) e os que não representam (tendência linear, CatBoost,
XGBoost, ingênuo sazonal), e dentro de cada grupo é empate.

## Próximos passos, em ordem de bloqueio

### 1. Bloqueiam a submissão, e dependem do Fabiano

1.1. FEITO. Resumo, Abstract e Resumen no pacote, 249, 245 e 247 palavras, dentro do
     limite de 250 que a CSP define no documento de recomendação do resumo. Não
     estruturados e com o mínimo de siglas, como ela pede. Revisar a tradução.
1.2. Autoria, afiliações, ORCID, contribuições (CRediT), financiamento, conflitos e
     agradecimentos. São os 5 marcadores `[PENDING]` restantes. Só o Fabiano resolve.
1.2b. FEITO em 2026-09-28, aprovado pelo Fabiano. Título com "pre-specified" no lugar de
     "pre-registered" (nos dois geradores), e as quatro declarações do TRIPOD+AI no texto:
     ética (Res. CNS 510/2016) e protocolo/registro no fim dos Métodos, envolvimento do
     público em Additional information. A frase de protocolo foi conferida contra os
     timestamps do Linear e do git (ver `docs/tripod_ai_checklist.md`).
1.2c. Na hora de submeter, trocar o commit `81f5937` citado no texto pelo commit com tag.
1.3. Decidir a seção: "Artigo" ou "Questões Metodológicas". O documento da seção
     metodológica descreve como típico a proposta de um método novo, e este paper compara
     métodos existentes. O texto dela cobre "análise, comparação ou desenvolvimento
     metodológico", então continua defensável, mas menos óbvio do que eu disse antes.

### 2. Bloqueava a validade, e foi resolvido

2.1. FEITO em 2026-09-18. `scripts/crosscheck_tabnet.py` consulta o TabNet e compara ano a
     ano. A série reproduz exatamente os óbitos por residência nos 14 anos, diferença zero,
     total 741.313 nos dois. Contra a visão por ocorrência a diferença é de 1,74%, que é a
     distinção entre duas definições de população e não erro de extração. Isso também
     corrigiu uma imprecisão: o manuscrito não dizia que a base é por residência, e agora
     diz. Relatório em `results/tabnet_crosscheck.json`.

### 2b. Revisão de robustez, feita em 2026-09-23

- Benchmark agora falha na hora se um modelo perde qualquer janela. CSVs publicados
  regerados e idênticos byte a byte.
- XGBoost reproduz o valor publicado (3.112688870260289, diferença zero), mas depende do
  número de threads, amplitude de 0,032 pp. Versão fixada em 3.4.1, documentado em
  `docs/xgboost_reprodutibilidade.md`.
- Intervalos conformais em `src/onco_timeseries/intervals.py`, calibrados só com janelas
  anteriores. Dentro do regime a cobertura a 95% fica entre 0,911 e 0,961; fora do regime
  cai para 0,500 nos sete modelos. O WIS reordena o grupo de baixo.
- Parágrafo de limitação de hiperparâmetros em `docs/limitacao_hiperparametros.md`, sem
  rodar Optuna. A LAB-128 foi fechada sem executar nada, porque o cardiovascular já
  testou a diferenciação sazonal e ela não passa no critério.

### 3. Melhoram o manuscrito, não bloqueiam

3.1. FEITO em 2026-09-28. Checklist item a item em `docs/tripod_ai_checklist.md`, com a
     lista oficial extraída do PMC. Dois buracos corrigidos no texto: o método dos
     intervalos conformais e do WIS não estava nos Métodos, e não se dizia que os modelos
     são univariados.
3.2. FEITO em 2026-09-28. Guerra 2017 (GBD, taxas padronizadas estáveis 1990-2015) e Lima e
     Queiroz 2014 (completude do SIM, melhor no Sul e Sudeste), conferidas no texto de
     origem. Entraram também os dois precedentes da própria CSP, Jerez-Roig 2014 (próstata)
     e Reis 2026 (pulmão), e Bracher 2021 para o WIS. Agora são 12 referências.
3.4. O manuscrito de revisão (`scripts/build_docx.py`) não recebeu nada disso: ainda tem os
     números de citação digitados e o `[PENDING]` do INCA. Só o pacote da CSP foi atualizado.
3.3. `/eng` para polir o inglês.

### 4. Continuam o projeto, fora do manuscrito atual

4.1. LAB-135: decidir a métrica do critério. O bootstrap usa sMAPE, que fica cego em série
     com surto. Bloqueia qualquer publicação que inclua dengue, não bloqueia esta.
4.2. LAB-128: FECHADA como Canceled em 2026-09-23. Não vale rodar a diferenciação aqui:
     o cardiovascular já testou 12 variantes de boosting, incluindo a diferença sazonal,
     e nenhuma passou no critério. O achado ficou em `docs/limitacao_hiperparametros.md`
     e já está aplicado no manuscrito.
4.3. LAB-120: relatório comparativo entre os três domínios, In Review, travado pela LAB-135.

## Decisões tomadas e por quê

- **Treinar só até 2019.** A tendência 2010-2019 é quase uma reta (R2 = 0,992) e a projeção
  erra 2020 por -6,6% e ainda erra 2023 por -2,7%. A ruptura é real e não fechou, então
  modelá-la exigiria uma dummy sem fim óbvio. 2020-2023 virou teste de regime.
- **Critério com duas condições**, IC excluindo zero E Diebold-Mariano abaixo de 0,05 em 3
  ou mais dos 6 horizontes. Fixado antes de rodar. Mudou a conclusão duas vezes: sem a
  segunda condição o relatório teria saído com ranking de sete posições.
- **Cadernos de Saúde Pública como alvo.** Diamond confirmada na página do editor, com
  precedente direto de julho de 2026 sobre projeções de mortalidade por câncer no Brasil.
- **Corte de 10 para 5 ilustrações.** A CSP cobra taxa por excedente. O teste de regime
  perdeu tabela e figura e virou texto com números inline, porque material suplementar da
  CSP não pode carregar resultado principal.

- **Citação por chave no pacote da CSP.** A CSP exige numeração na ordem de citação e em
  sobrescrito. O texto citava 5, 7, 6, 4, 1, 2, 3 com números digitados. Agora cita
  `[@chave]` e `cite_runs()` numera pela primeira aparição; chave desconhecida ou
  referência nunca citada derruba o build.
- **Resumo e Resumen com acento e número local** (741.313; 1,51%). Estavam em ASCII e com
  separador em inglês. `LIMITE_RESUMO` existia mas nunca era conferido; agora o build
  imprime a contagem dos três.

## Restrições ativas

- Microdado nunca é versionado. Só a série agregada, sem identificação, em `results/series/`.
- Nenhum número vai para README, paper ou Linear sem ter sido medido pelo script que o produz.
- Diferença entre modelos só é afirmada com o intervalo de confiança junto.
- Material suplementar da CSP não pode conter resultado principal.

## O que foi descartado, e por quê

- **Boosting no nível da série.** CatBoost e XGBoost fizeram 0 previsões acima do máximo do
  treino em 330, enquanto 26,7% das observações de teste estão acima dele. Limite estrutural
  de árvore, não de tuning. Virou LAB-128, fechada sem execução: o cardiovascular já testou
  12 variantes, incluindo a diferença sazonal, e nenhuma bateu o ingênuo sazonal pelo
  critério. A melhor delas, catboost_diff12, vai de 6,589 para 6,203 e ainda assim reprova.
- **Sensibilidade com a série inteira** sem tratar o período pandêmico. Recomendada na
  LAB-114, nunca executada.
- **Estratificação por sexo.** A hipótese de pulmão subir em mulheres e cair em homens
  continua não testada.
- **Incerteza do teste de regime.** Origem única, n = 1. O desenho atual não permite medir.

## Comandos

```
make extract-sim   make validate   make benchmark   make uncertainty
make sites         make domains    make paper       make test
python scripts/build_csp_submission.py
```
