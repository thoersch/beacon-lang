#!/usr/bin/env bash
set -euo pipefail
export BEACON_HOME="$PWD"
run() { bash ./beacon.sh "$1"; }
good() {
  local label="$1" source="$2" expected="$3"
  local file="/tmp/beacon-typed-good-$$.beacon"
  printf '%s\n' "$source" > "$file"
  local actual
  actual="$(run "$file")"
  if [[ "$actual" != "$expected" ]]; then
    printf 'FAIL %s\nexpected:\n%s\nactual:\n%s\n' "$label" "$expected" "$actual" >&2
    exit 1
  fi
  echo "PASS $label"
  rm -f "$file"
}
bad() {
  local label="$1" source="$2" expected="$3"
  local file="/tmp/beacon-typed-bad-$$.beacon"
  printf '%s\n' "$source" > "$file"
  local actual status
  set +e
  actual="$(run "$file" 2>&1)"
  status=$?
  set -e
  if [[ $status -eq 0 ]] || ! grep -F "$expected" <<< "$actual" >/dev/null; then
    printf 'FAIL %s\nexpected failure containing: %s\nactual (%s):\n%s\n' "$label" "$expected" "$status" "$actual" >&2
    exit 1
  fi
  echo "PASS rejected $label"
  rm -f "$file"
}

sample="$(run examples/rpg-typed-inventory.beacon)"
[[ "$sample" == $'Jon\nPotion\n12\nDefeated the troll\n3' ]] ||
  { printf 'RPG example output mismatch: %s\n' "$sample" >&2; exit 1; }

good "generic typed lists, null and hetero list" '
values: list<number|string> = [1, "two", 3]
fallback: list<number>|null = null
nested: list<list<number>> = [[1, 2], [3]]
anything: list = [1, true, "ok"]
print(values@1)
print(nested@1@0)
print(anything@2)
' $'two\n3\nok'

good "contextual named Records and explicit values" '
item: type = { name: string }
hero: type = { inventory: list<item> }
jon: hero = { inventory: [{ name: "Potion" }, item { name: "Axe" }] }
print(jon.inventory@0.name)
print(jon.inventory@1.name)
' $'Potion\nAxe'

good "distinct union types and inline constructors" '
item: type = { name: string }
weapon: type = { damage: number }
contents: list<item|weapon> = [item { name: "Potion" }, { damage: 10 }]
print(contents@0.name)
print(contents@1.damage)
' $'Potion\n10'

good "typed lists survive filter, tail and concat" '
numbers: list<number> = [1, 2, 3]
greaterThanOne: fn(value: number) = value > 1
tail: list<number> = numbers.tail()
positives: list<number> = numbers.filter(greaterThanOne)
more: list<number> = numbers.concat([4, 5])
print(tail@0)
print(positives@0)
print(more@4)
' $'2\n2\n5'

good "typed variables through functions" '
bump: fn(values: list<number>) = [
    values.push(9),
    values.length()
]
numbers: list<number> = [1, 2]
print(bump(numbers))
print(numbers@2)
' $'3\n9'

good "nested contextual named Records" '
loot: type = { quantity: number }
bag: type = { items: list<loot> }
hero: type = { bags: list<bag> }
myHero: hero = { bags: [{ items: [{ quantity: 2 }] }] }
print(myHero.bags@0.items@0.quantity)
' '2'

bad "incorrect List literal" '
values: list<number> = [1, "oops"]
' 'expected number, got string'

bad "invalid push" '
values: list<number> = [1]
values.push("oops")
' 'Expected number, got string'

bad "invalid index assignment" '
values: list<number> = [1]
values@0 = "oops"
' 'Expected number, got string'

bad "invalid reassign" '
values: list<number> = [1]
values = ["oops"]
' 'Invalid list<number> element @0'

bad "invariant typed lists" '
numbers: list<number> = [1]
atoms: list<atom> = numbers
' 'mutable Lists are invariant'

bad "generic nested type rejection" '
values: list<list<number>> = [[1], [2, "oops"]]
' 'expected number, got string'

bad "Record field reassignment enforces list type" '
hero: type = { inventory: list<number> }
jon: hero = { inventory: [1] }
jon.inventory = ["oops"]
' 'Expected number, got string'

bad "Record dynamic set enforces list type" '
hero: type = { inventory: list<number> }
jon: hero = { inventory: [1] }
jon.set("inventory", ["oops"])
' 'Expected number, got string'

bad "unknown type in inline constructor" '
bad: record = missingType { name: "?" }
' "Unknown type 'missingType'"

bad "typed constructor fields checked" '
item: type = { name: string, quantity: number }
potion: item = item { name: "Potion", quantity: "oops" }
' 'expected number, got string'

bad "ambiguous union contextual shape" '
left: type = { value: number }
right: type = { value: number }
objects: list<left|right> = [{ value: 1 }]
' 'Ambiguous Record'

good "explicit constructor resolves ambiguity" '
left: type = { value: number }
right: type = { value: number }
objects: list<left|right> = [left { value: 1 }, right { value: 2 }]
print(objects@0.value)
print(objects@1.value)
' $'1\n2'

bad "typed Record nominal identity" '
left: type = { value: number }
right: type = { value: number }
first: left = { value: 1 }
second: right = first
' 'Expected right, got left'

bad "typed List via untyped alias" '
numbers: list<number> = [1, 2]
alias: list = numbers
alias.push("oops")
' 'Expected number, got string'

bad "empty generic argument" '
numbers: list<> = []
' 'Expected type name'

bad "comma generic arguments disallowed" '
numbers: list<number,string> = []
' "Expected '>'"

bad "trailing pipe disallowed" '
numbers: list<number|> = []
' 'Expected type name'

bad "unknown type in empty typed List" '
empty: list<Undeclared> = []
' "Unknown type 'Undeclared'"

bad "unknown nested type in empty typed List" '
empty: list<list<Undeclared>> = []
' "Unknown type 'Undeclared'"

bad "typed List tail cannot accept wrong element" '
values: list<number> = [1, 2]
rest: list = values.tail()
rest.push("invalid")
' 'Expected number, got string'

bad "typed List filter preserves the constraint" '
positive: fn(v: number) = v > 0
values: list<number> = [1, 2]
filtered: list = values.filter(positive)
filtered.push("invalid")
' 'Expected number, got string'

bad "typed List concat preserves the constraint" '
values: list<number> = [1, 2]
combined: list = values.concat([3])
combined@0 = "invalid"
' 'Expected number, got string'

bad "typed List concat rejects incompatible input" '
numbers: list<number> = [1, 2]
strings: list<string> = ["x"]
mixed: list = numbers.concat(strings)
' 'mutable Lists are invariant'

bad "named Record rejects arbitrary field mutation" '
item: type = { name: string }
potion: item = { name: "Potion" }
potion.newField = 42
' "Unknown field 'newField'"

echo "All typed List and inline Record tests passed."
