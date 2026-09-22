using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace GK2Thai.Plugin.Runtime
{
    internal sealed class GlyphData
    {
        public int Index, X, Y, Width, Height, OffsetX, OffsetY, Advance, Channel;
        public readonly List<int> Kerning = new List<int>();
    }
    internal sealed class FontData
    {
        public string Name;
        public int Size, Base, PanelX, PanelY;
        public readonly List<GlyphData> Glyphs = new List<GlyphData>();
    }
    internal sealed class EmbeddedPayload
    {
        public readonly Dictionary<string, string> Translations = new Dictionary<string, string>(StringComparer.Ordinal);
        public readonly Dictionary<string, string> Mapping = new Dictionary<string, string>(StringComparer.Ordinal);
        public readonly Dictionary<string, FontData> Fonts = new Dictionary<string, FontData>(StringComparer.Ordinal);
        private sealed class Node { public string Value; public readonly Dictionary<char, Node> Next = new Dictionary<char, Node>(); }
        private readonly Node root = new Node();
        private static int Count(BinaryReader r, int max) { int n = r.ReadInt32(); if (n < 0 || n > max) throw new InvalidDataException("Invalid payload count"); return n; }
        public static EmbeddedPayload Parse(byte[] data)
        {
            try
            {
                using (var stream = new MemoryStream(data, false)) using (var r = new BinaryReader(stream, new UTF8Encoding(false, true)))
                {
                    if (Encoding.ASCII.GetString(r.ReadBytes(5)) != "GK1P1") throw new InvalidDataException("Payload header");
                    var p = new EmbeddedPayload();
                    int count = Count(r, 100000);
                    if (count == 0) throw new InvalidDataException("Empty translations");
                    for (int i = 0; i < count; i++) p.Translations.Add(r.ReadString(), r.ReadString());
                    count = Count(r, 6400);
                    var pua = new HashSet<string>();
                    for (int i = 0; i < count; i++)
                    {
                        string key = r.ReadString(), value = r.ReadString();
                        if (key.Length < 2 || value.Length != 1 || value[0] < '\ue000' || value[0] > '\uf8ff' || !pua.Add(value)) throw new InvalidDataException("Cluster mapping invalid");
                        p.Mapping.Add(key, value);
                        var node = p.root;
                        foreach (char c in key) { Node next; if (!node.Next.TryGetValue(c, out next)) { next = new Node(); node.Next.Add(c, next); } node = next; }
                        node.Value = value;
                    }
                    count = Count(r, 7);
                    if (count == 0) throw new InvalidDataException("Empty fonts");
                    for (int i = 0; i < count; i++)
                    {
                        var f = new FontData { Name = r.ReadString(), Size = r.ReadInt32(), Base = r.ReadInt32(), PanelX = r.ReadInt32(), PanelY = r.ReadInt32() };
                        if (f.Size <= 0 || f.PanelX < 0 || f.PanelY < 0 || f.PanelX + 1024 > 4096 || f.PanelY + 1024 > 4096) throw new InvalidDataException("Font panel bounds");
                        int glyphs = Count(r, 65536); var indices = new HashSet<int>();
                        for (int j = 0; j < glyphs; j++)
                        {
                            var g = new GlyphData { Index = r.ReadInt32(), X = r.ReadInt32(), Y = r.ReadInt32(), Width = r.ReadInt32(), Height = r.ReadInt32(), OffsetX = r.ReadInt32(), OffsetY = r.ReadInt32(), Advance = r.ReadInt32(), Channel = r.ReadInt32() };
                            if (!indices.Add(g.Index) || g.Index < 0 || g.Index > 65535 || g.Width < 0 || g.Height < 0 || g.X < 0 || g.Y < 0 || g.X + g.Width > 1024 || g.Y + g.Height > 1024) throw new InvalidDataException("Glyph bounds/duplicate");
                            int pairs = Count(r, 65536);
                            for (int k = 0; k < pairs; k++) { g.Kerning.Add(r.ReadInt32()); g.Kerning.Add(r.ReadInt32()); }
                            f.Glyphs.Add(g);
                        }
                        p.Fonts.Add(f.Name, f);
                    }
                    if (stream.Position != stream.Length) throw new InvalidDataException("Trailing payload data");
                    return p;
                }
            }
            catch (EndOfStreamException e) { throw new InvalidDataException("Truncated payload", e); }
            catch (ArgumentException e) { throw new InvalidDataException("Duplicate/invalid payload", e); }
        }
        public string Shape(string text)
        {
            if (string.IsNullOrEmpty(text)) return text;
            var output = new StringBuilder(text.Length);
            for (int i = 0; i < text.Length;)
            {
                if (text[i] == '[')
                {
                    int end = text.IndexOf(']', i + 1);
                    if (end >= 0) { output.Append(text, i, end - i + 1); i = end + 1; continue; }
                }
                Node node = root, next; string best = null; int finish = i;
                for (int j = i; j < text.Length && node.Next.TryGetValue(text[j], out next); j++)
                { node = next; if (node.Value != null) { best = node.Value; finish = j + 1; } }
                if (best == null) { output.Append(text[i++]); } else { output.Append(best); i = finish; }
            }
            return output.ToString();
        }
    }
}
