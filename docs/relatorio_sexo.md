# Estratificação por sexo: previsão e tendência da mortalidade por câncer de pulmão

Relatório da LAB-182. Gerado por `scripts/write_sex_report.py` a partir de `results/`; não editar à mão. O plano (séries, protocolo, população padrão, método de tendência e o que conta como apoio à hipótese) foi registrado na issue antes de rodar.

## Resposta curta

**A hipótese de que a mortalidade por câncer de pulmão sobe em mulheres e cai em homens se sustenta** na taxa padronizada por idade, de 2010 a 2019: variação percentual anual (APC) de 1,15% [0,58; 1,72] no sexo feminino e -0,99% [-1,26; -0,71] no masculino.

Em contagem bruta, o número de óbitos variou 4,60% ao ano no feminino e 2,34% no masculino. A distância entre contagem e taxa padronizada é o envelhecimento da população: é por isso que a hipótese foi testada na taxa.

Na previsão, algum modelo bate o ingênuo sazonal de forma confirmada nas quatro séries. SARIMA e Prophet batem em todas; tendência linear em 3 de 4; TimesFM em 3 de 4; XGBoost e CatBoost não batem em nenhuma.

## 1. Séries

Mesma extração do manuscrito: SIM por residência, Estado de São Paulo, 2010-2023.

| Desfecho | Óbitos | Masculino | Feminino | Sexo ignorado | Idade ignorada |
|---|---:|---:|---:|---:|---:|
| Neoplasias malignas | 741.313 | 390.776 | 350.518 | 19 | 95 (0,01%) |
| Traqueia, brônquios e pulmão | 92.821 | 53.122 | 39.697 | 2 | 20 (0,02%) |

Masculino, feminino e sexo ignorado somam o total do manuscrito (741.313 óbitos); o script aborta se não somarem.

## 2. Previsão por sexo

Protocolo idêntico ao do manuscrito: 2010-2019, horizonte de 6 meses, treino mínimo de 60, 55 janelas, os sete modelos, bootstrap de janelas inteiras e critério v2 (sMAPE e MAE concordando, e Diebold-Mariano em ≥ 3 de 6 horizontes).

sMAPE (%) com IC95%. Em negrito, a menor estimativa pontual de cada série.

| Modelo | Câncer, masculino | Câncer, feminino | Pulmão, masculino | Pulmão, feminino |
|---|---|---|---|---|
| Ingênuo sazonal | 3,22 [2,94; 3,50] | 4,05 [3,69; 4,43] | 7,88 [7,22; 8,59] | 9,33 [8,53; 10,20] |
| Tendência linear | 3,28 [3,06; 3,49] | 2,79 [2,53; 3,07] | 5,64 [5,25; 6,05] | 7,18 [6,56; 7,84] |
| SARIMA | **2,05 [1,92; 2,18]** | **2,05 [1,91; 2,19]** | **5,13 [4,73; 5,56]** | 7,29 [6,71; 7,87] |
| Prophet | 2,31 [2,13; 2,50] | 2,13 [1,98; 2,27] | 5,63 [5,11; 6,18] | **7,01 [6,41; 7,62]** |
| TimesFM | 2,22 [2,03; 2,42] | 2,19 [1,98; 2,43] | 6,18 [5,66; 6,72] | 8,02 [7,34; 8,75] |
| XGBoost | 3,78 [3,49; 4,09] | 3,77 [3,42; 4,14] | 6,73 [6,14; 7,34] | 9,29 [8,55; 10,11] |
| CatBoost | 3,42 [3,15; 3,70] | 3,59 [3,24; 3,96] | 6,86 [6,21; 7,54] | 9,00 [8,37; 9,69] |

| Série | Óbitos por mês | Pares confirmados | Discordantes sMAPE x MAE | Batem o ingênuo sazonal | sMAPE observado / esperado por Poisson |
|---|---:|---|---|---|---:|
| Câncer, masculino | 2.263 | 14 de 21 | 0 de 21 | SARIMA, Prophet e TimesFM | 0,99 |
| Câncer, feminino | 1.988 | 15 de 21 | 0 de 21 | Tendência linear, SARIMA, Prophet e TimesFM | 0,92 |
| Pulmão, masculino | 313 | 10 de 21 | 0 de 21 | Tendência linear, SARIMA, Prophet e TimesFM | 0,92 |
| Pulmão, feminino | 220 | 11 de 21 | 1 de 21 | Tendência linear, SARIMA e Prophet | 1,05 |

A última coluna compara o erro do melhor modelo em cada série com o do agregado, descontado o que o tamanho da contagem explica (raiz da razão das médias mensais, como nos sítios). Perto de 1, a série não é mais difícil do que sua contagem implica. Todas as quatro ficam entre 0,8 e 1,25.

## 3. Tendência da taxa de pulmão padronizada por idade

Padronização direta, população mundial de Segi modificada por Doll, 17 faixas (80+). Denominador: DataSUS/RIPSA, estimativas por município, idade e sexo 2000-2025. Taxas por 100.000 habitantes.

| Ano | Feminino, taxa | Masculino, taxa | Feminino, óbitos | Masculino, óbitos |
|---|---:|---:|---:|---:|
| 2010 | 8,08 | 16,23 | 2.141 | 3.366 |
| 2011 | 8,11 | 15,85 | 2.240 | 3.410 |
| 2012 | 8,18 | 15,94 | 2.314 | 3.538 |
| 2013 | 8,17 | 16,11 | 2.416 | 3.705 |
| 2014 | 8,50 | 15,74 | 2.577 | 3.713 |
| 2015 | 9,00 | 15,38 | 2.822 | 3.781 |
| 2016 | 8,52 | 15,73 | 2.769 | 3.978 |
| 2017 | 8,56 | 14,83 | 2.874 | 3.889 |
| 2018 | 8,85 | 15,20 | 3.085 | 4.109 |
| 2019 | 8,89 | 14,60 | 3.192 | 4.095 |
| 2020 | 8,33 | 13,12 | 3.098 | 3.795 |
| 2021 | 8,33 | 13,28 | 3.214 | 3.933 |
| 2022 | 8,46 | 12,58 | 3.343 | 3.834 |
| 2023 | 8,83 | 12,68 | 3.612 | 3.976 |

Prais-Winsten do log10 contra o ano. APC em % ao ano, com IC95%.

| Sexo | Janela | Medida | APC [IC95%] | Sentido |
|---|---|---|---|---|
| feminino | 2010-2019 | taxa padronizada | 1,15 [0,58; 1,72] | aumento |
| feminino | 2010-2019 | contagem bruta | 4,60 [4,05; 5,15] | aumento |
| feminino | 2010-2023 | taxa padronizada | 0,52 [-0,09; 1,13] | estável |
| feminino | 2010-2023 | contagem bruta | 3,92 [3,30; 4,55] | aumento |
| masculino | 2010-2019 | taxa padronizada | -0,99 [-1,26; -0,71] | queda |
| masculino | 2010-2019 | contagem bruta | 2,34 [2,06; 2,62] | aumento |
| masculino | 2010-2023 | taxa padronizada | -1,98 [-2,72; -1,24] | queda |
| masculino | 2010-2023 | contagem bruta | 1,21 [0,36; 2,08] | aumento |

**Veredito pela regra da LAB-182:** hipótese apoiada. Queda no masculino: sim; aumento no feminino: sim.

Na sensibilidade com 2010-2023, o APC é 0,52% no feminino e -1,98% no masculino. A idade ignorada ficou em 0,02% dos óbitos de pulmão, abaixo do limiar de 1% declarado; a sensibilidade de redistribuição não se aplica.

## 4. Limitações

- **Denominador revisado.** As estimativas de 2024 do DataSUS/RIPSA substituem as de 2000-2021; os números de população diferem da série antiga. Usar uma fonte só, de 2010 a 2023, foi a escolha declarada.
- **Faixa aberta em 80 anos.** O denominador fecha em 80+, então os pesos de Segi de 80-84 e 85+ foram somados. Em pulmão, com óbitos concentrados em idade alta, isso pesa mais do que em cânceres de idade menor.
- **Um estado.** A tendência é de São Paulo; Reis 2026 projeta por região.
- **XGBoost depende da máquina.** O benchmark por sexo rodou num Apple M4; o XGBoost não reproduz entre máquinas (ver `docs/xgboost_reprodutibilidade.md`), então os números dele nesta tabela podem diferir em outro computador. Os outros seis modelos reproduzem.
- **Taxa padronizada só para pulmão**, como declarado. A previsão por sexo usa contagem, como o resto do projeto.
- **Manuscrito da CSP inalterado.** Estes resultados não entram no texto submetido.

## 5. Reprodução

```
make extract-sim   # microdado do SIM, fora do git
make sex           # séries, população, benchmark, critério, tendência e este relatório
```
