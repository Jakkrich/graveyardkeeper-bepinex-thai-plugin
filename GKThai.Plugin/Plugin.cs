using System;
using System.IO;
using System.Reflection;
using BepInEx;
using BepInEx.Logging;
using HarmonyLib;
using GKThai.Plugin.Runtime;

namespace GKThai.Plugin
{
    [BepInPlugin("jakkr.gkthai", "GKThai - Graveyard Keeper", "0.1.0")]
    public sealed class Plugin : BaseUnityPlugin
    {
        internal static EmbeddedPayload Payload;
        internal static byte[] GlyphImage;
        internal static ManualLogSource Log;
        internal static bool Active;
        private static Harmony harmony;
        private static byte[] Resource(string name)
        {
            using (var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("GKThai." + name))
            {
                if (stream == null) throw new FileNotFoundException("Missing embedded " + name);
                using (var buffer = new MemoryStream()) { stream.CopyTo(buffer); return buffer.ToArray(); }
            }
        }
        private void Awake()
        {
            Log = Logger;
            try
            {
                BuildGuard.Check(Path.GetDirectoryName(Info.Location));
                var bytes = Resource("payload.bin"); GlyphImage = Resource("glyphs.png");
                if (BuildGuard.Hash(bytes) != BuildConstants.PayloadHash || BuildGuard.Hash(GlyphImage) != BuildConstants.GlyphHash) throw new InvalidDataException("Embedded payload hash mismatch");
                Payload = EmbeddedPayload.Parse(bytes);
                FontRegistry.Prepare();
                harmony = new Harmony("jakkr.gkthai"); harmony.PatchAll(typeof(Plugin).Assembly);
                Active = true; LocaleOverride.Apply();
                Logger.LogInfo("GKThai 0.1.0 active: pristine guard passed; runtime-only locale/NGUI/HD2 patches installed");
            }
            catch (Exception e) { Fail(e); }
        }
        internal static void Fail(Exception e)
        {
            Active = false;
            if (Log != null) Log.LogError("GKThai disabled; original game files untouched: " + e);
            Cleanup();
        }
        private static void Cleanup()
        {
            if (harmony != null) { harmony.UnpatchSelf(); harmony = null; }
            LocaleOverride.Restore(); FontRegistry.Dispose();
        }
        private void OnDestroy() { Active = false; Cleanup(); }
    }
}
