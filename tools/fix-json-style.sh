#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path
path = Path('std/json.beacon')
text = path.read_text()
old = '''        else
            if _jsonControlCode(character) >= 0 then
                _jsonError(state, "Unescaped control character in string")
            end
            result += character
'''
new = '''        else if _jsonControlCode(character) >= 0 then
            _jsonError(state, "Unescaped control character in string")
        else
            result += character
'''
if text.count(old) != 1:
    raise SystemExit('Expected one nested string-control conditional')
text = text.replace(old, new, 1)
text = text.replace('    scanning: boolean = true,\n\n', '', 1)
path.write_text(text)
PY

rm -f tools/fix-json-style.sh
rm -f .github/workflows/fix-json-style.yml
rm -f .github/workflows/refresh-json-seed-v2.yml

git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add std/json.beacon
git add -u tools/fix-json-style.sh .github/workflows/fix-json-style.yml .github/workflows/refresh-json-seed-v2.yml
git commit -m 'Use canonical else-if style in std.json'
git push origin HEAD:feature/std-json
