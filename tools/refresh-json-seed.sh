#!/usr/bin/env bash
set -euo pipefail

python3 tools/refresh-json-seed.py beacon

MIGRATION=d6680d72646aed04cda62fdb76c74325c640cd94
BASE="https://raw.githubusercontent.com/thoersch/beacon-lang/$MIGRATION"
curl -fsSL "$BASE/tools/reconstruct-current-seed.py" -o /tmp/reconstruct-current-seed.py
curl -fsSL "$BASE/tools/migrate-fs-path-boundary.py" -o /tmp/migrate-fs-path-boundary.py
curl -fsSL "$BASE/tools/patch-seed-secondary-host-table.py" -o /tmp/patch-seed-secondary-host-table.py
python3 /tmp/reconstruct-current-seed.py
python3 /tmp/migrate-fs-path-boundary.py seed
python3 /tmp/patch-seed-secondary-host-table.py
python3 tools/refresh-json-seed.py seed

PROGRAM=tools/seed-refresh/Beacon.Compiler/Program.cs
grep -F 'public static string HostCharacter' "$PROGRAM"
grep -F '"Runtime.HostCharacter" => HostCharacterMethod' "$PROGRAM"
for removed in AppendFile DeletePath CopyFile ListFiles ListDirectories ParentPath FileName PathExtension PathIsAbsolute CombinePath DirectoryName FileExists ReadFile AbsolutePath EnvironmentValue; do
    if grep -F "Runtime.$removed" "$PROGRAM"; then
        echo "Old high-level runtime call returned during reconstruction: Runtime.$removed" >&2
        exit 1
    fi
done

rm -rf /tmp/beacon-stage0
dotnet publish tools/seed-refresh/Beacon.Compiler/Beacon.Compiler.csproj -c Release -o /tmp/beacon-stage0 -p:UseAppHost=false
rm -f /tmp/beacon-stage0/*.pdb

rm -rf bootstrap/stage0
mkdir -p bootstrap/stage0
cp /tmp/beacon-stage0/Beacon.Compiler.dll bootstrap/stage0/
cp /tmp/beacon-stage0/Beacon.Compiler.deps.json bootstrap/stage0/
cp /tmp/beacon-stage0/Beacon.Compiler.runtimeconfig.json bootstrap/stage0/
cat > bootstrap/stage0/PROVENANCE.txt <<EOF
Beacon Stage-0 bootstrap seed
=============================

Purpose: immutable CLR bootstrap/runtime boundary for the self-hosted Beacon compiler.
Seed refresh: adds hostCharacter(Number), the irreducible CLR primitive for constructing a String from a Unicode scalar. JSON parsing, serialization, escape handling, number grammar, surrogate handling, and validation remain Beacon code under std/json.beacon. Flattened else-if parser support and the reduced filesystem/path host boundary are preserved.
Historical implementation language: C#
Source branch: feature/std-json
.NET SDK: $(dotnet --version)

The one-time C# refresh source was reconstructed from the verified historical migration lineage and removed after this seed was built and fixed-point verified.
The canonical compiler implementation remains Beacon source under compiler/.
EOF
(cd bootstrap/stage0 && sha256sum Beacon.Compiler.dll Beacon.Compiler.deps.json Beacon.Compiler.runtimeconfig.json PROVENANCE.txt > SHA256SUMS)

export BEACON_HOME="$PWD"
bash ./beacon.sh self-host
bash ./beacon.sh examples/std-json.beacon

rm -rf tools/seed-refresh
rm -f tools/refresh-json-seed.py tools/refresh-json-seed.sh
rm -f .github/workflows/inspect-seed-json.yml
rm -f .github/workflows/refresh-json-seed.yml
rm -f .github/workflows/refresh-json-seed-v2.yml

if find . -path './.git' -prune -o \( -name '*.cs' -o -name '*.csproj' \) -print | grep -q .; then
    echo 'C# source remains after seed refresh.' >&2
    exit 1
fi

git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add compiler/emitter.beacon std/json.beacon bootstrap/stage0
git add -u tools .github/workflows
git commit -m 'Add Unicode scalar host primitive for std.json'
git push origin HEAD:feature/std-json
