#!/usr/bin/env bash
# Fila do piloto da LAB-237: treino curto (deterministico) e depois os cenarios com
# sorteio, R = 20. Para no primeiro erro. Rodar com caffeinate para o Mac nao dormir:
#   caffeinate -i nohup bash scripts/fila_simulacao.sh > results/simulacao/fila.log 2>&1 &
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src
PY=.venv/bin/python
R=${R:-20}
for spec in treino_curto:24 treino_curto:36 treino_curto:48 \
            faltantes:0.05 faltantes:0.1 faltantes:0.2 \
            quebra:0.05 quebra:-0.05 quebra:0.1 quebra:-0.1 \
            atipico:0.2 ruido:0.02 ruido:0.05 ruido:0.1; do
  c=${spec%%:*}; n=${spec#*:}
  if [ -f "results/simulacao/$c/$n/resumo.json" ]; then echo "[pula] $spec"; continue; fi
  echo "[$(date '+%F %T')] inicio $spec"
  $PY scripts/run_simulacao.py rodada --cenario "$c" --nivel "$n" --replicas "$R"
  echo "[$(date '+%F %T')] fim $spec"
done
echo "[$(date '+%F %T')] fila completa"
