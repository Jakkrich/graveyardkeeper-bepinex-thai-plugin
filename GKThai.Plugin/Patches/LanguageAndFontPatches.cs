using System;
using HarmonyLib;
using GKThai.Plugin.Runtime;

namespace GKThai.Plugin.Patches
{
    [HarmonyPatch(typeof(GJL), "LoadLanguageResource")]
    internal static class GjlLanguagePatch
    {
        static void Postfix() { if (!Plugin.Active) return; try { LocaleOverride.Apply(); } catch (Exception e) { Plugin.Fail(e); } }
    }
    [HarmonyPatch(typeof(GJL), "EnsureLabelHasCorrectFont")]
    internal static class GjlFontPatch
    {
        static void Prefix(UILabel label) { if (Plugin.Active) FontRegistry.RestoreLabel(label); }
        static void Postfix(UILabel label) { try { FontRegistry.Bind(label); } catch (Exception e) { Plugin.Fail(e); } }
    }
    [HarmonyPatch(typeof(UILabel), "UpdateNGUIText")]
    internal static class NguiFontPatch
    {
        static void Prefix(UILabel __instance) { try { FontRegistry.Bind(__instance); } catch (Exception e) { Plugin.Fail(e); } }
    }
    [HarmonyPatch(typeof(UILabel), "ProcessText")]
    internal static class DisplayScope
    {
        [ThreadStatic] internal static UILabel Current;
        static void Prefix(UILabel __instance, out UILabel __state)
        {
            __state = Current;
            try { FontRegistry.Bind(__instance); Current = Plugin.Active && LocaleOverride.English && FontRegistry.IsOwned(__instance.bitmapFont) && !FontRegistry.IsEditable(__instance) ? __instance : null; }
            catch (Exception e) { Current = null; Plugin.Fail(e); }
        }
        static Exception Finalizer(Exception __exception, UILabel __state) { Current = __state; return __exception; }
    }
    [HarmonyPatch(typeof(UILabel), "get_printedText")]
    internal static class DisplayTextPatch
    {
        static void Postfix(UILabel __instance, ref string __result)
        {
            if (Plugin.Active && ReferenceEquals(DisplayScope.Current, __instance)) __result = Plugin.Payload.Shape(__result);
        }
    }
}
