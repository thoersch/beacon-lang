from pathlib import Path
import re

root = Path('.')
beacon_files = list((root / 'compiler').glob('*.beacon'))
beacon_files.append(root / 'examples' / 'bootstrap-primitives.beacon')

# Statically named Record fields always use dot notation.
for path in beacon_files:
    text = path.read_text()
    text = re.sub(r'@"([A-Za-z_][A-Za-z0-9_]*)"', r'.\1', text)
    path.write_text(text)

replacements = {
    'compiler/core.beacon': [
        ('character: string = name@i', 'character: string = name.slice(i, 1)'),
        ('children@part = newNamespaceNode()', 'children.set(part, newNamespaceNode())'),
        ('node = children@part', 'node = children.get(part)'),
        ('childExpressions@key = namespaceNodeExpression(children@key)', 'childExpressions.set(key, namespaceNodeExpression(children.get(key)))'),
        ('namespaceNodeExpression(root@name)', 'namespaceNodeExpression(root.get(name))'),
    ],
    'compiler/emitter.beacon': [
        ('value: emit(node@key)', 'value: emit(node.get(key))'),
        ('value: emit(children@key)', 'value: emit(children.get(key))'),
        ('member: atom | list | record = members@key', 'member: atom | list | record = members.get(key)'),
    ],
    'compiler/lexer.beacon': [
        ('result = source@index', 'result = source.slice(index, 1)'),
        ('if characters@i == character then', 'if characters.slice(i, 1) == character then'),
    ],
    'compiler/diagnostics.beacon': [
        ('character: string = source@i', 'character: string = source.slice(i, 1)'),
    ],
    'compiler/parser.beacon': [
        ('members@(nameToken.text) = parseFunctionAfterFn(state)', 'members.set(nameToken.text, parseFunctionAfterFn(state))'),
        ('members@(nameToken.text) = symbol(parseTypeAnnotation(state))', 'members.set(nameToken.text, symbol(parseTypeAnnotation(state)))'),
        ('result@(key.text) = parseExpression(state)', 'result.set(key.text, parseExpression(state))'),
    ],
    'compiler/typecheck.beacon': [
        ('types@(name.name) = node@3', 'types.set(name.name, node@3)'),
        ('character: string = typeName@i', 'character: string = typeName.slice(i, 1)'),
        ('if left@i == right@i then', 'if left.slice(i, 1) == right.slice(i, 1) then'),
        ('kind(members@key)', 'kind(members.get(key))'),
        ('typeNode: atom | list | record = types@typeName', 'typeNode: atom | list | record = types.get(typeName)'),
        ('expectedFieldType: symbol = members@key', 'expectedFieldType: symbol = members.get(key)'),
        ('validateValueAgainstType(value@key,', 'validateValueAgainstType(value.get(key),'),
        ('expectedSymbol: symbol = members@suggestion', 'expectedSymbol: symbol = members.get(suggestion)'),
        ('{ field: key, type: staticTypeName(value@key) }', '{ field: key, type: staticTypeName(value.get(key)) }'),
        ('member: atom | list | record = members@key', 'member: atom | list | record = members.get(key)'),
    ],
    'examples/bootstrap-primitives.beacon': [
        ('print(source@0)', 'print(source.slice(0, 1))'),
        ('print(node.text)\nprint(node.has("kind"))', 'print(node.text)\nfield: string = "text"\nprint(node.get(field))\nnode.set(field, "name")\nprint(node.text)\nprint(node.has("kind"))'),
    ],
}

for filename, changes in replacements.items():
    path = root / filename
    text = path.read_text()
    for old, new in changes:
        if old not in text:
            raise SystemExit(f'Expected migration pattern not found in {filename}: {old}')
        text = text.replace(old, new)
    path.write_text(text)

readme = root / 'README.md'
text = readme.read_text()
old = '''Member access uses `.`:\n\n```beacon\nperson.name\n```\n'''
new = '''Member access uses `.`:\n\n```beacon\nperson.name\n```\n\n`@` is exclusively positional List access. Records are named structures and Strings are not Lists, so neither supports `@`. When a Record key is data rather than a statically known name, use the explicit Record methods:\n\n```beacon\nfield: string = "name"\nprint(person.get(field))\nperson.set(field, "Grace")\n```\n'''
if old not in text:
    raise SystemExit('README member-access section was not found')
readme.write_text(text.replace(old, new, 1))
