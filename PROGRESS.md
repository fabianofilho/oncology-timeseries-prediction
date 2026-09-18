# PROGRESS

Última atualização: 2026-09-18. Commit de referência: `f5c7221`.

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

Achado principal: não há vencedor. Existe um degrau entre os modelos que representam a
série (SARIMA, TimesFM, Prophet) e os que não representam (tendência linear, CatBoost,
XGBoost, ingênuo sazonal), e dentro de cada grupo é empate.

## Próximos passos, em ordem de bloqueio

### 1. Bloqueiam a submissão, e dependem do Fabiano

1.1. Resumo em português e resumen em espanhol. A CSP exige os três idiomas e só existe o
     em inglês.
1.2. Autoria, afiliações, ORCID, contribuições (CRediT), financiamento, conflitos e
     agradecimentos. São 5 dos 9 marcadores `[PENDING]`.
1.3. Decidir a seção: "Artigo" ou "Questões Metodológicas". A segunda encaixa melhor
     porque a contribuição é de reporte, e muda o perfil do revisor. Mesmo limite de
     6.000 palavras e 5 ilustrações nas duas, então não muda o texto.

### 2. Bloqueava a validade, e foi resolvido

2.1. FEITO em 2026-09-18. `scripts/crosscheck_tabnet.py` consulta o TabNet e compara ano a
     ano. A série reproduz exatamente os óbitos por residência nos 14 anos, diferença zero,
     total 741.313 nos dois. Contra a visão por ocorrência a diferença é de 1,74%, que é a
     distinção entre duas definições de população e não erro de extração. Isso também
     corrigiu uma imprecisão: o manuscrito não dizia que a base é por residência, e agora
     diz. Relatório em `results/tabnet_crosscheck.json`.

### 3. Melhoram o manuscrito, não bloqueiam

3.1. Rodar `/paper check` contra o checklist completo do TRIPOD+AI antes de mandar para
     coautor.
3.2. Encontrar as 2 referências que faltam: carga e tendência de mortalidade por câncer no
     Brasil (INCA), e cobertura e completude do SIM em São Paulo.
3.3. `/eng` para polir o inglês.

### 4. Continuam o projeto, fora do manuscrito atual

4.1. LAB-135: decidir a métrica do critério. O bootstrap usa sMAPE, que fica cego em série
     com surto. Bloqueia qualquer publicação que inclua dengue, não bloqueia esta.
4.2. LAB-128: testar boosting sobre a série diferenciada, com condição de parada declarada.
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

## Restrições ativas

- Microdado nunca é versionado. Só a série agregada, sem identificação, em `results/series/`.
- Nenhum número vai para README, paper ou Linear sem ter sido medido pelo script que o produz.
- Diferença entre modelos só é afirmada com o intervalo de confiança junto.
- Material suplementar da CSP não pode conter resultado principal.

## O que foi descartado, e por quê

- **Boosting no nível da série.** CatBoost e XGBoost fizeram 0 previsões acima do máximo do
  treino em 330, enquanto 26,7% das observações de teste estão acima dele. Limite estrutural
  de árvore, não de tuning. Virou LAB-128.
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
