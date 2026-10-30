from pathlib import Path

SEED = Path('tools/seed-refresh/Beacon.Compiler/Program.cs')
EMITTER = Path('compiler/emitter.beacon')


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Expected exactly one {label} match, found {count}')
    return text.replace(old, new, 1)


def apply_math(text: str) -> str:
    marker = '''    private static readonly BFn StringLength = NativeMethod(0, (self, _) =>\n'''
    methods = '''    private static readonly BFn NumberFloor = NativeMethod(0, (self, _) =>\n        self is double value ? Math.Floor(value) : throw new Exception("floor() requires a Number receiver"));\n\n    private static readonly BFn NumberCeil = NativeMethod(0, (self, _) =>\n        self is double value ? Math.Ceiling(value) : throw new Exception("ceil() requires a Number receiver"));\n\n    private static readonly BFn NumberSqrt = NativeMethod(0, (self, _) =>\n        self is double value ? Math.Sqrt(value) : throw new Exception("sqrt() requires a Number receiver"));\n\n    private static readonly BFn NumberPow = NativeMethod(1, (self, args) =>\n    {\n        if (self is not double value || args[0] is not double exponent)\n            throw new Exception("pow() requires a Number receiver and Number exponent");\n        return Math.Pow(value, exponent);\n    });\n\n'''
    text = replace_once(text, marker, methods + marker, 'Number method insertion')

    string_dispatch = '''        if (target is string)\n            return member switch\n'''
    number_dispatch = '''        if (target is double)\n            return member switch\n            {\n                "floor" => NumberFloor,\n                "ceil" => NumberCeil,\n                "sqrt" => NumberSqrt,\n                "pow" => NumberPow,\n                _ => throw new Exception($"Number has no member '{member}'")\n            };\n'''
    return replace_once(text, string_dispatch, number_dispatch + string_dispatch, 'Number dispatch insertion')


def apply_fs_path_runtime(text: str) -> str:
    file_marker = '''    public static bool FileExists(object? path) =>\n        File.Exists(PathArgument(path, "fileExists"));\n\n    public static string AbsolutePath(object? path) =>\n'''
    file_methods = '''    public static bool FileExists(object? path) =>\n        File.Exists(PathArgument(path, "fileExists"));\n\n    public static string WriteFile(object? path, object? value)\n    {\n        var filePath = PathArgument(path, "writeFile");\n        var text = value is string content ? content : throw new Exception("writeFile() expects string content");\n        File.WriteAllText(filePath, text);\n        return filePath;\n    }\n\n    public static string AppendFile(object? path, object? value)\n    {\n        var filePath = PathArgument(path, "appendFile");\n        var text = value is string content ? content : throw new Exception("appendFile() expects string content");\n        File.AppendAllText(filePath, text);\n        return filePath;\n    }\n\n    public static bool DirectoryExists(object? path) =>\n        Directory.Exists(PathArgument(path, "directoryExists"));\n\n    public static bool DeletePath(object? path)\n    {\n        var value = PathArgument(path, "deletePath");\n        if (File.Exists(value))\n        {\n            File.Delete(value);\n            return true;\n        }\n        if (Directory.Exists(value))\n        {\n            Directory.Delete(value, recursive: false);\n            return true;\n        }\n        return false;\n    }\n\n    public static string CopyFile(object? source, object? destination)\n    {\n        var sourcePath = PathArgument(source, "copyFile");\n        var destinationPath = PathArgument(destination, "copyFile");\n        if (!File.Exists(sourcePath))\n            throw new Exception($"copyFile() source file does not exist: {sourcePath}");\n        File.Copy(sourcePath, destinationPath, overwrite: false);\n        return destinationPath;\n    }\n\n    public static string MovePath(object? source, object? destination)\n    {\n        var sourcePath = PathArgument(source, "movePath");\n        var destinationPath = PathArgument(destination, "movePath");\n        if (File.Exists(sourcePath))\n            File.Move(sourcePath, destinationPath);\n        else if (Directory.Exists(sourcePath))\n            Directory.Move(sourcePath, destinationPath);\n        else\n            throw new Exception($"movePath() source does not exist: {sourcePath}");\n        return destinationPath;\n    }\n\n    public static List<object?> ListFiles(object? path) =>\n        Directory.GetFiles(PathArgument(path, "listFiles"))\n            .OrderBy(value => value, StringComparer.Ordinal)\n            .Select(value => (object?)value)\n            .ToList();\n\n    public static List<object?> ListDirectories(object? path) =>\n        Directory.GetDirectories(PathArgument(path, "listDirectories"))\n            .OrderBy(value => value, StringComparer.Ordinal)\n            .Select(value => (object?)value)\n            .ToList();\n\n    public static string CreateDirectoryPath(object? path)\n    {\n        var value = PathArgument(path, "createDirectoryPath");\n        Directory.CreateDirectory(value);\n        return value;\n    }\n\n    public static string AbsolutePath(object? path) =>\n'''
    text = replace_once(text, file_marker, file_methods, 'filesystem runtime insertion')

    path_marker = '''    public static string CombinePath(object? basePath, object? relativePath) =>\n        Path.Combine(\n            PathArgument(basePath, "combinePath"),\n            PathArgument(relativePath, "combinePath"));\n\n    public static string EnvironmentValue(object? name) =>\n'''
    path_methods = '''    public static string CombinePath(object? basePath, object? relativePath) =>\n        Path.Combine(\n            PathArgument(basePath, "combinePath"),\n            PathArgument(relativePath, "combinePath"));\n\n    public static string ParentPath(object? path) =>\n        Path.GetDirectoryName(PathArgument(path, "parentPath")) ?? "";\n\n    public static string FileName(object? path) =>\n        Path.GetFileName(PathArgument(path, "fileName"));\n\n    public static string PathExtension(object? path) =>\n        Path.GetExtension(PathArgument(path, "pathExtension"));\n\n    public static bool PathIsAbsolute(object? path) =>\n        Path.IsPathFullyQualified(PathArgument(path, "pathIsAbsolute"));\n\n    public static string EnvironmentValue(object? name) =>\n'''
    text = replace_once(text, path_marker, path_methods, 'path runtime insertion')

    method_marker = '''    private static readonly MethodInfo ReadFileMethod = Method(nameof(Runtime.ReadFile), typeof(object));\n    private static readonly MethodInfo FileExistsMethod = Method(nameof(Runtime.FileExists), typeof(object));\n    private static readonly MethodInfo AbsolutePathMethod = Method(nameof(Runtime.AbsolutePath), typeof(object));\n    private static readonly MethodInfo DirectoryNameMethod = Method(nameof(Runtime.DirectoryName), typeof(object));\n    private static readonly MethodInfo CombinePathMethod = Method(nameof(Runtime.CombinePath), typeof(object), typeof(object));\n    private static readonly MethodInfo EnvironmentValueMethod = Method(nameof(Runtime.EnvironmentValue), typeof(object));\n'''
    method_replacement = '''    private static readonly MethodInfo ReadFileMethod = Method(nameof(Runtime.ReadFile), typeof(object));\n    private static readonly MethodInfo FileExistsMethod = Method(nameof(Runtime.FileExists), typeof(object));\n    private static readonly MethodInfo WriteFileMethod = Method(nameof(Runtime.WriteFile), typeof(object), typeof(object));\n    private static readonly MethodInfo AppendFileMethod = Method(nameof(Runtime.AppendFile), typeof(object), typeof(object));\n    private static readonly MethodInfo DirectoryExistsMethod = Method(nameof(Runtime.DirectoryExists), typeof(object));\n    private static readonly MethodInfo DeletePathMethod = Method(nameof(Runtime.DeletePath), typeof(object));\n    private static readonly MethodInfo CopyFileMethod = Method(nameof(Runtime.CopyFile), typeof(object), typeof(object));\n    private static readonly MethodInfo MovePathMethod = Method(nameof(Runtime.MovePath), typeof(object), typeof(object));\n    private static readonly MethodInfo ListFilesMethod = Method(nameof(Runtime.ListFiles), typeof(object));\n    private static readonly MethodInfo ListDirectoriesMethod = Method(nameof(Runtime.ListDirectories), typeof(object));\n    private static readonly MethodInfo CreateDirectoryPathMethod = Method(nameof(Runtime.CreateDirectoryPath), typeof(object));\n    private static readonly MethodInfo AbsolutePathMethod = Method(nameof(Runtime.AbsolutePath), typeof(object));\n    private static readonly MethodInfo DirectoryNameMethod = Method(nameof(Runtime.DirectoryName), typeof(object));\n    private static readonly MethodInfo CombinePathMethod = Method(nameof(Runtime.CombinePath), typeof(object), typeof(object));\n    private static readonly MethodInfo ParentPathMethod = Method(nameof(Runtime.ParentPath), typeof(object));\n    private static readonly MethodInfo FileNameMethod = Method(nameof(Runtime.FileName), typeof(object));\n    private static readonly MethodInfo PathExtensionMethod = Method(nameof(Runtime.PathExtension), typeof(object));\n    private static readonly MethodInfo PathIsAbsoluteMethod = Method(nameof(Runtime.PathIsAbsolute), typeof(object));\n    private static readonly MethodInfo EnvironmentValueMethod = Method(nameof(Runtime.EnvironmentValue), typeof(object));\n'''
    text = replace_once(text, method_marker, method_replacement, 'PlanAssembler method table')

    call_marker = '''        "Runtime.ReadFile" => ReadFileMethod,\n        "Runtime.FileExists" => FileExistsMethod,\n        "Runtime.AbsolutePath" => AbsolutePathMethod,\n        "Runtime.DirectoryName" => DirectoryNameMethod,\n        "Runtime.CombinePath" => CombinePathMethod,\n        "Runtime.EnvironmentValue" => EnvironmentValueMethod,\n'''
    call_replacement = '''        "Runtime.ReadFile" => ReadFileMethod,\n        "Runtime.FileExists" => FileExistsMethod,\n        "Runtime.WriteFile" => WriteFileMethod,\n        "Runtime.AppendFile" => AppendFileMethod,\n        "Runtime.DirectoryExists" => DirectoryExistsMethod,\n        "Runtime.DeletePath" => DeletePathMethod,\n        "Runtime.CopyFile" => CopyFileMethod,\n        "Runtime.MovePath" => MovePathMethod,\n        "Runtime.ListFiles" => ListFilesMethod,\n        "Runtime.ListDirectories" => ListDirectoriesMethod,\n        "Runtime.CreateDirectoryPath" => CreateDirectoryPathMethod,\n        "Runtime.AbsolutePath" => AbsolutePathMethod,\n        "Runtime.DirectoryName" => DirectoryNameMethod,\n        "Runtime.CombinePath" => CombinePathMethod,\n        "Runtime.ParentPath" => ParentPathMethod,\n        "Runtime.FileName" => FileNameMethod,\n        "Runtime.PathExtension" => PathExtensionMethod,\n        "Runtime.PathIsAbsolute" => PathIsAbsoluteMethod,\n        "Runtime.EnvironmentValue" => EnvironmentValueMethod,\n'''
    return replace_once(text, call_marker, call_replacement, 'PlanAssembler runtime call table')


def apply_emitter(text: str) -> str:
    start = text.index('emitCall: fn(node: list) = [')
    end = text.index('\nemitFunctionClauses: fn', start)
    replacement = '''emitCall: fn(node: list) = [
    callee: atom | list | record = node@1,
    args: list = [],
    result: list = [],
    handled: boolean = false,

    for [i: number = 2, i < node.length(), i += 1]
        args.push(emit(node@i))
    loop,

    if kind(callee) == "symbol" and callee.name == "print" then
        result = [{ op: "print", args: args }]
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "kind" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.Kind" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "fail" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.Fail" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "symbol" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.Symbol" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "number" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.Number" })
        result.push({ op: "box", arg: "number" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "readFile" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.ReadFile" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "fileExists" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.FileExists" })
        result.push({ op: "box", arg: "boolean" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "writeFile" then
        result = args@0
        result = result.concat(args@1)
        result.push({ op: "call", arg: "Runtime.WriteFile" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "appendFile" then
        result = args@0
        result = result.concat(args@1)
        result.push({ op: "call", arg: "Runtime.AppendFile" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "directoryExists" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.DirectoryExists" })
        result.push({ op: "box", arg: "boolean" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "deletePath" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.DeletePath" })
        result.push({ op: "box", arg: "boolean" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "copyFile" then
        result = args@0
        result = result.concat(args@1)
        result.push({ op: "call", arg: "Runtime.CopyFile" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "movePath" then
        result = args@0
        result = result.concat(args@1)
        result.push({ op: "call", arg: "Runtime.MovePath" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "listFiles" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.ListFiles" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "listDirectories" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.ListDirectories" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "createDirectoryPath" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.CreateDirectoryPath" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "absolutePath" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.AbsolutePath" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "directoryName" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.DirectoryName" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "combinePath" then
        result = args@0
        result = result.concat(args@1)
        result.push({ op: "call", arg: "Runtime.CombinePath" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "parentPath" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.ParentPath" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "fileName" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.FileName" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "pathExtension" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.PathExtension" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "pathIsAbsolute" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.PathIsAbsolute" })
        result.push({ op: "box", arg: "boolean" })
        handled = true
    end,
    if not handled and kind(callee) == "symbol" and callee.name == "environment" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.EnvironmentValue" })
        handled = true
    end,

    if not handled then
        if isForm(callee, "get") then
            result = [{
                op: "invoke.member",
                receiver: emitTarget(callee@1),
                member: callee@2,
                args: args
            }]
        else
            result = [{
                op: "invoke",
                callee: emit(callee),
                args: args
            }]
        end
    end,

    result
]
'''
    return text[:start] + replacement + text[end:]


seed = SEED.read_text()
seed = apply_math(seed)
seed = apply_fs_path_runtime(seed)
SEED.write_text(seed)

emitter = EMITTER.read_text()
EMITTER.write_text(apply_emitter(emitter))
