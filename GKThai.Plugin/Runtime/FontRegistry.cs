using System;
using System.Collections.Generic;
using UnityEngine;

namespace GKThai.Plugin.Runtime
{
    internal static class FontRegistry
    {
        private static readonly Dictionary<UIFont, UIFont> Fonts = new Dictionary<UIFont, UIFont>();
        private static readonly HashSet<UIFont> Owned = new HashSet<UIFont>();
        private static readonly Dictionary<UIAtlas, UIAtlas> Atlases = new Dictionary<UIAtlas, UIAtlas>();
        private static readonly Dictionary<UILabel, UIFont> Labels = new Dictionary<UILabel, UIFont>();
        private static readonly List<UnityEngine.Object> Allocated = new List<UnityEngine.Object>();
        private static GameObject container;
        internal static int FontCount { get { return Owned.Count; } }
        internal static bool IsOwned(UIFont font) { return font != null && Owned.Contains(font); }
        internal static bool IsEditable(UILabel label) { return label != null && label.GetComponentInParent<UIInput>() != null; }
        private static GameObject Node(string name)
        {
            if (container == null) { container = new GameObject("GKThai Runtime Fonts"); container.hideFlags = HideFlags.HideAndDontSave; UnityEngine.Object.DontDestroyOnLoad(container); }
            var go = new GameObject(name); go.hideFlags = HideFlags.HideAndDontSave; go.transform.SetParent(container.transform, false); return go;
        }
        internal static void Prepare()
        {
            foreach (var font in Resources.LoadAll<UIFont>("")) TryClone(font);
            if (Owned.Count < Plugin.Payload.Fonts.Count) throw new InvalidOperationException("Cannot locate all expected NGUI fonts: " + Owned.Count);
            Plugin.Log.LogInfo("GKThai fonts prepared: " + Owned.Count + "; atlases=" + Atlases.Count);
        }
        private static UIAtlas CloneAtlas(UIAtlas source)
        {
            UIAtlas result;
            if (Atlases.TryGetValue(source, out result)) return result;
            if (source == null || source.spriteMaterial == null) throw new InvalidOperationException("Missing font atlas");
            Texture original = source.spriteMaterial.mainTexture;
            if (original == null || original.width != 1024 || original.height != 1024) throw new InvalidOperationException("Expected pristine 1024 atlas");
            var texture = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            Allocated.Add(texture);
            if (!ImageConversion.LoadImage(texture, Plugin.GlyphImage, false) || texture.width != 4096 || texture.height != 4096) throw new InvalidOperationException("Glyph image invalid");
            var rt = RenderTexture.GetTemporary(1024, 1024, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.Default);
            var previous = RenderTexture.active;
            Texture2D readable = null;
            try
            {
                Graphics.Blit(original, rt); RenderTexture.active = rt;
                readable = new Texture2D(1024, 1024, TextureFormat.RGBA32, false);
                readable.ReadPixels(new Rect(0, 0, 1024, 1024), 0, 0); readable.Apply();
                texture.SetPixels(0, 3072, 1024, 1024, readable.GetPixels());
                texture.filterMode = FilterMode.Point; texture.wrapMode = TextureWrapMode.Clamp; texture.Apply(false, false);
            }
            finally { RenderTexture.active = previous; RenderTexture.ReleaseTemporary(rt); if (readable != null) UnityEngine.Object.Destroy(readable); }
            var material = new Material(source.spriteMaterial); Allocated.Add(material); material.mainTexture = texture;
            result = Node("Atlas " + source.name).AddComponent<UIAtlas>();
            result.spriteMaterial = material; result.pixelSize = source.pixelSize;
            var sprites = new List<UISpriteData>();
            foreach (var s in source.spriteList)
            {
                var copy = new UISpriteData(); copy.CopyFrom(s);
                FontData data;
                if (Plugin.Payload.Fonts.TryGetValue(copy.name, out data))
                { copy.name = "gk1_hd2_" + data.Name; copy.x = data.PanelX; copy.y = data.PanelY; copy.width = copy.height = 1024; copy.SetPadding(0, 0, 0, 0); copy.SetBorder(0, 0, 0, 0); }
                sprites.Add(copy);
            }
            result.spriteList = sprites; Atlases.Add(source, result); return result;
        }
        private static UIFont TryClone(UIFont source)
        {
            if (source == null || IsOwned(source)) return source;
            while (source.replacement != null) source = source.replacement;
            UIFont result; if (Fonts.TryGetValue(source, out result)) return result;
            FontData data;
            if (source.bmFont == null || !Plugin.Payload.Fonts.TryGetValue(source.bmFont.spriteName, out data)) return source;
            var atlas = CloneAtlas(source.atlas);
            result = Node("Font " + source.name).AddComponent<UIFont>();
            var bm = new BMFont { charSize = data.Size, baseOffset = data.Base, texWidth = 1024, texHeight = 1024, spriteName = "gk1_hd2_" + data.Name };
            foreach (var g in data.Glyphs)
            {
                var glyph = bm.GetGlyph(g.Index, true);
                glyph.x = g.X; glyph.y = g.Y; glyph.width = g.Width; glyph.height = g.Height;
                glyph.offsetX = g.OffsetX; glyph.offsetY = g.OffsetY; glyph.advance = g.Advance; glyph.channel = g.Channel;
                glyph.kerning = new List<int>(g.Kerning);
            }
            result.bmFont = bm; result.atlas = atlas;
            foreach (var symbol in source.symbols) result.symbols.Add(symbol.Copy());
            result.uvRect = new Rect(data.PanelX / 4096f, 1f - (data.PanelY + 1024) / 4096f, 0.25f, 0.25f);
            Fonts.Add(source, result); Owned.Add(result); return result;
        }
        internal static void Bind(UILabel label)
        {
            if (label == null || !Plugin.Active || !LocaleOverride.English || IsEditable(label)) return;
            var original = label.bitmapFont;
            if (original == null || IsOwned(original)) return;
            var font = TryClone(original);
            if (font == original) return;
            Labels[label] = original;
            label.bitmapFont = font;
        }
        internal static void RestoreLabels()
        {
            foreach (var pair in Labels) if (pair.Key != null && IsOwned(pair.Key.bitmapFont)) pair.Key.bitmapFont = pair.Value;
            Labels.Clear();
        }
        internal static void RestoreLabel(UILabel label)
        {
            UIFont original;
            if (label != null && Labels.TryGetValue(label, out original)) { if (IsOwned(label.bitmapFont)) label.bitmapFont = original; Labels.Remove(label); }
        }
        internal static void Dispose()
        {
            RestoreLabels(); Fonts.Clear(); Owned.Clear(); Atlases.Clear();
            if (container != null) UnityEngine.Object.Destroy(container); container = null;
            foreach (var value in Allocated) if (value != null) UnityEngine.Object.Destroy(value); Allocated.Clear();
        }
    }
}
