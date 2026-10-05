# PROGRESS, OPT (Oncology Prediction Timeseries)

Última atualização: 2026-09-29. Estratificação por sexo (LAB-182) e achado de reprodutibilidade do XGBoost.

Medir se modelos de forecasting preveem mortalidade mensal por neoplasia maligna (CID-10
C00-C97) no Estado de São Paulo melhor que baselines triviais, com incerteza medida e
critério de diferença declarado antes de ver resultado. Terceiro projeto da linha, junto
do CPT (cardiovascular) e do DFP (dengue). Linear: projeto OPT, time Labdaps.

**Onde está:** análise fechada; manuscrito da CSP pronto a menos dos 5 `[PENDING]` de
autoria. Achado principal: não há vencedor. Há um degrau entre os modelos que representam
a série (SARIMA, TimesFM, Prophet) e os que não representam (tendência linear, CatBoost,
XGBoost, ingênuo sazonal), e dentro de cada grupo é empate.

---

## STATUS ATUAL DO ROADMAP

### Concluído nesta sessão (2026-09-28), tudo mergeado na main

- [x] **Referências e ordem de citação da CSP** (PR #1, `69b7fc4`)
  - Os 2 PENDING de referência resolvidos, conferidos no texto de origem: Guerra 2017 e
    Lima e Queiroz 2014. Entraram Jerez-Roig 2014 e Reis 2026 (precedentes na própria CSP)
    e Bracher 2021 (WIS). 12 referências.
  - Citação por chave `[@chave]`, numerada pela primeira aparição e em sobrescrito, como a
    CSP exige. Antes: 5, 7, 6, 4, 1, 2, 3 digitados.
  - Resumo e Resumen com acento e número local; limite de 250 palavras conferido no build.
  - `docs/tripod_ai_checklist.md` com os 52 itens; Métodos ganharam o parágrafo dos
    intervalos conformais e a frase de modelos univariados.
- [x] **Título "pre-specified" e as 4 declarações do TRIPOD+AI** (PR #2, `f6c64cd`)
  - Ética (Res. CNS 510/2016), protocolo e registro nos Métodos; envolvimento do público
    em Additional information. Frase de protocolo conferida contra timestamps do Linear e
    do git.
- [x] **Seção: Questões Metodológicas** (PR #3, `c2343cd`). Mesmos limites do Artigo; o
  build imprime `SECAO` para lembrar no formulário.
- [x] **LAB-135, critério v2** (PR #4, `fba8a17`). sMAPE e MAE precisam concordar;
  discordância vira veredito próprio. Regra em `src/onco_timeseries/criterion.py`. Nenhum
  par de câncer ou cardiovascular muda; dengue tem 8 de 21 discordantes.
- [x] **LAB-120, relatório entre domínios** (PR #5, `1e9a907`). `docs/relatorio_dominios.md`,
  gerado por `scripts/write_domain_report.py`. Declarou que a dengue é o município de São
  Paulo e o resto é o estado; mediu 16 previsões negativas do SARIMA na dengue.
- [x] **Polimento do inglês** (PR #6, `1f69faa`). Números idênticos antes e depois.
- [x] **`build_docx.py` aposentado** (PR #7, `05d9690`). O pacote da CSP é a única versão
  do texto; `check_docx_numbers.py` confere o pacote (65 de 65 números, 22 cortes com
  motivo, estrutura e 300 dpi). `python-docx` e `matplotlib` no `requirements.txt`.

Linear: LAB-135 e LAB-120 fechadas como Done; LAB-169 com comentários do andamento.

### Concluído em 2026-09-29

- [x] **LAB-182, estratificação por sexo.** Plano registrado na issue antes de rodar.
  Relatório em `docs/relatorio_sexo.md`, gerado por `make sex`.
  - Hipótese do pulmão **apoiada** na taxa padronizada por idade (Segi-Doll), 2010-2019:
    APC feminino +1,15% [0,58; 1,72], masculino −0,99% [−1,26; −0,71]. Em contagem bruta
    os dois sobem (+4,60% e +2,34%): a diferença é envelhecimento.
  - Previsão por sexo repete o agregado: SARIMA e Prophet batem o ingênuo sazonal nas 4
    séries, boosting em nenhuma; nenhuma série é mais difícil do que a contagem explica.
  - Denominador: `popsvs2024br` do DataSUS (2000-2025), por `fetch_population_tabnet.py`.
- [x] **XGBoost muda um veredito em outra máquina** (PR #9). Reprodução num Apple M4:
  tendência linear x XGBoost vai de não confirmado (DM 2/6) para confirmado (3/6). Decisão
  do Fabiano: manter os números publicados e declarar nos Resultados e Limitações.
  `run_benchmark.py --processo-por-modelo` contorna a queda do Python com torch e XGBoost
  no mesmo processo no macOS.

### Concluído em 2026-10-04

- [x] **Varredura do histórico para tornar o repositório público:** nenhum segredo, dado
  pessoal ou microdado em 42 commits.
- [x] **`docs/registro_decisoes.md`** (PR #11): pré-registro exportado do Linear. Mostrou
  que o corte em 2019 foi só proposto antes do benchmark; as duas frases do manuscrito foram
  corrigidas (PR #12).
- [x] **Ressalva do XGBoost nos três resumos e frase de robustez** nas Limitações ("changes
  none of the 21 verdicts"), lidas de `results/`. Resumos com 243, 249 e 249 palavras.

- [x] **LAB-204, sensibilidade com a série inteira 2010-2023** (103 janelas, critério v2).
  Pela regra registrada, a conclusão **não sobrevive**: o degrau entre os grupos se mantém
  (12 de 12 pares), mas o Prophet se separa de SARIMA e TimesFM, que seguem empatados.
  Relatório em `docs/relatorio_serie_inteira.md`. Entrar ou não no manuscrito: decisão
  pendente do Fabiano.

### EM PROGRESSO

Nada pela metade. Git limpo e sincronizado com origin.

### PRÓXIMOS PASSOS NA ORDEM

- [ ] **1. Os 5 `[PENDING]` de autoria** (LAB-169, só o Fabiano resolve)
  - Autores, afiliações e ORCID; contribuições (CRediT); financiamento; conflitos;
    agradecimentos. Entram em `build_texto()` de `scripts/build_csp_submission.py`, no
    bloco de Additional information e logo abaixo do título.
  - Depois: `python scripts/build_csp_submission.py && python scripts/check_docx_numbers.py`
    tem de sair com 0 PENDING.
- [ ] **2. Revisões humanas antes de submeter**
  - Tradução do Resumo (PT) e do Resumen (ES): eu só corrigi acentos e formato numérico.
  - Leitura de pelo menos um coautor.
- [ ] **3. Submissão** (LAB-169)
  - Tag no commit submetido: `git tag -a csp-submissao-v1 -m "Submissão à CSP" && git push --tags`
  - Trocar o commit `81f5937` citado no texto pelo commit com tag. Ele vem de
    `_commit` no `paper/verified_numbers.json`, gravado por `build_paper_assets.py`, que
    neste Mac exige `make extract-sim` antes (ver INFRA). Sem a extração, a alternativa é
    editar só esse campo do JSON, num commit próprio que diga isso.
  - Cópia de `build/csp/` fora da máquina; seção Questões Metodológicas no formulário;
    número de submissão registrado na LAB-169.

### Fora do manuscrito atual, sem prazo

- [ ] **Publicação com dengue:** liberada pela LAB-135, mas o DM com pouco poder em série
  com surto precisa entrar como limitação.

---

## INFRA

- **Google Drive:** Meu Drive › Labs › Oncology Time Series
  (https://drive.google.com/drive/folders/1y4mFK7OqUGugn7pmdXksb3K1HEAtldbR). Nomes no
  padrão `CSP_texto_AAAA-MM-DD`; versões antigas nunca são apagadas. Em 2026-10-05 entrou o
  pacote inteiro como Google Docs para revisão de coautor (texto, tabelas, legendas e
  material suplementar, com sufixo `_2026-10-05`); o arquivo de submissão
  continua sendo o `.docx` gerado em `build/csp/`, que tem numeração de linha e de página.

- **Extração feita neste Mac em 2026-09-29** (`data/raw/`, fora do git): `make paper` e
  `make sex` rodam aqui agora. Modelos instalados de `requirements-optional.txt`.
- **No macOS, rode o benchmark com `--processo-por-modelo`** sempre que TimesFM e XGBoost
  estiverem juntos; sem isso o Python cai (código 139).
- **`make paper` não roda numa máquina nova sem antes `make extract-sim`.**
  `build_paper_assets.py` lê `data/processed/sim_onco_extraction_metadata.json`, que não
  é versionado. O pacote da CSP roda sem ele, a partir do `verified_numbers.json`
  versionado. Qualquer número novo no manuscrito exige a extração, que baixa de novo o
  microdado público do DataSUS.
- Ambiente: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`. Os
  modelos (Prophet, TimesFM, XGBoost 3.4.1, CatBoost) ficam em `requirements-optional.txt`.
- `make domains` relê as séries de origem em `../cardiovascular-timeseries-prediction` e
  `../dengue-time-series` (este último não está clonado neste Mac). Sem eles, os CSVs
  versionados em `results/series/comp_*` bastam para o resto.
- Fluxo de mudança: branch, PR e merge squash na hora (repositório pessoal).

## Decisões tomadas e por quê

- **Treinar só até 2019.** A tendência 2010-2019 é quase uma reta (R2 = 0,992) e a projeção
  erra 2020 por -6,6% e ainda erra 2023 por -2,7%. A ruptura é real e não fechou, então
  modelá-la exigiria uma dummy sem fim óbvio. 2020-2023 virou teste de regime.
- **Critério com duas condições** (v1, LAB-118), IC excluindo zero E Diebold-Mariano abaixo
  de 0,05 em 3 ou mais dos 6 horizontes. Fixado antes de rodar. Mudou a conclusão duas
  vezes: sem a segunda condição o relatório teria saído com ranking de sete posições.
- **Critério v2** (LAB-135), opção 3: sMAPE e MAE concordando. As outras opções trocariam a
  métrica depois de ver o resultado. A v1 fica gravada em `confirmado_v1`.
- **Cadernos de Saúde Pública, seção Questões Metodológicas.** Diamond; precedentes diretos
  na própria revista (Jerez-Roig 2014, Reis 2026).
- **Corte de 10 para 5 ilustrações.** A CSP cobra taxa por excedente. O teste de regime
  perdeu tabela e figura e virou texto com números inline, porque material suplementar da
  CSP não pode carregar resultado principal.
- **"Pre-specified", não "pre-registered".** Não há registro em repositório de protocolos;
  as decisões foram registradas no Linear e no git antes do benchmark.
- **Um texto só.** O pacote da CSP é a única versão; o manuscrito de revisão foi aposentado
  porque divergia.

## Restrições ativas

- Microdado nunca é versionado. Só a série agregada, sem identificação, em `results/series/`.
- Nenhum número vai para README, paper ou Linear sem ter sido medido pelo script que o
  produz. O manuscrito e o relatório entre domínios são gerados, nunca editados à mão.
- Diferença entre modelos só é afirmada com o intervalo de confiança junto.
- Material suplementar da CSP não pode conter resultado principal.
- Regra do critério não muda depois de ver resultado; mudança se registra na issue antes.
- Citação no manuscrito é por chave, `[@chave]` ou `[@a,@b]`, com a referência em
  `REFERENCES`; nunca número digitado.
- Depois de mexer no texto, `python scripts/check_docx_numbers.py` tem de sair com código 0.
- `CLAUDE.md` existe só localmente (está no `.gitignore` desde o scaffold); as regras que
  valem para qualquer máquina estão aqui.

## O que foi descartado, e por quê

- **Boosting no nível da série.** CatBoost e XGBoost fizeram 0 previsões acima do máximo do
  treino em 330, enquanto 26,7% das observações de teste estão acima dele. Limite estrutural
  de árvore, não de tuning. LAB-128 fechada sem execução: o cardiovascular já testou 12
  variantes, incluindo a diferença sazonal, e nenhuma bateu o ingênuo sazonal pelo
  critério.
- **MASE como métrica do critério** (opção 2 da LAB-135): reescreveria vereditos publicados.
- **Incerteza do teste de regime.** Origem única, n = 1. O desenho atual não permite medir.

## Comandos

```
make extract-sim   make validate   make benchmark   make uncertainty
make sites         make domains    make paper       make test
python scripts/build_csp_submission.py   # só o pacote, sem regerar verified_numbers.json
python scripts/check_docx_numbers.py     # confere o pacote contra o JSON
python scripts/write_domain_report.py     # só o relatório entre domínios
```

---

## HISTÓRICO

- **2026-09-23, revisão de robustez.** Benchmark falha na hora se um modelo perde janela
  (CSVs regerados idênticos byte a byte). XGBoost reproduz o valor publicado, mas depende
  do número de threads (amplitude 0,032 pp); versão fixada em 3.4.1
  (`docs/xgboost_reprodutibilidade.md`). Intervalos conformais em
  `src/onco_timeseries/intervals.py`: cobertura a 95% entre 0,911 e 0,961 no regime, 0,500
  fora dele. Limitação de hiperparâmetros em `docs/limitacao_hiperparametros.md`.
- **2026-09-18, conferência contra o TabNet.** `scripts/crosscheck_tabnet.py`: a série
  reproduz exatamente os óbitos por residência nos 14 anos (741.313 nos dois). Contra a
  visão por ocorrência, diferença de 1,74%, que é definição de população, não erro.
- **2026-09-18.** Resumo, Abstract e Resumen no pacote, dentro de 250 palavras (`ecf9789`).
- **2026-08-29 e 30.** Manuscrito de revisão (`7d59298`, aposentado em 2026-09-28) e
  primeira versão do pacote da CSP (`f5c7221`).
- **2026-08-18 e 19.** Extração do SIM, benchmark dos 7 modelos em 55 janelas, critério
  pré-declarado (12 de 21 pares), 4 sítios tumorais e comparação entre domínios.
