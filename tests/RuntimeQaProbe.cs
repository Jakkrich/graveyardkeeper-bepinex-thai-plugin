using System;
using System.IO;
using System.Linq;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using BepInEx;
using UnityEngine;

[BepInPlugin("jakkr.gk2thai.gk1.qa", "GK1Thai Runtime QA Probe", "0.1.0")]
[BepInDependency("jakkr.gk2thai.gk1", BepInDependency.DependencyFlags.SoftDependency)]
public sealed class RuntimeQaProbe : BaseUnityPlugin
{
    private readonly List<string> lines = new List<string>();
    private int failures;
    private string output;
    private Type registry;
    private static readonly BindingFlags Flags = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance;
    private static readonly FieldInfo Current = typeof(GJL).GetField("cur_lng", Flags);
    private const string Thai = "น้ำ ปู่ ปี่ กุ้ง ซื้อ เก็บเกี่ยว 0123456789";
    private void Awake()
    {
        if (Environment.GetCommandLineArgs().Contains("--gk1thai-qa-baseline"))
        {
            output = Path.Combine(Paths.BepInExRootPath, "GK1Thai-QA-baseline.txt");
            lines.Add("GK1Thai uninstall baseline " + DateTime.UtcNow.ToString("o"));
            Flush(); StartCoroutine(Baseline()); return;
        }
        if (!Environment.GetCommandLineArgs().Contains("--gk1thai-qa")) return;
        output = Path.Combine(Paths.BepInExRootPath, "GK1Thai-QA.txt");
        lines.Add("GK1Thai isolated runtime QA " + DateTime.UtcNow.ToString("o"));
        Flush(); StartCoroutine(Run());
    }
    private IEnumerator Baseline()
    {
        yield return new WaitForSecondsRealtime(15);
        Test("baseline", delegate {
            var locale = Locale();
            var resource = Resources.Load<GJL>("Locales/lng_en");
            Check("stock English locale reference", locale != null && locale.id == "en" && ReferenceEquals(locale,resource));
            Check("stock English no Thai payload", locale != null && !locale.dict.Values.Any(s => s != null && s.Any(c => c >= '\u0E00' && c <= '\u0E7F')));
            var labels = Resources.FindObjectsOfTypeAll<UILabel>().Where(l => l.gameObject.activeInHierarchy).ToArray();
            Check("baseline menu labels exist", labels.Length > 0);
            Check("no plugin font bound", !labels.Any(l => l.bitmapFont != null && l.bitmapFont.bmFont.spriteName != null && l.bitmapFont.bmFont.spriteName.StartsWith("gk1_hd2_")));
            lines.Add("STATE labels=" + labels.Length + " locale=" + (locale == null ? "null" : locale.id));
            foreach (string relative in new[] { "Graveyard Keeper_Data/Managed/Assembly-CSharp-firstpass.dll", "Graveyard Keeper_Data/Managed/Assembly-CSharp.dll", "Graveyard Keeper_Data/resources.assets" })
            {
                using (var hash = System.Security.Cryptography.SHA256.Create())
                using (var stream = File.OpenRead(Path.Combine(Paths.GameRootPath, relative)))
                    lines.Add("SHA256 " + relative + " " + BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant());
            }
            Flush();
        });
        yield return new WaitForEndOfFrame();
        Test("baseline screenshot", delegate { ScreenCapture.CaptureScreenshot(Path.Combine(Paths.BepInExRootPath, "GK1Thai-baseline-menu.png")); });
        yield return new WaitForSecondsRealtime(2);
        lines.Add("RESULT failures=" + failures); Flush(); Application.Quit();
    }
    private void Flush() { File.WriteAllLines(output, lines.ToArray(), new System.Text.UTF8Encoding(false)); }
    private void Check(string name, bool ok)
    {
        if (!ok) failures++;
        string line = (ok ? "PASS " : "FAIL ") + name;
        lines.Add(line); Logger.LogInfo(line); Flush();
    }
    private void Test(string name, Action body)
    {
        try { body(); }
        catch (Exception e) { failures++; lines.Add("FAIL " + name + " EXCEPTION " + e); Logger.LogError(e); Flush(); }
    }
    private bool Owned(UIFont font) { return (bool)registry.GetMethod("IsOwned", Flags).Invoke(null, new object[] { font }); }
    private static bool Pua(string s) { return s != null && s.Any(c => c >= '\uE000' && c <= '\uF8FF'); }
    private static GJL Locale() { return (GJL)Current.GetValue(null); }
    private UILabel Label(Transform parent, UIFont font, string name, int y)
    {
        var go = new GameObject(name); go.transform.SetParent(parent, false);
        go.transform.localPosition = new Vector3(-350, y, 0);
        var label = go.AddComponent<UILabel>(); label.bitmapFont = font;
        label.fontSize = 24; label.width = 1100; label.height = 70;
        label.pivot = UIWidget.Pivot.Left; label.overflowMethod = UILabel.Overflow.ResizeHeight;
        label.text = Thai; return label;
    }
    private IEnumerator Run()
    {
        yield return new WaitForSecondsRealtime(15);
        GameObject sheet = null;
        Test("initialization", delegate {
            var main = AppDomain.CurrentDomain.GetAssemblies().First(a => a.GetName().Name == "GK2Thai.Plugin");
            var plugin = main.GetType("GK2Thai.Plugin.Plugin", true);
            registry = main.GetType("GK2Thai.Plugin.Runtime.FontRegistry", true);
            Check("main plugin active", (bool)plugin.GetField("Active", Flags).GetValue(null));
            Check("seven prepared fonts", (int)registry.GetProperty("FontCount", Flags).GetValue(null, null) == 7);
        });
        yield return new WaitForEndOfFrame();
        Test("menu screenshot", delegate { ScreenCapture.CaptureScreenshot(Path.Combine(Paths.BepInExRootPath, "GK1Thai-menu.png")); });
        yield return null;
        Test("runtime assertions", delegate {
            if (registry == null) throw new InvalidOperationException("Plugin registry unavailable");
            var fontPairs = (IDictionary)registry.GetField("Fonts", Flags).GetValue(null);
            var originals = new List<UIFont>();
            foreach (DictionaryEntry pair in fontPairs) originals.Add((UIFont)pair.Key);
            if (originals.Count == 0) throw new InvalidOperationException("No prepared font pairs");
            var root = Resources.FindObjectsOfTypeAll<UIRoot>().FirstOrDefault(r => r.gameObject.activeInHierarchy);
            if (root == null) throw new InvalidOperationException("No live UIRoot after 15 seconds");
            sheet = new GameObject("GK1Thai QA font sheet"); sheet.transform.SetParent(root.transform, false);
            var panel = sheet.AddComponent<UIPanel>(); panel.depth = 30000;
            GJL.LoadLanguageResource("en");
            var resource = Resources.Load<GJL>("Locales/lng_en");
            var pristine = new Dictionary<string,string>(resource.dict);
            Check("locale cloned", Locale() != resource && !ReferenceEquals(Locale().dict, resource.dict));
            string key = Locale().dict.First(p => p.Value != null && p.Value.Any(c => c >= '\u0E00' && c <= '\u0E7F')).Key;
            string translation = Locale().dict[key];
            Check("locale contains Unicode Thai", !Pua(translation));
            var labels = new List<UILabel>();
            for (int i = 0; i < originals.Count; i++)
            {
                var label = Label(sheet.transform, originals[i], "QA " + originals[i].name, 240 - i * 65);
                labels.Add(label);
                bool callbackPua = false; int callbacks = 0;
                label.onChange += delegate { callbacks++; callbackPua |= Pua(label.text); };
                typeof(UIWidget).GetField("mHeight", Flags).SetValue(label, 1);
                label.ProcessText(false, true);
                Check("font " + i + " bound", Owned(label.bitmapFont));
                Check("font " + i + " raw preserved", label.text == Thai);
                Check("font " + i + " processed PUA", Pua(label.processedText));
                Check("font " + i + " onChange raw Unicode", callbacks > 0 && !callbackPua);
                label.UpdateNGUIText();
                int ch = label.processedText.First(c => c >= '\uE000' && c <= '\uF8FF');
                var first = NGUIText.GetGlyph(ch, 0); float advance = first.advance;
                var second = NGUIText.GetGlyph(ch, 0);
                Check("font " + i + " repeat stable", Math.Abs(advance - second.advance) < 0.0001f && !ReferenceEquals(first, second));
                Check("font " + i + " measure matches", Math.Abs(NGUIText.GetGlyphWidth(ch, 0) - second.advance) < 0.001f);
                var cjk = registry.Assembly.GetType("GK2Thai.Plugin.Patches.NguiWrapPatch").GetMethod("IsCjkForWrap", Flags);
                Check("font " + i + " CJK stays CJK", (bool)cjk.Invoke(null, new object[] { 0x4e00 }));
                Check("font " + i + " Thai PUA word wrap", !(bool)cjk.Invoke(null, new object[] { ch }));
                NGUIText.bitmapFont = originals[i]; NGUIText.dynamicFont = null; NGUIText.fontScale = 1;
                Check("font " + i + " nonowned CJK rule", (bool)cjk.Invoke(null, new object[] { ch }));
                var g = originals[i].bmFont.GetGlyph('A');
                if (g != null) Check("font " + i + " nonowned unchanged", Math.Abs(NGUIText.GetGlyphWidth('A',0) - g.advance) < 0.001f);
            }
            var inputGo = new GameObject("QA editable"); inputGo.transform.SetParent(sheet.transform, false);
            var input = inputGo.AddComponent<UIInput>();
            var editable = Label(inputGo.transform, originals[0], "Input label", -350); input.label = editable;
            editable.ProcessText(false,true);
            Check("UIInput excluded", !Owned(editable.bitmapFont) && editable.text == Thai && !Pua(editable.processedText));
            UnityEngine.Object.Destroy(inputGo);
            GJL.LoadLanguageResource("de");
            Check("German resource active", Locale().id == "de" && !ReferenceEquals(Locale(), resource));
            foreach (var label in labels) { label.ProcessText(false,true); Check("German font restored " + label.name, !Owned(label.bitmapFont)); }
            GJL.LoadLanguageResource("en");
            Check("English translation reapplied", Locale().dict[key] == translation);
            foreach (var label in labels) { label.ProcessText(false,true); Check("English font rebound " + label.name, Owned(label.bitmapFont) && label.text == Thai); }
            Check("English resource untouched", pristine.Count == resource.dict.Count && pristine.All(p => resource.dict.ContainsKey(p.Key) && resource.dict[p.Key] == p.Value));
            NGUIText.bitmapFont = null; NGUIText.dynamicFont = null;
        });
        yield return new WaitForSecondsRealtime(2);
        yield return new WaitForEndOfFrame();
        Test("font sheet screenshot", delegate { ScreenCapture.CaptureScreenshot(Path.Combine(Paths.BepInExRootPath, "GK1Thai-font-sheet.png")); });
        yield return new WaitForSecondsRealtime(2);
        lines.Add("RESULT failures=" + failures); Flush();
        if (sheet != null) UnityEngine.Object.Destroy(sheet);
        Application.Quit();
    }
}
