from pathlib import Path

ROOT = Path('.')


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if old not in text:
        raise SystemExit(f'Expected migration pattern not found in {path}:\n{old[:300]}')
    path.write_text(text.replace(old, new, 1))


# ---------------------------------------------------------------------------
# Parser: unary numeric negation plus break/continue statements.
# ---------------------------------------------------------------------------
parser = ROOT / 'compiler/parser.beacon'

replace_once(
    parser,
    '''parseStatement: fn(state: record) = [
    result: atom | list | record = null,
    if checkIdentifier(state, "include") then
        result = parseInclude(state)
    else
        if checkIdentifier(state, "if") then
            result = parseIf(state)
        else
            if checkIdentifier(state, "for") then
                result = parseFor(state)
            else
                if checkToken(state, "identifier") and checkNextToken(state, "colon") then
                    result = parseDeclaration(state)
                else
                    result = parseExpression(state)
                end
            end
        end
    end,
    result
]
''',
    '''parseStatement: fn(state: record) = [
    result: atom | list | record = null,
    if checkIdentifier(state, "include") then
        result = parseInclude(state)
    else
        if checkIdentifier(state, "if") then
            result = parseIf(state)
        else
            if checkIdentifier(state, "for") then
                result = parseFor(state)
            else
                if matchIdentifier(state, "break") then
                    result = [symbol("break")]
                else
                    if matchIdentifier(state, "continue") then
                        result = [symbol("continue")]
                    else
                        if checkToken(state, "identifier") and checkNextToken(state, "colon") then
                            result = parseDeclaration(state)
                        else
                            result = parseExpression(state)
                        end
                    end
                end
            end
        end
    end,
    result
]
''')

replace_once(
    parser,
    '''parseUnary: fn(state: record) = [
    result: atom | list | record = null,
    if matchIdentifier(state, "not") then
        result = [symbol("not"), parseUnary(state)]
    else
        result = parsePostfix(state)
    end,
    result
]
''',
    '''parseUnary: fn(state: record) = [
    result: atom | list | record = null,
    if matchIdentifier(state, "not") then
        result = [symbol("not"), parseUnary(state)]
    else
        if matchToken(state, "minus") then
            result = [symbol("neg"), parseUnary(state)]
        else
            result = parsePostfix(state)
        end
    end,
    result
]
''')


# ---------------------------------------------------------------------------
# Emitter: loop-context stack and direct branch lowering.
# No Stage-0/runtime additions are required: all emitted plan operations already
# exist for ordinary if/for control flow and subtraction.
# ---------------------------------------------------------------------------
emitter = ROOT / 'compiler/emitter.beacon'

replace_once(
    emitter,
    '''labelCounter: number = 0

nextLabel: fn(prefix: string) = [
''',
    '''labelCounter: number = 0
loopContexts: list = []
loopDepth: number = 0

pushLoopContext: fn(breakLabel: string, continueLabel: string) = [
    context: record = { breakLabel: breakLabel, continueLabel: continueLabel },
    if loopDepth < loopContexts.length() then
        loopContexts@loopDepth = context
    else
        loopContexts.append(context)
    end,
    loopDepth += 1,
    null
]

popLoopContext: fn() = [
    loopDepth = loopDepth - 1,
    null
]

currentLoopContext: fn(keyword: string) = [
    if loopDepth == 0 then
        fail("'" + keyword + "' can only be used inside a loop")
    end,
    loopContexts@(loopDepth - 1)
]

nextLabel: fn(prefix: string) = [
''')

replace_once(
    emitter,
    '''isStatementForm: fn(node: atom | list | record) = [
    result: boolean = false,
    if isForm(node, "if") or isForm(node, "for") then
        result = true
    end,
    result
]
''',
    '''isStatementForm: fn(node: atom | list | record) = [
    result: boolean = false,
    if isForm(node, "if") or isForm(node, "for") or isForm(node, "break") or isForm(node, "continue") then
        result = true
    end,
    result
]
''')

replace_once(
    emitter,
    '''compile: fn(program: list) = [
    labelCounter = 0,
    head: symbol = program@0,
''',
    '''compile: fn(program: list) = [
    labelCounter = 0,
    loopContexts = [],
    loopDepth = 0,
    head: symbol = program@0,
''')

replace_once(
    emitter,
    '''emitStatement: fn(node: atom | list | record) = [
    result: list = [],
    if isForm(node, "if") then
        result = emitIf(node)
    else
        if isForm(node, "for") then
            result = emitFor(node)
        else
            result = emit(node)
            result.append({ op: "pop" })
        end
    end,
    result
]
''',
    '''emitStatement: fn(node: atom | list | record) = [
    result: list = [],
    if isForm(node, "if") then
        result = emitIf(node)
    else
        if isForm(node, "for") then
            result = emitFor(node)
        else
            if isForm(node, "break") then
                result = emitBreak()
            else
                if isForm(node, "continue") then
                    result = emitContinue()
                else
                    result = emit(node)
                    result.append({ op: "pop" })
                end
            end
        end
    end,
    result
]
''')

replace_once(
    emitter,
    '''    if form == "not" then
        result = emitLogicalNot(node)
        handled = true
    end,
''',
    '''    if form == "not" then
        result = emitLogicalNot(node)
        handled = true
    end,
    if form == "neg" then
        result = emitNegate(node)
        handled = true
    end,
''')

replace_once(
    emitter,
    '''emitBinary: fn(node: list, runtimeMethod: string) = [
    ops: list = emit(node@1),
    ops = ops.concat(emit(node@2)),
    ops.append({ op: "call", arg: runtimeMethod }),
    ops
]
''',
    '''emitBinary: fn(node: list, runtimeMethod: string) = [
    ops: list = emit(node@1),
    ops = ops.concat(emit(node@2)),
    ops.append({ op: "call", arg: runtimeMethod }),
    ops
]

emitNegate: fn(node: list) = [
    ops: list = [
        { op: "ldc.r8", arg: 0 },
        { op: "box", arg: "number" }
    ],
    ops = ops.concat(emit(node@1)),
    ops.append({ op: "call", arg: "Runtime.Sub" }),
    ops
]
''')

old_function = '''emitFunction: fn(node: list) = [
    result: list = [],

    if node.length() == 2 then
        result = emitFunctionClauses(node)
    else
        rawParams: list = node@1
        params: list = []

        for [i: number = 0, i < rawParams.length(), i += 1]
            parameter: record = rawParams@i
            paramName: symbol = parameter.name
            paramType: symbol = parameter.type
            params.append({ name: paramName.name, type: paramType.name })
        loop

        result = [{
            op: "fn",
            params: params,
            body: emitFunctionBody(node@2)
        }]
    end,

    result
]
'''
new_function = '''emitFunction: fn(node: list) = [
    result: list = [],

    if node.length() == 2 then
        result = emitFunctionClauses(node)
    else
        rawParams: list = node@1
        params: list = []

        for [i: number = 0, i < rawParams.length(), i += 1]
            parameter: record = rawParams@i
            paramName: symbol = parameter.name
            paramType: symbol = parameter.type
            params.append({ name: paramName.name, type: paramType.name })
        loop

        savedLoopDepth: number = loopDepth
        loopDepth = 0
        bodyPlan: list = emitFunctionBody(node@2)
        loopDepth = savedLoopDepth

        result = [{
            op: "fn",
            params: params,
            body: bodyPlan
        }]
    end,

    result
]
'''
replace_once(emitter, old_function, new_function)

old_for = '''emitFor: fn(node: list) = [
    conditionLabel: string = nextLabel("for_condition_"),
    endLabel: string = nextLabel("for_end_"),
    ops: list = emitStatement(node@1),
    ops.append({ op: "label", name: conditionLabel }),
    ops = ops.concat(emit(node@2)),
    ops.append({ op: "call", arg: "Runtime.Bool" }),
    ops.append({ op: "brfalse", label: endLabel }),
    ops = ops.concat(emitDoStatements(node@4)),
    ops = ops.concat(emit(node@3)),
    ops.append({ op: "pop" }),
    ops.append({ op: "br", label: conditionLabel }),
    ops.append({ op: "label", name: endLabel }),
    ops
]
'''
new_for = '''emitBreak: fn() = [
    context: record = currentLoopContext("break"),
    [{ op: "br", label: context.breakLabel }]
]

emitContinue: fn() = [
    context: record = currentLoopContext("continue"),
    [{ op: "br", label: context.continueLabel }]
]

emitFor: fn(node: list) = [
    conditionLabel: string = nextLabel("for_condition_"),
    continueLabel: string = nextLabel("for_continue_"),
    endLabel: string = nextLabel("for_end_"),
    ops: list = emitStatement(node@1),
    ops.append({ op: "label", name: conditionLabel }),
    ops = ops.concat(emit(node@2)),
    ops.append({ op: "call", arg: "Runtime.Bool" }),
    ops.append({ op: "brfalse", label: endLabel }),

    pushLoopContext(endLabel, continueLabel)
    bodyOps: list = emitDoStatements(node@4)
    popLoopContext()

    ops = ops.concat(bodyOps),
    ops.append({ op: "label", name: continueLabel }),
    ops = ops.concat(emit(node@3)),
    ops.append({ op: "pop" }),
    ops.append({ op: "br", label: conditionLabel }),
    ops.append({ op: "label", name: endLabel }),
    ops
]
'''
replace_once(emitter, old_for, new_for)


# ---------------------------------------------------------------------------
# Documentation.
# ---------------------------------------------------------------------------
readme = ROOT / 'README.md'
replace_once(
    readme,
    '''Logical:\n\n```text\nand  or  not\n```\n\nAssignment:\n''',
    '''Logical:\n\n```text\nand  or  not\n```\n\nUnary negation:\n\n```beacon\nx: number = -1\ny: number = -x\nz: number = -(x + 5)\n```\n\nLoop control uses `break` and `continue`. Both target the innermost loop; `continue` executes the `for` step before re-checking its condition:\n\n```beacon\nfor [i: number = 0, i < values.length(), i += 1]\n    if values@i == 0 then\n        continue\n    end\n\n    if values@i < 0 then\n        break\n    end\n\n    print(values@i)\nloop\n```\n\nUsing `break` or `continue` outside a loop is a compile error. Function bodies are separate control-flow scopes, so a function declared inside a loop cannot break or continue that enclosing loop.\n\nAssignment:\n''')


# ---------------------------------------------------------------------------
# Executable example used by migration verification and permanent CI.
# ---------------------------------------------------------------------------
example = ROOT / 'examples/unary-loop-control.beacon'
example.write_text('''negative: number = -1\nvalue: number = 4\n\nprint(negative)\nprint(-value)\nprint(5 + -2)\nprint(-2 * 3)\nprint(-(-2))\n\nvalues: list = [1, 2, 3, 4, 5]\ntotal: number = 0\n\nfor [i: number = 0, i < values.length(), i += 1]\n    if values@i == 2 then\n        continue\n    end\n\n    if values@i == 5 then\n        break\n    end\n\n    total += values@i\nloop\n\nprint(total)\n\nouterCount: number = 0\ninnerCount: number = 0\n\nfor [i: number = 0, i < 3, i += 1]\n    for [j: number = 0, j < 3, j += 1]\n        if j == 1 then\n            break\n        end\n        innerCount += 1\n    loop\n    outerCount += 1\nloop\n\nprint(outerCount)\nprint(innerCount)\n''')
