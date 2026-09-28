# Checklist TRIPOD+AI do manuscrito da CSP

Conferido em 2026-09-28 contra `build/csp/CSP_texto.docx` regerado nesta data. Lista de itens
extraída da Tabela 1 de Collins et al., BMJ 2024;385:e078378 (PMC11019967), não de memória.

O manuscrito já declara, nos Métodos, que o TRIPOD+AI foi feito para modelo clínico com dado
individual e que os itens de participante, preditor individual e calibração de risco não se
aplicam a uma contagem mensal agregada. Os N/A abaixo seguem essa declaração.

Legenda: **OK** reportado · **Parcial** reportado em parte · **Falta** ausente · **N/A** não se aplica

## Resumo

| Situação | Itens |
|---|---|
| OK | 1, 2, 3a, 4, 5a, 5b, 6a, 6b, 7, 8a, 9a, 10, 11, 12a, 12c, 12e, 12g, 15, 16, 18e, 18f, 20a, 20b, 21, 22, 23a, 23b, 25, 26 |
| Parcial | 3b, 3c, 12b, 27c |
| Falta, depende do Fabiano | 17, 18a, 18b, 18c, 18d, 19 |
| N/A | 6c, 8b, 8c, 9b, 9c, 12d, 12f, 13, 14, 20c, 24, 27a, 27b |

## Item a item

| Item | Situação | Onde está, ou o que falta |
|---|---|---|
| 1 Título | OK, com ressalva | Identifica avaliação de modelos, população (SP) e desfecho. **Diz "pre-registered", mas não há registro em repositório de protocolos**: ver 18d |
| 2 Resumo | OK | Três resumos não estruturados, como a CSP exige |
| 3a Contexto e modelos existentes | OK | Introdução, parágrafo 1: carga (ref. 1) e projeções publicadas na CSP (refs. 2 e 3) |
| 3b População-alvo e usuários | Parcial | O uso (planejamento) aparece; o usuário (gestor, vigilância) fica implícito na Discussão |
| 3c Desigualdades | Parcial | Só na limitação: sem estratificação por sexo. A série agregada não permite mais |
| 4 Objetivos | OK | Último parágrafo da Introdução |
| 5a Fonte e representatividade | OK | SIM por residência, conferência exata com o TabNet, completude (ref. 4) |
| 5b Datas | OK | 2010-2023; treino até 2019 |
| 6a Cenário | OK | População geral do Estado de São Paulo |
| 6b Elegibilidade | OK | Residentes em SP, causa básica C00-C97, exclusões justificadas |
| 6c Tratamentos | N/A | |
| 7 Preparo e checagem | OK | Checagem automática 9/9 e TabNet |
| 8a Desfecho e horizonte | OK | Contagem mensal, horizonte de 6 meses |
| 8b, 8c Avaliação do desfecho | N/A | Causa básica codificada no SIM, sem avaliação feita pelo estudo |
| 9a Escolha de preditores | OK | Entrou em 2026-09-28: os sete modelos são univariados, sem covariáveis |
| 9b, 9c Definição de preditores | N/A | Só defasagens da própria série |
| 10 Tamanho | OK | 120 meses, 55 janelas, 330 previsões por modelo |
| 11 Dados faltantes | OK | Nenhum mês faltante |
| 12a Uso dos dados | OK | Origem rolante; 2020-2023 como teste de regime |
| 12b Tratamento dos preditores | Parcial | Sazonalidade multiplicativa do SARIMA declarada; o boosting sem diferenciação está só em `docs/limitacao_hiperparametros.md` |
| 12c Modelo, ajuste, validação interna | OK | Ordens, configurações, hiperparâmetros fixados sem tuning |
| 12d Heterogeneidade entre clusters | N/A | Um estado; os sítios estão em 23b |
| 12e Medidas de desempenho | OK | MAE, RMSE, sMAPE, bootstrap, DM. **Os intervalos conformais e o WIS só apareciam nos Resultados e na legenda do suplementar; o parágrafo de método entrou em 2026-09-28** |
| 12f Atualização do modelo | N/A | |
| 12g Como as previsões foram calculadas | OK | Código público |
| 13 Desbalanceamento | N/A | |
| 14 Equidade | N/A | Desfecho agregado. Dá para declarar isso numa frase, se o revisor pedir |
| 15 Saída do modelo | OK | Contagem pontual mais intervalos |
| 16 Diferença entre treino e avaliação | OK | Teste fora do regime |
| 17 Ética | **Falta** | O texto diz que o dado é público e anonimizado, mas não cita a dispensa. Proposta abaixo |
| 18a Financiamento | **Falta** | `[PENDING]` |
| 18b Conflitos | **Falta** | `[PENDING]` |
| 18c Protocolo | **Falta** | Proposta abaixo |
| 18d Registro | **Falta** | Proposta abaixo; afeta o título |
| 18e Dados | OK | Série agregada no GitHub; microdado no DataSUS |
| 18f Código | OK, trocar na submissão | O texto aponta o commit `81f5937`, que é antigo. Trocar pelo commit com tag da submissão |
| 19 Envolvimento do público | **Falta** | Proposta abaixo |
| 20a Fluxo | OK | 4.317.224 registros, 741.313 elegíveis |
| 20b Características | OK | Média, faixa e total por ano |
| 20c Comparação com o desenvolvimento | N/A | Mesma base |
| 21 Números por análise | OK | |
| 22 Especificação | OK | |
| 23a Desempenho com IC | OK | Tabela 1 e Figura 3 |
| 23b Heterogeneidade | OK | Quatro sítios, análise de escala |
| 24 Atualização | N/A | |
| 25 Interpretação | OK | |
| 26 Limitações | OK | Parágrafo próprio |
| 27a, 27b Uso na prática | N/A | Não é ferramenta implantada |
| 27c Próximos passos | Parcial | Monitoramento de mudança de regime está na Discussão; não há um "próximos estudos" explícito |

## Texto proposto para os itens que faltam

Não entrou no manuscrito porque são afirmações que só os autores podem fazer.

**17 Ética.** "In accordance with Resolution 510/2016 of the Brazilian National Health Council,
research using publicly available data without identifiable information does not require
review by a research ethics committee."

**18c Protocolo e 18d Registro.** "No formal protocol was published and the study was not
registered. The training cutoff, the model set and the criterion for a confirmed difference
were recorded in the project's issue tracker and version history before the benchmark was
run."

**Título, por causa do 18d.** Trocar "a pre-registered comparison" por "a pre-specified
comparison". "Pre-registered" sugere registro em repositório de protocolos (OSF,
PROSPERO), que não existe, e o revisor pode pedir o número.

**19 Envolvimento do público.** "There was no patient or public involvement in this study."
