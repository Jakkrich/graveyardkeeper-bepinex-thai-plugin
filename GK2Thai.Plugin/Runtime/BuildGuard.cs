using System;
using System.IO;
using System.Security.Cryptography;
using UnityEngine;

namespace GK2Thai.Plugin.Runtime
{
    internal static class BuildGuard
    {
        internal static string Hash(byte[] bytes) { using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant(); }
        internal static string HashFile(string file) { using (var s = File.OpenRead(file)) using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(s)).Replace("-", "").ToLowerInvariant(); }
        internal static void Match(string path, string expected)
        { if (!File.Exists(path) || HashFile(path) != expected) throw new InvalidDataException("Unsupported or modified file: " + path); }
        internal static void Check(string pluginRoot)
        {
            Match(Path.Combine(Application.dataPath, "resources.assets"), "215c7981901a4b72d5db717666ba47ad3cc032527c95f58dc39d8af1293a69ca");
            Match(Path.Combine(Application.dataPath, "Managed/Assembly-CSharp-firstpass.dll"), "9dc6def3b7715dd27eeb168ddc0af47e31c6f38d3fbee24bf592899392026498");
            Match(Path.Combine(Application.dataPath, "Managed/Assembly-CSharp.dll"), "e72e4270e4b88dd0a87ca23c9cf1750aec4c4a0fedb40b6d2dae7902fc9c7fd8");
            Match(Path.Combine(pluginRoot, "font.ttf"), BuildConstants.FontHash);
        }
    }
}
