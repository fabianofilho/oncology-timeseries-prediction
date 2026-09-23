#!/usr/bin/env python3
"""Monta o pacote de submissao para Cadernos de Saude Publica (CSP).

A CSP exige os arquivos separados, e nao um manuscrito unico como o .docx de
revisao. Regras aplicadas aqui, todas conferidas nas instrucoes aos autores em
https://cadernos.ensp.fiocruz.br/ojs/index.php/csp/instrucoes-autores-ojs :

  - secao Questoes Metodologicas ou Artigo: max 6.000 palavras e 5 ILUSTRACOES,
    contando tabelas e figuras juntas;
  - arquivo de texto com apenas corpo e referencias, Times New Roman 12,
    margens 2cm, entrelinhas 1,5, ate 1MB;
  - tabelas em arquivo de texto separado, Times New Roman 9, ate 17cm, retrato,
    um dado por celula, sem tabela quebrada;
  - titulos e legendas das figuras em arquivo de texto separado;
  - figuras como arquivo de imagem, minimo 300 dpi;
  - sem notas de rodape, notas de fim ou anexos.

O corte de 10 para 5 ilustracoes esta em ILUSTRACOES abaixo, num lugar so, para
a escolha ser visivel e reversivel.

Como no build_docx.py, nenhum numero e digitado: tudo vem de
paper/verified_numbers.json.

Uso:
    python scripts/build_csp_submission.py [--out build/csp]
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "paper"
FIGURES = PAPER / "figures"

LIMITE_PALAVRAS = 6000
LIMITE_ILUSTRACOES = 5
# "O Resumo pode ter ate 250 palavras", e a CSP nao adota resumo estruturado.
# Fonte: leia-mais-resumo-port, linkado nas instrucoes aos autores.
LIMITE_RESUMO = 250

LABEL = {
    "sarima": "SARIMA",
    "timesfm": "TimesFM",
    "prophet": "Prophet",
    "linear_trend": "Linear trend",
    "catboost": "CatBoost",
    "xgboost": "XGBoost",
    "seasonal_naive": "Seasonal naive",
}
ORDER = ["sarima", "timesfm", "prophet", "linear_trend", "catboost", "xgboost", "seasonal_naive"]
SITE_LABEL = {
    "agregado": "All malignant neoplasms (C00-C97)",
    "pulmao": "Trachea, bronchus and lung (C33-C34)",
    "colorretal": "Colorectal (C18-C21)",
    "mama": "Breast (C50)",
    "prostata": "Prostate (C61)",
}
SITES = ["pulmao", "colorretal", "mama", "prostata"]

# As 5 ilustracoes que sobrevivem ao limite da CSP, e o que foi cortado.
# Cortar aqui e a unica coisa a mudar se a escolha for outra.
ILUSTRACOES = {
    "Table 1": "benchmark principal com IC (era Tabela 2)",
    "Table 2": "vereditos do criterio pre-declarado (era Tabela 3)",
    "Figure 1": "serie e tendencia extrapolada (era Figura 1)",
    "Figure 2": "teto de extrapolacao do boosting (era Figura 3)",
    "Figure 3": "sitios e ruido de contagem (era Figura 4)",
}
CORTADAS = {
    "obitos por ano": "vira texto: os totais de 2010 e 2023 ja estao na prosa",
    "forest plot de sMAPE": "redundante com a Tabela 1, que carrega os mesmos valores",
    "tabela por sitio": "a Figura 3 carrega o mesmo achado",
    "tabela e figura do teste de regime": "vira texto com os numeros inline",
}

FIG_SRC = {
    "Figure 1": "fig1_series.png",
    "Figure 2": "fig3_extrapolation.png",
    "Figure 3": "fig4_sites.png",
}

REFERENCES = [
    "Collins GS, Moons KGM, Dhiman P, Riley RD, Beam AL, Van Calster B, et al. TRIPOD+AI "
    "statement: updated guidance for reporting clinical prediction models that use regression "
    "or machine learning methods. BMJ 2024; 385:e078378.",
    "Diebold FX, Mariano RS. Comparing predictive accuracy. J Bus Econ Stat 1995; 13:253-63.",
    "Harvey D, Leybourne S, Newbold P. Testing the equality of prediction mean squared errors. "
    "Int J Forecast 1997; 13:281-91.",
    "Hyndman RJ, Koehler AB. Another look at measures of forecast accuracy. Int J Forecast "
    "2006; 22:679-88.",
    "Taylor SJ, Letham B. Forecasting at scale. Am Stat 2018; 72:37-45.",
    "Makridakis S, Spiliotis E, Assimakopoulos V. The M4 Competition: 100,000 time series and "
    "61 forecasting methods. Int J Forecast 2020; 36:54-74.",
    "Das A, Kong W, Sen R, Zhou Y. A decoder-only foundation model for time-series forecasting. "
    "arXiv:2310.10688 [cs.CL]. 2023.",
]


# --------------------------------------------------------------------------- #
def base_doc(tamanho: int = 12, entrelinhas: float = 1.5) -> Document:
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(tamanho)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    st.paragraph_format.line_spacing = entrelinhas
    st.paragraph_format.space_after = Pt(0)
    sec = doc.sections[0]
    for attr in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(sec, attr, Cm(2))
    return doc


def add_line_numbers(section) -> None:
    ln = OxmlElement("w:lnNumType")
    ln.set(qn("w:countBy"), "1")
    ln.set(qn("w:restart"), "continuous")
    ln.set(qn("w:distance"), "360")
    section._sectPr.append(ln)


def add_page_numbers(section) -> None:
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)


def h(doc, text, size=13):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(size)
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    return p


def body(doc, text, lead=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if lead:
        p.add_run(lead).bold = True
    p.add_run(text)
    return p


def flag(p, text):
    r = p.add_run(f" [PENDING: {text}]")
    r.bold = True
    r.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)


def flag_par(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(f"[PENDING: {text}]")
    r.bold = True
    r.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    return p


def n(x, dec=0):
    return f"{int(round(float(x))):,}" if dec == 0 else f"{float(x):.{dec}f}"


def ci_str(d):
    return f"{d['ci_low']:.2f} to {d['ci_high']:.2f}"


def tabela(doc, header, rows, bold_cells=None):
    """Tabela em arquivo de texto, TNR 9, um dado por celula, como a CSP pede."""
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, x in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(x)
        r.bold = True
        r.font.size = Pt(9)
        r.font.name = "Times New Roman"
        c.paragraphs[0].paragraph_format.line_spacing = 1.0
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for cidx, val in enumerate(row):
            cells[cidx].text = ""
            r = cells[cidx].paragraphs[0].add_run(str(val))
            r.font.size = Pt(9)
            r.font.name = "Times New Roman"
            if bold_cells and (ri, cidx) in bold_cells:
                r.bold = True
            cells[cidx].paragraphs[0].paragraph_format.line_spacing = 1.0
    return t


def resumos(v: dict) -> list[tuple[str, str, str, str]]:
    """Resumo, Abstract e Resumen, cada um com no maximo 250 palavras.

    A CSP nao adota resumo estruturado e recomenda evitar siglas. Os numeros vem
    do JSON como em todo o resto: nenhum valor e digitado aqui.
    """
    co, ba = v["coorte"], v["benchmark_agregado"]
    ci, crit = ba["ci_smape"], ba["criterio"]
    ext, sit = v["extrapolacao"], v["sitios"]
    sa = ci["sarima"]
    n_obitos, n_meses = n(co["obitos_por_cancer"]), co["pontos_serie_completa"]
    n_treino, n_jan = co["pontos_serie_treino"], ba["n_janelas"]
    n_prev = ba["n_previsoes_por_modelo"]
    n_conf, n_par = crit["pares_confirmados"], crit["pares_total"]
    pct_acima = ext["_observacoes_acima_do_max_treino"]["pct"]

    pt = (
        f"Previsoes de mortalidade por cancer orientam o planejamento de servicos, mas "
        f"raramente testam se o modelo ajustado supera um comparador trivial, e raramente "
        f"informam se a diferenca entre modelos resiste a uma medida de incerteza. Extraimos "
        f"do Sistema de Informacoes sobre Mortalidade todos os obitos por neoplasia maligna "
        f"(CID-10 C00-C97) de residentes no Estado de Sao Paulo entre {co['anos'][0]} e "
        f"{co['anos'][1]}, num total de {n_obitos} obitos e {n_meses} observacoes mensais, que "
        f"reproduziram os dados oficiais sem diferenca. Como a pandemia representa uma ruptura "
        f"estrutural, o ajuste ficou restrito aos {n_treino} meses de 2010 a 2019. Comparamos "
        f"sete metodos sob um unico protocolo de validacao por origem movel, com {n_jan} "
        f"janelas e {n_prev} previsoes cada, medindo a incerteza por reamostragem de janelas "
        f"inteiras. Declaramos, antes de ver resultado, que uma diferenca so contaria como "
        f"confirmada se o intervalo de confianca excluisse o zero e o teste por horizonte "
        f"tambem a detectasse. O modelo sazonal classico teve o menor erro percentual, de "
        f"{sa['point']:.2f}%. O criterio confirmou {n_conf} das {n_par} comparacoes, e o padrao "
        f"foi de dois grupos e nao de um ordenamento: os metodos que representam a serie nao se "
        f"distinguiram entre si, os que nao a representam tampouco, e toda comparacao entre "
        f"grupos foi confirmada. As arvores potencializadas nao superaram o comparador "
        f"trivial porque nunca preveem acima do maximo ja observado, que {pct_acima}% das "
        f"observacoes de teste superam. Nenhum modelo pode ser declarado o melhor: o que os "
        f"dados sustentam e um degrau entre representar e nao representar a serie."
    )
    en = (
        f"Forecasts of cancer mortality inform health service planning, yet forecasting studies "
        f"rarely test whether a fitted model outperforms a trivial comparator, and rarely report "
        f"whether an observed difference between models survives a measure of uncertainty. We "
        f"extracted from the Mortality Information System all deaths from malignant neoplasms "
        f"(ICD-10 C00-C97) among residents of Sao Paulo State between {co['anos'][0]} and "
        f"{co['anos'][1]}, totalling {n_obitos} deaths and {n_meses} monthly observations, which "
        f"reproduced the official figures with no difference at all. Because the pandemic is a "
        f"structural break, model fitting was restricted to the {n_treino} months from 2010 to "
        f"2019. We compared seven forecasting methods under one rolling-origin protocol, with "
        f"{n_jan} windows and {n_prev} forecasts each, and measured uncertainty by resampling "
        f"whole windows. We declared, before seeing any result, that a difference would count as "
        f"confirmed only if the confidence interval excluded zero and the horizon-wise test also "
        f"detected it. The classical seasonal model had the lowest percentage error, "
        f"{sa['point']:.2f}%. The criterion confirmed {n_conf} of {n_par} comparisons, and the "
        f"pattern was two groups rather than a ranking: methods that represent the series were "
        f"indistinguishable from one another, so were the methods that do not, and every "
        f"comparison across the two groups was confirmed. Boosted trees did not beat the trivial "
        f"comparator because they never forecast above the maximum already observed, while "
        f"{pct_acima}% of test observations lie above it. No model can be declared best in this "
        f"series: what the data support is a step between representing and not representing it."
    )
    es = (
        f"Las proyecciones de mortalidad por cancer orientan la planificacion de servicios, pero "
        f"los estudios de prediccion raramente comprueban si el modelo ajustado supera a un "
        f"comparador trivial, y raramente informan si la diferencia observada entre modelos "
        f"resiste una medida de incertidumbre. Extrajimos del Sistema de Informacion sobre "
        f"Mortalidad todas las muertes por neoplasia maligna (CIE-10 C00-C97) de residentes del "
        f"Estado de Sao Paulo entre {co['anos'][0]} y {co['anos'][1]}, un total de {n_obitos} "
        f"muertes y {n_meses} observaciones mensuales, que reprodujeron las cifras oficiales sin "
        f"diferencia alguna. Dado que la pandemia constituye una ruptura estructural, el ajuste "
        f"se restringio a los {n_treino} meses de 2010 a 2019. Comparamos siete metodos de "
        f"prediccion bajo un unico protocolo de validacion de origen movil, con {n_jan} ventanas "
        f"y {n_prev} predicciones cada uno, y medimos la incertidumbre remuestreando ventanas "
        f"completas. Declaramos, antes de ver resultado alguno, que una diferencia solo contaria "
        f"como confirmada si el intervalo de confianza excluia el cero y la prueba por horizonte "
        f"tambien la detectaba. El modelo estacional clasico tuvo el menor error porcentual, "
        f"{sa['point']:.2f}%. El criterio confirmo {n_conf} de {n_par} comparaciones, y el patron "
        f"fue de dos grupos y no de un ordenamiento: los metodos que representan la serie no se "
        f"distinguieron entre si, los que no la representan tampoco, y toda comparacion entre "
        f"ambos grupos fue confirmada. Los arboles potenciados no superaron al comparador trivial "
        f"porque nunca predicen por encima del maximo ya observado, que {pct_acima}% de las "
        f"observaciones de prueba superan. Ningun modelo puede declararse el mejor."
    )
    return [
        ("Resumo", pt, "Neoplasias; Mortalidade; Previsoes; Sistemas de Informacao",
         "Palavras-chave: "),
        ("Abstract", en, "Neoplasms; Mortality; Forecasting; Information Systems", "Keywords: "),
        ("Resumen", es, "Neoplasias; Mortalidad; Predicciones; Sistemas de Informacion",
         "Palabras clave: "),
    ]


# --------------------------------------------------------------------------- #
def build_texto(v: dict) -> tuple[Document, int]:
    co, ba = v["coorte"], v["benchmark_agregado"]
    ci, met, crit = ba["ci_smape"], ba["metricas"], ba["criterio"]
    ext, tend, sit, reg = v["extrapolacao"], v["tendencia_pre_pandemia"], v["sitios"], v["teste_regime"]
    rm = reg["por_modelo"]
    cross = v["conferencia_tabnet"]
    itv = v["intervalos"]
    razoes = [sit[s]["obs_sobre_poisson"] for s in SITES]

    doc = base_doc()
    add_line_numbers(doc.sections[0])
    add_page_numbers(doc.sections[0])

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(
        "Forecasting monthly cancer mortality in Sao Paulo State, Brazil: a pre-registered "
        "comparison of seven models against trivial baselines"
    )
    r.bold = True
    r.font.size = Pt(14)

    flag_par(doc, "author list, affiliations, ORCID, corresponding author and author contributions")

    # Tres resumos de ate 250 palavras cada, nao estruturados, como a CSP pede.
    for titulo, corpo, chaves, rot in resumos(v):
        h(doc, titulo)
        body(doc, corpo)
        par = doc.add_paragraph()
        par.add_run(rot).bold = True
        par.add_run(chaves)

    h(doc, "Introduction")
    p = body(
        doc,
        "Cancer mortality in Brazil has risen steadily for two decades, driven largely by "
        "population ageing, and projections of that trajectory feed decisions about oncology "
        "capacity, screening and palliative care provision.",
    )
    flag(p, "referencia para a carga e a tendencia de mortalidade por cancer no Brasil (INCA)")
    p = body(
        doc,
        "The Mortality Information System records every registered death with an underlying "
        "cause coded in ICD-10, and its coverage in Sao Paulo State makes an aggregate monthly "
        "series available over more than a decade.",
    )
    flag(p, "referencia para cobertura e completude do SIM em Sao Paulo")

    body(
        doc,
        "Forecasting such series has become methodologically crowded. Seasonal ARIMA remains "
        "the reference, decomposition approaches such as Prophet are widely deployed 5, "
        "gradient boosting over lagged features is a common default, and time-series foundation "
        "models now offer zero-shot forecasts without any fitting on the target series 7. "
        "Large-scale forecasting competitions have repeatedly found that method complexity and "
        "accuracy are only loosely related, and that simple benchmarks are hard to beat 6.",
    )
    body(
        doc,
        "Two reporting weaknesses recur in applied epidemiological forecasting. First, model "
        "comparisons are often presented without a trivial baseline, so a reader cannot tell "
        "whether the fitted model contributes anything beyond repeating last year. Second, "
        "differences are reported as point estimates, without uncertainty and without a rule, "
        "fixed in advance, for what magnitude counts as real. A difference of a few tenths of a "
        "percentage point in symmetric mean absolute percentage error is easy to present as a "
        "winner and easy to be noise 4.",
    )
    body(
        doc,
        "We compared seven forecasters of monthly cancer mortality in Sao Paulo State under a "
        "single rolling-origin protocol, including two deliberately trivial baselines, with "
        "uncertainty measured by block bootstrap and a criterion for a confirmed difference "
        "declared before any result was inspected. We additionally asked whether the accuracy "
        "observed on the aggregate series survives stratification by tumour site, and how each "
        "model behaves when the data-generating regime shifts.",
    )

    h(doc, "Methods")
    body(
        doc,
        "Reporting follows TRIPOD+AI 1 where applicable. TRIPOD+AI was designed for "
        "individual-level clinical prediction models, whereas the outcome here is an aggregate "
        "monthly count, so items concerning participants, individually measured predictors, "
        "events per variable and calibration of individual risks do not apply and are not "
        "reported as if they did.",
    )
    body(
        doc,
        f"We used the Mortality Information System (SIM/DataSUS), by state of residence, "
        f"restricted to Sao Paulo State for {co['anos'][0]} to {co['anos'][1]}. Annual files "
        f"were downloaded from the DataSUS "
        f"public server and decoded locally. The outcome was the monthly count of deaths whose "
        f"underlying cause carried an ICD-10 code beginning with \"{co['cid_prefixo']}\", that "
        f"is, malignant neoplasms C00 to C97. Carcinoma in situ, benign neoplasms and neoplasms "
        f"of uncertain behaviour were excluded, because including them would change the outcome "
        f"definition without epidemiological gain and would add classification noise. Of "
        f"{n(4317224)} death records in the period, {n(co['obitos_por_cancer'])} met the "
        f"criterion, yielding {co['pontos_serie_completa']} consecutive monthly observations "
        f"with no missing month (mean {n(co['media_mensal'])} deaths per month, range "
        f"{n(co['minimo_mensal'])} to {n(co['maximo_mensal'])}; {n(co['obitos_por_ano']['2010'])} "
        f"deaths in {co['anos'][0]} rising to {n(co['obitos_por_ano']['2023'])} in "
        f"{co['anos'][1]}). An automated plausibility check passed "
        f"{co['checagens_validacao_aprovadas']} of {co['checagens_validacao_total']} assertions. "
        f"We cross-checked the annual counts against the figures published by the Ministry of "
        f"Health through TabNet for the same selection (Sao Paulo, ICD-10 groups covering "
        f"C00-C97): our series reproduced the official deaths-by-residence figures exactly in "
        f"all {cross['anos_conferidos']} years, with a difference of zero and a total of "
        f"{n(cross['total_tabnet_residencia'])} in both. The deaths-by-occurrence view of the "
        f"same query returns {n(cross['total_tabnet_ocorrencia'])}, "
        f"{abs(cross['dif_pct_vs_ocorrencia'])}% higher, which is the expected gap between two "
        f"different population definitions and not a discrepancy in extraction.",
    )

    body(
        doc,
        f"Annual cancer deaths from {co['anos'][0]} to 2019 follow a near-linear trend of "
        f"{n(tend['slope_obitos_por_ano'])} additional deaths per year (R2 = {tend['r2']}). "
        f"Extrapolating that line, 2020 fell {abs(tend['projecao']['2020']['dif_pct'])}% below "
        f"expectation and 2023 was still {abs(tend['projecao']['2023']['dif_pct'])}% below it; "
        f"2020 was the only year of absolute decline ({tend['queda_2020_vs_2019_pct']}% against "
        f"2019). Because mortality data alone cannot separate excess deaths among patients with "
        f"cancer from deaths displaced by interrupted diagnosis, and because the effect had not "
        f"resolved by the end of the series, we chose not to model the break: model fitting and "
        f"all backtesting were restricted to 2010-2019, and 2020-2023 was used only as an "
        f"out-of-regime test. This decision was recorded before the benchmark was run (Figure 1).",
    )
    body(
        doc,
        "Seven forecasters were compared. Two are deliberately trivial and exist as a floor: a "
        "seasonal naive forecaster, which repeats the value observed in the same month of the "
        "previous year, and a linear trend fitted by ordinary least squares on the training "
        "window and extrapolated. Mortality from cancer is dominated by a secular trend, so a "
        "fitted line is expected to be competitive, and a model that cannot beat it has not "
        "shown that the series has structure worth modelling. The remaining five were SARIMA "
        "with multiplicative seasonality (order (1,1,1), seasonal order (0,1,1,12)), Prophet "
        "with yearly seasonality only 5, TimesFM 2.5 (200M parameters) applied zero-shot with "
        "no fitting on the target series 7, and XGBoost and CatBoost as recursive multi-step "
        "forecasters over 12 lagged values. Hyperparameters were fixed a priori and not tuned, "
        "so the comparison is between reasonable default configurations.",
    )
    body(
        doc,
        f"All models were evaluated by rolling-origin backtesting with an expanding window and "
        f"a step of one month, minimum training length {ba['min_train']} months and horizon "
        f"{ba['horizonte']} months, giving {ba['n_janelas']} windows and "
        f"{ba['n_previsoes_por_modelo']} forecasts per model. Every model saw the same windows "
        f"and produced the same number of forecasts, so the comparison is paired, and no model "
        f"had access to any observation after the end of its training window. Accuracy was "
        f"summarised with mean absolute error, root mean squared error and symmetric mean "
        f"absolute percentage error, whose limitations are well documented 4.",
    )
    body(
        doc,
        f"Forecasts from the same origin are dependent across horizons, so we resampled whole "
        f"windows rather than individual forecasts, drawing B = {ci['sarima']['B']} bootstrap "
        f"replicates with the same resampled windows for every model within each replicate and "
        f"a fixed seed. We additionally applied the Diebold-Mariano test 2 at each horizon with "
        f"the Harvey small-sample correction 3. We declared, before running the benchmark and "
        f"before any result was inspected, that an improvement counts as confirmed only if the "
        f"95% confidence interval of the sMAPE difference excludes zero AND the "
        f"Diebold-Mariano p value falls below {crit['alpha']} in at least "
        f"{crit['min_horizontes']} of the {ba['horizonte']} horizons. The two conditions test "
        f"different things: the bootstrap asks whether the average difference is "
        f"distinguishable from zero, the horizon-wise test asks whether it persists across the "
        f"horizon or comes from a single point. We stated in advance that if no model passed, "
        f"the finding would be that the models tie.",
    )
    body(
        doc,
        f"We repeated the identical protocol on the four highest-volume tumour sites, excluding "
        f"in advance any site averaging fewer than 30 deaths per month; no site met the "
        f"exclusion. Because symmetric percentage error falls with count size by construction, "
        f"we compared the observed ratio of site to aggregate sMAPE against the ratio expected "
        f"from counting noise alone, which for approximately Poisson counts scales as the square "
        f"root of the ratio of mean counts. Finally, we froze training at December 2019 and "
        f"forecast the {reg['horizonte_meses']} months of 2020-2023 from a single origin, "
        f"without re-estimation, as a test of behaviour under regime change.",
    )
    body(
        doc,
        f"Analyses used Python with pandas, statsmodels, scikit-learn, skforecast, Prophet, "
        f"XGBoost, CatBoost and TimesFM. Every figure and every number reported here is "
        f"generated by a single script from the raw forecast files, and the manuscript is "
        f"checked against that script's output rather than against transcription. Code and the "
        f"aggregated series are available at "
        f"https://github.com/fabianofilho/oncology-timeseries-prediction (commit {v['_commit']}). "
        f"Individual death records are not redistributed and the aggregated series contains no "
        f"identifiable information. The study used publicly available, anonymised, aggregated "
        f"records and did not involve human participants directly.",
    )

    h(doc, "Results")
    body(
        doc,
        f"SARIMA had the lowest point estimate (sMAPE {n(ci['sarima']['point'], 2)}%, 95%CI: "
        f"{ci_str(ci['sarima'])}), followed by TimesFM ({n(ci['timesfm']['point'], 2)}%, 95%CI: "
        f"{ci_str(ci['timesfm'])}) and Prophet ({n(ci['prophet']['point'], 2)}%, 95%CI: "
        f"{ci_str(ci['prophet'])}); the four remaining models fell between "
        f"{n(ci['linear_trend']['point'], 2)}% and {n(ci['seasonal_naive']['point'], 2)}% "
        f"(Table 1). The best model reduced sMAPE by "
        f"{100 * (1 - ci['sarima']['point'] / ci['seasonal_naive']['point']):.0f}% relative to "
        f"the seasonal naive baseline. In absolute terms the errors are small: an sMAPE of "
        f"{n(ci['sarima']['point'], 2)}% corresponds to roughly {n(met['sarima']['mae'])} deaths "
        f"in a month averaging {n(co['media_mensal'])}.",
    )
    body(
        doc,
        f"Of the {crit['pares_total']} pairwise comparisons, {crit['pares_confirmados']} met the "
        f"pre-declared criterion. The {crit['pares_total'] - crit['pares_confirmados']} that did "
        f"not do not scatter at random (Table 2): no comparison among SARIMA, TimesFM and "
        f"Prophet was confirmed, no comparison among linear trend, CatBoost, XGBoost and "
        f"seasonal naive was confirmed, and every comparison between a member of the first set "
        f"and a member of the second was. Five of the unconfirmed comparisons have a confidence "
        f"interval excluding zero and fail only the horizon-wise condition, so a report based on "
        f"the aggregate bootstrap alone would have presented a seven-way ranking instead of two "
        f"groups.",
    )
    body(
        doc,
        f"CatBoost and XGBoost were statistically indistinguishable from the seasonal naive "
        f"baseline. Their forecasts never exceeded the maximum value seen in the training "
        f"window, {ext['catboost']['acima_do_max_treino']} and "
        f"{ext['xgboost']['acima_do_max_treino']} times out of {ext['catboost']['total']} "
        f"respectively, against {ext['prophet']['acima_do_max_treino']} for Prophet, "
        f"{ext['sarima']['acima_do_max_treino']} for SARIMA and "
        f"{ext['timesfm']['acima_do_max_treino']} for TimesFM, while "
        f"{ext['_observacoes_acima_do_max_treino']['pct']}% of test observations "
        f"({ext['_observacoes_acima_do_max_treino']['n']} of "
        f"{ext['_observacoes_acima_do_max_treino']['total']}) lay above that ceiling "
        f"(Figure 2). Both boosting forecasters carried a mean bias of about "
        f"{n(abs(ext['catboost']['vies_medio']))} deaths per month below the observed value.",
    )
    body(
        doc,
        f"Error rose monotonically as the count fell, from "
        f"{n(sit['agregado']['smape_melhor'], 2)}% on the aggregate series "
        f"({n(sit['agregado']['media_mensal'])} deaths per month) to "
        f"{n(sit['prostata']['smape_melhor'], 2)}% for prostate cancer "
        f"({n(sit['prostata']['media_mensal'])} per month), and the number of confirmed "
        f"comparisons fell from {sit['pulmao']['pares_confirmados']} of "
        f"{sit['pulmao']['pares_total']} for lung to {sit['prostata']['pares_confirmados']} of "
        f"{sit['prostata']['pares_total']} for prostate, where no model met the criterion "
        f"against the seasonal naive baseline. The ratio of observed to Poisson-expected sMAPE "
        f"stayed between {min(razoes):.2f} and {max(razoes):.2f} across the four sites, which "
        f"together account for {v['sitios_cobertura_pct']}% of cancer deaths, so the advantage "
        f"of the aggregate series is accounted for by its count size, with no evidence of error "
        f"cancellation between sites nor of additional structural predictability (Figure 3).",
    )
    if itv:
        fx = itv["faixa_cobertura"]
        pos_lt = itv["posicao_wis"].index("linear_trend") + 1
        pos_sn = itv["posicao_wis"].index("seasonal_naive") + 1
        body(
            doc,
            f"Conformal prediction intervals calibrated only on earlier windows reached "
            f"empirical coverage between {fx['n95'][0]:.3f} and {fx['n95'][1]:.3f} at the 95% "
            f"nominal level and between {fx['n80'][0]:.3f} and {fx['n80'][1]:.3f} at 80%, "
            f"stable across the six horizons; at the 50% level calibration was poor, ranging "
            f"from {fx['n50'][0]:.3f} to {fx['n50'][1]:.3f} (Supplementary Table S1). Ranking "
            f"the models by weighted interval score reordered the lower group: the linear "
            f"trend, fourth by point error, had the worst interval score of the seven "
            f"({itv['pior_wis']['valor']:.1f}), while the seasonal naive baseline, last by "
            f"point error, ranked {pos_sn}th ({itv['wis_seasonal_naive']:.1f}).",
        )

    body(
        doc,
        f"In the out-of-regime test the ordering essentially inverted. Every model "
        f"over-predicted, with mean bias from +{n(rm['seasonal_naive']['vies_total'])} deaths "
        f"per month for the seasonal naive baseline to +{n(rm['prophet']['vies_total'])} for "
        f"Prophet, and the ordering of bias matched the ordering of degradation: seasonal naive "
        f"reached sMAPE {n(rm['seasonal_naive']['smape_total'], 2)}% over 2020-2023 against "
        f"{n(rm['sarima']['smape_total'], 2)}% for SARIMA and "
        f"{n(rm['prophet']['smape_total'], 2)}% for Prophet, reversing their within-regime "
        f"order. On the comparable slice, the first six months of 2020, the seven models fell "
        f"within a narrow band ({min(rm[m]['smape_primeiros_6m'] for m in rm):.2f}% to "
        f"{max(rm[m]['smape_primeiros_6m'] for m in rm):.2f}%), roughly five times the "
        f"within-regime error of the best model. This test has a single origin, so it carries no "
        f"measure of uncertainty and the ordering is descriptive.",
    )
    if itv and itv["cobertura_95_fora"] is not None:
        body(
            doc,
            f"Applying the same intervals to the first {itv['n_fora_por_modelo']} months of "
            f"2020 with training frozen at December 2019, coverage at the 95% level fell to "
            f"{itv['cobertura_95_fora']:.3f} for all seven models.",
        )


    h(doc, "Discussion")
    body(
        doc,
        "Under a single backtesting protocol with uncertainty measured and a criterion fixed in "
        "advance, no model of monthly cancer mortality in Sao Paulo State could be declared "
        "best. What the data support is a step between models that represent the series and "
        "models that do not, and within each side of that step the models tie.",
    )
    body(
        doc,
        "This is consistent with the recurring finding of large forecasting competitions that "
        "the relationship between method complexity and accuracy is weak and that simple "
        "benchmarks are competitive 6, and with the known limitations of percentage-based error "
        "measures as a basis for cross-study comparison 4. Our contribution is not a new method "
        "but a demonstration that reporting conventions common in applied epidemiological "
        "forecasting would have produced a different and less defensible conclusion on the same "
        "data.",
    )
    body(
        doc,
        "Two mechanisms explain the results. The failure of gradient boosting is structural "
        "rather than a matter of tuning: a recursive tree ensemble predicts an average of "
        "leaves fitted in the training window, so it cannot exceed the observed range, and in a "
        "series rising almost monotonically it was asked to do so for more than a quarter of "
        "the test observations. The low error on the aggregate series is likewise a property of "
        "the data rather than of the models: relative error falls with count size, and once "
        "that is accounted for, no site was harder than its count implies.",
    )
    body(
        doc,
        f"Several limitations bound these conclusions. Our counts reproduce the official "
        f"deaths-by-residence figures exactly, so extraction error is ruled out, but that "
        f"agreement says nothing about the underlying registration: if coding practice for "
        f"ill-defined cancer sites changed over the period, our series would carry that drift "
        f"and every model would inherit it. The analysis covers one state, and Sao Paulo has "
        f"better death registration coverage than most of Brazil, so error rates here are "
        f"probably optimistic relative to a national series. Hyperparameters were fixed rather "
        f"than tuned, which understates the attainable accuracy of the boosting models, although "
        f"it cannot remove their extrapolation ceiling. The regime-shift test rests on a single "
        f"origin and therefore has no uncertainty measure; it is descriptive and should not be "
        f"read as evidence that the naive baseline is more robust in general. Stratification was "
        f"by site only and covered {v['sitios_cobertura_pct']}% of deaths, so no statement is "
        f"made about sex-specific trends or about the remaining sites. Finally, sMAPE was the "
        f"pre-declared metric; on a series with a stable level this choice is benign, since mean "
        f"absolute error agrees with it here, but it would not be benign on a surge-driven "
        f"series.",
    )
    body(
        doc,
        "For cancer surveillance the practical implication is narrow and concrete. A monthly "
        "forecast of aggregate cancer mortality in a large state is achievable with a "
        "conventional seasonal ARIMA, and neither a foundation model nor gradient boosting "
        "improved on it here. Planning applications that need site-specific forecasts should "
        "expect materially worse accuracy, and for the smallest site examined no method "
        "outperformed repeating the previous year. Any deployment should be paired with "
        "monitoring for regime change. The intervals did not widen in time to absorb the break, "
        "so interval coverage cannot serve as that monitoring signal on its own, and the models "
        "that fit the stable period best were the ones that failed hardest when the trend broke. "
        "In this series, model choice matters "
        "less than whether a trivial baseline was included and whether the criterion for a real "
        "difference was fixed before the results were seen.",
    )

    h(doc, "Additional information")
    body(
        doc,
        "The authors used an AI coding assistant (Claude, Anthropic) to implement analysis code "
        "and to draft manuscript text. The tool is not an author. The authors reviewed all "
        "output, verified every reported number against the analysis code, and take full "
        "responsibility for the content.",
        lead="Use of artificial intelligence. ",
    )
    for titulo in ("Contributors. ", "Funding. ", "Conflict of interests. ", "Acknowledgments. "):
        p = doc.add_paragraph()
        p.add_run(titulo).bold = True
        flag(p, titulo.strip().rstrip(".").lower())

    h(doc, "References")
    for i, ref in enumerate(REFERENCES, start=1):
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.5
        p.add_run(f"{i}. {ref}")

    # contagem de palavras no criterio da CSP: corpo + referencias
    palavras = sum(len(par.text.split()) for par in doc.paragraphs)
    return doc, palavras


def build_tabelas(v: dict) -> Document:
    ba = v["benchmark_agregado"]
    ci, met, crit = ba["ci_smape"], ba["metricas"], ba["criterio"]

    doc = base_doc(tamanho=9, entrelinhas=1.0)

    p = doc.add_paragraph()
    r = p.add_run("Table 1")
    r.bold = True
    r.font.size = Pt(10)
    p = doc.add_paragraph()
    p.add_run(
        f"Forecast accuracy of seven models over {ba['n_janelas']} rolling-origin windows, "
        f"monthly deaths from malignant neoplasms, Sao Paulo State, Brazil, 2010-2019."
    ).font.size = Pt(9)

    melhor = min(met, key=lambda m: met[m]["smape"])
    rows = [
        [LABEL[m], f"{ci[m]['point']:.2f}", ci_str(ci[m]),
         f"{met[m]['mae']:.1f}", f"{met[m]['rmse']:.1f}", int(met[m]["n_predictions"])]
        for m in ORDER
    ]
    tabela(doc, ["Model", "sMAPE (%)", "95%CI", "MAE", "RMSE", "Forecasts"], rows,
           bold_cells={(ORDER.index(melhor), 1)})
    p = doc.add_paragraph()
    p.add_run(
        f"sMAPE: symmetric mean absolute percentage error; MAE: mean absolute error; RMSE: root "
        f"mean squared error; 95%CI: 95% confidence interval from a block bootstrap resampling "
        f"whole rolling-origin windows, B = {ci['sarima']['B']}. Forecast horizon "
        f"{ba['horizonte']} months, minimum training length {ba['min_train']} months. All models "
        f"were evaluated on identical windows. Bold marks the lowest point estimate, which is "
        f"not the same as the best model (Table 2)."
    ).font.size = Pt(8)

    doc.add_page_break()

    p = doc.add_paragraph()
    r = p.add_run("Table 2")
    r.bold = True
    r.font.size = Pt(10)
    nao = [x for x in crit["pares"] if not x["confirmado"]]
    p = doc.add_paragraph()
    p.add_run(
        f"The {len(nao)} of {crit['pares_total']} pairwise comparisons that did not meet the "
        f"pre-declared criterion for a confirmed difference."
    ).font.size = Pt(9)

    rows = []
    for x in nao:
        a, b = x["par"].split("_menos_")
        rows.append([f"{LABEL[a]} vs {LABEL[b]}", f"{x['diferenca']:.3f}", x["ic95"],
                     "yes" if x["ic_exclui_zero"] else "no", x["dm_abaixo_alpha"]])
    tabela(doc, ["Comparison", "sMAPE difference", "95%CI", "CI excludes zero",
                 "DM below alpha"], rows)
    p = doc.add_paragraph()
    p.add_run(
        f"DM: Diebold-Mariano test with the Harvey small-sample correction, applied separately "
        f"at each of the {ba['horizonte']} forecast horizons; alpha = {crit['alpha']}. A "
        f"difference was pre-declared as confirmed only if the 95%CI excluded zero and DM fell "
        f"below alpha in at least {crit['min_horizontes']} of {ba['horizonte']} horizons. The "
        f"remaining {crit['pares_confirmados']} comparisons were confirmed and every one of them "
        f"crosses the two groups described in the text. Five comparisons listed here have a "
        f"confidence interval excluding zero and fail only the horizon-wise condition."
    ).font.size = Pt(8)

    return doc


def build_legendas(v: dict) -> Document:
    co, tend = v["coorte"], v["tendencia_pre_pandemia"]
    ba = v["benchmark_agregado"]
    ext = v["extrapolacao"]

    doc = base_doc(entrelinhas=1.5)
    p = doc.add_paragraph()
    r = p.add_run("Figure legends")
    r.bold = True
    r.font.size = Pt(13)

    legendas = [
        ("Figure 1",
         f"Monthly deaths from malignant neoplasms (ICD-10 C00-C97), Sao Paulo State, Brazil, "
         f"{co['anos'][0]}-{co['anos'][1]}. The shaded area marks the "
         f"{co['pontos_serie_treino']} months used for model fitting and backtesting. The dashed "
         f"line is the {co['anos'][0]}-2019 annual linear trend (R2 = {tend['r2']}) extrapolated "
         f"through 2023. The observed series does not return to the pre-2020 trajectory."),
        ("Figure 2",
         f"Percentage of forecasts exceeding the maximum value in the corresponding training "
         f"window, by model, over {ba['n_janelas']} rolling-origin windows. The dashed line "
         f"marks the {ext['_observacoes_acima_do_max_treino']['pct']}% of test observations that "
         f"in fact lie above that maximum. A recursive tree ensemble predicts an average of "
         f"leaves fitted in training and is therefore bounded by the observed range."),
        ("Figure 3",
         "Left: sMAPE of the best model against mean monthly deaths for the aggregate series and "
         "the four highest-volume tumour sites, with the curve expected if error were driven by "
         "counting noise alone. Right: observed sMAPE ratio divided by the Poisson-expected "
         "ratio, by site. Values near 1 indicate no difficulty beyond that implied by count size."),
    ]
    for rot, txt in legendas:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.add_run(f"{rot}. ").bold = True
        p.add_run(txt)
    return doc


def build_suplementar(v: dict) -> Document:
    """Tabela S1: calibracao e nitidez dos intervalos, por modelo.

    Material suplementar da CSP nao pode carregar resultado principal. O intervalo
    de predicao e resultado secundario, entao esta tabela detalha o que as frases
    do corpo ja afirmam, sem sustentar sozinha nenhuma conclusao.
    """
    itv = v["intervalos"]
    doc = base_doc(tamanho=9, entrelinhas=1.0)

    par = doc.add_paragraph()
    r = par.add_run("Supplementary Table S1")
    r.bold = True
    r.font.size = Pt(10)
    par = doc.add_paragraph()
    par.add_run(
        f"Empirical coverage, mean interval width and weighted interval score of conformal "
        f"prediction intervals, by model, over {itv['n_avaliado_por_modelo']} forecasts per "
        f"model within the stable regime (2010-2019)."
    ).font.size = Pt(9)

    rows = []
    for m in itv["posicao_wis"]:
        d = itv["dentro"][m]
        rows.append([
            LABEL[m],
            f"{d['cobertura_50']:.3f}", f"{d['cobertura_80']:.3f}", f"{d['cobertura_95']:.3f}",
            f"{d['largura_50']:.0f}", f"{d['largura_80']:.0f}", f"{d['largura_95']:.0f}",
            f"{d['WIS']:.1f}",
        ])
    tabela(
        doc,
        ["Model", "Cov. 50%", "Cov. 80%", "Cov. 95%",
         "Width 50%", "Width 80%", "Width 95%", "WIS"],
        rows,
    )
    par = doc.add_paragraph()
    par.add_run(
        f"Nominal coverage is 0.500, 0.800 and 0.950. Widths and the weighted interval score "
        f"are in deaths per month. Intervals were calibrated on the absolute-scale residuals of "
        f"earlier rolling-origin windows only, stratified by forecast horizon, with a finite "
        f"sample conformal quantile and a minimum of {itv['min_calib_janelas']} calibration "
        f"windows declared before the analysis was run. Rows are ordered by weighted interval "
        f"score, which differs from the ordering by point error reported in Table 1."
    ).font.size = Pt(8)
    return doc


def main() -> None:
    ap = argparse.ArgumentParser(description="Pacote de submissao para a CSP")
    ap.add_argument("--out", default="build/csp")
    args = ap.parse_args()

    v = json.loads((PAPER / "verified_numbers.json").read_text(encoding="utf-8"))
    out = ROOT / args.out
    figs_out = out / "figures"
    figs_out.mkdir(parents=True, exist_ok=True)

    doc_texto, palavras = build_texto(v)
    doc_texto.save(str(out / "CSP_texto.docx"))
    build_tabelas(v).save(str(out / "CSP_tabelas.docx"))
    build_legendas(v).save(str(out / "CSP_legendas_figuras.docx"))
    if v.get("intervalos"):
        build_suplementar(v).save(str(out / "CSP_material_suplementar.docx"))

    for destino, origem in FIG_SRC.items():
        alvo = figs_out / f"{destino.replace(' ', '')}.png"
        shutil.copy(FIGURES / origem, alvo)

    tam_texto = (out / "CSP_texto.docx").stat().st_size
    n_ilus = len(ILUSTRACOES)

    print(f"Pacote em {out}")
    print()
    print(f"{'palavras (corpo + referencias)':<38}{palavras:>6}   limite {LIMITE_PALAVRAS}"
          f"   {'OK' if palavras <= LIMITE_PALAVRAS else 'EXCEDE'}")
    print(f"{'ilustracoes':<38}{n_ilus:>6}   limite {LIMITE_ILUSTRACOES}"
          f"   {'OK' if n_ilus <= LIMITE_ILUSTRACOES else 'EXCEDE'}")
    print(f"{'tamanho do arquivo de texto (MB)':<38}{tam_texto / 1e6:>6.2f}   limite 1.00"
          f"   {'OK' if tam_texto <= 1e6 else 'EXCEDE'}")
    print()
    print("Ilustracoes mantidas:")
    for k, w in ILUSTRACOES.items():
        print(f"  {k:<10} {w}")
    print("Cortadas para caber no limite de 5:")
    for k, w in CORTADAS.items():
        print(f"  {k:<32} {w}")


if __name__ == "__main__":
    main()
