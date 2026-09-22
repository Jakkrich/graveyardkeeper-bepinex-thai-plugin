using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using HarmonyLib;
using GKThai.Plugin.Runtime;

namespace GKThai.Plugin.Patches
{
    [HarmonyPatch(typeof(NGUIText), "GetGlyph")]
    internal static class NguiGlyphPatch
    {
        static void Postfix(ref NGUIText.GlyphInfo __result)
        {
            if (!Plugin.Active || __result == null || !FontRegistry.IsOwned(NGUIText.bitmapFont)) return;
            var g = __result;
            __result = new NGUIText.GlyphInfo { v0 = g.v0 * 0.5f, v1 = g.v1 * 0.5f,
                u0 = g.u0, u1 = g.u1, u2 = g.u2, u3 = g.u3,
                advance = ThaiGlyphMetrics.Advance(g.advance, g.channel, NGUIText.fontScale), channel = g.channel & 15 };
        }
    }
    [HarmonyPatch(typeof(NGUIText), "GetGlyphWidth")]
    internal static class NguiWidthPatch
    {
        static void Postfix(int ch, ref float __result)
        {
            if (!Plugin.Active || !FontRegistry.IsOwned(NGUIText.bitmapFont)) return;
            var glyph = NGUIText.bitmapFont.bmFont.GetGlyph(ch == 8201 ? 32 : ch);
            if (glyph != null) __result = ThaiGlyphMetrics.Advance(__result, glyph.channel, NGUIText.fontScale);
        }
    }
    [HarmonyPatch]
    internal static class NguiWrapPatch
    {
        static MethodBase TargetMethod() { return AccessTools.Method(typeof(NGUIText), "WrapText", new[] { typeof(string), typeof(string).MakeByRefType(), typeof(bool), typeof(bool), typeof(bool) }); }
        static bool IsCjkForWrap(int character)
        {
            return character > 12287 && !(Plugin.Active && FontRegistry.IsOwned(NGUIText.bitmapFont) && character >= 0xe000 && character <= 0xf8ff);
        }
        static IEnumerable<CodeInstruction> Transpiler(IEnumerable<CodeInstruction> instructions)
        {
            var code = instructions.ToList(); int replacements = 0;
            for (int i = 0; i + 1 < code.Count; i++)
            {
                if (!code[i].LoadsConstant(12287) || (code[i + 1].opcode != OpCodes.Ble && code[i + 1].opcode != OpCodes.Ble_S)) continue;
                code[i].opcode = OpCodes.Call; code[i].operand = AccessTools.Method(typeof(NguiWrapPatch), "IsCjkForWrap");
                code[i + 1].opcode = OpCodes.Brfalse; replacements++;
            }
            if (replacements != 1) throw new InvalidOperationException("NGUI WrapText CJK pattern changed: " + replacements);
            return code;
        }
    }
}
