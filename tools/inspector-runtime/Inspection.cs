using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Threading;

// The only new host boundary is read-only local transport and runtime state
// observation. Values, tree presentation, and session UI remain Beacon-owned.
public static partial class Runtime
{
    public static readonly object InspectGate = new();
    private static volatile bool _inspectionArmed;
    private static BEnv? _inspectionRoot;
    private static string _inspectionSource = "";

    internal static void CaptureInspectedRoot(BEnv env)
    {
        if (!_inspectionArmed) return;
        lock (InspectGate)
            _inspectionRoot ??= env;
    }

    public static void BeginInspection(string source)
    {
        lock (InspectGate)
        {
            _inspectionSource = Path.GetFullPath(source);
            _inspectionRoot = null;
            _inspectionArmed = true;
        }
        var server = new Thread(InspectionServerLoop)
        {
            IsBackground = true,
            Name = "Beacon Inspector IPC"
        };
        server.Start();
    }

    public static void EndInspection()
    {
        _inspectionArmed = false;
        lock (InspectGate) _inspectionRoot = null;
    }

    private static string InspectionPipeName(int pid) => "beacon-inspect-v1-" + pid;

    private static void InspectionServerLoop()
    {
        while (_inspectionArmed)
        {
            try
            {
                using var pipe = new NamedPipeServerStream(
                    InspectionPipeName(Environment.ProcessId),
                    PipeDirection.InOut, 1, PipeTransmissionMode.Byte,
                    PipeOptions.CurrentUserOnly);
                pipe.WaitForConnection();

                using var reader = new StreamReader(pipe, new UTF8Encoding(false), false, 4096, leaveOpen: true);
                using var writer = new StreamWriter(pipe, new UTF8Encoding(false), 4096, leaveOpen: true)
                { AutoFlush = true };
                var command = reader.ReadLine();
                if (command == "snapshot")
                    writer.WriteLine(JsonSerializer.Serialize(InspectionSnapshot()));
                else
                    writer.WriteLine("{\"protocol\":1,\"connected\":false,\"error\":\"Unsupported inspection command\"}");
            }
            catch (IOException) { /* A client disconnected; keep the target alive. */ }
            catch (ObjectDisposedException) { break; }
            catch (Exception ex)
            {
                // Inspection must never crash the application under observation.
                Console.Error.WriteLine("Beacon inspection: " + ex.Message);
            }
        }
    }

    private static Dictionary<string, object?> InspectionSnapshot()
    {
        lock (InspectGate)
        {
            var variables = new List<object?>();
            if (_inspectionRoot is not null)
            {
                foreach (var entry in _inspectionRoot.InspectEntries().OrderBy(x => x.Key, StringComparer.Ordinal))
                    variables.Add(InspectNode(entry.Key, entry.Value, 0, new HashSet<object>(ReferenceEqualityComparer.Instance)));
            }
            return new Dictionary<string, object?>
            {
                ["protocol"] = 1,
                ["connected"] = true,
                ["status"] = _inspectionRoot is null ? "starting" : "running",
                ["pid"] = Environment.ProcessId,
                ["source"] = _inspectionSource,
                ["values"] = variables,
            };
        }
    }

    private static Dictionary<string, object?> InspectNode(
        string name, object? value, int depth, HashSet<object> ancestors)
    {
        var kind = Kind(value);
        var children = new List<object?>();
        var truncated = false;
        string preview = kind switch
        {
            "string" => (string)value!,
            "number" => ((double)value!).ToString(System.Globalization.CultureInfo.InvariantCulture),
            "boolean" => ((bool)value!).ToString().ToLowerInvariant(),
            "null" => "null",
            "list" => "[" + ((List<object?>)value!).Count + "]",
            "record" => "{" + ((BRecord)value!).Count + "}",
            "symbol" => ((BSymbol)value!).Name,
            "type" => ((BType)value!).Name,
            "fn" => "<function>",
            _ => "<unknown>"
        };

        if (value is List<object?> || value is BRecord)
        {
            if (!ancestors.Add(value!))
            {
                preview = "<cycle>";
                truncated = true;
            }
            else
            {
                if (depth < 4)
                {
                    if (value is List<object?> list)
                    {
                        for (var i = 0; i < Math.Min(64, list.Count); i++)
                            children.Add(InspectNode("@" + i, list[i], depth + 1, ancestors));
                        truncated = list.Count > 64;
                    }
                    else if (value is BRecord record)
                    {
                        foreach (var member in record.OrderBy(x => x.Key, StringComparer.Ordinal).Take(64))
                            children.Add(InspectNode(member.Key, member.Value, depth + 1, ancestors));
                        truncated = record.Count > 64;
                    }
                }
                else
                    truncated = true;
                ancestors.Remove(value!);
            }
        }

        if (preview.Length > 180) preview = preview.Substring(0, 180) + "…";
        return new Dictionary<string, object?>
        {
            ["name"] = name,
            ["kind"] = kind,
            ["preview"] = preview,
            ["children"] = children,
            ["truncated"] = truncated,
        };
    }

    private static object? DecodeInspectionJson(JsonElement element) => element.ValueKind switch
    {
        JsonValueKind.Object => DecodeInspectionRecord(element),
        JsonValueKind.Array => element.EnumerateArray().Select(DecodeInspectionJson).ToList(),
        JsonValueKind.String => element.GetString(),
        JsonValueKind.Number => element.GetDouble(),
        JsonValueKind.True => true,
        JsonValueKind.False => false,
        _ => null
    };

    private static BRecord DecodeInspectionRecord(JsonElement element)
    {
        var record = new BRecord();
        foreach (var property in element.EnumerateObject())
            record[property.Name] = DecodeInspectionJson(property.Value);
        return record;
    }

    private static BRecord DisconnectedInspection(string message) => new()
    {
        ["protocol"] = 1.0,
        ["connected"] = false,
        ["status"] = "disconnected",
        ["error"] = message,
        ["source"] = "",
        ["values"] = new List<object?>()
    };

    public static object? HostInspect(object? actionValue, object? payload)
    {
        if (actionValue is not string action)
            throw new Exception("hostInspect() action must be a String");

        if (action == "launch")
        {
            if (payload is not string path || path.Length == 0)
                throw new Exception("inspect.launch() requires a source path");
            var source = Path.GetFullPath(path);
            if (!File.Exists(source))
                throw new Exception("Beacon application not found: " + source);
            var home = Environment.GetEnvironmentVariable("BEACON_HOME") ??
                       throw new Exception("BEACON_HOME is required to launch inspection targets");
            var seed = Path.Combine(home, "bootstrap", "stage0", "Beacon.Compiler.dll");
            var compiler = Path.Combine(home, "compiler", "compiler.beacon");
            var start = new ProcessStartInfo("dotnet")
            {
                UseShellExecute = false,
                WorkingDirectory = home,
            };
            start.ArgumentList.Add(seed);
            start.ArgumentList.Add(compiler);
            start.ArgumentList.Add("--stage1-run");
            start.ArgumentList.Add(source);
            start.ArgumentList.Add("--inspect");
            start.Environment["BEACON_HOME"] = home;
            using var process = Process.Start(start) ??
                throw new Exception("Unable to launch Beacon inspection target");
            return (double)process.Id;
        }

        if (action == "snapshot")
        {
            if (payload is not double number || number < 1 || number > int.MaxValue ||
                number != Math.Truncate(number))
                throw new Exception("inspect.snapshot() expects a positive integer PID");
            var pid = (int)number;
            try
            {
                using var pipe = new NamedPipeClientStream(
                    ".", InspectionPipeName(pid), PipeDirection.InOut, PipeOptions.CurrentUserOnly);
                pipe.Connect(450);
                using var reader = new StreamReader(pipe, new UTF8Encoding(false), false, 4096, leaveOpen: true);
                using var writer = new StreamWriter(pipe, new UTF8Encoding(false), 4096, leaveOpen: true)
                { AutoFlush = true };
                writer.WriteLine("snapshot");
                var json = reader.ReadLine() ??
                    throw new IOException("Inspection target closed the connection");
                using var document = JsonDocument.Parse(json);
                return DecodeInspectionJson(document.RootElement);
            }
            catch (Exception ex) when (ex is IOException or TimeoutException or UnauthorizedAccessException)
            {
                return DisconnectedInspection(ex.Message);
            }
        }

        throw new Exception("Unknown hostInspect() action: " + action);
    }
}
