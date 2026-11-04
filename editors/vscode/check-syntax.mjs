import fs from "node:fs"

const grammar = JSON.parse(
    fs.readFileSync(new URL("./syntaxes/beacon.tmLanguage.json", import.meta.url), "utf8")
)

const checks = [
    {
        repository: "keywords",
        scope: "keyword.control.conditional.beacon",
        tokens: ["if", "then", "else", "when", "otherwise", "end"]
    },
    {
        repository: "keywords",
        scope: "keyword.control.loop.beacon",
        tokens: ["for", "loop"]
    },
    {
        repository: "keywords",
        scope: "keyword.control.flow.beacon",
        tokens: ["break", "continue"]
    },
    {
        repository: "keywords",
        scope: "keyword.control.logical.beacon",
        tokens: ["and", "or", "not"]
    },
    {
        repository: "keywords",
        scope: "storage.modifier.function.beacon",
        tokens: ["private"]
    },
    {
        repository: "keywords",
        scope: "keyword.control.import.include.beacon",
        tokens: ["include"]
    },
    {
        repository: "types",
        scope: "storage.type.function.beacon",
        tokens: ["fn"]
    },
    {
        repository: "types",
        scope: "storage.type.beacon",
        tokens: ["type", "number", "string", "boolean", "list", "record", "atom", "symbol", "null"]
    },
    {
        repository: "constants",
        scope: "constant.language.boolean.beacon",
        tokens: ["true", "false"]
    },
    {
        repository: "constants",
        scope: "constant.language.null.beacon",
        tokens: ["null"]
    },
    {
        repository: "operators",
        scope: "keyword.operator.assignment.beacon",
        tokens: ["=", "+="]
    },
    {
        repository: "operators",
        scope: "keyword.operator.comparison.beacon",
        tokens: ["==", "!=", "<", "<=", ">", ">="]
    },
    {
        repository: "operators",
        scope: "keyword.operator.arithmetic.beacon",
        tokens: ["+", "-", "*", "/"]
    },
    {
        repository: "operators",
        scope: "keyword.operator.index.beacon",
        tokens: ["@"]
    },
    {
        repository: "operators",
        scope: "keyword.operator.type-union.beacon",
        tokens: ["|"]
    }
]

const failures = []

for (const check of checks) {
    const patterns = grammar.repository?.[check.repository]?.patterns ?? []
    const matchingPatterns = patterns.filter(pattern => pattern.name === check.scope && pattern.match)

    for (const token of check.tokens) {
        const highlighted = matchingPatterns.some(pattern => {
            const exact = new RegExp(`^(?:${pattern.match})$`)
            return exact.test(token)
        })

        if (!highlighted) {
            failures.push(`${token}: expected ${check.scope}`)
        }
    }
}

// Parameterized Lists and anonymous typed Records are first-class syntax.
const listPattern = grammar.repository?.["generic-list"]?.patterns?.find(
    pattern => pattern.name === "meta.type.parameterized-list.beacon"
)
if (!listPattern || !(new RegExp(listPattern.begin)).test("list<number|weapon>") ||
    !listPattern.patterns?.some(pattern => pattern.include === "#generic-list") ||
    !listPattern.patterns?.some(pattern => pattern.name === "keyword.operator.type-union.beacon")) {
    failures.push("list<T|U> and nested list<list<T>> must be highlighted as Beacon types")
}
const constructorPattern = grammar.repository?.["typed-constructor"]?.patterns?.find(
    pattern => pattern.name === "meta.typed.record.constructor.beacon"
)
if (!constructorPattern || !(new RegExp(constructorPattern.match)).test("item {")) {
    failures.push("Type { ... } anonymous typed constructors must be highlighted")
}

if (failures.length > 0) {
    console.error("Beacon VS Code grammar is missing syntax coverage:")
    for (const failure of failures) {
        console.error(`  - ${failure}`)
    }
    process.exit(1)
}

console.log("Beacon VS Code grammar covers the current language keyword, type, literal, and operator surface.")
