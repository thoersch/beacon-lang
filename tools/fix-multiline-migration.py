from pathlib import Path

path = Path("tools/apply-multiline-expressions.py")
text = path.read_text()
old = "marker = '''## Control flow\\n'''"
new = "marker = '''## Typing\\n'''"
if old not in text:
    raise SystemExit("Expected README anchor in migration script")
path.write_text(text.replace(old, new, 1))
