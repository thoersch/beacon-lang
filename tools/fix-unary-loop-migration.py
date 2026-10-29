from pathlib import Path

path = Path('compiler/emitter.beacon')
text = path.read_text()

old = '''        savedLoopDepth: number = loopDepth
        loopDepth = 0
        bodyPlan: list = emitFunctionBody(node@2)
        loopDepth = savedLoopDepth
'''
new = '''        savedLoopDepth: number = loopDepth,
        loopDepth = 0,
        bodyPlan: list = emitFunctionBody(node@2),
        loopDepth = savedLoopDepth,
'''
if old not in text:
    raise SystemExit('Function loop-scope separator block not found')
text = text.replace(old, new, 1)

old = '''    pushLoopContext(endLabel, continueLabel)
    bodyOps: list = emitDoStatements(node@4)
    popLoopContext()
'''
new = '''    pushLoopContext(endLabel, continueLabel),
    bodyOps: list = emitDoStatements(node@4),
    popLoopContext(),
'''
if old not in text:
    raise SystemExit('For loop-context separator block not found')
text = text.replace(old, new, 1)

path.write_text(text)

parts = [
    'compiler/diagnostics.beacon',
    'compiler/core.beacon',
    'compiler/lexer.beacon',
    'compiler/parser.beacon',
    'compiler/source-map.beacon',
    'compiler/typecheck.beacon',
    'compiler/emitter.beacon',
]
combined = []
for part in parts:
    combined.extend(Path(part).read_text().splitlines())

print('--- combined compiler around reported line 2597 ---')
for line_no in range(2588, 2607):
    if line_no <= len(combined):
        print(f'{line_no:04}: {combined[line_no - 1]}')
