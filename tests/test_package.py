import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

PATH = Path(__file__).resolve().parents[1] / 'tools/package.py'
spec = importlib.util.spec_from_file_location('gk1_package', PATH)
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class PackageTests(unittest.TestCase):
    def test_source_edit_invalidates_build(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'Plugin.cs'
            source.write_text('original')
            expected = {str(source): package.sha(source)}
            package.verify_paths(expected)
            source.write_text('changed')
            with self.assertRaisesRegex(ValueError, 'Stale'):
                package.verify_paths(expected)

    def test_embedded_mismatch(self):
        with self.assertRaisesRegex(ValueError, 'Embedded'):
            package.verify_embedded({'GKThai.payload.bin': b'old'}, {'payload.bin': b'new'})

    def test_archive_crc_members_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'release.zip'
            members = {'BepInEx/plugins/GKThai/GKThai.Plugin.dll': b'dll',
                       'BepInEx/plugins/GKThai/font.ttf': b'font'}
            package.write_verified_zip(target, members)
            package.verify_zip(target, members)
            with zipfile.ZipFile(target, 'a') as archive:
                archive.writestr('unexpected-game.dll', b'game')
            with self.assertRaisesRegex(ValueError, 'members'):
                package.verify_zip(target, members)

    def test_archive_modified_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'release.zip'
            package.write_verified_zip(target, {'font.ttf': b'font'})
            with self.assertRaisesRegex(ValueError, 'content'):
                package.verify_zip(target, {'font.ttf': b'other'})

    def test_no_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'release.zip'
            package.write_verified_zip(target, {'a': b'one'})
            original = target.read_bytes()
            with self.assertRaises(FileExistsError):
                package.write_verified_zip(target, {'a': b'two'})
            self.assertEqual(target.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
