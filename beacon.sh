#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="$ROOT/bootstrap/stage0/Beacon.Compiler.dll"
COMPILER="$ROOT/compiler/compiler.beacon"
export BEACON_HOME="$ROOT"

if [[ ! -f "$HOST" ]]; then
  echo "Beacon bootstrap seed not found: $HOST" >&2
  echo "Run tools/finalize-bootstrap.sh before using this checkout." >&2
  exit 2
fi

usage() {
  cat <<'USAGE'
Usage:
  ./beacon.sh file.beacon
  ./beacon.sh run file.beacon
  ./beacon.sh plan file.beacon
  ./beacon.sh self-host
USAGE
  exit 2
}

[[ $# -gt 0 ]] || usage

case "$1" in
  self-host)
    exec dotnet "$HOST" "$COMPILER" --self-host
    ;;
  plan)
    [[ $# -ge 2 ]] || usage
    exec dotnet "$HOST" "$COMPILER" --stage1 "$2"
    ;;
  run)
    [[ $# -ge 2 ]] || usage
    exec dotnet "$HOST" "$COMPILER" --stage1-run "$2"
    ;;
  *)
    exec dotnet "$HOST" "$COMPILER" --stage1-run "$1"
    ;;
esac
