# Choque ou poder? Separação do Prophet na série inteira

Análise **exploratória** da LAB-204, registrada na issue antes de rodar. Gerado por `scripts/choque_poder.py`; não editar à mão.

As 48 janelas que preveem algum mês de 2020-2023 são um único choque visto por janelas sobrepostas: o resultado descreve esta pandemia nesta série, não uma regra geral.

## Controle

As 55 janelas estáveis, filtradas das previsões da série inteira, reproduzem par a par os 21 vereditos da análise principal nesta máquina.

## Resultado por par

| Par | Estáveis | Choque | Prophet erra mais no choque? | Dif. em dif. sMAPE [IC95%] | Dif. em dif. MAE [IC95%] | Veredito |
|---|---|---|---|---|---|---|
| Prophet x SARIMA | não confirmado (1/6) | não confirmado (2/6) | sim | 0,37 [0,09; 0,65] | 19,7 [6,4; 32,8] | **indeterminado** |
| Prophet x TimesFM | não confirmado (0/6) | confirmado (6/6) | sim | 0,82 [0,51; 1,17] | 40,3 [25,8; 56,5] | **choque** |

Entre parênteses, os horizontes com Diebold-Mariano abaixo de 0,05. A diferença em diferenças é a perda do Prophet menos a do rival nas janelas de choque, menos a mesma diferença nas estáveis, em pontos de sMAPE e em óbitos por mês.

**Regra registrada:** choque se o Prophet é confirmado como pior nas 48 janelas *e* a diferença em diferenças tem IC positivo em sMAPE e em MAE; inconsistente se um aponta para o choque e o outro contradiz; indeterminado nos demais casos. "Poder" não é veredito possível.

Para Prophet × SARIMA, a diferença em diferenças positiva é evidência secundária e não muda o veredito: nas 103 janelas esse par só se confirma juntando os dois grupos, então a separação dele não pode ser atribuída ao choque sozinho.

## Descritivo, sem veredito

| Janelas | n | Prophet | SARIMA | TimesFM |
|---|---:|---:|---:|---:|
| Treino até 2019 (21 de 36 previsões em 2020 ou depois) | 6 | 3,43 | 3,70 | 3,20 |
| Treino com meses de 2020 ou depois (252 de 252 previsões em 2020 ou depois) | 42 | 4,07 | 3,39 | 3,12 |

sMAPE (%). **Este recorte não separa as duas explicações e não sustenta conclusão nenhuma.** No primeiro grupo, só 21 das 36 previsões caem em 2020; as demais são meses estáveis de 2019, o que explica erros bem abaixo dos medidos no primeiro semestre de 2020. O segundo grupo mistura duas coisas: treinar com meses da pandemia e prever a recuperação de 2021 a 2023. Com 6 janelas, nenhum teste se aplica.

## Limitações

- **Um único choque.** As janelas de 2020-2023 veem o mesmo evento; o resultado descreve esta pandemia nesta série.
- **Janelas sobrepostas.** O bootstrap da diferença em diferenças reamostra janelas como independentes dentro de cada grupo, mas janelas vizinhas compartilham meses previstos. Os IC tendem a ser estreitos demais. É a mesma premissa da análise principal, mantida aqui por coerência e não alterada depois de ver o resultado.
- **Exploratória.** Fora do plano original da LAB-204, registrada na issue antes de rodar. Não entra no manuscrito sem decisão do Fabiano.
