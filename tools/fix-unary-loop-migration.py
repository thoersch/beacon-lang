from pathlib import Path

path = Path('compiler/emitter.beacon')
text = path.read_text()

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
