#!/usr/bin/env python3
"""Estudo de simulacao da LAB-237: roda cenarios, niveis e replicas e aplica o criterio v2.

Desenho registrado na issue (comentario de 19/10/2026, aprovado em 22/10):
- as mesmas 55 janelas de teste do OPT (origem a partir do mes 60, horizonte 6);
- perturbacoes em src/onco_timeseries/simulacao.py;
- falha de modelo numa janela NAO aborta a replica: e registrada, e os pares daquele
  modelo saem do criterio naquela replica;
- bootstrap por replica com B = 2.000 e a semente do OPT (20260818);
- controle: sem perturbacao, com B = 10.000, tem de reproduzir par a par
  results/reproducao/criterion_verdict_mac10.json antes de qualquer cenario.

Uso:
    PYTHONPATH=src python scripts/run_simulacao.py controle
    PYTHONPATH=src python scripts/run_simulacao.py rodada --cenario ruido --nivel 0.05 --replicas 20

Saidas em results/simulacao/; nada aqui toca os arquivos que o manuscrito le.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from onco_timeseries.data import load_and_aggregate_series  # noqa: E402
from onco_timeseries.evaluate import rolling_origin_splits  # noqa: E402
from onco_timeseries.simulacao import CENARIOS, DETERMINISTICOS, aplica_faltantes, prepara  # noqa: E402

SERIE = ROOT / "results" / "series" / "serie_onco_SP_sim_real_2010-2019.csv"
OUT = ROOT / "results" / "simulacao"
MODELOS = ["seasonal_naive", "linear_trend", "sarima", "prophet", "timesfm", "xgboost", "catboost"]
HORIZONTE, TREINO_MIN = 6, 60
B_SIM, B_CONTROLE, SEMENTE_BOOT = 2_000, 10_000, 20260818
CONTROLE_REF = ROOT / "results" / "reproducao" / "criterion_verdict_mac10.json"
PRED_REF = ROOT / "results" / "reproducao" / "benchmark_mac10_predictions.csv"


def pasta(cenario: str, nivel: float) -> Path:
    return OUT / cenario / f"{nivel:g}"


def carrega_serie() -> pd.Series:
    return load_and_aggregate_series(csv_path=str(SERIE), date_col="date", value_col="value", freq="MS")


# --------------------------------------------------------------------------- previsoes
def previsoes(cenario: str, nivel: float, replicas: list[int], modelo: str, saida: Path) -> None:
    """Um modelo, varias replicas, num processo so (carrega o modelo uma vez)."""
    from run_benchmark import build_models

    model = build_models([modelo])[0]
    base = carrega_serie()
    linhas, falhas = [], []
    t0 = time.time()
    for r in replicas:
        p = prepara(base, cenario, nivel, r)
        serie = p["serie"]
        janelas = rolling_origin_splits(serie, horizon=HORIZONTE, min_train_size=TREINO_MIN,
                                        max_train_size=p["max_train"])
        for w, (train, test) in enumerate(janelas, start=1):
            if p["faltantes"] is not None:
                train = aplica_faltantes(train, p["faltantes"])
            try:
                y = np.asarray(model.forecast(train, horizon=len(test)), dtype=float)
                if len(y) != len(test) or not np.all(np.isfinite(y)):
                    raise ValueError("previsao invalida (tamanho ou nao finita)")
            except Exception as exc:  # falha conta como desfecho, nao derruba a replica
                falhas.append({"replica": r, "window": w, "model": modelo, "erro": str(exc)[:200]})
                continue
            for h, (dt, yt, yp) in enumerate(zip(test.index, test.to_numpy(float), y), start=1):
                linhas.append({"replica": r, "model": modelo, "date": dt, "y_true": yt,
                               "y_pred": yp, "window": w, "horizon": h})
    saida.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(linhas).to_csv(saida, index=False)
    pd.DataFrame(falhas, columns=["replica", "window", "model", "erro"]).to_csv(
        saida.with_name(saida.stem + "_falhas.csv"), index=False)
    print(json.dumps({"modelo": modelo, "segundos": round(time.time() - t0, 1),
                      "replicas": len(replicas), "falhas": len(falhas)}))


def roda_modelos(cenario: str, nivel: float, replicas: list[int], sufixo: str = "") -> dict:
    """Um subprocesso por modelo (torch e XGBoost no mesmo processo derrubam o macOS)."""
    tempos = {}
    for m in MODELOS:
        saida = pasta(cenario, nivel) / f"pred_{m}{sufixo}.csv"
        cmd = [sys.executable, __file__, "previsoes", "--cenario", cenario, "--nivel", str(nivel),
               "--replicas", ",".join(map(str, replicas)), "--modelo", m, "--saida", str(saida)]
        t0 = time.time()
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
        if r.returncode != 0:
            raise SystemExit(f"[ERRO] {m} saiu com codigo {r.returncode}:\n{r.stderr[-2000:]}")
        tempos[m] = round(time.time() - t0, 1)
    return tempos


# --------------------------------------------------------------------------- criterio
def criterio(pred: pd.DataFrame, modelos: list[str], destino: Path, b: int) -> dict:
    """Bootstrap + DM + criterio v2 com os scripts do artigo, sem alterar nada neles."""
    destino.mkdir(parents=True, exist_ok=True)
    csv = destino / "predictions.csv"
    pred.drop(columns=["replica"], errors="ignore").to_csv(csv, index=False)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    subprocess.run([sys.executable, "scripts/run_uncertainty.py", "--predictions-csv", str(csv),
                    "--models", ",".join(modelos), "--n-boot", str(b), "--seed", str(SEMENTE_BOOT),
                    "--output-prefix", str(destino / "uncertainty")],
                   cwd=ROOT, check=True, capture_output=True, env=env)
    subprocess.run([sys.executable, "scripts/apply_criterion.py", "--pairwise-csv",
                    str(destino / "uncertainty_pairwise_tests.csv"),
                    "--report-output", str(destino / "criterion_verdict.json")],
                   cwd=ROOT, check=True, capture_output=True, env=env)
    return json.loads((destino / "criterion_verdict.json").read_text(encoding="utf-8"))


def le_previsoes(cenario: str, nivel: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Junta os lotes de previsao de cada modelo (o lote inicial e os acrescimos)."""
    p = pasta(cenario, nivel)
    arqs = [f for m in MODELOS for f in sorted(p.glob(f"pred_{m}*.csv")) if not f.stem.endswith("_falhas")]
    pred = pd.concat([pd.read_csv(f) for f in arqs], ignore_index=True)
    falhas = pd.concat([pd.read_csv(f.with_name(f.stem + "_falhas.csv")) for f in arqs], ignore_index=True)
    if pred.duplicated(["replica", "model", "window", "horizon"]).any():
        raise SystemExit(f"previsoes duplicadas em {p}: lote repetido")
    return pred, falhas


def resumo_replica(pred: pd.DataFrame, falhas: pd.DataFrame, r: int, destino: Path, b: int) -> dict:
    sub = pred[pred.replica == r]
    falhos = sorted(set(falhas.loc[falhas.replica == r, "model"]))
    validos = [m for m in MODELOS if m not in falhos and (sub.model == m).any()]
    erro = {}
    for m in validos:
        g = sub[sub.model == m]
        erro[m] = {"smape": float((200 * (g.y_pred - g.y_true).abs()
                                   / (g.y_true.abs() + g.y_pred.abs())).mean()),
                   "mae": float((g.y_pred - g.y_true).abs().mean())}
    ver = criterio(sub[sub.model.isin(validos)], validos, destino, b) if len(validos) >= 2 else {"pares": []}
    return {"replica": r, "modelos_com_falha": falhos, "erro": erro,
            "pares": [{k: p[k] for k in ("par", "veredito", "confirmado", "diferenca",
                                         "diferenca_mae", "dm_abaixo_alpha")} for p in ver["pares"]]}


# --------------------------------------------------------------------------- comandos
def cmd_controle(_args) -> None:
    """Sem perturbacao: tem de reproduzir a analise principal nesta maquina."""
    cen, niv = "controle", 0.0
    tempos = roda_modelos(cen, niv, [1])
    pred, falhas = le_previsoes(cen, niv)
    if len(falhas):
        raise SystemExit(f"[CONTROLE FALHOU] {len(falhas)} janelas com falha sem perturbacao")
    ref = pd.read_csv(PRED_REF)
    m = pred.merge(ref, on=["model", "window", "horizon"], suffixes=("", "_ref"))
    if len(m) != len(ref):
        raise SystemExit(f"[CONTROLE FALHOU] {len(m)} previsoes casadas de {len(ref)}")
    dif = (m.y_pred - m.y_pred_ref).abs().groupby(m.model).max().to_dict()
    res = resumo_replica(pred, falhas, 1, pasta(cen, niv) / "r1", B_CONTROLE)
    ref_ver = {p["par"]: p["veredito"] for p in json.loads(CONTROLE_REF.read_text())["pares"]}
    nosso = {p["par"]: p["veredito"] for p in res["pares"]}
    diverge = {k: (ref_ver[k], nosso.get(k)) for k in ref_ver if nosso.get(k) != ref_ver[k]}
    out = {"tempos_s": tempos, "max_dif_previsao": dif, "pares_divergentes": diverge,
           "reproduz": not diverge}
    (pasta(cen, niv) / "controle.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    if diverge:
        raise SystemExit("[CONTROLE FALHOU] vereditos divergem da analise principal")


def cmd_rodada(args) -> None:
    cen, niv = args.cenario, float(args.nivel)
    if cen not in CENARIOS or niv not in CENARIOS[cen]:
        raise SystemExit(f"nivel {niv} nao registrado para {cen}: {CENARIOS.get(cen)}")
    if not (OUT / "controle" / "0" / "controle.json").exists():
        raise SystemExit("rode o controle antes de qualquer cenario")
    if not json.loads((OUT / "controle" / "0" / "controle.json").read_text())["reproduz"]:
        raise SystemExit("controle nao reproduziu; nenhum cenario roda")
    arq = pasta(cen, niv) / "resumo.json"
    anterior = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else None
    if anterior and cen in DETERMINISTICOS:
        raise SystemExit(f"{cen} e deterministico e ja rodou")
    ja = anterior["replicas"] if anterior else 0
    r_tot = 1 if cen in DETERMINISTICOS else args.replicas
    if r_tot <= ja:
        raise SystemExit(f"{cen} {niv:g} ja tem {ja} replicas; pedir mais que isso")
    # Acrescimo (regra de 22/10 na LAB-237): so replicas novas, as anteriores ficam.
    replicas = list(range(ja + 1, r_tot + 1))
    sufixo = f"_r{replicas[0]}-{replicas[-1]}" if anterior else ""
    tempos = roda_modelos(cen, niv, replicas, sufixo)
    pred, falhas = le_previsoes(cen, niv)
    res = [resumo_replica(pred, falhas, r, pasta(cen, niv) / f"r{r}", B_SIM) for r in replicas]
    out = {"cenario": cen, "nivel": niv, "replicas": r_tot, "B": B_SIM,
           "tempos_s": tempos, "falhas_por_modelo": falhas.groupby("model").size().to_dict(),
           "por_replica": (anterior["por_replica"] if anterior else []) + res}
    if anterior:
        out["tempos_s"] = {"inicial": anterior["tempos_s"], sufixo.lstrip("_"): tempos}
    (pasta(cen, niv) / "resumo.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({"cenario": cen, "nivel": niv, "tempos_s": tempos,
                      "falhas": out["falhas_por_modelo"]}))


NOVOS = {"timesfm", "prophet", "xgboost", "catboost"}
SIMPLES = {"seasonal_naive", "linear_trend", "sarima"}
LIMITE = (0.35, 0.65)


def proporcoes(resumo: dict) -> dict[str, float]:
    """Fracao de replicas em que cada par novo x simples foi confirmado."""
    cont: dict[str, list[bool]] = {}
    for rep in resumo["por_replica"]:
        for p in rep["pares"]:
            a, b = p["par"].split("_menos_")
            if {a, b} & NOVOS and {a, b} & SIMPLES:
                cont.setdefault(p["par"], []).append(bool(p["confirmado"]))
    return {k: sum(v) / resumo["replicas"] for k, v in cont.items()}


def cmd_limite(_args) -> None:
    """Aplica a regra registrada em 22/10: quais niveis precisam de mais replicas."""
    repetir = []
    for c, niveis in CENARIOS.items():
        if c in DETERMINISTICOS:
            continue
        for n in niveis:
            arq = pasta(c, n) / "resumo.json"
            if not arq.exists():
                continue
            r = json.loads(arq.read_text(encoding="utf-8"))
            no_limite = {k: v for k, v in proporcoes(r).items() if LIMITE[0] < v < LIMITE[1]}
            if no_limite and r["replicas"] < 50:
                repetir.append({"cenario": c, "nivel": n, "pares": no_limite})
    print(json.dumps(repetir, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("previsoes")
    p.add_argument("--cenario", required=True)
    p.add_argument("--nivel", type=float, required=True)
    p.add_argument("--replicas", required=True)
    p.add_argument("--modelo", required=True)
    p.add_argument("--saida", required=True)
    sub.add_parser("controle")
    sub.add_parser("limite")
    p = sub.add_parser("rodada")
    p.add_argument("--cenario", required=True)
    p.add_argument("--nivel", required=True)
    p.add_argument("--replicas", type=int, default=20)
    args = ap.parse_args()
    if args.cmd == "previsoes":
        previsoes(args.cenario, args.nivel, [int(x) for x in args.replicas.split(",")],
                  args.modelo, Path(args.saida))
    elif args.cmd == "controle":
        cmd_controle(args)
    elif args.cmd == "limite":
        cmd_limite(args)
    else:
        cmd_rodada(args)


if __name__ == "__main__":
    main()
