"""Build a glyph-only BepInEx payload; never serialize or install game assets."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'tools'))
RESOURCE_HASH = '215c7981901a4b72d5db717666ba47ad3cc032527c95f58dc39d8af1293a69ca'
FIRSTPASS_HASH = '9dc6def3b7715dd27eeb168ddc0af47e31c6f38d3fbee24bf592899392026498'
ASSEMBLY_HASH = 'e72e4270e4b88dd0a87ca23c9cf1750aec4c4a0fedb40b6d2dae7902fc9c7fd8'


def font_tools():
    import gk1_font
    return gk1_font


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_hash(actual, expected, label):
    if actual != expected:
        raise ValueError(label + ' hash mismatch; unknown or modified input')


def read_csv(path, allow_bom=False):
    data = Path(path).read_bytes()
    if data.startswith(b'\xef\xbb\xbf') and not allow_bom:
        raise ValueError('CSV must be UTF-8 without BOM: ' + str(path))
    with Path(path).open(encoding='utf-8-sig' if allow_bom else 'utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


class UnityReader:
    def __init__(self, data):
        self.data = data
        self.pos = 28

    def integer(self):
        if self.pos + 4 > len(self.data):
            raise ValueError('Unexpected end of locale asset')
        value = struct.unpack_from('<i', self.data, self.pos)[0]
        self.pos += 4
        return value

    def string(self):
        size = self.integer()
        if size < 0 or self.pos + size > len(self.data):
            raise ValueError('Invalid locale string size')
        value = self.data[self.pos:self.pos + size].decode('utf-8')
        self.pos = (self.pos + size + 3) & ~3
        return value

    def strings(self):
        count = self.integer()
        if count < 0 or count > 100000:
            raise ValueError('Invalid locale array size')
        return [self.string() for _ in range(count)]


def decode_locale(data):
    reader = UnityReader(data)
    name, language = reader.string(), reader.string()
    keys, texts, aliases1, aliases2 = [reader.strings() for _ in range(4)]
    if reader.pos != len(data) or name != 'lng_' + language:
        raise ValueError('Unrecognized GK1 locale layout')
    if len(keys) != len(texts) or len(aliases1) != len(aliases2) or len(keys) != len(set(keys)):
        raise ValueError('Invalid GK1 locale arrays')
    return dict(name=name, language=language, keys=keys, texts=texts,
                aliases1=aliases1, aliases2=aliases2)


def validate_rows(source, master):
    from gk1_runtime_text import check_text
    for rows in (source, master):
        keys = [row['key'] for row in rows]
        if len(keys) != len(set(keys)):
            raise ValueError('Duplicate translation keys')
    if [row['key'] for row in source] != [row['key'] for row in master]:
        raise ValueError('Keys/order differ from source')
    for original, row in zip(source, master):
        if row['source'] != original['value']:
            raise ValueError('Source modified: ' + row['key'])
        try:
            check_text(row['source'], row['translation'])
        except ValueError as exc:
            raise ValueError(row['key'] + ': ' + str(exc)) from exc
    return master


def write_string(value):
    value = value.encode('utf-8')
    length = len(value)
    prefix = bytearray()
    while length >= 128:
        prefix.append((length & 127) | 128)
        length >>= 7
    prefix.append(length)
    return bytes(prefix) + value


def read_string(data, pos):
    length = 0
    for shift in range(0, 35, 7):
        value = data[pos]
        pos += 1
        length |= (value & 127) << shift
        if value < 128:
            end = pos + length
            if end > len(data):
                raise ValueError('Truncated string')
            return data[pos:end].decode('utf-8'), end
    raise ValueError('Invalid 7bit string length')


def validate_glyph(glyph):
    _, x, y, width, height, _, _, _, _ = glyph
    if min(x, y, width, height) < 0 or x + width > 1024 or y + height > 1024:
        raise ValueError('Glyph exceeds 1024 panel')


def encode_payload(translations, mapping, fonts):
    out = bytearray(b'GK1P1')
    def number(value):
        out.extend(struct.pack('<i', value))
    number(len(translations))
    for key, value in translations:
        out.extend(write_string(key))
        out.extend(write_string(value))
    number(len(mapping))
    for cluster, pua in mapping.items():
        out.extend(write_string(cluster))
        out.extend(write_string(pua))
    number(len(fonts))
    for font in fonts:
        out.extend(write_string(font['name']))
        for field in ('size', 'base', 'panel_x', 'panel_y'):
            number(font[field])
        number(len(font['glyphs']))
        for glyph, kernings in font['glyphs']:
            validate_glyph(glyph)
            out.extend(struct.pack('<9i', *glyph))
            number(len(kernings))
            for previous, amount in kernings:
                out.extend(struct.pack('<2i', previous, amount))
    return bytes(out)


def decode_payload(data):
    if data[:5] != b'GK1P1':
        raise ValueError('Wrong payload magic')
    pos = 5
    def number():
        nonlocal pos
        value = struct.unpack_from('<i', data, pos)[0]
        pos += 4
        return value
    def string():
        nonlocal pos
        value, pos = read_string(data, pos)
        return value
    translations = [(string(), string()) for _ in range(number())]
    mapping = {string(): string() for _ in range(number())}
    fonts = []
    for _ in range(number()):
        font = {'name': string()}
        for field in ('size', 'base', 'panel_x', 'panel_y'):
            font[field] = number()
        glyphs = []
        for _ in range(number()):
            glyph = tuple(number() for _ in range(9))
            kerning = [(number(), number()) for _ in range(number())]
            glyphs.append((glyph, kerning))
        font['glyphs'] = glyphs
        fonts.append(font)
    if pos != len(data):
        raise ValueError('Trailing payload data')
    return translations, mapping, fonts


def build(args):
    import UnityPy
    from gk1_runtime_text import prepare_runtime_texts
    font = font_tools()
    require_hash(sha(args.pristine), RESOURCE_HASH, 'Pristine resources baseline')
    references = {
        'resources.assets': RESOURCE_HASH,
        'Assembly-CSharp-firstpass.dll': FIRSTPASS_HASH,
        'Assembly-CSharp.dll': ASSEMBLY_HASH,
    }
    firstpass = args.game_root / 'Graveyard Keeper_Data/Managed/Assembly-CSharp-firstpass.dll'
    assembly = args.game_root / 'Graveyard Keeper_Data/Managed/Assembly-CSharp.dll'
    require_hash(sha(firstpass), FIRSTPASS_HASH, 'Firstpass baseline')
    require_hash(sha(assembly), ASSEMBLY_HASH, 'Assembly baseline')
    watched = [args.master, args.font, args.config, args.pristine, firstpass, assembly]
    before = {str(path): sha(path) for path in watched}
    env = UnityPy.load(str(args.pristine))
    env.path = str(args.game_root / 'Graveyard Keeper_Data')
    objects = {obj.path_id: obj for obj in env.objects}
    locale = decode_locale(objects[150186].get_raw_data())
    source = [dict(key=key, value=value) for key, value in zip(locale['keys'], locale['texts'])]
    rows = validate_rows(source, read_csv(args.master, allow_bom=True))
    texts = prepare_runtime_texts(rows)
    original_config = font.CONFIG_PATH
    try:
        font.CONFIG_PATH = args.config
        config = font.load_config()
        mapping = font.build_font(env, texts, args.font)
    finally:
        font.CONFIG_PATH = original_config
    # UnityPy get_raw_data/read access the original reader even after set_raw_data.
    # Reopen the modified serialized bytes in memory; never write assets to disk.
    generated = UnityPy.load(env.file.save())
    generated.path = str(args.game_root / 'Graveyard Keeper_Data')
    objects = {obj.path_id: obj for obj in generated.objects}
    if not all(font.decode(font.encode(text, mapping), mapping) == text for text in texts):
        raise ValueError('Cluster roundtrip failed')
    fonts = []
    golden = {}
    samples = ['น้ำ', 'ปู่', 'ปี่', 'กุ้ง', 'ซื้อ', 'เก็บเกี่ยว', '0123456789']
    for index, fid in enumerate(font.FONT_IDS):
        parsed = font.parse_font(objects[fid].get_raw_data())
        glyphs = []
        for glyph, raw in parsed['glyphs']:
            if glyph[9] % 2:
                raise ValueError('Odd kerning int count')
            ints = struct.unpack_from('<' + str(glyph[9]) + 'i', raw, 40)
            glyphs.append((glyph[:9], list(zip(ints[::2], ints[1::2]))))
        name = parsed['name'].removeprefix('gk1_hd2_')
        fonts.append(dict(name=name, size=parsed['size'], base=parsed['base'],
                          panel_x=1024 + index % 3 * 1024, panel_y=index // 3 * 1024, glyphs=glyphs))
        by_index = {g[0]: g for g, _ in glyphs}
        golden[name] = {sample: [by_index[ord(char)] for char in font.encode(sample, mapping)] for sample in samples}
    translations = list(zip(locale['keys'], texts))
    payload = encode_payload(translations, mapping, fonts)
    if decode_payload(payload) != (translations, mapping, fonts):
        raise ValueError('Binary payload roundtrip failed')
    image = objects[5970].read().image.convert('RGBA')
    if image.size != (4096, 4096):
        raise ValueError('Unexpected generated atlas dimensions')
    image.paste((0, 0, 0, 0), (0, 0, 1024, 1024))
    if image.crop((0, 0, 1024, 1024)).getbbox() is not None:
        raise ValueError('Original game artwork leaked into glyph payload')
    for path in watched:
        require_hash(sha(path), before[str(path)], 'Input changed during build: ' + str(path))
    source_digest = hashlib.sha256(json.dumps(source, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()
    metadata = dict(schema=1, game='Graveyard Keeper 1', unity='2020.3.17f1',
                    translation_count=len(rows), mapping_count=len(mapping), font_count=len(fonts),
                    font_sha256=sha(args.font), source_sha256=source_digest, master_sha256=sha(args.master),
                    config_sha256=sha(args.config), config=config, baseline_sha256=references,
                    input_sha256=before, payload_sha256=hashlib.sha256(payload).hexdigest(),
                    format='GK1P1; LE int32; BinaryReader UTF8 strings; per-glyph kerning pair count',
                    golden_metrics=golden)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gk1-payload-', dir=args.output.parent) as temporary:
        staging = Path(temporary)
        (staging / 'payload.bin').write_bytes(payload)
        image.save(staging / 'glyphs.png')
        (staging / 'font.ttf').write_bytes(args.font.read_bytes())
        metadata['glyphs_sha256'] = sha(staging / 'glyphs.png')
        (staging / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        args.output.mkdir(parents=True, exist_ok=True)
        for name in ('payload.bin', 'glyphs.png', 'font.ttf', 'metadata.json'):
            os.replace(staging / name, args.output / name)
    print(json.dumps({key: metadata[key] for key in ('translation_count', 'mapping_count', 'font_count', 'payload_sha256')}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root', type=Path, default=BASE.parents[1])
    for name, default in {
        'master': BASE / 'translations/th.csv',
        'font': BASE / '.local/font.ttf',
        'config': BASE / 'config/gk1-font.json',
        'pristine': None,
        'output': BASE / 'payload',
    }.items():
        parser.add_argument('--' + name, type=Path, default=default)
    args = parser.parse_args()
    args.game_root = args.game_root.resolve()
    if args.pristine is None:
        args.pristine = args.game_root / 'Graveyard Keeper_Data/resources.assets'
    build(args)


if __name__ == '__main__':
    main()
