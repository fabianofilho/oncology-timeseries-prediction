# Limitação: hiperparâmetros fixos, e por que ajustá-los não mudaria a conclusão

Escrito em 2026-09-23 para a revisão de robustez. **Nenhum Optuna foi rodado neste
projeto.** O parágrafo abaixo se apoia em números já medidos, parte aqui e parte no projeto
cardiovascular, com a origem de cada um declarada.

## Parágrafo pronto para colar, em inglês

Destino sugerido: Discussão, dentro do parágrafo de limitações, logo após a frase sobre
cobertura de registro em São Paulo. Substitui a frase atual "Hyperparameters were fixed
rather than tuned, which understates the attainable accuracy of the boosting models,
although it cannot remove their extrapolation ceiling."

> Hyperparameters were fixed a priori rather than tuned, and this understates the accuracy
> attainable by the boosting models. Two lines of evidence indicate that tuning would not
> change the conclusion. First, the limitation of the tree ensembles here is structural
> rather than one of search: CatBoost and XGBoost produced no forecast above the maximum of
> the corresponding training window in 330 attempts, while 26.7% of test observations lay
> above that ceiling, and both carried a mean bias of about 90 deaths per month below the
> observed value. No choice of depth, learning rate or number of estimators lifts a
> prediction above the range of the training targets. Second, in a companion study applying
> the identical protocol to cardiovascular mortality in the same state, a leakage-free
> hyperparameter search improved CatBoost by 0.17 percentage points and worsened XGBoost by
> 0.23, and even an oracle search optimised directly on the test windows, which is an upper
> bound no legitimate procedure can reach, left CatBoost at 6.35 against 6.27 for the
> seasonal naive baseline. We therefore report the default configurations as the honest
> comparison between reasonable off-the-shelf choices, and treat the gap between the two
> model groups as a property of the series rather than of the search budget.

Contagem: 178 palavras. O parágrafo atual que ele substitui tem 24, então o texto do pacote
da CSP sobe de 3.251 para cerca de 3.405 palavras, bem dentro das 6.000.

## De onde vem cada número

| Número | Origem | Arquivo |
|---|---|---|
| 0 de 330 previsões acima do máximo do treino | este projeto | `paper/verified_numbers.json`, `extrapolacao` |
| 26,7% das observações de teste acima do máximo | este projeto | idem, `_observacoes_acima_do_max_treino` |
| viés de cerca de -90 óbitos/mês | este projeto | idem, `vies_medio` de catboost e xgboost |
| Optuna sem vazamento: CatBoost +0,17 pp, XGBoost -0,23 pp | cardiovascular | `scripts/revisao/README.md` |
| teto com vazamento do CatBoost 6,35 contra snaive 6,27 | cardiovascular | idem |

Os números do cardiovascular vêm da rodada de revisão de Victor Ovani Marchetti, agosto de
2026, reproduzida naquele repositório com divergência da ordem de 1e-11. Eles descrevem
outra série e entram no parágrafo rotulados como estudo companheiro, não como resultado
deste trabalho.

## O que este parágrafo deliberadamente não afirma

Não afirma que busca de hiperparâmetro é inútil em geral, nem que o boosting seria
incapaz nesta série sob outra formulação. A afirmação é mais estreita: **no nível da série**,
a árvore não extrapola, e é isso que a busca não resolve. Modelar a diferença sazonal em vez
do nível é outra formulação, e é justamente o que a LAB-128 propõe testar.
