# CID-10 de neoplasias malignas no SIM

O SIM registra a causa básica do óbito no campo `CAUSABAS`, com o código CID-10 sem ponto
(exemplo: `C509`, não `C50.9`). O filtro do projeto usa o prefixo `C`, que corresponde ao
capítulo II da CID-10 restrito às neoplasias malignas (C00 a C97).

## O que entra

| Faixa | Descrição |
|---|---|
| C00-C14 | Lábio, cavidade oral e faringe |
| C15-C26 | Órgãos digestivos |
| C30-C39 | Aparelho respiratório e órgãos intratorácicos |
| C40-C41 | Ossos e cartilagens articulares |
| C43-C44 | Melanoma e outras neoplasias da pele |
| C45-C49 | Tecido mesotelial e tecidos moles |
| C50 | Mama |
| C51-C58 | Órgãos genitais femininos |
| C60-C63 | Órgãos genitais masculinos |
| C64-C68 | Trato urinário |
| C69-C72 | Olho, encéfalo e sistema nervoso central |
| C73-C75 | Glândulas endócrinas |
| C76-C80 | Localizações mal definidas, secundárias e não especificadas |
| C81-C96 | Tecido linfático, hematopoiético e correlatos |
| C97 | Neoplasias malignas independentes de localizações múltiplas |

## O que fica de fora e por quê

- **D00-D09 (carcinoma in situ)**: não é neoplasia maligna invasiva, e a inclusão mudaria
  a definição do desfecho sem ganho epidemiológico.
- **D10-D36 (neoplasias benignas)**: fora do escopo.
- **D37-D48 (comportamento incerto ou desconhecido)**: a ambiguidade de comportamento
  introduz ruído de classificação no numerador da série. Se algum dia entrarem, precisam
  entrar como série separada, não somadas em C.

Uma sensibilidade incluindo D37-D48 é um teste legítimo, mas precisa ser relatada como
análise de sensibilidade, não como a série principal.

## Câncer de pele não melanoma

C44 tem letalidade baixa e comportamento muito diferente do resto do capítulo. Em análise
por sítio, ele deve ser reportado separado. Na série agregada C00-C97 ele entra, por ser a
definição padrão usada pelo INCA e pela OMS para mortalidade por câncer.

## Fonte

DataSUS, SIM/CID10/DORES, arquivos `DO<UF><ANO>.dbc`. Extração em
`scripts/extract_sim_real.py`, validação em `scripts/validate_real_dataset.py`.
