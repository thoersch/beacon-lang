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
  ./beacon.sh inspect file.beacon
  ./beacon.sh self-host
USAGE
  exit 2
}

[[ $# -gt 0 ]] || usage

# On Windows, programs using std.graphics must load a native module built
# from the matching checkout. The committed DLL can lag the Beacon bindings
# (for example the game uses the newer OpenGL "batch" action).
# Build to the normal SDK output directory, never into native/opengl itself:
# outputting there causes the SDK's default source glob to see generated files.
ensure_graphics_extension() {
  local target="${1:-}"
  [[ -f "$target" ]] || return 0
  [[ "${OS:-}" == "Windows_NT" ]] || return 0
  grep -Eq '^[[:space:]]*include[[:space:]]+std\\.graphics(\\.gl)?[[:space:]]*
case "$1" in
  inspect)
    [[ $# -ge 2 ]] || usage
    exec dotnet "$HOST" "$COMPILER" --stage1-run "$2" --inspect
    ;;
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
 "$target" || return 0

  local project="$ROOT/native/opengl/Beacon.Native.opengl.csproj"
  local built="$ROOT/native/opengl/bin/Release/net8.0/Beacon.Native.opengl.dll"
  local installed="$ROOT/native/opengl/Beacon.Native.opengl.dll"
  local stamp="$ROOT/native/opengl/obj/.beacon-opengl-source.sha256"
  local fingerprint=""
  fingerprint="$(sha256sum "$ROOT/native/opengl/Extension.cs" "$project" | sha256sum | cut -d ' ' -f 1)"
  if [[ ! -f "$installed" || ! -f "$stamp" || "$(cat "$stamp")" != "$fingerprint" ]]; then
    echo "Beacon: building native OpenGL extension for this checkout..." >&2
    dotnet build "$project" -c Release -p:UseAppHost=false -v:q >&2
    [[ -f "$built" ]] || { echo "Beacon: native OpenGL build produced no DLL" >&2; exit 1; }
    cp "$built" "$installed"
    printf '%s\\n' "$fingerprint" > "$stamp"
  fi
}

case "$1" in
  run|inspect|plan) [[ $# -ge 2 ]] && ensure_graphics_extension "$2" ;;
  self-host) ;;
  *) ensure_graphics_extension "$1" ;;
esac


case "$1" in
  inspect)
    [[ $# -ge 2 ]] || usage
    exec dotnet "$HOST" "$COMPILER" --stage1-run "$2" --inspect
    ;;
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
