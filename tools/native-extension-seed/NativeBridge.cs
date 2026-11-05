using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Runtime.Loader;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Beacon.Compiler;

// A single ABI for trusted local extensions, independent of any graphics API.
// All requests/results are JSON-backed Beacon Atom / List / Record data.
// External code never receives BEnv, managed Beacon objects, or CLR pointers.
public static partial class Runtime
{
    private const int NativeExtensionAbiVersion = 1;
    private static readonly object NativeExtensionLock = new();
    private static readonly Dictionary<string, Func<string, string>> NativeExtensions = new(StringComparer.Ordinal);

    public static object? HostNative(object? moduleValue, object? requestValue)
    {
        if (moduleValue is not string module || !Regex.IsMatch(module, "^[a-z][a-z0-9_-]{0,63}$"))
            throw new Exception("hostNative() module name must be a lowercase extension identifier");
        if (requestValue is not BRecord request)
            throw new Exception("hostNative() request must be a Record");

        var invoke = LoadNativeExtension(module);
        string response;
        try
        {
            var json = JsonSerializer.Serialize(request);
            if (json.Length > 4_194_304)
                throw new Exception("Native extension request exceeds 4 MiB");
            response = invoke(json);
            if (response is null || response.Length > 4_194_304)
                throw new Exception("Native extension response is missing or exceeds 4 MiB");
        }
        catch (TargetInvocationException ex) when (ex.InnerException is not null)
        {
            throw new Exception($"Native extension '{module}' failed: {ex.InnerException.Message}", ex.InnerException);
        }

        using var document = JsonDocument.Parse(response);
        return DecodeInspectionJson(document.RootElement);
    }

    private static Func<string, string> LoadNativeExtension(string module)
    {
        lock (NativeExtensionLock)
        {
            if (NativeExtensions.TryGetValue(module, out var cached))
                return cached;

            var home = Environment.GetEnvironmentVariable("BEACON_HOME");
            if (string.IsNullOrWhiteSpace(home))
                throw new Exception("Native extensions require BEACON_HOME");
            var filename = Path.Combine(home, "native", module, $"Beacon.Native.{module}.dll");
            filename = Path.GetFullPath(filename);
            if (!File.Exists(filename))
                throw new Exception($"Native extension '{module}' not installed: {filename}");
            // Names are constrained above and the path is rooted under BEACON_HOME.
            // Installed native extensions run as trusted, in-process code.
            var assembly = AssemblyLoadContext.Default.LoadFromAssemblyPath(filename);
            var entry = assembly.GetType("Beacon.Native.Extension", throwOnError: true)!;
            var abi = entry.GetProperty("AbiVersion", BindingFlags.Public | BindingFlags.Static);
            if (abi?.GetValue(null) is not int version || version != NativeExtensionAbiVersion)
                throw new Exception($"Native extension '{module}' requires ABI {NativeExtensionAbiVersion}");
            var method = entry.GetMethod("Invoke", BindingFlags.Public | BindingFlags.Static,
                null, new[] { typeof(string) }, null);
            if (method is null || method.ReturnType != typeof(string))
                throw new Exception($"Native extension '{module}' must expose string Invoke(string json)");

            string Invoke(string json)
            {
                try { return (string)(method.Invoke(null, new object?[] { json }) ?? "null"); }
                catch (TargetInvocationException ex) when (ex.InnerException is not null)
                {
                    throw new Exception($"Native extension '{module}': {ex.InnerException.Message}", ex.InnerException);
                }
            }
            NativeExtensions[module] = Invoke;
            return Invoke;
        }
    }
}
