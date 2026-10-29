#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SEED_PROJECT="$ROOT/tools/seed-refresh/Beacon.Compiler/Beacon.Compiler.csproj"
OUT="$ROOT/.seed-out"
STAGE0="$ROOT/bootstrap/stage0"
COMPILER="$ROOT/compiler/compiler.beacon"
EXAMPLE="$ROOT/examples/includes/main.beacon"

[[ -f "$SEED_PROJECT" ]] || { echo "Seed refresh source not found: $SEED_PROJECT" >&2; exit 2; }

rm -rf "$OUT"
dotnet publish "$SEED_PROJECT" -c Release -o "$OUT"
mkdir -p "$STAGE0"
cp "$OUT/Beacon.Compiler.dll" "$STAGE0/"
cp "$OUT/Beacon.Compiler.deps.json" "$STAGE0/"
cp "$OUT/Beacon.Compiler.runtimeconfig.json" "$STAGE0/"

export BEACON_HOME="$ROOT"
dotnet "$STAGE0/Beacon.Compiler.dll" "$COMPILER" --self-host
output="$(dotnet "$STAGE0/Beacon.Compiler.dll" "$COMPILER" --stage1-run "$EXAMPLE")"
printf '%s\n' "$output"
grep -F "Hello, I'm Ada" <<<"$output" >/dev/null
grep -F "Boston" <<<"$output" >/dev/null
grep -F "42" <<<"$output" >/dev/null

commit="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
{
  echo "Beacon Stage-0 bootstrap seed"
  echo "============================="
  echo
  echo "Purpose: immutable CLR bootstrap/runtime boundary for the self-hosted Beacon compiler."
  echo "Seed refresh: filesystem/path primitives, seed-only local include composition, and the generic namespace plan operation used by Beacon standard-library namespaces."
  echo "Historical implementation language: C#"
  echo "Source commit before refresh: $commit"
  echo ".NET SDK: $(dotnet --version)"
  echo "Generated (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo "The canonical compiler implementation is Beacon source under compiler/."
  echo "Stage 1+ resolves includes, lexes, parses, builds Core, and plans CLR IL in Beacon."
} > "$STAGE0/PROVENANCE.txt"
(
  cd "$STAGE0"
  sha256sum Beacon.Compiler.dll Beacon.Compiler.deps.json Beacon.Compiler.runtimeconfig.json > SHA256SUMS
)

dotnet build-server shutdown >/dev/null 2>&1 || true
sleep 1
rm -rf "$ROOT/tools/seed-refresh" "$OUT"
if find "$ROOT" -type f \( -name '*.cs' -o -name '*.csproj' \) -print -quit | grep -q .; then
  echo "C# source remains after seed refresh:" >&2
  find "$ROOT" -type f \( -name '*.cs' -o -name '*.csproj' \) -print >&2
  exit 1
fi

echo
echo "Beacon include bootstrap complete."
echo "The repository contains no .cs or .csproj files."
