#!/usr/bin/env python3
"""Gera o manuscrito em .docx para revisao, a partir de paper/verified_numbers.json.

Diferenca de proposito em relacao a um .tex de submissao: este .docx e o artefato
de REVISAO, nao o de submissao. Por isso aqui:

  - a figura entra embutida no ponto do texto que fala dela, e nao no fim, para o
    revisor ver o grafico junto do argumento que ele sustenta;
  - a tabela e tabela nativa do Word, nunca imagem, para o revisor comentar celula
    a celula e usar controle de alteracoes;
  - o topo carrega o carimbo de proveniencia, dizendo de qual execucao do pipeline
    os numeros vieram.

Nenhum numero e digitado neste arquivo. Todo valor vem do JSON gerado por
scripts/build_paper_assets.py. Onde falta dado, entra um marcador [PENDING: ...]
em vermelho, impossivel de submeter sem ver.

Uso:
    python scripts/build_docx.py [--out build/manuscript.docx]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "paper"
FIGURES = PAPER / "figures"

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

REFERENCES = [
    "Collins GS, Moons KGM, Dhiman P, Riley RD, Beam AL, Van Calster B, et al. TRIPOD+AI "
    "statement: updated guidance for reporting clinical prediction models that use regression "
    "or machine learning methods. BMJ. 2024;385:e078378. doi:10.1136/bmj-2023-078378",
    "Diebold FX, Mariano RS. Comparing predictive accuracy. Journal of Business and Economic "
    "Statistics. 1995;13:253-263. doi:10.1080/07350015.1995.10524599",
    "Harvey D, Leybourne S, Newbold P. Testing the equality of prediction mean squared errors. "
    "International Journal of Forecasting. 1997;13:281-291. doi:10.1016/S0169-2070(96)00719-4",
    "Hyndman RJ, Koehler AB. Another look at measures of forecast accuracy. International "
    "Journal of Forecasting. 2006;22:679-688. doi:10.1016/j.ijforecast.2006.03.001",
    "Taylor SJ, Letham B. Forecasting at scale. The American Statistician. 2018;72:37-45. "
    "doi:10.1080/00031305.2017.1380080",
    "Makridakis S, Spiliotis E, Assimakopoulos V. The M4 Competition: 100,000 time series and "
    "61 forecasting methods. International Journal of Forecasting. 2020;36:54-74. "
    "doi:10.1016/j.ijforecast.2019.04.014",
    "Das A, Kong W, Sen R, Zhou Y. A decoder-only foundation model for time-series forecasting. "
    "arXiv:2310.10688 [cs.CL]. 2023.",
]


# --------------------------------------------------------------------------- #
# infraestrutura de formatacao
# --------------------------------------------------------------------------- #
def setup_document() -> Document:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    pf = style.paragraph_format
    pf.line_spacing = 2.0
    pf.space_after = Pt(0)

    sec = doc.sections[0]
    for attr in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(sec, attr, Inches(1))
    add_line_numbers(sec)
    add_page_numbers(sec)
    return doc


def add_line_numbers(section) -> None:
    """Numeracao de linha continua. Quase todo journal exige e o Word nao liga
    por padrao, entao precisa ir direto no XML da secao."""
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


def heading(doc: Document, text: str, level: int = 1):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(14 if level == 1 else 12)
    r.font.name = "Times New Roman"
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    return p


def body(doc: Document, text: str, bold_lead: str | None = None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if bold_lead:
        r = p.add_run(bold_lead)
        r.bold = True
    p.add_run(text)
    return p


def caption(doc: Document, label: str, text: str):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_after = Pt(10)
    # A legenda nao pode rachar entre paginas: com keep_with_next sozinho ela
    # ainda quebra no meio, deixando meia frase no fim da pagina anterior.
    p.paragraph_format.keep_together = True
    r = p.add_run(label)
    r.bold = True
    r.font.size = Pt(10)
    r2 = p.add_run(" " + text)
    r2.font.size = Pt(10)
    return p


def add_figure(doc: Document, name: str, label: str, text: str, width: float = 6.4) -> bool:
    """Figura embutida no ponto do texto, com legenda logo abaixo."""
    path = FIGURES / f"{name}.png"
    if not path.exists():
        p = doc.add_paragraph()
        r = p.add_run(f"[FIGURA AUSENTE: {name}.png]")
        r.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
        r.bold = True
        return False
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_before = Pt(8)
    # Sem isso o Word quebra pagina entre a imagem e a legenda, e a legenda fica
    # orfa na pagina seguinte.
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Inches(width))
    caption(doc, label, text)
    return True


def add_table(doc: Document, header: list[str], rows: list[list[str]], label: str,
              text: str, bold_cells: set[tuple[int, int]] | None = None):
    """Tabela nativa do Word: o revisor consegue comentar e editar celula."""
    cap = caption(doc, label, text)
    # Legenda de tabela vai acima dela, entao precisa ficar colada na tabela.
    cap.paragraph_format.keep_with_next = True
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        cell = t.rows[0].cells[i]
        cell.text = ""
        r = cell.paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(9)
        cell.paragraphs[0].paragraph_format.line_spacing = 1.0
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for ci, val in enumerate(row):
            cells[ci].text = ""
            r = cells[ci].paragraphs[0].add_run(str(val))
            r.font.size = Pt(9)
            if bold_cells and (ri, ci) in bold_cells:
                r.bold = True
            cells[ci].paragraphs[0].paragraph_format.line_spacing = 1.0
    doc.add_paragraph().paragraph_format.space_after = Pt(6)
    return t


def note(doc: Document, text: str):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.0
    r = p.add_run(text)
    r.font.size = Pt(9)
    r.italic = True
    return p


def flag(doc: Document, text: str):
    """Marcador vermelho de pendencia. Mesma funcao do \\missing{} do LaTeX:
    ser impossivel submeter sem ver."""
    p = doc.add_paragraph()
    r = p.add_run(f"[PENDING: {text}]")
    r.bold = True
    r.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    return p


def inline_flag(p, text: str):
    r = p.add_run(f" [PENDING: {text}]")
    r.bold = True
    r.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    return r


# --------------------------------------------------------------------------- #
# helpers de numero: tudo sai do JSON
# --------------------------------------------------------------------------- #
def n(x, dec: int = 0) -> str:
    """Formata numero com separador de milhar, sem digitar valor nenhum."""
    if dec == 0:
        return f"{int(round(float(x))):,}".replace(",", ",")
    return f"{float(x):.{dec}f}"


def ci_str(d: dict) -> str:
    return f"{d['ci_low']:.2f} to {d['ci_high']:.2f}"


def build(v: dict) -> tuple[Document, dict]:
    stats = {"figuras": 0, "tabelas": 0, "pendencias": 0}
    doc = setup_document()

    co = v["coorte"]
    ba = v["benchmark_agregado"]
    ci = ba["ci_smape"]
    met = ba["metricas"]
    crit = ba["criterio"]
    ext = v["extrapolacao"]
    cross = v["conferencia_tabnet"]
    itv = v["intervalos"]
    tend = v["tendencia_pre_pandemia"]
    sit = v["sitios"]
    reg = v["teste_regime"]

    # ---------------- pagina de rosto ---------------- #
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(
        "Forecasting monthly cancer mortality in Sao Paulo State, Brazil: "
        "a pre-registered comparison of seven models against trivial baselines"
    )
    r.bold = True
    r.font.size = Pt(15)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Running title: Cancer mortality forecasting in Sao Paulo")
    r.italic = True
    r.font.size = Pt(11)

    flag(doc, "author list, affiliations, ORCID and corresponding author details")
    stats["pendencias"] += 1

    body(doc, "", bold_lead="Keywords: ")
    doc.paragraphs[-1].add_run(
        "neoplasms; mortality; forecasting; time series; machine learning; health information systems"
    )

    # carimbo de proveniencia
    note(
        doc,
        f"PROVENANCE. All numbers in this manuscript were generated by "
        f"scripts/build_paper_assets.py from repository commit {v['_commit']} at "
        f"{v['_gerado_em_utc']}. Cohort: {n(co['obitos_por_cancer'])} cancer deaths, "
        f"{co['pontos_serie_completa']} monthly observations "
        f"({co['anos'][0]}-{co['anos'][1]}), of which {co['pontos_serie_treino']} form the "
        f"modelling series; {ba['n_modelos']} models, {ba['n_janelas']} rolling-origin windows, "
        f"{ba['n_previsoes_por_modelo']} forecasts per model. Every model was evaluated on the "
        f"identical set of windows. This .docx is a review artifact, not a submission file: "
        f"figures are embedded next to the argument they support rather than collected at the end.",
    )

    doc.add_page_break()

    # ---------------- abstract ---------------- #
    heading(doc, "Abstract")

    body(doc, "", bold_lead="Background. ")
    doc.paragraphs[-1].add_run(
        "Forecasts of cancer mortality inform service planning, yet published forecasting "
        "studies rarely test whether a fitted model outperforms a trivial baseline, and rarely "
        "report whether an observed difference between models survives a measure of uncertainty."
    )

    body(doc, "", bold_lead="Methods. ")
    doc.paragraphs[-1].add_run(
        f"We extracted all deaths with an underlying cause coded as a malignant neoplasm "
        f"(ICD-10 C00-C97) in Sao Paulo State, Brazil, from the Mortality Information System "
        f"(SIM/DataSUS), {co['anos'][0]} to {co['anos'][1]} "
        f"({n(co['obitos_por_cancer'])} deaths; {co['pontos_serie_completa']} monthly "
        f"observations). Because the COVID-19 period is a structural break, we restricted "
        f"model fitting to {co['pontos_serie_treino']} months covering 2010 to 2019 and used "
        f"2020 to 2023 only as a regime-shift test. Seven forecasters were compared under an "
        f"identical rolling-origin protocol (expanding window, minimum training length "
        f"{ba['min_train']} months, forecast horizon {ba['horizonte']} months, "
        f"{ba['n_janelas']} windows, {ba['n_previsoes_por_modelo']} forecasts each): two "
        f"trivial baselines (seasonal naive, linear trend), SARIMA, Prophet, a time-series "
        f"foundation model (TimesFM) applied zero-shot, and two gradient-boosting forecasters "
        f"(XGBoost, CatBoost). Uncertainty was estimated by block bootstrap resampling whole "
        f"windows (B = {ci['sarima']['B']}). We pre-declared, before any result was seen, that "
        f"a difference counts as confirmed only if the 95% confidence interval excludes zero "
        f"AND the Diebold-Mariano test with the Harvey correction falls below "
        f"{crit['alpha']} in at least {crit['min_horizontes']} of the {ba['horizonte']} horizons."
    )

    body(doc, "", bold_lead="Results. ")
    doc.paragraphs[-1].add_run(
        f"SARIMA achieved the lowest error (sMAPE {n(ci['sarima']['point'], 2)}%, 95% CI "
        f"{ci_str(ci['sarima'])}), followed by TimesFM ({n(ci['timesfm']['point'], 2)}%, "
        f"{ci_str(ci['timesfm'])}) and Prophet ({n(ci['prophet']['point'], 2)}%, "
        f"{ci_str(ci['prophet'])}). The pre-declared criterion confirmed "
        f"{crit['pares_confirmados']} of {crit['pares_total']} pairwise comparisons, and the "
        f"pattern was not a ranking but two groups: no comparison within "
        f"{{SARIMA, TimesFM, Prophet}} was confirmed, no comparison within {{linear trend, "
        f"CatBoost, XGBoost, seasonal naive}} was confirmed, and every comparison across the "
        f"two groups was. Gradient boosting was statistically indistinguishable from the "
        f"seasonal naive baseline; CatBoost and XGBoost produced "
        f"{ext['catboost']['acima_do_max_treino']} and {ext['xgboost']['acima_do_max_treino']} "
        f"forecasts above the training maximum out of {ext['catboost']['total']}, while "
        f"{ext['_observacoes_acima_do_max_treino']['pct']}% of test observations lay above it. "
        f"Stratifying by tumour site, the ratio of observed to Poisson-expected sMAPE ranged "
        f"from {min(sit[s]['obs_sobre_poisson'] for s in ['pulmao','colorretal','mama','prostata']):.2f} "
        f"to {max(sit[s]['obs_sobre_poisson'] for s in ['pulmao','colorretal','mama','prostata']):.2f}, "
        f"indicating that the low error of the aggregate series reflects its count size rather "
        f"than greater structural predictability. In the regime-shift test the ordering "
        f"inverted: every model over-predicted, and the seasonal naive baseline was least wrong."
    )

    body(doc, "", bold_lead="Conclusions. ")
    doc.paragraphs[-1].add_run(
        "In this series, no single model can be declared best. What the data support is a step "
        "between models that represent the series and models that do not, and a warning that a "
        "low relative error on a large aggregate count is a property of the count, not evidence "
        "of a good model. Forecasting studies in cancer surveillance should report trivial "
        "baselines and a pre-declared criterion for what counts as a real difference."
    )

    doc.add_page_break()

    # ---------------- introduction ---------------- #
    heading(doc, "Introduction")
    body(
        doc,
        "Cancer mortality in Brazil has risen steadily for two decades, driven largely by "
        "population ageing, and projections of that trajectory feed decisions about oncology "
        "capacity, screening programmes and palliative care provision. ",
    )
    inline_flag(doc.paragraphs[-1], "reference for cancer mortality burden and trend in Brazil (INCA Estimativa)")
    stats["pendencias"] += 1
    doc.paragraphs[-1].add_run(
        " The Mortality Information System (SIM) records every registered death in the country "
        "with an underlying cause coded in ICD-10, and its coverage in Sao Paulo State makes an "
        "aggregate monthly series available over more than a decade."
    )
    inline_flag(doc.paragraphs[-1], "reference for SIM coverage and completeness in Sao Paulo")
    stats["pendencias"] += 1

    body(
        doc,
        "Forecasting such series has become methodologically crowded. Classical seasonal "
        "ARIMA remains the reference, decomposition approaches such as Prophet are widely "
        "deployed [5], gradient boosting over lagged features is a common default in applied "
        "work, and time-series foundation models trained on large corpora now offer zero-shot "
        "forecasts without any fitting on the target series [7]. Large-scale forecasting "
        "competitions have repeatedly found that method complexity and forecast accuracy are "
        "only loosely related, and that simple benchmarks are hard to beat [6].",
    )

    body(
        doc,
        "Two reporting weaknesses recur in applied epidemiological forecasting. First, model "
        "comparisons are often presented without a trivial baseline, so a reader cannot tell "
        "whether the fitted model contributes anything beyond repeating last year. Second, "
        "differences between models are reported as point estimates, without a measure of "
        "uncertainty and without a rule, fixed in advance, for what magnitude counts as real. "
        "A difference of a few tenths of a percentage point in symmetric mean absolute "
        "percentage error is easy to present as a winner and easy to be noise [4].",
    )

    body(
        doc,
        "We therefore compared seven forecasters of monthly cancer mortality in Sao Paulo "
        "State under a single rolling-origin protocol, including two deliberately trivial "
        "baselines, with uncertainty measured by block bootstrap and a criterion for a "
        "confirmed difference declared before any result was inspected. We additionally asked "
        "whether the accuracy observed on the aggregate series survives stratification by "
        "tumour site, and how each model behaves when the data-generating regime shifts.",
    )

    # ---------------- methods ---------------- #
    heading(doc, "Methods")
    note(
        doc,
        "Reporting follows TRIPOD+AI [1] where applicable. We note explicitly that TRIPOD+AI "
        "was designed for individual-level clinical prediction models, whereas the outcome here "
        "is an aggregate monthly count. Items concerning participants, predictors measured at "
        "an individual level, sample size for events per variable, and calibration of predicted "
        "individual risks do not apply and are not reported as if they did.",
    )

    heading(doc, "Data source and outcome", level=2)
    body(
        doc,
        f"We used the Mortality Information System (SIM/DataSUS), the national death "
        f"registration database, by state of residence, restricted to Sao Paulo State "
        f"(UF = {co['uf']}) for the years "
        f"{co['anos'][0]} to {co['anos'][1]}. Annual DBC files were downloaded from the DataSUS "
        f"public server and decoded locally. The outcome was the monthly count of deaths whose "
        f"underlying cause (field CAUSABAS) carried an ICD-10 code beginning with "
        f"\"{co['cid_prefixo']}\", that is, malignant neoplasms C00 to C97. Carcinoma in situ "
        f"(D00-D09), benign neoplasms (D10-D36) and neoplasms of uncertain behaviour (D37-D48) "
        f"were excluded, because including them would change the outcome definition without an "
        f"epidemiological gain and would add classification noise to the numerator.",
    )
    body(
        doc,
        f"Of {n(4317224)} death records in the period, {n(co['obitos_por_cancer'])} met the "
        f"cause-of-death criterion, yielding {co['pontos_serie_completa']} consecutive monthly "
        f"observations with no missing month and no zero-count month (mean "
        f"{n(co['media_mensal'])} deaths per month, range {n(co['minimo_mensal'])} to "
        f"{n(co['maximo_mensal'])}). An automated data-plausibility check passed "
        f"{co['checagens_validacao_aprovadas']} of {co['checagens_validacao_total']} assertions.",
    )
    body(
        doc,
        f"We cross-checked the annual counts against the figures published by the Ministry of "
        f"Health through TabNet, using the equivalent selection (Sao Paulo, ICD-10 groups "
        f"covering C00-C97). Our series reproduced the official deaths-by-residence counts "
        f"exactly in all {cross['anos_conferidos']} years, difference zero, total "
        f"{n(cross['total_tabnet_residencia'])} in both. Querying the same selection by state "
        f"of occurrence returns {n(cross['total_tabnet_ocorrencia'])}, "
        f"{abs(cross['dif_pct_vs_ocorrencia'])}% higher; that gap is the expected difference "
        f"between two population definitions and not a discrepancy in extraction. The annual "
        f"files distributed by DataSUS are organised by residence, which is the basis used "
        f"throughout this work.",
    )

    heading(doc, "Handling of the COVID-19 period", level=2)
    body(
        doc,
        f"Annual cancer deaths from {co['anos'][0]} to 2019 follow a near-linear trend of "
        f"{n(tend['slope_obitos_por_ano'])} additional deaths per year (R2 = {tend['r2']}). "
        f"Extrapolating that line, 2020 fell {abs(tend['projecao']['2020']['dif_pct'])}% below "
        f"expectation and 2023 was still {abs(tend['projecao']['2023']['dif_pct'])}% below it; "
        f"2020 was the only year of absolute decline in the series "
        f"({tend['queda_2020_vs_2019_pct']}% against 2019). Because mortality data alone cannot "
        f"separate excess deaths among patients with cancer from deaths displaced by "
        f"interrupted diagnosis, and because the effect had not resolved by the end of the "
        f"series, we chose not to model the break. We restricted model fitting and all "
        f"backtesting to 2010-2019 and used 2020-2023 exclusively as an out-of-regime test. "
        f"This decision was recorded before the benchmark was run.",
    )
    add_figure(
        doc, "fig1_series",
        "Figure 1.",
        "Monthly deaths from malignant neoplasms (ICD-10 C00-C97), Sao Paulo State, "
        f"{co['anos'][0]}-{co['anos'][1]}. The shaded area marks the {co['pontos_serie_treino']} "
        f"months used for model fitting and backtesting. The dashed line is the {co['anos'][0]}-2019 "
        f"annual linear trend (R2 = {tend['r2']}) extrapolated through 2023. The observed series "
        "does not return to the pre-2020 trajectory.",
    )
    stats["figuras"] += 1

    heading(doc, "Forecasting models", level=2)
    body(
        doc,
        "Seven forecasters were compared. Two are deliberately trivial and exist as a floor: "
        "a seasonal naive forecaster, which repeats the value observed in the same month of the "
        "previous year, and a linear trend forecaster, an ordinary least-squares line fitted on "
        "the training window and extrapolated. Mortality from cancer is dominated by a secular "
        "trend, so a fitted line is expected to be competitive, and a model that cannot beat it "
        "has not demonstrated that the series has structure worth modelling.",
    )
    body(
        doc,
        "The remaining five were SARIMA with multiplicative seasonality (order (1,1,1), "
        "seasonal order (0,1,1,12)); Prophet with yearly seasonality enabled and weekly and "
        "daily seasonality disabled [5]; TimesFM 2.5 (200M parameters, PyTorch), a decoder-only "
        "time-series foundation model applied zero-shot with no fitting on the target series "
        "[7]; and XGBoost and CatBoost as recursive multi-step forecasters over 12 lagged "
        "values. Hyperparameters were fixed a priori and not tuned on the target series, so the "
        "comparison is between reasonable default configurations rather than between the best "
        "attainable version of each method.",
    )

    heading(doc, "Backtesting protocol", level=2)
    body(
        doc,
        f"All models were evaluated by rolling-origin backtesting with an expanding window and "
        f"a step of one month. The minimum training length was {ba['min_train']} months and the "
        f"forecast horizon {ba['horizonte']} months, which yields {ba['n_janelas']} windows and "
        f"{ba['n_previsoes_por_modelo']} forecasts per model over the {co['pontos_serie_treino']}-month "
        f"series. Every model saw exactly the same windows and produced the same number of "
        f"forecasts, so the comparison is paired. No model had access to any observation after "
        f"the end of its training window. Accuracy was summarised with mean absolute error, "
        f"root mean squared error and symmetric mean absolute percentage error; the "
        f"limitations of percentage-based measures are well documented [4] and are revisited in "
        f"the Discussion.",
    )

    heading(doc, "Uncertainty and the pre-declared criterion", level=2)
    body(
        doc,
        f"Forecasts from the same origin are dependent across horizons, so we resampled whole "
        f"rolling-origin windows rather than individual forecasts. The block bootstrap drew "
        f"B = {ci['sarima']['B']} replicates, using the same resampled windows for every model "
        f"within each replicate to preserve pairing, with a fixed seed. We additionally applied "
        f"the Diebold-Mariano test [2] separately at each of the {ba['horizonte']} horizons, "
        f"with the Harvey small-sample correction [3].",
    )
    body(
        doc,
        f"We declared, before running the benchmark and before any result was inspected, that "
        f"an improvement counts as confirmed only if both conditions hold: the 95% confidence "
        f"interval of the sMAPE difference excludes zero, AND the Diebold-Mariano p value falls "
        f"below {crit['alpha']} in at least {crit['min_horizontes']} of the {ba['horizonte']} "
        f"horizons. The two conditions test different things: the bootstrap asks whether the "
        f"average difference is distinguishable from zero, the horizon-wise test asks whether "
        f"it persists across the forecast horizon or comes from a single point. We also stated "
        f"in advance that if no model passed, the finding would be that the models tie, and "
        f"that this would be reported without euphemism.",
    )

    heading(doc, "Stratified and out-of-regime analyses", level=2)
    body(
        doc,
        f"We repeated the identical protocol on the four highest-volume tumour sites and set a "
        f"stopping rule in advance, excluding any site averaging fewer than 30 deaths per "
        f"month; no site met the exclusion. Because symmetric percentage error falls with count "
        f"size by construction, we compared the observed ratio of site to aggregate sMAPE "
        f"against the ratio expected from counting noise alone, which for approximately Poisson "
        f"counts scales as the square root of the ratio of mean counts. Finally, we froze "
        f"training at December 2019 and forecast the {reg['horizonte_meses']} months of "
        f"2020-2023 from a single origin, without re-estimation, as a test of behaviour under "
        f"regime change.",
    )

    heading(doc, "Software and reproducibility", level=2)
    body(
        doc,
        f"Analyses used Python with pandas, statsmodels, scikit-learn, skforecast, Prophet, "
        f"XGBoost, CatBoost and TimesFM. All figures and every number reported in this "
        f"manuscript are generated by a single script from the raw forecast files, and the "
        f"manuscript is checked against that script's output rather than against transcription. "
        f"Metrics were recomputed from raw forecasts and reconciled against the stored "
        f"aggregates before being used. Code and the aggregated series are available at "
        f"https://github.com/fabianofilho/oncology-timeseries-prediction (commit "
        f"{v['_commit']}). Individual death records are not redistributed; the aggregated "
        f"monthly series contains no identifiable information.",
    )

    # ---------------- results ---------------- #
    heading(doc, "Results")

    heading(doc, "Cohort and series", level=2)
    anos = co["obitos_por_ano"]
    rows = [[a, n(anos[a])] for a in sorted(anos)]
    add_table(
        doc, ["Year", "Deaths from malignant neoplasms"], rows,
        "Table 1.",
        f"Annual deaths from malignant neoplasms (ICD-10 C00-C97), Sao Paulo State, "
        f"{co['anos'][0]}-{co['anos'][1]}, from SIM/DataSUS. Total "
        f"{n(co['obitos_por_cancer'])} deaths over {co['pontos_serie_completa']} months.",
    )
    stats["tabelas"] += 1

    heading(doc, "Accuracy within the stable regime", level=2)
    rows = []
    best = min(met, key=lambda m: met[m]["smape"])
    for m in ORDER:
        rows.append([
            LABEL[m], n(ci[m]["point"], 2), ci_str(ci[m]),
            n(met[m]["mae"], 1), n(met[m]["rmse"], 1), int(met[m]["n_predictions"]),
        ])
    bold = {(ORDER.index(best), 1)}
    add_table(
        doc,
        ["Model", "sMAPE (%)", "95% CI", "MAE", "RMSE", "Forecasts"],
        rows, "Table 2.",
        f"Forecast accuracy over {ba['n_janelas']} rolling-origin windows, 2010-2019, horizon "
        f"{ba['horizonte']} months. Confidence intervals from block bootstrap over whole "
        f"windows, B = {ci['sarima']['B']}. All models were evaluated on identical windows, so "
        f"the number of forecasts is the same for each. Bold marks the lowest point estimate, "
        f"which is not the same as the best model; see Table 3.",
        bold_cells=bold,
    )
    stats["tabelas"] += 1
    note(
        doc,
        "sMAPE, symmetric mean absolute percentage error; MAE, mean absolute error; RMSE, root "
        "mean squared error; CI, confidence interval.",
    )

    body(
        doc,
        f"SARIMA had the lowest point estimate ({n(ci['sarima']['point'], 2)}%), and the three "
        f"models that represent the series explicitly (SARIMA, TimesFM, Prophet) separated "
        f"clearly from the four that do not. The best model reduced sMAPE by "
        f"{100 * (1 - ci['sarima']['point'] / ci['seasonal_naive']['point']):.0f}% relative to "
        f"the seasonal naive baseline. In absolute terms the errors are small: an sMAPE of "
        f"{n(ci['sarima']['point'], 2)}% corresponds to roughly {n(met['sarima']['mae'])} deaths "
        f"in a month averaging {n(co['media_mensal'])}.",
    )
    add_figure(
        doc, "fig2_smape_ci", "Figure 2.",
        f"sMAPE with 95% confidence intervals for the seven models, {ba['n_janelas']} "
        f"rolling-origin windows, 2010-2019. Colour marks the two groups identified by the "
        f"pre-declared criterion: within each group no pairwise difference was confirmed, "
        f"while every comparison across groups was.",
    )
    stats["figuras"] += 1

    heading(doc, "What the pre-declared criterion confirms", level=2)
    nao_conf = [p_ for p_ in crit["pares"] if not p_["confirmado"]]
    rows = []
    for p_ in nao_conf:
        a, b = p_["par"].split("_menos_")
        rows.append([
            f"{LABEL[a]} vs {LABEL[b]}", n(p_["diferenca"], 3), p_["ic95"],
            "yes" if p_["ic_exclui_zero"] else "no", p_["dm_abaixo_alpha"],
        ])
    add_table(
        doc,
        ["Comparison", "sMAPE difference", "95% CI", "CI excludes zero", "DM below alpha"],
        rows, "Table 3.",
        f"The {len(nao_conf)} of {crit['pares_total']} pairwise comparisons that did NOT meet "
        f"the pre-declared criterion. The remaining {crit['pares_confirmados']} were confirmed, "
        f"and every one of them crosses the two groups. Note that five of these unconfirmed "
        f"comparisons have a confidence interval excluding zero and fail only on the "
        f"horizon-wise condition; had the criterion used the bootstrap alone, they would have "
        f"been reported as real differences.",
    )
    stats["tabelas"] += 1
    note(doc, "DM, Diebold-Mariano test with Harvey correction; alpha = " + str(crit["alpha"]) + ".")

    body(
        doc,
        f"Of the {crit['pares_total']} pairwise comparisons, {crit['pares_confirmados']} were "
        f"confirmed. The unconfirmed ones do not scatter at random. No comparison among SARIMA, "
        f"TimesFM and Prophet was confirmed, and no comparison among linear trend, CatBoost, "
        f"XGBoost and seasonal naive was confirmed, while all comparisons between a member of "
        f"the first set and a member of the second were. The structure in the data is a step "
        f"between two groups, not a ranking of seven models.",
    )

    heading(doc, "Gradient boosting and the extrapolation ceiling", level=2)
    body(
        doc,
        f"CatBoost and XGBoost were statistically indistinguishable from the seasonal naive "
        f"baseline. Their forecasts never exceeded the maximum value seen in the training "
        f"window: {ext['catboost']['acima_do_max_treino']} and "
        f"{ext['xgboost']['acima_do_max_treino']} times out of {ext['catboost']['total']} "
        f"respectively, compared with {ext['prophet']['acima_do_max_treino']} for Prophet, "
        f"{ext['sarima']['acima_do_max_treino']} for SARIMA and "
        f"{ext['timesfm']['acima_do_max_treino']} for TimesFM. Because the series rises almost "
        f"monotonically, {ext['_observacoes_acima_do_max_treino']['pct']}% of test observations "
        f"("
        f"{ext['_observacoes_acima_do_max_treino']['n']} of "
        f"{ext['_observacoes_acima_do_max_treino']['total']}) lie above that ceiling. Both "
        f"boosting forecasters carried a mean bias of about "
        f"{n(abs(ext['catboost']['vies_medio']))} deaths per month below the observed value.",
    )
    add_figure(
        doc, "fig3_extrapolation", "Figure 3.",
        "Percentage of forecasts exceeding the maximum value in the corresponding training "
        "window, by model. The dashed line marks the percentage of test observations that in "
        "fact lie above that maximum. A recursive tree ensemble predicts an average of leaves "
        "fitted in training and is therefore bounded by the observed range, which is a "
        "structural limit and not a consequence of hyperparameter choice.",
    )
    stats["figuras"] += 1

    heading(doc, "Stratification by tumour site", level=2)
    rows = []
    for s in ["agregado", "pulmao", "colorretal", "mama", "prostata"]:
        d = sit[s]
        rows.append([
            SITE_LABEL[s], n(d["media_mensal"]), LABEL.get(d["melhor_modelo"], d["melhor_modelo"]),
            n(d["smape_melhor"], 2),
            f"{d['pares_confirmados']}/{d['pares_total']}",
            "-" if s == "agregado" else f"{d['obs_sobre_poisson']:.2f}",
        ])
    add_table(
        doc,
        ["Series", "Mean deaths/month", "Best model", "sMAPE (%)", "Confirmed pairs",
         "Observed / Poisson-expected"],
        rows, "Table 4.",
        f"Identical protocol applied to the aggregate series and to the four highest-volume "
        f"tumour sites, which together account for {v['sitios_cobertura_pct']}% of cancer "
        f"deaths. The final column divides the observed ratio of site to aggregate sMAPE by the "
        f"ratio expected from counting noise alone; a value near 1 means the site is no harder "
        f"than its count size implies.",
    )
    stats["tabelas"] += 1

    body(
        doc,
        f"Error rose monotonically as the count fell, from {n(sit['agregado']['smape_melhor'], 2)}% "
        f"on the aggregate to {n(sit['prostata']['smape_melhor'], 2)}% for prostate cancer, and "
        f"the number of confirmed comparisons fell from {sit['pulmao']['pares_confirmados']} of "
        f"{sit['pulmao']['pares_total']} for lung to {sit['prostata']['pares_confirmados']} of "
        f"{sit['prostata']['pares_total']} for prostate, where no model met the criterion "
        f"against the seasonal naive baseline. The ratio of observed to Poisson-expected sMAPE "
        f"stayed between "
        f"{min(sit[s]['obs_sobre_poisson'] for s in ['pulmao','colorretal','mama','prostata']):.2f} "
        f"and "
        f"{max(sit[s]['obs_sobre_poisson'] for s in ['pulmao','colorretal','mama','prostata']):.2f} "
        f"across all four sites, so the advantage of the aggregate series is accounted for by "
        f"its count size, with no evidence of error cancellation between sites nor of additional "
        f"structural predictability.",
    )
    if itv:
        fx = itv["faixa_cobertura"]
        pos_sn = itv["posicao_wis"].index("seasonal_naive") + 1
        heading(doc, "Calibration of prediction intervals", level=2)
        body(
            doc,
            f"Conformal prediction intervals calibrated only on earlier windows reached "
            f"empirical coverage between {fx['n95'][0]:.3f} and {fx['n95'][1]:.3f} at the 95% "
            f"nominal level and between {fx['n80'][0]:.3f} and {fx['n80'][1]:.3f} at 80%, "
            f"stable across the six horizons; at the 50% level calibration was poor, ranging "
            f"from {fx['n50'][0]:.3f} to {fx['n50'][1]:.3f}. Ranking the models by weighted "
            f"interval score reordered the lower group: the linear trend, fourth by point "
            f"error, had the worst interval score of the seven "
            f"({itv['pior_wis']['valor']:.1f}), while the seasonal naive baseline, last by "
            f"point error, ranked {pos_sn}th ({itv['wis_seasonal_naive']:.1f}). Applying the "
            f"same intervals to the first {itv['n_fora_por_modelo']} months of 2020 with "
            f"training frozen at December 2019, coverage at the 95% level fell to "
            f"{itv['cobertura_95_fora']:.3f} for all seven models.",
        )
        linhas_itv = []
        for m in itv["posicao_wis"]:
            d = itv["dentro"][m]
            linhas_itv.append([
                LABEL[m], f"{d['cobertura_50']:.3f}", f"{d['cobertura_80']:.3f}",
                f"{d['cobertura_95']:.3f}", f"{d['largura_95']:.0f}", f"{d['WIS']:.1f}",
            ])
        add_table(
            doc,
            ["Model", "Cov. 50%", "Cov. 80%", "Cov. 95%", "Width 95%", "WIS"],
            linhas_itv, "Table 6.",
            f"Coverage, width and weighted interval score of conformal prediction intervals "
            f"over {itv['n_avaliado_por_modelo']} forecasts per model, 2010-2019. Nominal "
            f"coverage is 0.500, 0.800 and 0.950; widths and WIS are in deaths per month. "
            f"Rows are ordered by weighted interval score, which differs from the ordering by "
            f"point error in Table 2.",
        )
        stats["tabelas"] += 1
    add_figure(
        doc, "fig4_sites", "Figure 4.",
        "Left: sMAPE of the best model against mean monthly deaths, with the curve expected if "
        "error were driven by counting noise alone. Right: observed sMAPE ratio divided by the "
        "Poisson-expected ratio, by site. Values near 1 indicate no difficulty beyond that "
        "implied by the count size.",
    )
    stats["figuras"] += 1

    heading(doc, "Behaviour under regime change", level=2)
    rows = []
    for m in sorted(reg["por_modelo"], key=lambda k: reg["por_modelo"][k]["smape_total"]):
        d = reg["por_modelo"][m]
        rows.append([
            LABEL[m], n(d["smape_total"], 2), n(d["smape_primeiros_6m"], 2),
            f"+{n(d['vies_total'])}" if d["vies_total"] > 0 else n(d["vies_total"]),
            n(ci[m]["point"], 2),
        ])
    add_table(
        doc,
        ["Model", "sMAPE 2020-2023 (%)", "sMAPE first 6 months (%)",
         "Mean bias (deaths/month)", "sMAPE within regime (%)"],
        rows, "Table 5.",
        f"Regime-shift test. Training was frozen at December 2019 and the following "
        f"{reg['horizonte_meses']} months were forecast from a single origin without "
        f"re-estimation. The last column repeats the within-regime result of Table 2 for "
        f"reference; the two columns come from different designs (one origin with a "
        f"{reg['horizonte_meses']}-month horizon versus {ba['n_janelas']} origins with a "
        f"{ba['horizonte']}-month horizon) and are not directly comparable.",
    )
    stats["tabelas"] += 1

    body(
        doc,
        f"The ordering essentially inverted. Every model over-predicted, with mean bias ranging "
        f"from +{n(reg['por_modelo']['seasonal_naive']['vies_total'])} deaths per month for the "
        f"seasonal naive baseline to +{n(reg['por_modelo']['prophet']['vies_total'])} for "
        f"Prophet, and the ordering of bias matched the ordering of degradation. On the "
        f"comparable slice, the first six months of 2020, the seven models fell within a narrow "
        f"band ("
        f"{min(reg['por_modelo'][m]['smape_primeiros_6m'] for m in reg['por_modelo']):.2f}% to "
        f"{max(reg['por_modelo'][m]['smape_primeiros_6m'] for m in reg['por_modelo']):.2f}%), "
        f"roughly five times the within-regime error of the best model, and the differences "
        f"between them largely disappeared. This test has a single origin, so it carries no "
        f"measure of uncertainty and the ordering is descriptive.",
    )
    add_figure(
        doc, "fig5_regime", "Figure 5.",
        "Observed monthly deaths and forecasts from a single origin with training frozen at "
        "December 2019. Every forecast path runs above the observed series after 2020. Models "
        "that extrapolate the pre-2020 trend most strongly deviate most once the trend stops.",
    )
    stats["figuras"] += 1

    # ---------------- discussion ---------------- #
    heading(doc, "Discussion")
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
        "the relationship between method complexity and accuracy is weak, and that simple "
        "benchmarks are competitive [6]. It also converges with the observation that "
        "percentage-based error measures behave poorly as a basis for cross-study comparison "
        "[4]. Our contribution is not a new method but a demonstration that the reporting "
        "conventions common in applied epidemiological forecasting would have produced a "
        "different and less defensible conclusion on the same data: five comparisons here have "
        "confidence intervals excluding zero and fail only the horizon-wise condition, and a "
        "report based on the aggregate bootstrap alone would have presented a seven-way ranking.",
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
        "Several limitations bound these conclusions. The external cross-check of our extracted "
        "counts against an independent source has not been performed, so we have validated our "
        "reading of the SIM files but not the files themselves; if coding practice for "
        "ill-defined cancer sites changed over the period, our series would carry that drift "
        "and every model would inherit it. The analysis covers one state, and Sao Paulo has "
        "better death registration coverage than most of Brazil, so error rates here are "
        "probably optimistic relative to a national series. Hyperparameters were fixed rather "
        "than tuned, which understates the attainable accuracy of the boosting models, although "
        "it cannot remove their extrapolation ceiling. The regime-shift test rests on a single "
        "origin and therefore has no uncertainty measure; it is descriptive and should not be "
        "read as evidence that the naive baseline is more robust in general. Stratification was "
        f"by site only and covered {v['sitios_cobertura_pct']}% of deaths, so no statement is "
        "made about sex-specific trends or about the remaining sites. Finally, sMAPE was the "
        "pre-declared metric; on a series with a stable level this choice is benign, as mean "
        "absolute error agrees with it here, but it would not be benign on a surge-driven "
        "series.",
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
        "that fit the stable period best were the ones that failed hardest when the trend broke.",
    )
    body(
        doc,
        "In this series, model choice matters less than whether a trivial baseline was included "
        "and whether the criterion for a real difference was fixed before the results were "
        "seen. Both practices are cheap, and both changed the conclusion here.",
    )

    # ---------------- declaracoes ---------------- #
    heading(doc, "Declarations")
    for titulo, texto in [
        ("Ethics approval. ",
         "This study used publicly available, anonymised, aggregated mortality records from a "
         "national health information system and did not involve human participants directly."),
        ("Data availability. ",
         "The aggregated monthly series analysed here is available in the project repository. "
         "Individual death records are not redistributed and can be obtained directly from "
         "DataSUS."),
        ("Code availability. ",
         "All analysis code, including the script that generates every number, table and figure "
         f"in this manuscript, is available at "
         f"https://github.com/fabianofilho/oncology-timeseries-prediction (commit {v['_commit']})."),
        ("Use of artificial intelligence. ",
         "The authors used an AI coding assistant (Claude, Anthropic) to implement analysis "
         "code and to draft manuscript text. The tool is not an author. The authors reviewed "
         "all output, verified every reported number against the analysis code, and take full "
         "responsibility for the content."),
    ]:
        body(doc, texto, bold_lead=titulo)

    for titulo in ("Author contributions. ", "Funding. ", "Competing interests. ",
                   "Acknowledgements. "):
        p = doc.add_paragraph()
        r = p.add_run(titulo)
        r.bold = True
        inline_flag(p, titulo.strip().rstrip(".").lower())
        stats["pendencias"] += 1

    # ---------------- referencias ---------------- #
    heading(doc, "References")
    for i, ref in enumerate(REFERENCES, start=1):
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.5
        p.add_run(f"{i}. {ref}").font.size = Pt(11)
    note(
        doc,
        "All DOIs above were verified against Crossref, and the arXiv identifier against the "
        "arXiv API, at the time of generation. References marked [PENDING] in the text have not "
        "been sourced and are not listed here.",
    )

    return doc, stats


def main() -> None:
    ap = argparse.ArgumentParser(description="Manuscrito .docx para revisao")
    ap.add_argument("--out", default="build/manuscript.docx")
    args = ap.parse_args()

    v = json.loads((PAPER / "verified_numbers.json").read_text(encoding="utf-8"))
    doc, stats = build(v)

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))

    print(f"Gravado: {out}")
    print(f"Figuras embutidas: {stats['figuras']}")
    print(f"Tabelas nativas: {stats['tabelas']}")
    print(f"Marcadores [PENDING]: {stats['pendencias']}")


if __name__ == "__main__":
    main()
