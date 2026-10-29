using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;
using System.Reflection;
using System.Reflection.Emit;

namespace Beacon.Compiler;

// ---------- Core: Atom / List / Record ----------

abstract record Core;

enum AtomKind { Symbol, Number, String, Boolean, Null }

sealed record Atom(AtomKind Kind, object? Value) : Core
{
    public static Atom Symbol(string value) => new(AtomKind.Symbol, value);
    public static Atom Number(double value) => new(AtomKind.Number, value);
    public static Atom String(string value) => new(AtomKind.String, value);
    public static Atom Boolean(bool value) => new(AtomKind.Boolean, value);
    public static readonly Atom Null = new(AtomKind.Null, null);
    public string Text => (string)Value!;
}

sealed record ListCore(List<Core> Items) : Core
{
    public ListCore(params Core[] items) : this(items.ToList()) { }
}

sealed record RecordCore(List<KeyValuePair<string, Core>> Fields) : Core
{
    public RecordCore() : this(new List<KeyValuePair<string, Core>>()) { }
    public void Add(string key, Core value) => Fields.Add(new(key, value));
}

static class CoreForms
{
    public static ListCore Form(string name, params Core[] items) =>
        new(new[] { Atom.Symbol(name) }.Concat(items).ToList());
}

// ---------- Lexer ----------

enum TokenKind
{
    Identifier, Number, String, NewLine,
    Colon, Equal, EqualEqual, BangEqual, PlusEqual, Plus, Minus, Star, Slash,
    Less, LessEqual, Greater, GreaterEqual, At, Pipe,
    LParen, RParen, LBracket, RBracket, LBrace, RBrace,
    Dot, Comma,
    End
}

readonly record struct Token(TokenKind Kind, string Text, int Line, int Column);

sealed class Lexer
{
    private readonly string _source;
    private int _i;
    private int _line = 1;
    private int _column = 1;

    public Lexer(string source) => _source = source.Replace("\r\n", "\n");

    public List<Token> Lex()
    {
        var tokens = new List<Token>();
        while (!AtEnd)
        {
            var c = Peek();
            var line = _line;
            var col = _column;

            if (c is ' ' or '\t') { Advance(); continue; }
            if (c == '\n') { Advance(); tokens.Add(new(TokenKind.NewLine, "\n", line, col)); continue; }

            if (c == '/' && Peek(1) == '/')
            {
                while (!AtEnd && Peek() != '\n') Advance();
                continue;
            }

            if (char.IsLetter(c) || c == '_')
            {
                var start = _i;
                while (!AtEnd && (char.IsLetterOrDigit(Peek()) || Peek() == '_')) Advance();
                tokens.Add(new(TokenKind.Identifier, _source[start.._i], line, col));
                continue;
            }

            if (char.IsDigit(c))
            {
                var start = _i;
                while (!AtEnd && char.IsDigit(Peek())) Advance();
                if (!AtEnd && Peek() == '.' && char.IsDigit(Peek(1)))
                {
                    Advance();
                    while (!AtEnd && char.IsDigit(Peek())) Advance();
                }
                tokens.Add(new(TokenKind.Number, _source[start.._i], line, col));
                continue;
            }

            if (c == '"')
            {
                Advance();
                var sb = new StringBuilder();
                while (!AtEnd && Peek() != '"')
                {
                    if (Peek() == '\\')
                    {
                        Advance();
                        if (AtEnd) throw Error("Unterminated string", line, col);
                        var esc = Advance();
                        sb.Append(esc switch
                        {
                            'n' => '\n', 'r' => '\r', 't' => '\t',
                            '"' => '"', '\\' => '\\', _ => esc
                        });
                    }
                    else sb.Append(Advance());
                }
                if (AtEnd) throw Error("Unterminated string", line, col);
                Advance();
                tokens.Add(new(TokenKind.String, sb.ToString(), line, col));
                continue;
            }

            TokenKind kind;
            string text;
            switch (c)
            {
                case ':': kind = TokenKind.Colon; text = ":"; Advance(); break;
                case '=':
                    if (Peek(1) == '=') { kind = TokenKind.EqualEqual; text = "=="; Advance(); Advance(); }
                    else { kind = TokenKind.Equal; text = "="; Advance(); }
                    break;
                case '!':
                    if (Peek(1) == '=') { kind = TokenKind.BangEqual; text = "!="; Advance(); Advance(); }
                    else throw Error("Expected '=' after '!'", line, col);
                    break;
                case '+':
                    if (Peek(1) == '=') { kind = TokenKind.PlusEqual; text = "+="; Advance(); Advance(); }
                    else { kind = TokenKind.Plus; text = "+"; Advance(); }
                    break;
                case '-': kind = TokenKind.Minus; text = "-"; Advance(); break;
                case '*': kind = TokenKind.Star; text = "*"; Advance(); break;
                case '/': kind = TokenKind.Slash; text = "/"; Advance(); break;
                case '<':
                    if (Peek(1) == '=') { kind = TokenKind.LessEqual; text = "<="; Advance(); Advance(); }
                    else { kind = TokenKind.Less; text = "<"; Advance(); }
                    break;
                case '>':
                    if (Peek(1) == '=') { kind = TokenKind.GreaterEqual; text = ">="; Advance(); Advance(); }
                    else { kind = TokenKind.Greater; text = ">"; Advance(); }
                    break;
                case '@': kind = TokenKind.At; text = "@"; Advance(); break;
                case '|': kind = TokenKind.Pipe; text = "|"; Advance(); break;
                case '(': kind = TokenKind.LParen; text = "("; Advance(); break;
                case ')': kind = TokenKind.RParen; text = ")"; Advance(); break;
                case '[': kind = TokenKind.LBracket; text = "["; Advance(); break;
                case ']': kind = TokenKind.RBracket; text = "]"; Advance(); break;
                case '{': kind = TokenKind.LBrace; text = "{"; Advance(); break;
                case '}': kind = TokenKind.RBrace; text = "}"; Advance(); break;
                case '.': kind = TokenKind.Dot; text = "."; Advance(); break;
                case ',': kind = TokenKind.Comma; text = ","; Advance(); break;
                default: throw Error($"Unexpected character '{c}'", line, col);
            }
            tokens.Add(new(kind, text, line, col));
        }
        tokens.Add(new(TokenKind.End, "", _line, _column));
        return tokens;
    }

    private bool AtEnd => _i >= _source.Length;
    private char Peek(int offset = 0) => _i + offset < _source.Length ? _source[_i + offset] : '\0';
    private char Advance()
    {
        var c = _source[_i++];
        if (c == '\n') { _line++; _column = 1; }
        else _column++;
        return c;
    }

    private static Exception Error(string message, int line, int col) =>
        new Exception($"{message} at {line}:{col}");
}

// ---------- Parser: surface syntax -> Atom/List/Record core ----------

sealed class Parser
{
    private readonly List<Token> _tokens;
    private int _i;

    public Parser(List<Token> tokens) => _tokens = tokens;

    public Core ParseProgram()
    {
        var expressions = new List<Core> { Atom.Symbol("do") };
        SkipNewLines();
        while (!Check(TokenKind.End))
        {
            expressions.Add(ParseStatement());
            RequireStatementBoundary();
            SkipNewLines();
        }
        return new ListCore(expressions);
    }

    private Core ParseStatement()
    {
        if (CheckIdentifier("if")) return ParseIf();
        if (CheckIdentifier("for")) return ParseFor();
        if (Check(TokenKind.Identifier) && CheckNext(TokenKind.Colon))
            return ParseDeclaration();
        return ParseExpression();
    }

    private Core ParseIf()
    {
        ConsumeIdentifier("if", "Expected 'if'");
        var condition = ParseExpression();
        ConsumeIdentifier("then", "Expected 'then' after if condition");
        RequireNewLine("Expected newline after 'then'");

        var thenItems = ParseStatementsUntil("else", "end");
        Core elseBody = new ListCore(new List<Core> { Atom.Symbol("do") });

        if (MatchIdentifier("else"))
        {
            RequireNewLine("Expected newline after 'else'");
            elseBody = ParseStatementsUntil("end");
        }

        ConsumeIdentifier("end", "Expected 'end' to close if");
        return CoreForms.Form("if", condition, thenItems, elseBody);
    }

    private Core ParseFor()
    {
        ConsumeIdentifier("for", "Expected 'for'");
        Consume(TokenKind.LBracket, "Expected '[' after 'for'");

        Core initializer;
        if (Check(TokenKind.Identifier) && CheckNext(TokenKind.Colon)) initializer = ParseDeclaration();
        else initializer = ParseExpression();

        Consume(TokenKind.Comma, "Expected ',' after for initializer");
        var condition = ParseExpression();
        Consume(TokenKind.Comma, "Expected ',' after for condition");
        var step = ParseExpression();
        Consume(TokenKind.RBracket, "Expected ']' after for header");
        RequireNewLine("Expected newline after for header");

        var body = ParseStatementsUntil("loop");
        ConsumeIdentifier("loop", "Expected 'loop' to close for");
        return CoreForms.Form("for", initializer, condition, step, body);
    }

    private ListCore ParseStatementsUntil(params string[] terminators)
    {
        var items = new List<Core> { Atom.Symbol("do") };
        SkipNewLines();
        while (!Check(TokenKind.End) && !terminators.Any(CheckIdentifier))
        {
            items.Add(ParseStatement());
            RequireStatementBoundary();
            SkipNewLines();
        }
        if (Check(TokenKind.End))
            throw Error(Current, $"Expected {string.Join(" or ", terminators.Select(x => $"'{x}'"))}");
        return new ListCore(items);
    }

    private Core ParseDeclaration()
    {
        var name = Consume(TokenKind.Identifier, "Expected declaration name").Text;
        Consume(TokenKind.Colon, "Expected ':'");

        if (MatchIdentifier("fn"))
        {
            var fn = ParseFunctionAfterFn();
            return CoreForms.Form("def", Atom.Symbol(name), Atom.Symbol("fn"), fn);
        }

        if (MatchIdentifier("type"))
        {
            Consume(TokenKind.Equal, "Expected '=' after type declaration");
            var type = ParseTypeDefinition();
            return CoreForms.Form("def", Atom.Symbol(name), Atom.Symbol("type"), type);
        }

        var typeName = ParseTypeAnnotation();
        Consume(TokenKind.Equal, "Expected '=' in declaration");
        var value = ParseExpression();
        return CoreForms.Form("def", Atom.Symbol(name), Atom.Symbol(typeName), value);
    }

    private string ParseTypeAnnotation()
    {
        var types = new List<string>();
        while (true)
        {
            var token = Consume(TokenKind.Identifier, "Expected type name");
            if (token.Text == "any")
                throw Error(token, "Beacon has no 'any' type; use an explicit type or union");
            types.Add(token.Text);
            if (!Match(TokenKind.Pipe)) break;
        }
        return string.Join("|", types);
    }

    private Core ParseFunctionAfterFn()
    {
        Consume(TokenKind.LParen, "Expected '(' after fn");
        var parameters = new List<Core>();
        SkipNewLines();
        if (!Check(TokenKind.RParen))
        {
            while (true)
            {
                var pName = Consume(TokenKind.Identifier, "Expected parameter name").Text;
                Consume(TokenKind.Colon, "Expected ':' after parameter name");
                var pType = ParseTypeAnnotation();
                var p = new RecordCore();
                p.Add("name", Atom.Symbol(pName));
                p.Add("type", Atom.Symbol(pType));
                parameters.Add(p);
                if (!Match(TokenKind.Comma)) break;
                SkipNewLines();
            }
        }
        Consume(TokenKind.RParen, "Expected ')' after parameters");
        Consume(TokenKind.Equal, "Expected '=' before function body");
        var body = ParseBody();
        return CoreForms.Form("fn", new ListCore(parameters), body);
    }

    private Core ParseBody()
    {
        SkipNewLines();
        if (!Match(TokenKind.LBracket)) return ParseExpression();

        var items = new List<Core> { Atom.Symbol("do") };
        SkipNewLines();
        if (!Check(TokenKind.RBracket))
        {
            while (true)
            {
                items.Add(ParseStatement());
                SkipNewLines();
                if (Match(TokenKind.RBracket)) break;
                Consume(TokenKind.Comma, "Beacon Lists require commas between elements");
                SkipNewLines();
            }
            return new ListCore(items);
        }
        Advance();
        return new ListCore(items);
    }

    private Core ParseTypeDefinition()
    {
        Consume(TokenKind.LBrace, "Expected '{' after type =");
        var members = new RecordCore();
        SkipNewLines();

        while (!Check(TokenKind.RBrace))
        {
            var name = Consume(TokenKind.Identifier, "Expected member name").Text;
            Consume(TokenKind.Colon, "Expected ':' after member name");

            if (MatchIdentifier("fn"))
                members.Add(name, ParseFunctionAfterFn());
            else
                members.Add(name, Atom.Symbol(ParseTypeAnnotation()));

            if (Match(TokenKind.Comma)) SkipNewLines();
            else if (!Check(TokenKind.RBrace)) RequireNewLine("Expected newline or ',' between Record members");
            SkipNewLines();
        }

        Consume(TokenKind.RBrace, "Expected '}'");
        return CoreForms.Form("type", members);
    }

    private Core ParseExpression() => ParseAssignment();

    private Core ParseAssignment()
    {
        var left = ParseOr();
        if (Match(TokenKind.PlusEqual))
            return CoreForms.Form("+=", left, ParseAssignment());
        if (Match(TokenKind.Equal))
            return CoreForms.Form("=", left, ParseAssignment());
        return left;
    }


    private Core ParseOr()
    {
        var expr = ParseAnd();
        while (MatchIdentifier("or")) expr = CoreForms.Form("or", expr, ParseAnd());
        return expr;
    }

    private Core ParseAnd()
    {
        var expr = ParseComparison();
        while (MatchIdentifier("and")) expr = CoreForms.Form("and", expr, ParseComparison());
        return expr;
    }

    private Core ParseComparison()
    {
        var expr = ParseAdditive();
        while (true)
        {
            if (Match(TokenKind.EqualEqual)) expr = CoreForms.Form("==", expr, ParseAdditive());
            else if (Match(TokenKind.BangEqual)) expr = CoreForms.Form("!=", expr, ParseAdditive());
            else if (Match(TokenKind.Less)) expr = CoreForms.Form("<", expr, ParseAdditive());
            else if (Match(TokenKind.LessEqual)) expr = CoreForms.Form("<=", expr, ParseAdditive());
            else if (Match(TokenKind.Greater)) expr = CoreForms.Form(">", expr, ParseAdditive());
            else if (Match(TokenKind.GreaterEqual)) expr = CoreForms.Form(">=", expr, ParseAdditive());
            else break;
        }
        return expr;
    }

    private Core ParseAdditive()
    {
        var expr = ParseMultiplicative();
        while (true)
        {
            if (Match(TokenKind.Plus)) expr = CoreForms.Form("+", expr, ParseMultiplicative());
            else if (Match(TokenKind.Minus)) expr = CoreForms.Form("-", expr, ParseMultiplicative());
            else break;
        }
        return expr;
    }

    private Core ParseMultiplicative()
    {
        var expr = ParseUnary();
        while (true)
        {
            if (Match(TokenKind.Star)) expr = CoreForms.Form("*", expr, ParseUnary());
            else if (Match(TokenKind.Slash)) expr = CoreForms.Form("/", expr, ParseUnary());
            else break;
        }
        return expr;
    }

    private Core ParseUnary()
    {
        if (MatchIdentifier("not")) return CoreForms.Form("not", ParseUnary());
        return ParsePostfix();
    }

    private Core ParsePostfix()
    {
        Core expr = ParsePrimary();
        while (true)
        {
            if (Match(TokenKind.Dot))
            {
                var member = Consume(TokenKind.Identifier, "Expected member name after '.'").Text;
                expr = CoreForms.Form("get", expr, Atom.String(member));
                continue;
            }

            if (Match(TokenKind.At))
            {
                var index = ParsePrimary();
                expr = CoreForms.Form("index", expr, index);
                continue;
            }

            if (Match(TokenKind.LParen))
            {
                var items = new List<Core> { Atom.Symbol("call"), expr };
                SkipNewLines();
                if (!Check(TokenKind.RParen))
                {
                    while (true)
                    {
                        items.Add(ParseExpression());
                        if (!Match(TokenKind.Comma)) break;
                        SkipNewLines();
                    }
                }
                Consume(TokenKind.RParen, "Expected ')' after arguments");
                expr = new ListCore(items);
                continue;
            }

            break;
        }
        return expr;
    }

    private Core ParsePrimary()
    {
        if (Match(TokenKind.Number))
            return Atom.Number(double.Parse(Previous.Text, CultureInfo.InvariantCulture));
        if (Match(TokenKind.String)) return Atom.String(Previous.Text);

        if (Match(TokenKind.Identifier))
        {
            return Previous.Text switch
            {
                "true" => Atom.Boolean(true),
                "false" => Atom.Boolean(false),
                "null" => Atom.Null,
                _ => Atom.Symbol(Previous.Text)
            };
        }

        if (Match(TokenKind.Dot))
        {
            var member = Consume(TokenKind.Identifier, "Expected member after '.'").Text;
            return CoreForms.Form("get", Atom.Symbol("self"), Atom.String(member));
        }

        if (Match(TokenKind.LParen))
        {
            var expr = ParseExpression();
            Consume(TokenKind.RParen, "Expected ')'");
            return expr;
        }

        if (Match(TokenKind.LBracket)) return ParseListLiteralAfterOpen();
        if (Match(TokenKind.LBrace)) return ParseRecordLiteralAfterOpen();

        throw Error(Current, $"Expected expression, got {Current.Kind}");
    }

    private Core ParseListLiteralAfterOpen()
    {
        var items = new List<Core> { Atom.Symbol("list") };
        SkipNewLines();
        if (!Check(TokenKind.RBracket))
        {
            while (true)
            {
                items.Add(ParseExpression());
                SkipNewLines();
                if (Match(TokenKind.RBracket)) return new ListCore(items);
                Consume(TokenKind.Comma, "Beacon Lists require commas between elements");
                SkipNewLines();
            }
        }
        Advance();
        return new ListCore(items);
    }

    private Core ParseRecordLiteralAfterOpen()
    {
        var record = new RecordCore();
        SkipNewLines();
        while (!Check(TokenKind.RBrace))
        {
            var key = Consume(TokenKind.Identifier, "Expected Record field name").Text;
            Consume(TokenKind.Colon, "Expected ':' after field name");
            record.Add(key, ParseExpression());

            if (Match(TokenKind.Comma)) SkipNewLines();
            else if (!Check(TokenKind.RBrace)) RequireNewLine("Expected newline or ',' between Record fields");
            SkipNewLines();
        }
        Consume(TokenKind.RBrace, "Expected '}'");
        return record;
    }

    private void RequireStatementBoundary()
    {
        if (Check(TokenKind.End) || Check(TokenKind.RBrace) || Check(TokenKind.RBracket)) return;
        if (!Check(TokenKind.NewLine)) throw Error(Current, "Expected newline between expressions");
    }

    private void RequireNewLine(string message)
    {
        if (!Match(TokenKind.NewLine)) throw Error(Current, message);
        while (Match(TokenKind.NewLine)) { }
    }

    private void SkipNewLines() { while (Match(TokenKind.NewLine)) { } }
    private bool CheckIdentifier(string text) => Check(TokenKind.Identifier) && Current.Text == text;
    private Token ConsumeIdentifier(string text, string message) => CheckIdentifier(text) ? Advance() : throw Error(Current, message);
    private bool MatchIdentifier(string text) => CheckIdentifier(text) && AdvanceIsTrue();
    private bool AdvanceIsTrue() { Advance(); return true; }
    private bool Match(TokenKind kind) { if (!Check(kind)) return false; Advance(); return true; }
    private bool Check(TokenKind kind) => Current.Kind == kind;
    private bool CheckNext(TokenKind kind) => _i + 1 < _tokens.Count && _tokens[_i + 1].Kind == kind;
    private Token Consume(TokenKind kind, string message) => Check(kind) ? Advance() : throw Error(Current, message);
    private Token Advance() { if (_i < _tokens.Count - 1) _i++; return _tokens[_i - 1]; }
    private Token Current => _tokens[_i];
    private Token Previous => _tokens[_i - 1];
    private static Exception Error(Token t, string message) => new Exception($"{message} at {t.Line}:{t.Column}");
}

// ---------- Core printer ----------

static class CorePrinter
{
    public static string Print(Core core, int indent = 0) => core switch
    {
        Atom a => a.Kind switch
        {
            AtomKind.String => $"\"{a.Value}\"",
            AtomKind.Null => "null",
            AtomKind.Boolean => ((bool)a.Value!).ToString().ToLowerInvariant(),
            AtomKind.Number => ((double)a.Value!).ToString(CultureInfo.InvariantCulture),
            _ => a.Value?.ToString() ?? "null"
        },
        ListCore l => "[" + string.Join(" ", l.Items.Select(x => Print(x, indent + 1))) + "]",
        RecordCore r => "{" + string.Join(" ", r.Fields.Select(kv => $"{kv.Key}: {Print(kv.Value, indent + 1)}")) + "}",
        _ => "?"
    };
}


// ---------- Beacon runtime ----------

public sealed class BEnv
{
    private readonly Dictionary<string, object?> _values = new();
    public BEnv? Parent { get; }

    public BEnv() { }
    public BEnv(BEnv? parent) => Parent = parent;

    public void Define(string name, object? value) => _values[name] = value;

    public object? Get(string name)
    {
        if (_values.TryGetValue(name, out var value)) return value;
        if (Parent is not null) return Parent.Get(name);
        throw new Exception($"Unknown symbol '{name}'");
    }

    public object? Set(string name, object? value)
    {
        if (_values.ContainsKey(name)) { _values[name] = value; return value; }
        if (Parent is not null) return Parent.Set(name, value);
        throw new Exception($"Unknown symbol '{name}'");
    }
}

public delegate object? BCallable(BEnv closure, object? self, object?[] args);

public sealed class BFn
{
    public BCallable Code { get; }
    public BEnv Closure { get; }
    public BFn(BCallable code, BEnv closure) { Code = code; Closure = closure; }
}

public sealed class BRecord : Dictionary<string, object?> { }

// Runtime representation of a Beacon symbol when compiler Core is exposed to Beacon.
// Symbols are Atoms, but remain distinct from string literals.
public sealed record BSymbol(string Name);

public sealed class BType
{
    public string Name { get; }
    public Dictionary<string, string> Fields { get; }
    public BRecord Methods { get; }

    public BType(string name, Dictionary<string, string> fields, BRecord methods)
    {
        Name = name;
        Fields = fields;
        Methods = methods;
    }

    public BRecord Create(BEnv env, BRecord values)
    {
        var result = new BRecord();
        foreach (var field in Fields)
        {
            if (!values.TryGetValue(field.Key, out var value))
                throw new Exception($"Missing {Name}.{field.Key}");
            result[field.Key] = Runtime.CheckType(env, field.Value, value);
        }
        foreach (var method in Methods) result[method.Key] = method.Value;
        return result;
    }
}

static class FunctionRegistry
{
    private static readonly Dictionary<int, BCallable> Functions = new();
    private static int _nextId;

    public static void Clear() { Functions.Clear(); _nextId = 0; }
    public static int Register(BCallable function)
    {
        var id = ++_nextId;
        Functions[id] = function;
        return id;
    }
    public static BCallable Get(int id) => Functions.TryGetValue(id, out var fn)
        ? fn
        : throw new Exception($"Unknown compiled function {id}");
}

public static class Runtime
{
    private static readonly BEnv NativeEnv = new();

    private static readonly BFn ListLength = NativeMethod(0, (self, _) =>
        self is List<object?> list ? (double)list.Count : throw new Exception("length() requires a List receiver"));

    private static readonly BFn ListAppend = NativeMethod(1, (self, args) =>
    {
        if (self is not List<object?> list) throw new Exception("append() requires a List receiver");
        list.Add(args[0]);
        return list;
    });

    private static readonly BFn ListConcat = NativeMethod(1, (self, args) =>
    {
        if (self is not List<object?> left || args[0] is not List<object?> right)
            throw new Exception("concat() requires Lists");
        return left.Concat(right).ToList();
    });

    private static readonly BFn StringLength = NativeMethod(0, (self, _) =>
        self is string text ? (double)text.Length : throw new Exception("length() requires a String receiver"));

    private static readonly BFn StringSlice = new(
        (_, self, args) =>
        {
            if (self is not string text) throw new Exception("slice() requires a String receiver");
            if (args.Length is not (1 or 2)) throw new Exception("slice() expects start or start, length");
            var start = WholeIndex(args[0], "slice start");
            if (start < 0 || start > text.Length) throw new Exception("slice start is out of range");
            if (args.Length == 1) return text[start..];
            var length = WholeIndex(args[1], "slice length");
            if (length < 0 || start + length > text.Length) throw new Exception("slice length is out of range");
            return text.Substring(start, length);
        },
        NativeEnv);

    private static readonly BFn StringStartsWith = NativeMethod(1, (self, args) =>
    {
        if (self is not string text || args[0] is not string prefix)
            throw new Exception("startsWith() requires a String receiver and String prefix");
        return text.StartsWith(prefix, StringComparison.Ordinal);
    });

    private static readonly BFn RecordKeys = NativeMethod(0, (self, _) =>
        self is BRecord record ? record.Keys.Cast<object?>().ToList() : throw new Exception("keys() requires a Record receiver"));

    private static readonly BFn RecordHas = NativeMethod(1, (self, args) =>
    {
        if (self is not BRecord record || args[0] is not string key)
            throw new Exception("has() requires a Record receiver and String key");
        return record.ContainsKey(key);
    });

    private static BFn NativeMethod(int arity, Func<object?, object?[], object?> body) => new(
        (_, self, args) =>
        {
            if (args.Length != arity) throw new Exception($"Native method expected {arity} argument(s), got {args.Length}");
            return body(self, args);
        },
        NativeEnv);

    public static object? GetVar(BEnv env, string name) => env.Get(name);
    public static object? SetVar(BEnv env, string name, object? value) => env.Set(name, value);

    public static object? Declare(BEnv env, string name, string type, object? value)
    {
        var checkedValue = CheckType(env, type, value);
        env.Define(name, checkedValue);
        return checkedValue;
    }

    public static object? CheckType(BEnv env, string type, object? value)
    {
        if (type == "any")
            throw new Exception("Beacon has no 'any' type; declarations must be explicitly typed");

        var alternatives = type.Split('|', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        if (alternatives.Length == 0) throw new Exception("Empty type annotation");

        foreach (var alternative in alternatives)
        {
            if (BuiltinTypeMatches(alternative, value)) return value;

            if (!IsBuiltinTypeName(alternative))
            {
                object? typeValue;
                try { typeValue = env.Get(alternative); }
                catch { continue; }

                if (typeValue is BType beaconType && value is BRecord record)
                {
                    try { return beaconType.Create(env, record); }
                    catch { /* This alternative did not match; try the next union member. */ }
                }
            }
        }

        throw new Exception($"Expected {type}, got {Kind(value)}");
    }

    private static bool IsBuiltinTypeName(string type) => type is
        "number" or "string" or "boolean" or "list" or "record" or
        "symbol" or "atom" or "null" or "fn" or "type";

    private static bool BuiltinTypeMatches(string type, object? value) => type switch
    {
        "number" => value is double,
        "string" => value is string,
        "boolean" => value is bool,
        "list" => value is List<object?>,
        "record" => value is BRecord,
        "symbol" => value is BSymbol,
        "atom" => value is null or BSymbol or double or string or bool,
        "null" => value is null,
        "fn" => value is BFn,
        "type" => value is BType,
        _ => false
    };

    public static BFn MakeFunction(int id, BEnv closure) => new(FunctionRegistry.Get(id), closure);

    public static void RequireArgs(object?[] args, int count)
    {
        if (args.Length != count) throw new Exception($"Function expected {count} argument(s), got {args.Length}");
    }

    public static object? Call(object? callable, object? self, object?[] args) =>
        callable is BFn fn ? fn.Code(fn.Closure, self, args) : throw new Exception("Value is not callable");

    public static object? Print(object?[] values)
    {
        Console.WriteLine(string.Join(" ", values.Select(Display)));
        return null;
    }

    public static string Kind(object? value) => value switch
    {
        null => "null",
        BSymbol => "symbol",
        double => "number",
        string => "string",
        bool => "boolean",
        List<object?> => "list",
        BRecord => "record",
        BFn => "fn",
        BType => "type",
        _ => "unknown"
    };

    public static object? Fail(object? message) =>
        throw new Exception(Display(message));

    public static BRecord MakeRecord(string[] keys, object?[] values)
    {
        var record = new BRecord();
        for (var i = 0; i < keys.Length; i++) record[keys[i]] = values[i];
        return record;
    }

    public static List<object?> MakeList(object?[] values) => values.ToList();

    public static BType MakeType(string name, string[] fieldNames, string[] fieldTypes, string[] methodNames, object?[] methodValues)
    {
        var fields = new Dictionary<string, string>();
        for (var i = 0; i < fieldNames.Length; i++) fields[fieldNames[i]] = fieldTypes[i];

        var methods = new BRecord();
        for (var i = 0; i < methodNames.Length; i++) methods[methodNames[i]] = methodValues[i];
        return new BType(name, fields, methods);
    }

    public static object? Get(object? target, string member)
    {
        if (target is BRecord record)
        {
            if (record.TryGetValue(member, out var value)) return value;
            return member switch
            {
                "keys" => RecordKeys,
                "has" => RecordHas,
                _ => throw new Exception($"Record has no member '{member}'")
            };
        }
        if (target is List<object?>)
            return member switch
            {
                "length" => ListLength,
                "append" => ListAppend,
                "concat" => ListConcat,
                _ => throw new Exception($"List has no member '{member}'")
            };
        if (target is string)
            return member switch
            {
                "length" => StringLength,
                "slice" => StringSlice,
                "startsWith" => StringStartsWith,
                _ => throw new Exception($"String has no member '{member}'")
            };
        if (target is BSymbol symbol && member == "name") return symbol.Name;
        throw new Exception($"Cannot access .{member} on this value");
    }

    public static object? SetMember(object? target, string member, object? value)
    {
        if (target is not BRecord record) throw new Exception($"Cannot assign .{member} on non-Record");
        record[member] = value;
        return value;
    }

    public static object? Index(object? target, object? index)
    {
        if (target is List<object?> list)
        {
            var i = WholeIndex(index, "List index");
            if (i < 0 || i >= list.Count) throw new Exception($"List index {i} is out of range");
            return list[i];
        }
        if (target is string text)
        {
            var i = WholeIndex(index, "String index");
            if (i < 0 || i >= text.Length) throw new Exception($"String index {i} is out of range");
            return text[i].ToString();
        }
        if (target is BRecord record)
        {
            if (index is not string key) throw new Exception("Record @ access requires a String key");
            if (!record.TryGetValue(key, out var value)) throw new Exception($"Record has no key '{key}'");
            return value;
        }
        throw new Exception("@ requires a List, String, or Record on the left");
    }

    public static object? SetIndex(object? target, object? index, object? value)
    {
        if (target is List<object?> list)
        {
            var i = WholeIndex(index, "List index");
            if (i < 0 || i >= list.Count) throw new Exception($"List index {i} is out of range");
            list[i] = value;
            return value;
        }
        if (target is BRecord record)
        {
            if (index is not string key) throw new Exception("Record @ assignment requires a String key");
            record[key] = value;
            return value;
        }
        throw new Exception("@ assignment requires a List or Record on the left");
    }

    private static int WholeIndex(object? value, string label)
    {
        if (value is not double n || Math.Abs(n % 1) > double.Epsilon) throw new Exception($"{label} must be an integer number");
        return checked((int)n);
    }

    public static bool Bool(object? value) =>
        value is bool b ? b : throw new Exception("Condition must evaluate to boolean");

    public static bool Equal(object? a, object? b)
    {
        if (a is double x && b is double y) return x == y;
        if (a is List<object?> leftList && b is List<object?> rightList)
            return leftList.Count == rightList.Count && leftList.Zip(rightList).All(pair => Equal(pair.First, pair.Second));
        if (a is BRecord leftRecord && b is BRecord rightRecord)
        {
            var leftFields = leftRecord.Where(x => x.Value is not BFn).ToList();
            var rightFields = rightRecord.Where(x => x.Value is not BFn).ToDictionary(x => x.Key, x => x.Value);
            return leftFields.Count == rightFields.Count && leftFields.All(x => rightFields.TryGetValue(x.Key, out var value) && Equal(x.Value, value));
        }
        return Equals(a, b);
    }

    public static bool Compare(object? a, object? b, string op)
    {
        if (a is not double x || b is not double y) throw new Exception($"{op} requires numbers");
        return op switch
        {
            "<" => x < y,
            "<=" => x <= y,
            ">" => x > y,
            ">=" => x >= y,
            _ => throw new Exception($"Unknown comparison operator {op}")
        };
    }

    public static object? AddAssignVar(BEnv env, string name, object? value) => env.Set(name, Add(env.Get(name), value));

    public static object? AddAssignMember(object? target, string member, object? value)
    {
        if (target is not BRecord record) throw new Exception($"Cannot assign .{member} on non-Record");
        var result = Add(Get(record, member), value);
        record[member] = result;
        return result;
    }

    public static object? Add(object? a, object? b)
    {
        if (a is double x && b is double y) return x + y;
        if (a is string || b is string) return Display(a) + Display(b);
        throw new Exception("+ requires numbers, or a string operand");
    }

    public static object? Sub(object? a, object? b) => Numbers(a, b, (x, y) => x - y, "-");
    public static object? Mul(object? a, object? b) => Numbers(a, b, (x, y) => x * y, "*");
    public static object? Div(object? a, object? b) => Numbers(a, b, (x, y) => x / y, "/");

    private static object? Numbers(object? a, object? b, Func<double, double, double> op, string name) =>
        a is double x && b is double y ? op(x, y) : throw new Exception($"{name} requires numbers");

    public static string Interpolate(string text, BEnv env, object? self)
    {
        return Regex.Replace(text, "\\{(\\.?[A-Za-z_][A-Za-z0-9_]*)\\}", match =>
        {
            var hole = match.Groups[1].Value;
            var value = hole.StartsWith('.')
                ? Get(self ?? throw new Exception("Receiver interpolation {.member} is only valid inside behavior functions"), hole[1..])
                : env.Get(hole);
            return Display(value);
        });
    }

    public static string Display(object? value) => value switch
    {
        null => "null",
        double n when Math.Abs(n % 1) < double.Epsilon => ((long)n).ToString(CultureInfo.InvariantCulture),
        double n => n.ToString(CultureInfo.InvariantCulture),
        bool b => b ? "true" : "false",
        string s => s,
        BSymbol symbol => symbol.Name,
        BRecord r => "{" + string.Join(", ", r.Where(x => x.Value is not BFn).Select(x => $"{x.Key}: {Display(x.Value)}")) + "}",
        List<object?> l => "[" + string.Join(", ", l.Select(Display)) + "]",
        _ => value.ToString() ?? "null"
    };
}

// ---------- Core bridge: compiler Core -> Beacon runtime values ----------

static class CoreBridge
{
    public static object? ToValue(Core core) => core switch
    {
        Atom { Kind: AtomKind.Symbol } a => new BSymbol(a.Text),
        Atom { Kind: AtomKind.Number } a => (double)a.Value!,
        Atom { Kind: AtomKind.String } a => (string)a.Value!,
        Atom { Kind: AtomKind.Boolean } a => (bool)a.Value!,
        Atom { Kind: AtomKind.Null } => null,
        ListCore list => list.Items.Select(ToValue).ToList(),
        RecordCore record => ToRecord(record),
        _ => throw new Exception("Unknown Core value")
    };

    private static BRecord ToRecord(RecordCore record)
    {
        var result = new BRecord();
        foreach (var field in record.Fields) result[field.Key] = ToValue(field.Value);
        return result;
    }
}

// ---------- Stage-1 symbolic plan assembler ----------
//
// compiler/compiler.beacon decides how Core is lowered. This class deliberately
// knows nothing about Beacon Core forms; it only translates Beacon-produced
// instruction Records into CLR IL.

sealed class PlanAssembler
{
    private static readonly MethodInfo GetVarMethod = Method(nameof(Runtime.GetVar), typeof(BEnv), typeof(string));
    private static readonly MethodInfo DeclareMethod = Method(nameof(Runtime.Declare), typeof(BEnv), typeof(string), typeof(string), typeof(object));
    private static readonly MethodInfo AddMethod = Method(nameof(Runtime.Add), typeof(object), typeof(object));
    private static readonly MethodInfo SubMethod = Method(nameof(Runtime.Sub), typeof(object), typeof(object));
    private static readonly MethodInfo MulMethod = Method(nameof(Runtime.Mul), typeof(object), typeof(object));
    private static readonly MethodInfo DivMethod = Method(nameof(Runtime.Div), typeof(object), typeof(object));
    private static readonly MethodInfo EqualMethod = Method(nameof(Runtime.Equal), typeof(object), typeof(object));
    private static readonly MethodInfo CompareMethod = Method(nameof(Runtime.Compare), typeof(object), typeof(object), typeof(string));
    private static readonly MethodInfo GetMethod = Method(nameof(Runtime.Get), typeof(object), typeof(string));
    private static readonly MethodInfo IndexMethod = Method(nameof(Runtime.Index), typeof(object), typeof(object));
    private static readonly MethodInfo PrintMethod = Method(nameof(Runtime.Print), typeof(object[]));
    private static readonly MethodInfo MakeRecordMethod = Method(nameof(Runtime.MakeRecord), typeof(string[]), typeof(object[]));
    private static readonly MethodInfo MakeListMethod = Method(nameof(Runtime.MakeList), typeof(object[]));

    public CompiledProgram Compile(object? value)
    {
        if (value is not List<object?> plan)
            throw new Exception("Stage-1 compiler must return a List instruction plan");

        var method = new DynamicMethod(
            "Beacon_Stage1_Main",
            typeof(BEnv),
            Type.EmptyTypes,
            typeof(PlanAssembler).Module,
            true);

        var il = method.GetILGenerator();
        var env = il.DeclareLocal(typeof(BEnv));
        il.Emit(OpCodes.Newobj, typeof(BEnv).GetConstructor(Type.EmptyTypes)!);
        il.Emit(OpCodes.Stloc, env);

        EmitPlan(plan, il, env);

        il.Emit(OpCodes.Ldloc, env);
        il.Emit(OpCodes.Ret);

        return new CompiledProgram((Func<BEnv>)method.CreateDelegate(typeof(Func<BEnv>)));
    }

    private static void EmitPlan(List<object?> plan, ILGenerator il, LocalBuilder env)
    {
        foreach (var value in plan)
        {
            if (value is not BRecord instruction)
                throw new Exception("Stage-1 instruction plan entries must be Records");
            EmitInstruction(instruction, il, env);
        }
    }

    private static void EmitInstruction(BRecord instruction, ILGenerator il, LocalBuilder env)
    {
        var op = StringField(instruction, "op");
        switch (op)
        {
            case "ldenv":
                il.Emit(OpCodes.Ldloc, env);
                return;
            case "ldstr":
                il.Emit(OpCodes.Ldstr, StringField(instruction, "arg"));
                return;
            case "ldc.r8":
                il.Emit(OpCodes.Ldc_R8, NumberField(instruction, "arg"));
                return;
            case "ldbool":
                il.Emit(BoolField(instruction, "arg") ? OpCodes.Ldc_I4_1 : OpCodes.Ldc_I4_0);
                return;
            case "ldnull":
                il.Emit(OpCodes.Ldnull);
                return;
            case "not.bool":
                il.Emit(OpCodes.Ldc_I4_0);
                il.Emit(OpCodes.Ceq);
                return;
            case "box":
                var boxType = StringField(instruction, "arg") switch
                {
                    "number" => typeof(double),
                    "boolean" => typeof(bool),
                    var type => throw new Exception($"Stage-1 cannot box '{type}'")
                };
                il.Emit(OpCodes.Box, boxType);
                return;
            case "call":
                il.Emit(OpCodes.Call, ResolveRuntimeCall(StringField(instruction, "arg")));
                return;
            case "pop":
                il.Emit(OpCodes.Pop);
                return;
            case "print":
                EmitPrint(instruction, il, env);
                return;
            case "record":
                EmitRecord(instruction, il, env);
                return;
            case "list":
                EmitList(instruction, il, env);
                return;
            default:
                throw new Exception($"Unknown Stage-1 plan operation '{op}'");
        }
    }

    private static void EmitPrint(BRecord instruction, ILGenerator il, LocalBuilder env)
    {
        var args = ListField(instruction, "args");
        EmitPlanArray(args, il, env);
        il.Emit(OpCodes.Call, PrintMethod);
    }

    private static void EmitRecord(BRecord instruction, ILGenerator il, LocalBuilder env)
    {
        var fields = ListField(instruction, "fields");

        il.Emit(OpCodes.Ldc_I4, fields.Count);
        il.Emit(OpCodes.Newarr, typeof(string));
        for (var i = 0; i < fields.Count; i++)
        {
            var field = fields[i] as BRecord ?? throw new Exception("Record plan field must be a Record");
            il.Emit(OpCodes.Dup);
            il.Emit(OpCodes.Ldc_I4, i);
            il.Emit(OpCodes.Ldstr, StringField(field, "name"));
            il.Emit(OpCodes.Stelem_Ref);
        }

        il.Emit(OpCodes.Ldc_I4, fields.Count);
        il.Emit(OpCodes.Newarr, typeof(object));
        for (var i = 0; i < fields.Count; i++)
        {
            var field = (BRecord)fields[i]!;
            il.Emit(OpCodes.Dup);
            il.Emit(OpCodes.Ldc_I4, i);
            EmitPlan(ListField(field, "value"), il, env);
            il.Emit(OpCodes.Stelem_Ref);
        }

        il.Emit(OpCodes.Call, MakeRecordMethod);
    }

    private static void EmitList(BRecord instruction, ILGenerator il, LocalBuilder env)
    {
        var items = ListField(instruction, "items");
        EmitPlanArray(items, il, env);
        il.Emit(OpCodes.Call, MakeListMethod);
    }

    private static void EmitPlanArray(List<object?> plans, ILGenerator il, LocalBuilder env)
    {
        il.Emit(OpCodes.Ldc_I4, plans.Count);
        il.Emit(OpCodes.Newarr, typeof(object));
        for (var i = 0; i < plans.Count; i++)
        {
            if (plans[i] is not List<object?> argPlan)
                throw new Exception("Stage-1 argument must contain an instruction List");
            il.Emit(OpCodes.Dup);
            il.Emit(OpCodes.Ldc_I4, i);
            EmitPlan(argPlan, il, env);
            il.Emit(OpCodes.Stelem_Ref);
        }
    }

    private static MethodInfo ResolveRuntimeCall(string name) => name switch
    {
        "Runtime.GetVar" => GetVarMethod,
        "Runtime.Declare" => DeclareMethod,
        "Runtime.Add" => AddMethod,
        "Runtime.Sub" => SubMethod,
        "Runtime.Mul" => MulMethod,
        "Runtime.Div" => DivMethod,
        "Runtime.Equal" => EqualMethod,
        "Runtime.Compare" => CompareMethod,
        "Runtime.Get" => GetMethod,
        "Runtime.Index" => IndexMethod,
        _ => throw new Exception($"Stage-1 plan references unsupported runtime call '{name}'")
    };

    private static string StringField(BRecord record, string key) =>
        record.TryGetValue(key, out var value) && value is string text
            ? text
            : throw new Exception($"Stage-1 instruction field '{key}' must be string");

    private static double NumberField(BRecord record, string key) =>
        record.TryGetValue(key, out var value) && value is double number
            ? number
            : throw new Exception($"Stage-1 instruction field '{key}' must be number");

    private static bool BoolField(BRecord record, string key) =>
        record.TryGetValue(key, out var value) && value is bool boolean
            ? boolean
            : throw new Exception($"Stage-1 instruction field '{key}' must be boolean");

    private static List<object?> ListField(BRecord record, string key) =>
        record.TryGetValue(key, out var value) && value is List<object?> list
            ? list
            : throw new Exception($"Stage-1 instruction field '{key}' must be List");

    private static MethodInfo Method(string name, params Type[] args) =>
        typeof(Runtime).GetMethod(name, BindingFlags.Public | BindingFlags.Static, null, args, null)
        ?? throw new Exception($"Runtime method {name} not found");
}

// ---------- Direct CLR IL compiler ----------

sealed record CompiledProgram(Func<BEnv> Execute)
{
    public void Run() => _ = Execute();
}

sealed class IlCompiler
{
    private static readonly System.Reflection.MethodInfo GetVarMethod = Method(nameof(Runtime.GetVar), typeof(BEnv), typeof(string));
    private static readonly System.Reflection.MethodInfo SetVarMethod = Method(nameof(Runtime.SetVar), typeof(BEnv), typeof(string), typeof(object));
    private static readonly System.Reflection.MethodInfo DeclareMethod = Method(nameof(Runtime.Declare), typeof(BEnv), typeof(string), typeof(string), typeof(object));
    private static readonly System.Reflection.MethodInfo MakeFunctionMethod = Method(nameof(Runtime.MakeFunction), typeof(int), typeof(BEnv));
    private static readonly System.Reflection.MethodInfo RequireArgsMethod = Method(nameof(Runtime.RequireArgs), typeof(object[]), typeof(int));
    private static readonly System.Reflection.MethodInfo CallMethod = Method(nameof(Runtime.Call), typeof(object), typeof(object), typeof(object[]));
    private static readonly System.Reflection.MethodInfo PrintMethod = Method(nameof(Runtime.Print), typeof(object[]));
    private static readonly System.Reflection.MethodInfo MakeRecordMethod = Method(nameof(Runtime.MakeRecord), typeof(string[]), typeof(object[]));
    private static readonly System.Reflection.MethodInfo MakeListMethod = Method(nameof(Runtime.MakeList), typeof(object[]));
    private static readonly System.Reflection.MethodInfo MakeTypeMethod = Method(nameof(Runtime.MakeType), typeof(string), typeof(string[]), typeof(string[]), typeof(string[]), typeof(object[]));
    private static readonly System.Reflection.MethodInfo GetMethod = Method(nameof(Runtime.Get), typeof(object), typeof(string));
    private static readonly System.Reflection.MethodInfo SetMemberMethod = Method(nameof(Runtime.SetMember), typeof(object), typeof(string), typeof(object));
    private static readonly System.Reflection.MethodInfo IndexMethod = Method(nameof(Runtime.Index), typeof(object), typeof(object));
    private static readonly System.Reflection.MethodInfo SetIndexMethod = Method(nameof(Runtime.SetIndex), typeof(object), typeof(object), typeof(object));
    private static readonly System.Reflection.MethodInfo KindMethod = Method(nameof(Runtime.Kind), typeof(object));
    private static readonly System.Reflection.MethodInfo FailMethod = Method(nameof(Runtime.Fail), typeof(object));
    private static readonly System.Reflection.MethodInfo BoolMethod = Method(nameof(Runtime.Bool), typeof(object));
    private static readonly System.Reflection.MethodInfo EqualMethod = Method(nameof(Runtime.Equal), typeof(object), typeof(object));
    private static readonly System.Reflection.MethodInfo CompareMethod = Method(nameof(Runtime.Compare), typeof(object), typeof(object), typeof(string));
    private static readonly System.Reflection.MethodInfo AddAssignVarMethod = Method(nameof(Runtime.AddAssignVar), typeof(BEnv), typeof(string), typeof(object));
    private static readonly System.Reflection.MethodInfo AddAssignMemberMethod = Method(nameof(Runtime.AddAssignMember), typeof(object), typeof(string), typeof(object));
    private static readonly System.Reflection.MethodInfo AddMethod = Method(nameof(Runtime.Add), typeof(object), typeof(object));
    private static readonly System.Reflection.MethodInfo SubMethod = Method(nameof(Runtime.Sub), typeof(object), typeof(object));
    private static readonly System.Reflection.MethodInfo MulMethod = Method(nameof(Runtime.Mul), typeof(object), typeof(object));
    private static readonly System.Reflection.MethodInfo DivMethod = Method(nameof(Runtime.Div), typeof(object), typeof(object));
    private static readonly System.Reflection.MethodInfo InterpolateMethod = Method(nameof(Runtime.Interpolate), typeof(string), typeof(BEnv), typeof(object));

    public CompiledProgram Compile(Core program)
    {
        FunctionRegistry.Clear();
        if (program is not ListCore body || !IsForm(body, "do", out _))
            throw new Exception("Program must lower to a do List");

        var method = new System.Reflection.Emit.DynamicMethod(
            "Beacon_Main",
            typeof(BEnv),
            Type.EmptyTypes,
            typeof(IlCompiler).Module,
            true);

        var il = method.GetILGenerator();
        var env = il.DeclareLocal(typeof(BEnv));
        il.Emit(System.Reflection.Emit.OpCodes.Newobj, typeof(BEnv).GetConstructor(Type.EmptyTypes)!);
        il.Emit(System.Reflection.Emit.OpCodes.Stloc, env);

        var ctx = new EmitContext(il, env, HasSelf: false);
        foreach (var expression in body.Items.Skip(1)) EmitStatement(expression, ctx);
        il.Emit(System.Reflection.Emit.OpCodes.Ldloc, env);
        il.Emit(System.Reflection.Emit.OpCodes.Ret);

        return new CompiledProgram((Func<BEnv>)method.CreateDelegate(typeof(Func<BEnv>)));
    }

    private void EmitStatement(Core core, EmitContext ctx)
    {
        if (IsForm(core, "if", out var ifItems)) { EmitIf(ifItems, ctx); return; }
        if (IsForm(core, "for", out var forItems)) { EmitFor(forItems, ctx); return; }
        if (IsForm(core, "def", out var defItems))
        {
            EmitDefinition(defItems, ctx);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Pop);
            return;
        }

        EmitExpr(core, ctx);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Pop);
    }

    private void EmitExpr(Core core, EmitContext ctx)
    {
        switch (core)
        {
            case Atom atom:
                EmitAtom(atom, ctx);
                return;
            case RecordCore record:
                EmitRecord(record, ctx);
                return;
            case ListCore list:
                EmitList(list, ctx);
                return;
            default:
                throw new Exception("Unknown core node");
        }
    }

    private void EmitAtom(Atom atom, EmitContext ctx)
    {
        var il = ctx.IL;
        switch (atom.Kind)
        {
            case AtomKind.Symbol:
                il.Emit(System.Reflection.Emit.OpCodes.Ldloc, ctx.Env);
                il.Emit(System.Reflection.Emit.OpCodes.Ldstr, atom.Text);
                il.Emit(System.Reflection.Emit.OpCodes.Call, GetVarMethod);
                break;
            case AtomKind.Number:
                il.Emit(System.Reflection.Emit.OpCodes.Ldc_R8, (double)atom.Value!);
                il.Emit(System.Reflection.Emit.OpCodes.Box, typeof(double));
                break;
            case AtomKind.String:
                il.Emit(System.Reflection.Emit.OpCodes.Ldstr, (string)atom.Value!);
                il.Emit(System.Reflection.Emit.OpCodes.Ldloc, ctx.Env);
                EmitSelf(ctx);
                il.Emit(System.Reflection.Emit.OpCodes.Call, InterpolateMethod);
                break;
            case AtomKind.Boolean:
                il.Emit((bool)atom.Value! ? System.Reflection.Emit.OpCodes.Ldc_I4_1 : System.Reflection.Emit.OpCodes.Ldc_I4_0);
                il.Emit(System.Reflection.Emit.OpCodes.Box, typeof(bool));
                break;
            case AtomKind.Null:
                il.Emit(System.Reflection.Emit.OpCodes.Ldnull);
                break;
        }
    }

    private void EmitList(ListCore list, EmitContext ctx)
    {
        if (list.Items.Count == 0) { EmitObjectArray(Array.Empty<Core>(), ctx); ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, MakeListMethod); return; }
        var form = list.Items[0] is Atom { Kind: AtomKind.Symbol } head ? head.Text : null;

        switch (form)
        {
            case "call": EmitCall(list, ctx); return;
            case "get": EmitGet(list, ctx); return;
            case "index": EmitExpr(list.Items[1], ctx); EmitExpr(list.Items[2], ctx); ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, IndexMethod); return;
            case "and": EmitLogicalAnd(list, ctx); return;
            case "or": EmitLogicalOr(list, ctx); return;
            case "not": EmitLogicalNot(list, ctx); return;
            case "+=": EmitPlusAssign(list, ctx); return;
            case "=": EmitAssign(list, ctx); return;
            case "==": EmitExpr(list.Items[1], ctx); EmitExpr(list.Items[2], ctx); ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, EqualMethod); BoxBool(ctx.IL); return;
            case "!=":
                EmitExpr(list.Items[1], ctx); EmitExpr(list.Items[2], ctx); ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, EqualMethod);
                ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldc_I4_0); ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ceq); BoxBool(ctx.IL); return;
            case "<": case "<=": case ">": case ">=":
                EmitExpr(list.Items[1], ctx); EmitExpr(list.Items[2], ctx); ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldstr, form);
                ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, CompareMethod); BoxBool(ctx.IL); return;
            case "+": EmitBinary(list, ctx, AddMethod); return;
            case "-": EmitBinary(list, ctx, SubMethod); return;
            case "*": EmitBinary(list, ctx, MulMethod); return;
            case "/": EmitBinary(list, ctx, DivMethod); return;
            case "list": EmitObjectArray(list.Items.Skip(1).ToArray(), ctx); ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, MakeListMethod); return;
            case "fn": EmitFunctionValue(list, ctx); return;
            case "do": throw new Exception("A do-form is only valid as a body");
            default: throw new Exception($"Unknown core form: {form}");
        }
    }

    private void EmitDefinition(List<Core> items, EmitContext ctx)
    {
        var name = Symbol(items[1]);
        var type = Symbol(items[2]);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldloc, ctx.Env);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldstr, name);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldstr, type);
        if (type == "type") EmitType(name, items[3], ctx);
        else EmitExpr(items[3], ctx);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, DeclareMethod);
    }

    private void EmitAssign(ListCore list, EmitContext ctx)
    {
        var target = list.Items[1];
        var value = list.Items[2];
        if (target is Atom { Kind: AtomKind.Symbol } symbol)
        {
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldloc, ctx.Env);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldstr, symbol.Text);
            EmitExpr(value, ctx);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, SetVarMethod);
            return;
        }
        if (IsForm(target, "get", out var get))
        {
            EmitMemberTarget(get[1], ctx);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldstr, StringValue(get[2]));
            EmitExpr(value, ctx);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, SetMemberMethod);
            return;
        }
        if (IsForm(target, "index", out var index))
        {
            EmitExpr(index[1], ctx);
            EmitExpr(index[2], ctx);
            EmitExpr(value, ctx);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, SetIndexMethod);
            return;
        }
        throw new Exception("Left side of = must be a variable, member, or indexed value");
    }

    private void EmitPlusAssign(ListCore list, EmitContext ctx)
    {
        var target = list.Items[1];
        var value = list.Items[2];
        if (target is Atom { Kind: AtomKind.Symbol } symbol)
        {
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldloc, ctx.Env);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldstr, symbol.Text);
            EmitExpr(value, ctx);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, AddAssignVarMethod);
            return;
        }
        if (IsForm(target, "get", out var get))
        {
            EmitMemberTarget(get[1], ctx);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldstr, StringValue(get[2]));
            EmitExpr(value, ctx);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, AddAssignMemberMethod);
            return;
        }
        throw new Exception("Left side of += must be a variable or member");
    }

    private void EmitGet(ListCore list, EmitContext ctx)
    {
        EmitMemberTarget(list.Items[1], ctx);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldstr, StringValue(list.Items[2]));
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, GetMethod);
    }

    private void EmitMemberTarget(Core target, EmitContext ctx)
    {
        if (target is Atom { Kind: AtomKind.Symbol } self && self.Text == "self")
        {
            if (!ctx.HasSelf) throw new Exception("'.member' is only valid inside behavior functions");
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldarg_1);
            return;
        }
        EmitExpr(target, ctx);
    }

    private void EmitCall(ListCore list, EmitContext ctx)
    {
        var callee = list.Items[1];
        var args = list.Items.Skip(2).ToArray();

        if (callee is Atom { Kind: AtomKind.Symbol } atom && atom.Text == "print")
        {
            EmitObjectArray(args, ctx);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, PrintMethod);
            return;
        }

        if (callee is Atom { Kind: AtomKind.Symbol } kindAtom && kindAtom.Text == "kind")
        {
            if (args.Length != 1) throw new Exception("kind() expects one argument");
            EmitExpr(args[0], ctx);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, KindMethod);
            return;
        }

        if (callee is Atom { Kind: AtomKind.Symbol } failAtom && failAtom.Text == "fail")
        {
            if (args.Length != 1) throw new Exception("fail() expects one argument");
            EmitExpr(args[0], ctx);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, FailMethod);
            return;
        }

        if (IsForm(callee, "get", out var get))
        {
            var receiver = ctx.IL.DeclareLocal(typeof(object));
            EmitMemberTarget(get[1], ctx);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Stloc, receiver);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldloc, receiver);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldstr, StringValue(get[2]));
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, GetMethod);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldloc, receiver);
            EmitObjectArray(args, ctx);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, CallMethod);
            return;
        }

        EmitExpr(callee, ctx);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldnull);
        EmitObjectArray(args, ctx);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, CallMethod);
    }

    private void EmitLogicalAnd(ListCore list, EmitContext ctx)
    {
        var falseLabel = ctx.IL.DefineLabel();
        var endLabel = ctx.IL.DefineLabel();
        EmitExpr(list.Items[1], ctx);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, BoolMethod);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Brfalse, falseLabel);
        EmitExpr(list.Items[2], ctx);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, BoolMethod);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Br, endLabel);
        ctx.IL.MarkLabel(falseLabel);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldc_I4_0);
        ctx.IL.MarkLabel(endLabel);
        BoxBool(ctx.IL);
    }

    private void EmitLogicalOr(ListCore list, EmitContext ctx)
    {
        var trueLabel = ctx.IL.DefineLabel();
        var endLabel = ctx.IL.DefineLabel();
        EmitExpr(list.Items[1], ctx);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, BoolMethod);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Brtrue, trueLabel);
        EmitExpr(list.Items[2], ctx);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, BoolMethod);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Br, endLabel);
        ctx.IL.MarkLabel(trueLabel);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldc_I4_1);
        ctx.IL.MarkLabel(endLabel);
        BoxBool(ctx.IL);
    }

    private void EmitLogicalNot(ListCore list, EmitContext ctx)
    {
        EmitExpr(list.Items[1], ctx);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, BoolMethod);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldc_I4_0);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ceq);
        BoxBool(ctx.IL);
    }

    private void EmitBinary(ListCore list, EmitContext ctx, System.Reflection.MethodInfo method)
    {
        EmitExpr(list.Items[1], ctx);
        EmitExpr(list.Items[2], ctx);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, method);
    }

    private void EmitIf(List<Core> items, EmitContext ctx)
    {
        var elseLabel = ctx.IL.DefineLabel();
        var endLabel = ctx.IL.DefineLabel();

        EmitExpr(items[1], ctx);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, BoolMethod);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Brfalse, elseLabel);
        EmitDoStatements((ListCore)items[2], ctx);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Br, endLabel);
        ctx.IL.MarkLabel(elseLabel);
        EmitDoStatements((ListCore)items[3], ctx);
        ctx.IL.MarkLabel(endLabel);
    }

    private void EmitFor(List<Core> items, EmitContext ctx)
    {
        var initializer = items[1];
        if (IsForm(initializer, "def", out var def))
        {
            EmitDefinition(def, ctx);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Pop);
        }
        else
        {
            EmitExpr(initializer, ctx);
            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Pop);
        }

        var conditionLabel = ctx.IL.DefineLabel();
        var endLabel = ctx.IL.DefineLabel();
        ctx.IL.MarkLabel(conditionLabel);
        EmitExpr(items[2], ctx);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, BoolMethod);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Brfalse, endLabel);
        EmitDoStatements((ListCore)items[4], ctx);
        EmitExpr(items[3], ctx);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Pop);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Br, conditionLabel);
        ctx.IL.MarkLabel(endLabel);
    }

    private void EmitDoStatements(ListCore body, EmitContext ctx)
    {
        foreach (var expression in body.Items.Skip(1)) EmitStatement(expression, ctx);
    }

    private void EmitFunctionValue(ListCore fn, EmitContext parentCtx)
    {
        var id = CompileFunction(fn);
        parentCtx.IL.Emit(System.Reflection.Emit.OpCodes.Ldc_I4, id);
        parentCtx.IL.Emit(System.Reflection.Emit.OpCodes.Ldloc, parentCtx.Env);
        parentCtx.IL.Emit(System.Reflection.Emit.OpCodes.Call, MakeFunctionMethod);
    }

    private int CompileFunction(ListCore fn)
    {
        var parameters = fn.Items[1] as ListCore ?? throw new Exception("fn parameters must be List");
        var body = fn.Items[2];

        var method = new System.Reflection.Emit.DynamicMethod(
            $"Beacon_Fn_{Guid.NewGuid():N}",
            typeof(object),
            new[] { typeof(BEnv), typeof(object), typeof(object[]) },
            typeof(IlCompiler).Module,
            true);

        var il = method.GetILGenerator();
        il.Emit(System.Reflection.Emit.OpCodes.Ldarg_2);
        il.Emit(System.Reflection.Emit.OpCodes.Ldc_I4, parameters.Items.Count);
        il.Emit(System.Reflection.Emit.OpCodes.Call, RequireArgsMethod);

        var env = il.DeclareLocal(typeof(BEnv));
        il.Emit(System.Reflection.Emit.OpCodes.Ldarg_0);
        il.Emit(System.Reflection.Emit.OpCodes.Newobj, typeof(BEnv).GetConstructor(new[] { typeof(BEnv) })!);
        il.Emit(System.Reflection.Emit.OpCodes.Stloc, env);

        var ctx = new EmitContext(il, env, HasSelf: true);
        for (var i = 0; i < parameters.Items.Count; i++)
        {
            var p = (RecordCore)parameters.Items[i];
            var pName = Symbol(Field(p, "name"));
            var pType = Symbol(Field(p, "type"));
            il.Emit(System.Reflection.Emit.OpCodes.Ldloc, env);
            il.Emit(System.Reflection.Emit.OpCodes.Ldstr, pName);
            il.Emit(System.Reflection.Emit.OpCodes.Ldstr, pType);
            il.Emit(System.Reflection.Emit.OpCodes.Ldarg_2);
            il.Emit(System.Reflection.Emit.OpCodes.Ldc_I4, i);
            il.Emit(System.Reflection.Emit.OpCodes.Ldelem_Ref);
            il.Emit(System.Reflection.Emit.OpCodes.Call, DeclareMethod);
            il.Emit(System.Reflection.Emit.OpCodes.Pop);
        }

        EmitFunctionBody(body, ctx);
        il.Emit(System.Reflection.Emit.OpCodes.Ret);

        var callable = (BCallable)method.CreateDelegate(typeof(BCallable));
        return FunctionRegistry.Register(callable);
    }

    private void EmitFunctionBody(Core body, EmitContext ctx)
    {
        if (IsForm(body, "do", out var items))
        {
            if (items.Count == 1) { ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldnull); return; }
            for (var i = 1; i < items.Count - 1; i++) EmitStatement(items[i], ctx);

            var last = items[^1];
            if (IsStatementForm(last))
            {
                EmitStatement(last, ctx);
                ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldnull);
            }
            else EmitExpr(last, ctx);
            return;
        }
        EmitExpr(body, ctx);
    }

    private void EmitRecord(RecordCore record, EmitContext ctx)
    {
        EmitStringArray(record.Fields.Select(x => x.Key).ToArray(), ctx.IL);
        EmitObjectArray(record.Fields.Select(x => x.Value).ToArray(), ctx);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, MakeRecordMethod);
    }

    private void EmitType(string name, Core typeCore, EmitContext ctx)
    {
        if (!IsForm(typeCore, "type", out var items) || items[1] is not RecordCore members)
            throw new Exception("Malformed type form");

        var fields = members.Fields.Where(kv => kv.Value is Atom { Kind: AtomKind.Symbol }).ToList();
        var methods = members.Fields.Where(kv => IsForm(kv.Value, "fn", out _)).ToList();
        if (fields.Count + methods.Count != members.Fields.Count) throw new Exception("Unsupported type member");

        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldstr, name);
        EmitStringArray(fields.Select(x => x.Key).ToArray(), ctx.IL);
        EmitStringArray(fields.Select(x => Symbol(x.Value)).ToArray(), ctx.IL);
        EmitStringArray(methods.Select(x => x.Key).ToArray(), ctx.IL);
        EmitObjectArray(methods.Select(x => x.Value).ToArray(), ctx);
        ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, MakeTypeMethod);
    }

    private void EmitObjectArray(IReadOnlyList<Core> values, EmitContext ctx)
    {
        var il = ctx.IL;
        il.Emit(System.Reflection.Emit.OpCodes.Ldc_I4, values.Count);
        il.Emit(System.Reflection.Emit.OpCodes.Newarr, typeof(object));
        for (var i = 0; i < values.Count; i++)
        {
            il.Emit(System.Reflection.Emit.OpCodes.Dup);
            il.Emit(System.Reflection.Emit.OpCodes.Ldc_I4, i);
            EmitExpr(values[i], ctx);
            il.Emit(System.Reflection.Emit.OpCodes.Stelem_Ref);
        }
    }

    private static void EmitStringArray(IReadOnlyList<string> values, System.Reflection.Emit.ILGenerator il)
    {
        il.Emit(System.Reflection.Emit.OpCodes.Ldc_I4, values.Count);
        il.Emit(System.Reflection.Emit.OpCodes.Newarr, typeof(string));
        for (var i = 0; i < values.Count; i++)
        {
            il.Emit(System.Reflection.Emit.OpCodes.Dup);
            il.Emit(System.Reflection.Emit.OpCodes.Ldc_I4, i);
            il.Emit(System.Reflection.Emit.OpCodes.Ldstr, values[i]);
            il.Emit(System.Reflection.Emit.OpCodes.Stelem_Ref);
        }
    }

    private static void EmitSelf(EmitContext ctx)
    {
        if (ctx.HasSelf) ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldarg_1);
        else ctx.IL.Emit(System.Reflection.Emit.OpCodes.Ldnull);
    }

    private static void BoxBool(System.Reflection.Emit.ILGenerator il) => il.Emit(System.Reflection.Emit.OpCodes.Box, typeof(bool));

    private static bool IsStatementForm(Core core) =>
        IsForm(core, "if", out _) || IsForm(core, "for", out _) || IsForm(core, "def", out _);

    private static bool IsForm(Core core, string form, out List<Core> items)
    {
        if (core is ListCore l && l.Items.Count > 0 && l.Items[0] is Atom { Kind: AtomKind.Symbol } a && a.Text == form)
        {
            items = l.Items;
            return true;
        }
        items = new();
        return false;
    }

    private static Core Field(RecordCore record, string key) => record.Fields.First(x => x.Key == key).Value;
    private static string Symbol(Core core) => core is Atom { Kind: AtomKind.Symbol } a ? a.Text : throw new Exception("Expected symbol");
    private static string StringValue(Core core) => core is Atom { Kind: AtomKind.String } a ? (string)a.Value! : throw new Exception("Expected string atom");

    private static System.Reflection.MethodInfo Method(string name, params Type[] args) =>
        typeof(Runtime).GetMethod(name, System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static, null, args, null)
        ?? throw new Exception($"Runtime method {name} not found");

    private sealed record EmitContext(System.Reflection.Emit.ILGenerator IL, System.Reflection.Emit.LocalBuilder Env, bool HasSelf);
}

// ---------- Driver ----------

static class Program
{
    public static int Main(string[] args)
    {
        try
        {
            if (args.Length == 0)
            {
                Console.Error.WriteLine("Usage: beacon <file.beacon> [--core | --run | --stage1 <target.beacon> | --stage1-run <target.beacon>]");
                return 2;
            }

            var sourcePath = Path.GetFullPath(args[0]);
            var source = File.ReadAllText(sourcePath);
            var core = new Parser(new Lexer(source).Lex()).ParseProgram();

            if (args.Contains("--core"))
            {
                Console.WriteLine(CorePrinter.Print(core));
                return 0;
            }

            var compiled = new IlCompiler().Compile(core);

            var stage1Index = Array.IndexOf(args, "--stage1");
            var stage1RunIndex = Array.IndexOf(args, "--stage1-run");
            if (stage1Index >= 0 || stage1RunIndex >= 0)
            {
                var optionIndex = stage1RunIndex >= 0 ? stage1RunIndex : stage1Index;
                if (optionIndex + 1 >= args.Length) throw new Exception("Stage-1 mode requires a target .beacon file");

                // Stage 0 only compiles compiler.beacon itself. The target's lowering decisions
                // are made by compile() in Beacon and returned as a symbolic IL plan.
                var compilerEnv = compiled.Execute();
                var compilerFn = compilerEnv.Get("compile");
                var targetSource = File.ReadAllText(Path.GetFullPath(args[optionIndex + 1]));
                var targetCore = new Parser(new Lexer(targetSource).Lex()).ParseProgram();
                var plan = Runtime.Call(compilerFn, null, new[] { CoreBridge.ToValue(targetCore) });

                if (stage1RunIndex >= 0)
                {
                    new PlanAssembler().Compile(plan).Run();
                    return 0;
                }

                Console.WriteLine(Runtime.Display(plan));
                return 0;
            }

            if (args.Contains("--run"))
            {
                compiled.Run();
                return 0;
            }

            Console.WriteLine("Beacon compiled successfully to CLR IL. Use --run to execute it.");
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("Beacon: " + ex.Message);
            return 1;
        }
    }
}
