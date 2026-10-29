#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PROJECT="$ROOT/Beacon.Compiler/Beacon.Compiler.csproj"
PROGRAM="$ROOT/Beacon.Compiler/Program.cs"
COMPILER="$ROOT/compiler/compiler.beacon"
STAGE0="$ROOT/bootstrap/stage0"

[[ -f "$PROJECT" && -f "$PROGRAM" ]] || {
  echo "Stage-0 source not found. Run this once from the v0.6 source tree." >&2
  exit 2
}

echo "[1/7] Verifying the source compiler reaches a self-hosting fixed point..."
dotnet run --project "$PROJECT" -- "$COMPILER" --self-host

echo "[2/7] Verifying a normal program through the Beacon-written compiler..."
dotnet run --project "$PROJECT" -- "$COMPILER" --stage1-run "$ROOT/examples/control-flow.beacon"

GIT_COMMIT="$(git rev-parse HEAD 2>/dev/null || printf unknown)"
PROGRAM_HASH="$(sha256sum "$PROGRAM" | awk '{print $1}')"
PROJECT_HASH="$(sha256sum "$PROJECT" | awk '{print $1}')"
SDK="$(dotnet --version)"

echo "[3/7] Publishing the immutable Stage-0 seed..."
rm -rf "$STAGE0"
mkdir -p "$STAGE0"
dotnet publish "$PROJECT" -c Release -o "$STAGE0" -p:UseAppHost=false
rm -f "$STAGE0"/*.pdb
SEED="$STAGE0/Beacon.Compiler.dll"
[[ -f "$SEED" ]] || { echo "Published Stage-0 seed was not produced." >&2; exit 1; }

echo "[4/7] Verifying the frozen seed independently..."
dotnet "$SEED" "$COMPILER" --self-host
dotnet "$SEED" "$COMPILER" --stage1-run "$ROOT/examples/control-flow.beacon"

cat > "$STAGE0/PROVENANCE.txt" <<PROVENANCE
Beacon Stage-0 bootstrap seed
Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Git source commit: $GIT_COMMIT
.NET SDK: $SDK
Beacon.Compiler/Program.cs SHA256: $PROGRAM_HASH
Beacon.Compiler/Beacon.Compiler.csproj SHA256: $PROJECT_HASH

The seed was verified by:
  1. compiler.beacon reaching the Stage-1/Stage-2/Stage-3 normalized-plan fixed point
  2. examples/control-flow.beacon compiling and executing through compiler.beacon

The canonical compiler source is compiler/compiler.beacon.
The Stage-0 binary is retained only to bootstrap a clean checkout.
PROVENANCE
(
  cd "$STAGE0"
  for file in *; do
    [[ "$file" == SHA256SUMS ]] && continue
    [[ -f "$file" ]] && sha256sum "$file"
  done | sort -k2 > SHA256SUMS
)

echo "[5/7] Installing final public documentation..."
cp "$ROOT/tools/final/README.md" "$ROOT/README.md"
cp "$ROOT/tools/final/BOOTSTRAP.md" "$ROOT/BOOTSTRAP.md"

echo "[6/7] Removing the C# seed source from the active tree..."
rm -rf "$ROOT/Beacon.Compiler"

echo "[7/7] Verifying the final tree contains no C# source..."
if find "$ROOT" -path "$ROOT/.git" -prune -o \( -name '*.cs' -o -name '*.csproj' \) -print | grep -q .; then
  echo "C# source remains in the tree:" >&2
  find "$ROOT" -path "$ROOT/.git" -prune -o \( -name '*.cs' -o -name '*.csproj' \) -print >&2
  exit 1
fi

dotnet "$SEED" "$COMPILER" --self-host

echo
echo "Beacon source-only transition complete."
echo "Canonical compiler: compiler/compiler.beacon"
echo "Frozen seed:        bootstrap/stage0/Beacon.Compiler.dll"
echo "Run:                ./beacon.sh examples/control-flow.beacon"
echo "Verify:             ./beacon.sh self-host"
echo
echo "Review 'git status', then commit the bootstrap binary and C# deletions together."
