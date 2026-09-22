"""Build shaped TA8bit Thai NGUI glyphs in a supplied UnityPy environment.

Never installs game files. Unicode work text is encoded to reversible BMP PUA
clusters only at build time; HarfBuzz applies the TTF's mark/mkmk tables.
"""
from pathlib import Path
import hashlib
import json
import re
import struct
import math
import freetype
import uharfbuzz as hb
from PIL import Image
from fontTools.ttLib import TTFont

CONFIG_PATH = Path(__file__).resolve().parents[1] / 'config/gk1-font.json'

def load_config():
    config = json.loads(CONFIG_PATH.read_text(encoding='utf8'))
    if not 0.5 <= config['global_scale'] <= 1.5:
        raise ValueError('global_scale must be between 0.5 and 1.5')
    if config['raster_mode'] not in ('mono', 'smooth', 'sharp') or config['texture_filter'] not in ('point', 'bilinear'):
        raise ValueError('Invalid font rendering mode')
    if config['replace_latin_and_digits'] is not True:
        raise ValueError('Unified font must replace Latin and digits')
    if config.get('digit_spacing_px',0) not in range(4):
        raise ValueError('digit_spacing_px must be 0 through 3')
    if config.get('raster_density', 1) not in (1, 2):
        raise ValueError('Supported raster_density: 1 or 2')
    gap = config.get('min_glyph_gap_px', 1)
    density = config.get('raster_density', 1)
    if isinstance(gap, bool) or not isinstance(gap, (int, float)) or not 0.1 <= gap <= 3:
        raise ValueError('min_glyph_gap_px must be 0.1–3')
    if density == 1 and not float(gap).is_integer():
        raise ValueError('Fractional gaps require HD2')
    if not math.isclose(gap*10, round(gap*10), abs_tol=1e-8):
        raise ValueError('HD2 gap precision is 0.1 logical pixels')
    return config

FONT_IDS = [151300, 151301, 151302, 151312, 151313, 151314, 155170]
MARKS = '\u0e31\u0e34-\u0e3a\u0e47-\u0e4e'
CLUSTER = re.compile('[\u0e01-\u0e2e\u0e30-\u0e45\u0e50-\u0e5b][' + MARKS + '\u0e33]*|[\u0e00-\u0e7f]')


def make_mapping(texts):
    clusters = sorted({m.group() for text in texts for m in CLUSTER.finditer(text) if len(m.group()) > 1})
    if len(clusters) > 6400:
        raise ValueError('Thai cluster count exceeds BMP PUA capacity')
    if any(any('\ue000' <= c <= '\uf8ff' for c in text) for text in texts):
        raise ValueError('Input already uses PUA; refusing ambiguous encoding')
    return {s: chr(0xe000 + i) for i, s in enumerate(clusters)}


def encode(text, mapping):
    return CLUSTER.sub(lambda m: mapping.get(m.group(), m.group()), text)


def decode(text, mapping):
    reverse = {v: k for k, v in mapping.items()}
    return ''.join(reverse.get(c, c) for c in text)


def select_font_characters(cmap, texts):
    """Keep runtime text plus Latin/Thai coverage without importing huge unused scripts."""
    required = {ord(char) for text in texts for char in text if not char.isspace()}
    missing = sorted(required - set(cmap))
    if missing:
        raise ValueError('Configured font misses runtime codepoints: ' + ', '.join(f'U+{code:04X}' for code in missing))
    selected = {
        code for code in cmap
        if 0x20 <= code <= 0x024f or 0x0e00 <= code <= 0x0e7f or code in required
    }
    return [chr(code) for code in sorted(selected) if not 0xe000 <= code <= 0xf8ff]


def _string(b, p):
    n = struct.unpack_from('<i', b, p)[0]
    return b[p+4:p+4+n].decode('utf8'), (p+4+n+3) & ~3


def _put_string(s):
    b = s.encode('utf8')
    return struct.pack('<i', len(b)) + b + b'\0' * (-len(b) % 4)


def parse_font(b):
    size, base, width, height = struct.unpack_from('<4i', b, 60)
    name, p = _string(b, 76)
    count = struct.unpack_from('<i', b, p)[0]
    p += 4
    glyphs = []
    for _ in range(count):
        start = p
        g = struct.unpack_from('<10i', b, p)
        p += 40 + 4 * g[9]
        glyphs.append((g, b[start:p]))
    assert p + 48 <= len(b)
    return dict(size=size, base=base, width=width, height=height, name=name, glyphs=glyphs, tail=b[p:])


def parse_atlas(b):
    count = struct.unpack_from('<i', b, 44)[0]
    p, sprites = 48, {}
    for _ in range(count):
        name, p = _string(b, p)
        sprites[name] = (p, struct.unpack_from('<12i', b, p))
        p += 48
    assert len(b) - p == 24
    return sprites


class Shaper:
    def __init__(self, path, size, mode='smooth'):
        self.mode = mode
        self.ft = freetype.Face(str(path))
        self.ft.set_pixel_sizes(0, size)
        self.hb = hb.Font(hb.Face(Path(path).read_bytes()))
        self.hb.scale = (size * 64, size * 64)
        hb.ot_font_set_funcs(self.hb)

    def render(self, text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, {'mark': True, 'mkmk': True})
        parts, pen = [], 0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            if info.codepoint == 0:
                raise ValueError('Missing TTF glyph in ' + repr(text))
            flags = freetype.FT_LOAD_RENDER | (freetype.FT_LOAD_TARGET_MONO if self.mode == 'mono' else freetype.FT_LOAD_TARGET_NORMAL)
            self.ft.load_glyph(info.codepoint, flags)
            slot = self.ft.glyph
            bm = slot.bitmap
            x = round((pen + pos.x_offset) / 64) + slot.bitmap_left
            y = -round(pos.y_offset / 64) - slot.bitmap_top
            if bm.width and bm.rows:
                pixel_mode = '1' if bm.pixel_mode == freetype.FT_PIXEL_MODE_MONO else 'L'
                alpha = Image.frombytes(pixel_mode, (bm.width, bm.rows), bytes(bm.buffer), 'raw', pixel_mode, bm.pitch).convert('L')
                parts.append((x, y, alpha))
            pen += pos.x_advance
        if not parts:
            return Image.new('RGBA', (1, 1)), 0, 0, round(pen / 64)
        left, top = min(p[0] for p in parts), min(p[1] for p in parts)
        right = max(x + a.width for x, y, a in parts)
        bottom = max(y + a.height for x, y, a in parts)
        canvas = Image.new('RGBA', (right-left, bottom-top))
        for x, y, a in parts:
            tile = Image.new('RGBA', a.size, 'white')
            tile.putalpha(a)
            canvas.alpha_composite(tile, (x-left, y-top))
        if self.mode == 'sharp':
            # Preserve NORMAL hinting, then remove translucent edge coverage.
            # 96 keeps small Thai marks that disappear with a 128 cutoff.
            alpha = canvas.getchannel('A')
            # Tiny punctuation can have no pixel reaching the usual cutoff.
            cutoff = min(96, alpha.getextrema()[1])
            canvas.putalpha(alpha.point(lambda a: 255 if a > 0 and a >= cutoff else 0))
        return canvas, left, top, round(pen / 64)


def build_font(env, texts, font_path, diagnostics_dir=None):
    """Mutate only in-memory resources assets; return reversible cluster mapping."""
    texts = list(texts)
    config = load_config()
    density = config.get('raster_density', 1)
    font_hash = hashlib.sha256(Path(font_path).read_bytes()).hexdigest()
    if font_hash != config['font_sha256']:
        raise ValueError('Font is not the configured user original')
    mapping = make_mapping(texts)
    for text in texts:
        assert decode(encode(text, mapping), mapping) == text
    objs = {o.path_id: o for o in env.objects if o.assets_file.name.endswith('resources.assets')}
    atlas = bytearray(objs[151315].get_raw_data())
    sprites = parse_atlas(atlas)
    texture = objs[5970].read()
    original = texture.image.convert('RGBA')
    if original.size != (1024, 1024):
        raise ValueError('Expected pristine GK1 gui_atlas1024; refusing repeated patch')
    canvas = Image.new('RGBA', (4096, 4096))
    canvas.paste(original, (0, 0))
    available = [{g[0] for g, b in parse_font(objs[fid].get_raw_data())['glyphs']} for fid in FONT_IDS]
    with TTFont(font_path) as ttf:
        cmap = ttf.getBestCmap()
    # Include runtime glyphs plus broad Latin/Thai coverage for dynamic labels. Large
    # desktop fonts can contain thousands of unrelated scripts that overflow NGUI's
    # fixed 1024x1024 panel.
    chars = select_font_characters(cmap, texts)
    entries = [(ord(c), c) for c in chars] + [(ord(pua), cluster) for cluster, pua in mapping.items()]
    report = {'mapping_count': len(mapping), 'unicode_count': len(chars), 'fonts': [], 'ttf_sha256': font_hash, 'config': config}
    replacements = {}
    for i, fid in enumerate(FONT_IDS):
        raw = objs[fid].get_raw_data()
        f = parse_font(raw)
        offset, spr = sprites[f['name']]
        sx, sy, sw, sh = spr[:4]
        if any(spr[4:]):
            raise ValueError('Unexpected padding in ' + f['name'])
        px, py = 1024 + (i % 3) * 1024, (i // 3) * 1024
        baseline = next((g[6]+g[4] for g, b in f['glyphs'] if g[0] == ord('H')), f['size']-2)
        # Keep layout and icon metadata; replace every text glyph from one source.
        logical_size = max(1, round(f['size'] * config['global_scale']))
        raster_size = logical_size * density
        shaper = Shaper(font_path, raster_size, config['raster_mode'])
        logical_shaper = Shaper(font_path, logical_size, 'sharp')
        x, y, row_h = 2, 2, 0
        glyph_bytes = []
        for code, cluster in entries:
            tile, left, top, advance = shaper.render(cluster)
            if density > 1:
                low, low_left, _, low_advance = logical_shaper.render(cluster)
                if 48 <= code <= 57:
                    low_advance += config.get('digit_spacing_px', 0)
                if low_advance > 0 and low.getchannel('A').getbbox():
                    low_advance = max(low_advance, max(0, low_left) + low.width + config.get('min_glyph_gap_px', 1))
                advance = low_advance * density
            if 48 <= code <= 57:
                advance += config.get('digit_spacing_px',0) if density == 1 else 0
            # Integer bitmap bounds may exceed the rounded, unhinted HB advance.
            # Keep complete shaped clusters together; standalone marks stay zero-width.
            if advance > 0 and tile.getchannel('A').getbbox():
                left = max(0, left)
                advance = max(advance, left + tile.width + density * config.get('min_glyph_gap_px', 1))
            if x + tile.width + 2 > 1024:
                x, y, row_h = 2, y + row_h + 2, 0
            if y + tile.height + 2 > 1024:
                raise ValueError('Font panel overflow: ' + f['name'])
            canvas.alpha_composite(tile, (px+x, py+y))
            # BMGlyph advances are integers. Encode the fractional correction in
            # unused high channel bits; the scoped runtime patch strips it before rendering.
            stored_advance = math.ceil(round(advance, 6))
            correction = round((stored_advance-advance)*100)
            assert 0 <= correction < 100
            channel = 15 | (correction << 4)
            assert density == 2 or correction == 0
            glyph_bytes.append(struct.pack('<10i', code, x, y, tile.width, tile.height, left, baseline*density+top, stored_advance, channel, 0))
            x += tile.width + 2
            row_h = max(row_h, tile.height)
        new = bytearray(raw[:60])
        struct.pack_into('<4f', new, 44, px/4096, 1-(py+1024)/4096, 0.25, 0.25)
        new.extend(struct.pack('<4i', f['size'], f['base'], 1024, 1024))
        sprite_name = ('gk1_hd2_' if density == 2 else '') + f['name']
        new.extend(_put_string(sprite_name))
        new.extend(struct.pack('<i', len(glyph_bytes)))
        new.extend(b''.join(glyph_bytes))
        new.extend(f['tail'])
        parsed = parse_font(new)
        assert parsed['tail'] == f['tail']
        assert len(parsed['glyphs']) == len(entries)
        required = {ord(c) for text in texts for c in encode(text, mapping) if not c.isspace()}
        assert required <= {g[0] for g, b in parsed['glyphs']}, 'Font coverage is incomplete'
        objs[fid].set_raw_data(bytes(new))
        struct.pack_into('<12i', atlas, offset, px, py, 1024, 1024, *([0]*8))
        replacements[f['name']] = sprite_name
        report['fonts'].append({'id': fid, 'name': sprite_name, 'size': f['size'], 'raster_size': raster_size, 'raster_density': density, 'baseline': baseline, 'glyph_count': len(glyph_bytes), 'symbols_preserved': True, 'all_text_replaced': True})
    assert canvas.crop((0, 0, 1024, 1024)).tobytes() == original.tobytes()
    # UIAtlas calculates UVs against the new texture size; sprite pixel coordinates
    # for icons and original CJK fonts are deliberately retained byte for byte.
    updated = parse_atlas(atlas)
    changed_names = set(replacements)
    assert all(v == updated[k] for k, v in sprites.items() if k not in changed_names)
    if density == 2:
        atlas = (atlas[:48] + b''.join(_put_string(replacements.get(name, name)) + struct.pack('<12i', *data)
                 for name, (_, data) in updated.items()) + atlas[-24:])
    objs[151315].set_raw_data(bytes(atlas))
    texture.set_image(canvas)
    texture.m_TextureSettings.m_FilterMode = 0 if config['texture_filter']=='point' else 1
    texture.save()
    if diagnostics_dir:
        out = Path(diagnostics_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out/'cluster-map.json').write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf8')
        (out/'build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
        # Draw the serialized integer glyph layout, not whole-string HB shaping.
        preview = Image.new('RGBA', (1000, 270), '#222222')
        glyphs = {g[0]: g for g, b in parsed['glyphs']}
        samples = ['Game by Lazy Bear Games  English 1920x1080',
                   'ระดับเสียงหลัก เสียงเอฟเฟกต์ ความละเอียด',
                   'ผู้ดูแลสุสาน น้ำ ปู่ ปี่ กุ้ง ซื้อ เก็บเกี่ยว',
                   'Producer Programmer 0123456789 +57 -20']
        for row, sample in enumerate(samples):
            line = Image.new('RGBA', (490*density, 30*density))
            pen = 0
            for char in encode(sample, mapping):
                g = glyphs[ord(char)]
                tile = canvas.crop((px+g[1], py+g[2], px+g[1]+g[3], py+g[2]+g[4]))
                line.alpha_composite(tile, (round(pen+g[5]), g[6]+4*density))
                pen += g[7]-(g[8] >> 4)/100
            preview.alpha_composite(line.resize((980,60),Image.Resampling.NEAREST), (10, row*65))
        preview.save(out/'thai-shaping-preview.png')
    return mapping
