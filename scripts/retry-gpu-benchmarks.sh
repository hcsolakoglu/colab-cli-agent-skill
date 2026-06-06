#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS="${RESULTS:-$ROOT/benchmark-results-gpu-retry-$(date +%Y%m%d-%H%M%S)}"
SCRIPT="$ROOT/colab-cli/scripts/benchmark-runtime.py"
ATTEMPTS="${ATTEMPTS:-120}"
SLEEP_SECONDS="${SLEEP_SECONDS:-30}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-900}"
GPUS=("${@:-T4 L4 G4 A100 H100}")

mkdir -p "$RESULTS"

for gpu in "${GPUS[@]}"; do
  echo "=== GPU $gpu ==="
  success=0
  for attempt in $(seq 1 "$ATTEMPTS"); do
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    session="codex-bench-${gpu,,}-${attempt}"
    stdout="$RESULTS/${gpu}.json"
    stderr="$RESULTS/${gpu}.${attempt}.${stamp}.stderr"
    echo "[$stamp] attempt $attempt/$ATTEMPTS for $gpu"
    set +e
    colab run --session "$session" --gpu "$gpu" --timeout "$TIMEOUT_SECONDS" \
      "$SCRIPT" "$gpu" > "$stdout" 2> "$stderr"
    status=$?
    set -e
    if [[ "$status" -eq 0 ]] && python3 -m json.tool "$stdout" >/dev/null 2>&1; then
      echo "[$stamp] success $gpu -> $stdout"
      success=1
      break
    fi
    echo "[$stamp] failed $gpu status=$status; see $stderr"
    colab stop -s "$session" >/dev/null 2>&1 || true
    colab sessions >> "$RESULTS/session-checks.log" 2>&1 || true
    sleep "$SLEEP_SECONDS"
  done
  if [[ "$success" != 1 ]]; then
    echo "GPU $gpu did not allocate after $ATTEMPTS attempts" | tee "$RESULTS/${gpu}.failed"
  fi
  colab sessions >> "$RESULTS/session-checks.log" 2>&1 || true
done

echo "Results: $RESULTS"
