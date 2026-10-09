#!/usr/bin/env python3
"""Gera figuras e paper/verified_numbers.json a partir dos dados brutos.

Regra do projeto: nenhum numero entra no manuscrito por digitacao. Todo valor que
o texto cita sai deste arquivo, e a conferencia do corpo do texto e feita contra
ele, nao contra a memoria de quem escreveu.

As metricas sao RECOMPUTADAS dos arquivos de previsao (y_true, y_pred por janela
e horizonte), nao relidas dos *_metrics.csv ja agregados. O agregado entra so
como checagem cruzada: divergencia acima da tolerancia aborta a geracao.

Uso:
    python scripts/build_paper_assets.py
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
PAPER = ROOT / "paper"
FIGURES = PAPER / "figures"

DPI = 300
TOL = 1e-6

MODELS = ["sarima", "timesfm", "prophet", "linear_trend", "catboost", "xgboost", "seasonal_naive"]
LABEL = {
    "sarima": "SARIMA",
    "timesfm": "TimesFM",
    "prophet": "Prophet",
    "linear_trend": "Linear trend",
    "catboost": "CatBoost",
    "xgboost": "XGBoost",
    "seasonal_naive": "Seasonal naive",
}
SITES = {
    "pulmao": "Lung (C33-C34)",
    "colorretal": "Colorectal (C18-C21)",
    "mama": "Breast (C50)",
    "prostata": "Prostate (C61)",
}

# Paleta unica, usada por todas as figuras.
C_TOP = "#1b4965"     # grupo que modela a serie
C_BOTTOM = "#bc4b51"  # grupo que nao modela
C_OBS = "#22333b"
C_GRID = "#d8d8d8"
GROUP_TOP = {"sarima", "timesfm", "prophet"}


# --------------------------------------------------------------------------- #
# metricas, recomputadas da fonte primaria
# --------------------------------------------------------------------------- #
def smape(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-8) -> float:
    denom = (np.abs(y_true) + np.abs(y_pred) + eps) / 2.0
    return float(np.mean(np.abs(y_true - y_pred) / denom) * 100.0)


def mae(y_true, y_pred) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true, y_pred) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def recompute(pred_path: Path, metrics_path: Path) -> pd.DataFrame:
    """Recomputa as metricas das previsoes e confere contra o agregado."""
    p = pd.read_csv(pred_path, parse_dates=["date"])
    linhas = []
    for m, g in p.groupby("model"):
        yt, yp = g.y_true.to_numpy(float), g.y_pred.to_numpy(float)
        linhas.append(
            {
                "model": m,
                "mae": mae(yt, yp),
                "rmse": rmse(yt, yp),
                "smape": smape(yt, yp),
                "n_predictions": len(g),
                "n_windows": int(g.window.nunique()),
            }
        )
    novo = pd.DataFrame(linhas).set_index("model").sort_values("smape")

    velho = pd.read_csv(metrics_path).set_index("model")
    for m in novo.index:
        for col in ("mae", "rmse", "smape", "n_predictions"):
            a, b = float(novo.loc[m, col]), float(velho.loc[m, col])
            if abs(a - b) > max(TOL, abs(b) * 1e-9):
                raise SystemExit(
                    f"[ERRO] {pred_path.name}: {m}.{col} recomputado={a} agregado={b}. "
                    "Divergencia entre a previsao bruta e o CSV de metricas."
                )
    return novo


def ci_por_modelo(path: Path) -> dict:
    b = pd.read_csv(path)
    b = b[b.metric == "smape"].set_index("model")
    return {
        m: {
            "point": float(b.loc[m, "point"]),
            "ci_low": float(b.loc[m, "ci_low"]),
            "ci_high": float(b.loc[m, "ci_high"]),
            "ci_width": float(b.loc[m, "ci_width"]),
            "n_windows": int(b.loc[m, "n_windows"]),
            "B": int(b.loc[m, "B"]),
        }
        for m in b.index
    }


def extrapolacao(pred_path: Path, serie_path: Path) -> dict:
    """Quantas previsoes ficam acima do maximo da janela de treino, por modelo."""
    ser = pd.read_csv(serie_path, parse_dates=["date"]).set_index("date").value
    pred = pd.read_csv(pred_path, parse_dates=["date", "train_end"])
    max_por_origem = {te: float(ser[ser.index <= te].max()) for te in pred.train_end.unique()}

    out: dict = {}
    for m, g in pred.groupby("model"):
        acima = sum(int((gg.y_pred > max_por_origem[te]).sum()) for te, gg in g.groupby("train_end"))
        out[m] = {
            "acima_do_max_treino": acima,
            "total": int(len(g)),
            "pct": round(100.0 * acima / len(g), 1),
            "vies_medio": round(float((g.y_pred - g.y_true).mean()), 1),
        }

    ref = pred[pred.model == pred.model.iloc[0]]
    necessarias = sum(int((gg.y_true > max_por_origem[te]).sum()) for te, gg in ref.groupby("train_end"))
    out["_observacoes_acima_do_max_treino"] = {
        "n": necessarias,
        "total": int(len(ref)),
        "pct": round(100.0 * necessarias / len(ref), 1),
    }
    return out


def tendencia_pre_pandemia(serie_path: Path) -> dict:
    s = pd.read_csv(serie_path, parse_dates=["date"])
    ano = s.assign(a=s.date.dt.year).groupby("a").value.sum()
    pre = ano.loc[2010:2019]
    x = np.arange(len(pre), dtype=float)
    slope, intercept = np.polyfit(x, pre.values, 1)
    r2 = float(np.corrcoef(x, pre.values)[0, 1] ** 2)

    proj = {}
    for i, a in enumerate(range(2010, 2024)):
        esperado = intercept + slope * i
        obs = float(ano[a])
        proj[str(a)] = {
            "observado": int(obs),
            "esperado": round(esperado, 0),
            "dif_pct": round(100.0 * (obs - esperado) / esperado, 1),
        }
    return {
        "slope_obitos_por_ano": round(float(slope), 0),
        "r2": round(r2, 3),
        "projecao": proj,
        "queda_2020_vs_2019_pct": round(100.0 * (ano[2020] / ano[2019] - 1), 1),
    }


# --------------------------------------------------------------------------- #
# figuras
# --------------------------------------------------------------------------- #
def _base_ax(ax) -> None:
    ax.grid(axis="y", color=C_GRID, linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)


def fig1_serie(v: dict) -> str:
    s = pd.read_csv(RESULTS / "series" / "serie_onco_SP_sim_real_2010-2023.csv", parse_dates=["date"])
    t = v["tendencia_pre_pandemia"]

    fig, ax = plt.subplots(figsize=(9.0, 4.2))
    _base_ax(ax)
    ax.axvspan(pd.Timestamp("2010-01-01"), pd.Timestamp("2019-12-01"),
               color="#eef3f6", zorder=0)
    ax.plot(s.date, s.value, color=C_OBS, linewidth=1.3, zorder=3)

    anos = pd.to_datetime([f"{a}-07-01" for a in range(2010, 2024)])
    esp = [t["projecao"][str(a)]["esperado"] / 12.0 for a in range(2010, 2024)]
    ax.plot(anos, esp, color=C_BOTTOM, linewidth=1.8, linestyle="--", zorder=4)

    ax.set_ylabel("Deaths per month")
    ax.set_ylim(3000, 5600)
    ax.legend(
        handles=[
            Line2D([], [], color=C_OBS, lw=1.3, label="Observed monthly deaths"),
            Line2D([], [], color=C_BOTTOM, lw=1.8, ls="--",
                   label=f"2010-2019 linear trend, extrapolated (R2 = {t['r2']:.3f})"),
            Line2D([], [], color="#eef3f6", lw=8, label="Training regime (2010-2019)"),
        ],
        frameon=False, fontsize=8.5, loc="upper left",
    )
    fig.tight_layout()
    out = FIGURES / "fig1_series.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return out.name


def fig2_smape(v: dict) -> str:
    ci = v["benchmark_agregado"]["ci_smape"]
    ordem = sorted(MODELS, key=lambda m: ci[m]["point"])
    y = np.arange(len(ordem))[::-1]

    fig, ax = plt.subplots(figsize=(8.4, 4.3))
    ax.grid(axis="x", color=C_GRID, linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)

    for yi, m in zip(y, ordem):
        c = C_TOP if m in GROUP_TOP else C_BOTTOM
        d = ci[m]
        ax.plot([d["ci_low"], d["ci_high"]], [yi, yi], color=c, linewidth=2.4,
                solid_capstyle="round", zorder=3)
        ax.plot([d["point"]], [yi], marker="o", markersize=6,
                markerfacecolor=c, markeredgecolor=c, zorder=4)
        ax.text(d["ci_high"] + 0.06, yi, f"{d['point']:.2f}", va="center", fontsize=8.5, color=c)

    ax.set_yticks(y)
    ax.set_yticklabels([LABEL[m] for m in ordem], fontsize=9)
    ax.set_xlabel("sMAPE (%), with 95% CI from block bootstrap over 55 rolling-origin windows")
    ax.set_xlim(1.2, 3.95)
    ax.tick_params(axis="y", length=0)
    # Legenda fora da area de plotagem: dentro dela, ela cobria a linha do
    # seasonal naive e escondia o rotulo do valor.
    ax.legend(
        handles=[
            Line2D([], [], color=C_TOP, lw=2.4, label="Upper group (mutually indistinguishable)"),
            Line2D([], [], color=C_BOTTOM, lw=2.4, label="Lower group (mutually indistinguishable)"),
        ],
        frameon=False, fontsize=8.5, loc="upper center",
        bbox_to_anchor=(0.5, -0.16), ncol=2,
    )
    fig.tight_layout()
    out = FIGURES / "fig2_smape_ci.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return out.name


def fig3_extrapolacao(v: dict) -> str:
    e = v["extrapolacao"]
    ordem = sorted(MODELS, key=lambda m: -e[m]["pct"])
    x = np.arange(len(ordem))
    vals = [e[m]["pct"] for m in ordem]
    cores = [C_TOP if m in GROUP_TOP else C_BOTTOM for m in ordem]

    fig, ax = plt.subplots(figsize=(8.4, 4.1))
    _base_ax(ax)
    ax.bar(x, vals, color=cores, width=0.62, zorder=3)
    alvo = e["_observacoes_acima_do_max_treino"]["pct"]
    ax.axhline(alvo, color=C_OBS, linestyle="--", linewidth=1.4, zorder=4)
    ax.text(len(ordem) - 0.45, alvo + 1.0,
            f"{alvo:.1f}% of test observations lie above the training maximum",
            ha="right", fontsize=8.5, color=C_OBS)

    for xi, m, val in zip(x, ordem, vals):
        ax.text(xi, val + 0.6, f"{val:.1f}%", ha="center", fontsize=8.5,
                color=C_TOP if m in GROUP_TOP else C_BOTTOM)

    ax.set_xticks(x)
    ax.set_xticklabels([LABEL[m] for m in ordem], fontsize=8.5, rotation=18, ha="right")
    ax.set_ylabel("Forecasts above the training maximum (%)")
    ax.set_ylim(0, 34)
    fig.tight_layout()
    out = FIGURES / "fig3_extrapolation.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return out.name


def fig4_sitios(v: dict) -> str:
    e = v["sitios"]
    nomes = ["agregado"] + list(SITES)
    rot = ["Aggregate (C00-C97)"] + [SITES[s] for s in SITES]
    media = [e[n]["media_mensal"] for n in nomes]
    sm = [e[n]["smape_melhor"] for n in nomes]

    # Painel unico desde 2026-10-09: a CSP conta figura composta painel a painel, entao a
    # razao observado/Poisson saiu para a Figura Suplementar S1 (figS1_sitios).
    fig, ax1 = plt.subplots(figsize=(5.6, 4.0))

    _base_ax(ax1)
    xs = np.linspace(min(media) * 0.8, max(media) * 1.25, 200)
    ax1.plot(xs, sm[0] * np.sqrt(media[0] / xs), color=C_BOTTOM, linestyle="--",
             linewidth=1.5, zorder=2)
    ax1.scatter(media, sm, s=54, color=C_TOP, zorder=3)
    for mm, ss, r in zip(media, sm, rot):
        ax1.annotate(r.split(" (")[0], (mm, ss), textcoords="offset points",
                     xytext=(7, 5), fontsize=8.0, color=C_OBS)
    ax1.set_xscale("log")
    # Escala de verdade no eixo log (revisao da Carine Savalli, 2026-10-09): marcas
    # regulares em vez dos valores de cada ponto, que pareciam um eixo sem escala.
    # A formatacao automatica do log sobrepoe rotulos de minor tick; por isso as
    # marcas sao fixas e os minor ticks ficam desligados.
    marcas = [m for m in (100, 200, 500, 1000, 2000, 5000, 10000)
              if xs.min() <= m <= xs.max()]
    ax1.set_xticks(marcas)
    ax1.set_xticklabels([f"{m:,}".replace(",", " ") for m in marcas], fontsize=8.2)
    ax1.minorticks_off()
    ax1.set_xlabel("Mean monthly deaths (log scale)")
    ax1.set_ylabel("sMAPE (%) of the best model")
    ax1.set_ylim(0, 8.2)
    ax1.legend(handles=[Line2D([], [], color=C_BOTTOM, lw=1.5, ls="--",
                               label="Poisson expectation (1/sqrt(N))")],
               frameon=False, fontsize=8.2, loc="upper right")

    fig.tight_layout()
    out = FIGURES / "fig4_sites.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return out.name


def figS1_sitios(v: dict) -> str:
    """Razao entre o sMAPE observado e o esperado por Poisson, por sitio (suplementar)."""
    e = v["sitios"]
    fig, ax2 = plt.subplots(figsize=(5.6, 4.0))
    _base_ax(ax2)
    sitios = list(SITES)
    razoes = [e[s]["obs_sobre_poisson"] for s in sitios]
    x = np.arange(len(sitios))
    ax2.bar(x, razoes, color=C_TOP, width=0.6, zorder=3)
    ax2.axhline(1.0, color=C_BOTTOM, linestyle="--", linewidth=1.4, zorder=4)
    # Anotacao ancorada a esquerda e acima do topo das barras: no canto direito
    # ela cobria o rotulo do valor da prostata.
    ax2.text(-0.42, 1.24, "ratio of 1.0 = no difficulty beyond counting noise",
             ha="left", fontsize=8.2, color=C_BOTTOM)
    for xi, r in zip(x, razoes):
        ax2.text(xi, r + 0.035, f"{r:.2f}", ha="center", fontsize=8.5, color=C_TOP)
    ax2.set_xticks(x)
    ax2.set_xticklabels([SITES[s].split(" (")[0] for s in sitios], fontsize=8.5)
    ax2.set_ylabel("Observed / Poisson-expected sMAPE ratio")
    ax2.set_ylim(0, 1.42)

    fig.tight_layout()
    out = FIGURES / "figS1_sites_ratio.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return out.name


def fig5_regime(v: dict) -> str:
    p = pd.read_csv(RESULTS / "regime_test_2020_2023_full_predictions.csv", parse_dates=["date"])
    hist = pd.read_csv(RESULTS / "series" / "serie_onco_SP_sim_real_2010-2023.csv", parse_dates=["date"])
    hist = hist[hist.date >= "2017-01-01"]

    fig, ax = plt.subplots(figsize=(9.2, 4.2))
    _base_ax(ax)
    ax.plot(hist.date, hist.value, color=C_OBS, linewidth=1.4, zorder=5)
    ax.axvline(pd.Timestamp("2019-12-01"), color="#888888", linewidth=1.0, linestyle=":", zorder=2)
    ax.text(pd.Timestamp("2020-01-20"), 5480, "training frozen", fontsize=8.2, color="#666666")

    finais = []
    for m in MODELS:
        g = p[p.model == m]
        c = C_TOP if m in GROUP_TOP else C_BOTTOM
        ax.plot(g.date, g.y_pred, color=c, linewidth=1.1, alpha=0.75, zorder=3)
        finais.append((float(g.y_pred.iloc[-1]), m, c, g.date.iloc[-1]))

    # Separacao minima entre rotulos: no valor final varios modelos coincidem e
    # os nomes ficam impressos um sobre o outro.
    finais.sort()
    gap = 95.0
    ys = [f[0] for f in finais]
    for i in range(1, len(ys)):
        if ys[i] - ys[i - 1] < gap:
            ys[i] = ys[i - 1] + gap
    for y_rot, (y_real, m, c, dt) in zip(ys, finais):
        ax.plot([dt, dt + pd.Timedelta(days=22)], [y_real, y_rot],
                color=c, linewidth=0.6, alpha=0.6, zorder=2)
        ax.text(dt + pd.Timedelta(days=28), y_rot, LABEL[m],
                fontsize=7.6, color=c, va="center")

    ax.set_ylabel("Deaths per month")
    ax.set_xlim(pd.Timestamp("2017-01-01"), pd.Timestamp("2025-06-01"))
    ax.set_ylim(3400, 5700)
    ax.legend(
        handles=[
            Line2D([], [], color=C_OBS, lw=1.4, label="Observed"),
            Line2D([], [], color=C_TOP, lw=1.1, label="Upper group forecasts"),
            Line2D([], [], color=C_BOTTOM, lw=1.1, label="Lower group forecasts"),
        ],
        frameon=False, fontsize=8.5, loc="lower left",
    )
    fig.tight_layout()
    out = FIGURES / "fig5_regime.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return out.name


# --------------------------------------------------------------------------- #
def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "desconhecido"


def main() -> None:
    argparse.ArgumentParser(description="Assets do manuscrito").parse_args()
    FIGURES.mkdir(parents=True, exist_ok=True)

    v: dict = {
        "_gerado_por": "scripts/build_paper_assets.py",
        "_gerado_em_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "_commit": git_commit(),
    }

    meta = json.loads(
        (ROOT / "data" / "processed" / "sim_onco_extraction_metadata.json").read_text(encoding="utf-8")
    )
    rep = json.loads((RESULTS / "data_reality_report_2010-2023.json").read_text(encoding="utf-8"))
    serie_full = pd.read_csv(RESULTS / "series" / "serie_onco_SP_sim_real_2010-2023.csv", parse_dates=["date"])
    serie_pre = pd.read_csv(RESULTS / "series" / "serie_onco_SP_sim_real_2010-2019.csv", parse_dates=["date"])

    v["coorte"] = {
        "fonte": "SIM/DataSUS",
        "uf": meta["uf"],
        "anos": [meta["years"][0], meta["years"][-1]],
        "cid_prefixo": meta["cid_prefix"],
        "obitos_por_cancer": int(meta["rows_after_cid_filter"]),
        "pontos_serie_completa": int(len(serie_full)),
        "pontos_serie_treino": int(len(serie_pre)),
        "media_mensal": round(float(serie_full.value.mean()), 0),
        "minimo_mensal": int(serie_full.value.min()),
        "maximo_mensal": int(serie_full.value.max()),
        "checagens_validacao_aprovadas": int(sum(bool(x) for x in rep["checks"].values())),
        "checagens_validacao_total": int(len(rep["checks"])),
        "obitos_por_ano": {
            str(a): int(g.value.sum())
            for a, g in serie_full.assign(a=serie_full.date.dt.year).groupby("a")
        },
    }

    m = recompute(
        RESULTS / "benchmark_onco_SP_2010_2019_full_predictions.csv",
        RESULTS / "benchmark_onco_SP_2010_2019_full_metrics.csv",
    )
    ci = ci_por_modelo(RESULTS / "uncertainty_onco_SP_2010_2019_full_bootstrap_metrics.csv")
    veredito = json.loads((RESULTS / "criterion_verdict_2010_2019_full.json").read_text(encoding="utf-8"))

    v["benchmark_agregado"] = {
        "horizonte": 6,
        "min_train": 60,
        "n_janelas": int(m.n_windows.iloc[0]),
        "n_previsoes_por_modelo": int(m.n_predictions.iloc[0]),
        "n_modelos": int(len(m)),
        "metricas": {
            k: {c: round(float(val), 4) for c, val in row.items()} for k, row in m.iterrows()
        },
        "ci_smape": ci,
        "criterio": {
            "alpha": veredito["criterio"]["alpha"],
            "min_horizontes": veredito["criterio"]["min_horizontes"],
            "pares_total": len(veredito["pares"]),
            "pares_confirmados": sum(1 for p in veredito["pares"] if p["confirmado"]),
            "pares": veredito["pares"],
        },
    }

    # Conferencia contra o TabNet, gerada por scripts/crosscheck_tabnet.py.
    # E a unica checagem que valida a fonte, entao entra no JSON e o manuscrito
    # cita a partir daqui.
    p_cross = RESULTS / "tabnet_crosscheck.json"
    if p_cross.exists():
        cross = json.loads(p_cross.read_text(encoding="utf-8"))
        v["conferencia_tabnet"] = {
            "fonte": cross["fonte"],
            "confere": cross["confere"],
            "anos_conferidos": len(cross["tabnet_residencia"]),
            "anos_divergentes": len(cross["anos_divergentes_vs_residencia"]),
            "base_comparacao": "obitos por residencia",
            "total_tabnet_residencia": sum(cross["tabnet_residencia"].values()),
            "total_tabnet_ocorrencia": sum(cross["tabnet_ocorrencia"].values()),
            "dif_pct_vs_ocorrencia": cross["dif_pct_vs_ocorrencia"],
        }
    else:
        v["conferencia_tabnet"] = {"confere": None}

    v["extrapolacao"] = extrapolacao(
        RESULTS / "benchmark_onco_SP_2010_2019_full_predictions.csv",
        RESULTS / "series" / "serie_onco_SP_sim_real_2010-2019.csv",
    )
    v["tendencia_pre_pandemia"] = tendencia_pre_pandemia(
        RESULTS / "series" / "serie_onco_SP_sim_real_2010-2023.csv"
    )

    escala = json.loads((RESULTS / "site_scale_analysis.json").read_text(encoding="utf-8"))
    sitios_rep = json.loads((RESULTS / "site_series_report.json").read_text(encoding="utf-8"))
    por_sitio = {}
    for reg in escala["series"]:
        nome = reg["serie"]
        d = {
            "media_mensal": reg["media_mensal"],
            "melhor_modelo": reg["melhor_modelo"],
            "smape_melhor": reg["smape"],
            "razao_observada": reg["razao_observada"],
            "razao_poisson": reg["razao_esperada_poisson"],
            "obs_sobre_poisson": reg["obs_sobre_poisson"],
        }
        if nome != "agregado":
            vd = json.loads(
                (RESULTS / f"criterion_verdict_{nome}_2010_2019.json").read_text(encoding="utf-8")
            )
            d["pares_confirmados"] = sum(1 for p in vd["pares"] if p["confirmado"])
            d["pares_total"] = len(vd["pares"])
            info = next(s for s in sitios_rep["sitios"] if s["sitio"] == nome)
            d["obitos"] = info["obitos"]
            d["cid"] = info["cid"]
        else:
            d["pares_confirmados"] = v["benchmark_agregado"]["criterio"]["pares_confirmados"]
            d["pares_total"] = v["benchmark_agregado"]["criterio"]["pares_total"]
            d["obitos"] = v["coorte"]["obitos_por_cancer"]
        por_sitio[nome] = d
    v["sitios"] = por_sitio
    v["sitios_cobertura_pct"] = round(
        100.0 * sum(por_sitio[s]["obitos"] for s in SITES) / por_sitio["agregado"]["obitos"], 1
    )

    # Intervalos conformais, gerados por scripts/run_intervals.py. Resultado
    # secundario: entra no texto em frases e numa tabela suplementar, sem
    # consumir nenhuma das 5 ilustracoes que a CSP permite.
    p_int = RESULTS / "intervals_2010_2019_report.json"
    if p_int.exists():
        rel = json.loads(p_int.read_text(encoding="utf-8"))
        dentro = {d["model"]: d for d in rel["dentro_do_regime"]}
        fora = {d["model"]: d for d in rel.get("fora_do_regime", [])}
        cobs = {p: [dentro[m][f"cobertura_{p}"] for m in dentro] for p in (50, 80, 95)}
        pior_wis = max(dentro, key=lambda m: dentro[m]["WIS"])
        v["intervalos"] = {
            "escala": rel["escala"],
            "min_calib_janelas": rel["min_calib_janelas"],
            "n_avaliado_por_modelo": int(next(iter(dentro.values()))["n_avaliado"]),
            "dentro": dentro,
            "fora": fora,
            "faixa_cobertura": {
                f"n{p}": [round(min(cobs[p]), 3), round(max(cobs[p]), 3)] for p in (50, 80, 95)
            },
            "pior_wis": {"model": pior_wis, "valor": round(dentro[pior_wis]["WIS"], 1)},
            "wis_seasonal_naive": round(dentro["seasonal_naive"]["WIS"], 1),
            "posicao_wis": [
                m for m in sorted(dentro, key=lambda x: dentro[x]["WIS"])
            ],
            "cobertura_95_fora": (
                round(rel["cobertura_95_media"]["fora"], 3)
                if "cobertura_95_media" in rel else None
            ),
            "n_fora_por_modelo": (
                int(next(iter(fora.values()))["n_avaliado"]) if fora else None
            ),
        }
    else:
        v["intervalos"] = None

    reg = pd.read_csv(RESULTS / "regime_test_2020_2023_full_metrics.csv").set_index("model")
    v["teste_regime"] = {
        "treino_ate": "2019-12",
        "horizonte_meses": int(reg.horizonte_total.iloc[0]),
        "por_modelo": {
            m_: {
                "smape_total": round(float(reg.loc[m_, "smape_total"]), 2),
                "smape_primeiros_6m": round(float(reg.loc[m_, "smape_primeiros_6m"]), 2),
                "vies_total": round(float(reg.loc[m_, "vies_total"]), 0),
            }
            for m_ in reg.index
        },
    }

    figs = [fig1_serie(v), fig2_smape(v), fig3_extrapolacao(v), fig4_sitios(v), figS1_sitios(v),
            fig5_regime(v)]
    v["_figuras"] = figs

    PAPER.mkdir(parents=True, exist_ok=True)
    out = PAPER / "verified_numbers.json"
    out.write_text(json.dumps(v, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Metricas recomputadas das previsoes e conferidas contra os CSV agregados: OK")
    print(f"Figuras geradas ({DPI} dpi): " + ", ".join(figs))
    print(f"Gravado: {out}")


if __name__ == "__main__":
    main()
