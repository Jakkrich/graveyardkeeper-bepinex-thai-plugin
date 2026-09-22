using System;
using System.Collections.Generic;
using System.Reflection;
using HarmonyLib;
using UnityEngine;

namespace GK2Thai.Plugin.Runtime
{
    internal static class LocaleOverride
    {
        private static readonly FieldInfo Current = AccessTools.Field(typeof(GJL), "cur_lng");
        private static readonly FieldInfo Keys = AccessTools.Field(typeof(GJL), "txt_ids");
        private static readonly FieldInfo Texts = AccessTools.Field(typeof(GJL), "txts");
        private static GJL original, clone;
        internal static bool English { get { var value = Current.GetValue(null) as GJL; return value != null && value.id == "en"; } }
        internal static void Apply()
        {
            GJL locale = Current.GetValue(null) as GJL;
            if (locale == null || locale == clone) return;
            if (locale.id != "en") { FontRegistry.RestoreLabels(); return; }
            ReleaseClone();
            var next = UnityEngine.Object.Instantiate(locale);
            try
            {
                next.hideFlags = HideFlags.HideAndDontSave;
                var keys = new List<string>((List<string>)Keys.GetValue(locale));
                var texts = new List<string>((List<string>)Texts.GetValue(locale));
                if (keys.Count != texts.Count) throw new InvalidOperationException("Locale keys/text count differs");
                int translated = 0;
                for (int i = 0; i < keys.Count; i++) { string text; if (Plugin.Payload.Translations.TryGetValue(keys[i], out text)) { texts[i] = text; translated++; } }
                if (translated != keys.Count) throw new InvalidOperationException("Translation key coverage differs: " + translated + "/" + keys.Count);
                Keys.SetValue(next, keys); Texts.SetValue(next, texts);
                next.dict = new Dictionary<string, string>();
                next.aliases_1 = new List<string>(locale.aliases_1);
                next.aliases_2 = new List<string>(locale.aliases_2);
                next.InitHashDictionary();
                original = locale; clone = next; Current.SetValue(null, clone);
                Plugin.Log.LogInfo("GK1Thai locale active: " + translated + " Unicode rows; original resource untouched");
            }
            catch { UnityEngine.Object.Destroy(next); throw; }
        }
        private static void ReleaseClone()
        {
            if (clone != null) { if (ReferenceEquals(Current.GetValue(null), clone)) Current.SetValue(null, original); UnityEngine.Object.Destroy(clone); }
            clone = null; original = null;
        }
        internal static void Restore() { ReleaseClone(); }
    }
}
