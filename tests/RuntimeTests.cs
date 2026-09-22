using System;
using System.IO;
using System.Text;
using GKThai.Plugin.Runtime;

internal static class RuntimeTests
{
    private static int count;
    static void Assert(bool value, string name) { if (!value) throw new Exception(name); count++; }
    static void Reject(Action action, string name) { bool failed = false; try { action(); } catch (InvalidDataException) { failed = true; } Assert(failed, name); }
    static byte[] Fixture(bool duplicate)
    {
        using (var s = new MemoryStream()) using (var w = new BinaryWriter(s, Encoding.UTF8))
        {
            w.Write(Encoding.ASCII.GetBytes("GK1P1")); w.Write(duplicate ? 2 : 1);
            w.Write("hello"); w.Write("น้ำ %1");
            if (duplicate) { w.Write("hello"); w.Write("น้ำ %1"); }
            w.Write(1); w.Write("น้ำ"); w.Write("\ue000");
            w.Write(1); w.Write("font"); w.Write(16); w.Write(16); w.Write(1024); w.Write(0); w.Write(1);
            foreach (int v in new[] { 0xe000, 0, 0, 10, 12, 0, 0, 11, 15 }) w.Write(v);
            w.Write(0); w.Flush(); return s.ToArray();
        }
    }
    public static void Main(string[] args)
    {
        var payload = EmbeddedPayload.Parse(Fixture(false));
        Assert(payload.Translations["hello"] == "น้ำ %1", "Unicode translation preserved");
        Assert(payload.Shape("น้ำ %1 [ff0000]น้ำ[-]") == "\ue000 %1 [ff0000]\ue000[-]", "display shaping and markup");
        Assert(payload.Shape(payload.Shape("น้ำ")) == "\ue000", "idempotent shaping");
        Assert(payload.Shape("[น้ำ]") == "[น้ำ]", "bracket token protected");
        Reject(delegate { EmbeddedPayload.Parse(Fixture(true)); }, "duplicate translation rejected");
        Reject(delegate { EmbeddedPayload.Parse(new byte[] { 1, 2 }); }, "truncated payload rejected");
        byte[] trailing = new byte[Fixture(false).Length + 1]; Fixture(false).CopyTo(trailing, 0);
        Reject(delegate { EmbeddedPayload.Parse(trailing); }, "trailing data rejected");
        Assert(Math.Abs(ThaiGlyphMetrics.Advance(20f, 15 | (40 << 4), 1f) - 9.8f) < 0.0001f, "fractional HD2 advance");
        Assert(Math.Abs(ThaiGlyphMetrics.Advance(0f, 15, 1f)) < 0.0001f, "zero width mark");
        if (args.Length != 0)
        {
            var actual = EmbeddedPayload.Parse(File.ReadAllBytes(args[0]));
            Assert(actual.Translations.Count == 10961, "current corpus count");
            Assert(actual.Fonts.Count == 7, "seven fonts");
            Assert(actual.Shape("น้ำ ปู่ ปี่ กุ้ง ซื้อ เก็บเกี่ยว").IndexOf('\ue000') >= 0 || actual.Mapping.Count > 0, "current cluster map");
        }
        Console.WriteLine("PASS: " + count + " runtime data/metrics assertions");
    }
}
