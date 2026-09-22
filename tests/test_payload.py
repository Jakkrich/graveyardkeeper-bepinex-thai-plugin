import importlib.util
import struct
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'tools/build_payload.py'
spec = importlib.util.spec_from_file_location('payload_builder', PATH)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PayloadTests(unittest.TestCase):
    def test_unicode_binaryreader_string(self):
        value = 'น้ำ' * 100
        encoded = builder.write_string(value)
        self.assertEqual(builder.read_string(encoded, 0), (value, len(encoded)))

    def test_binary_font_and_kerning_roundtrip(self):
        fonts = [dict(name='main', size=16, base=14, panel_x=1024, panel_y=0,
                      glyphs=[((65, 2, 2, 8, 14, 0, 0, 10, 15), [(66, -1)])])]
        translations, mapping = [('key', 'น้ำ')], {'น้ำ': '\ue000'}
        encoded = builder.encode_payload(translations, mapping, fonts)
        self.assertEqual(builder.decode_payload(encoded), (translations, mapping, fonts))
        with self.assertRaisesRegex(ValueError, 'Trailing'):
            builder.decode_payload(encoded + b'x')

    def test_generated_payload_contract(self):
        folder = PATH.parents[1] / 'payload'
        if not (folder / 'payload.bin').exists():
            self.skipTest('Build integration fixture first')
        from PIL import Image
        translations, mapping, fonts = builder.decode_payload((folder / 'payload.bin').read_bytes())
        self.assertEqual(len(translations), 10961)
        self.assertEqual(len(fonts), 7)
        self.assertTrue(all(not any('\ue000' <= c <= '\uf8ff' for c in text) for _, text in translations))
        self.assertTrue(all(not font['name'].startswith('gk1_hd2_') for font in fonts))
        with Image.open(folder / 'glyphs.png') as image:
            self.assertEqual(image.size, (4096, 4096))
            self.assertIsNone(image.crop((0, 0, 1024, 1024)).getbbox())

    def test_duplicate_keys(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            builder.validate_rows([{'key':'a','value':'Hi'}] * 2, [])

    def test_source_drift(self):
        with self.assertRaisesRegex(ValueError, 'Source modified'):
            builder.validate_rows([{'key':'a','value':'Hi'}], [{'key':'a','source':'Bye','translation':'ไป'}])

    def test_missing_translation(self):
        with self.assertRaisesRegex(ValueError, 'Missing translation'):
            builder.validate_rows([{'key':'a','value':'Hi'}], [{'key':'a','source':'Hi','translation':''}])

    def test_tokens(self):
        with self.assertRaisesRegex(ValueError, 'tokens'):
            builder.validate_rows([{'key':'a','value':'Hi %1'}], [{'key':'a','source':'Hi %1','translation':'สวัสดี'}])

    def test_pua_collision(self):
        with self.assertRaisesRegex(ValueError, 'PUA'):
            builder.font_tools().make_mapping(['\ue000'])

    def test_cluster_roundtrip(self):
        font = builder.font_tools()
        text = 'น้ำ ปู่ ปี่ กุ้ง ซื้อ เก็บเกี่ยว 0123456789'
        mapping = font.make_mapping([text])
        self.assertEqual(font.decode(font.encode(text, mapping), mapping), text)

    def test_mapping_capacity(self):
        with self.assertRaisesRegex(ValueError, 'capacity'):
            builder.font_tools().make_mapping(['ก' + '่' * i for i in range(1, 6402)])

    def test_unknown_glyph(self):
        with self.assertRaisesRegex(ValueError, 'codepoints'):
            builder.font_tools().select_font_characters({65:'A'}, ['น้ำ'])

    def test_panel_overflow(self):
        with self.assertRaisesRegex(ValueError, 'panel'):
            builder.validate_glyph((65, 1020, 0, 20, 10, 0, 0, 10, 15))

    def test_unknown_baseline(self):
        with self.assertRaisesRegex(ValueError, 'baseline'):
            builder.require_hash('bad', builder.RESOURCE_HASH, 'baseline')

    def test_empty_source_preserved(self):
        rows = builder.validate_rows([{'key':'a','value':' '}], [{'key':'a','source':' ','translation':' '}])
        self.assertEqual(rows[0]['source'], ' ')


if __name__ == '__main__':
    unittest.main()
