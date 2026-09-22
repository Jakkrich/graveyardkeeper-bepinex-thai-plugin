"""Package only verified GK1 plugin/font outputs and Thai installation guidance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile

BASE = Path(__file__).resolve().parents[1]
RESOURCES = ('payload.bin', 'glyphs.png', 'metadata.json')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(Path(path).read_bytes())


def verify_paths(expected):
    if not expected:
        raise ValueError('Build manifest has no tracked inputs')
    for name, expected_hash in expected.items():
        path = Path(name)
        if not path.is_absolute() or not path.is_file() or sha(path) != expected_hash:
            raise ValueError('Stale build input: ' + name)


def verify_embedded(resources, expected):
    if set(resources) != {'GKThai.' + name for name in expected}:
        raise ValueError('Embedded resource names differ from expected payload')
    for name, data in expected.items():
        if resources['GKThai.' + name] != data:
            raise ValueError('Embedded resource mismatch: ' + name)


def embedded_resources(path):
    import dnfile
    pe = dnfile.dnPE(str(path))
    try:
        if pe.net is None:
            raise ValueError('Plugin is not a managed assembly')
        entries = [(str(resource.name), resource.data) for resource in pe.net.resources]
        if len({name for name, _ in entries}) != len(entries):
            raise ValueError('Duplicate embedded resources')
        if any(not isinstance(data, bytes) for _, data in entries):
            raise ValueError('Unsupported embedded resource')
        return dict(entries)
    finally:
        pe.close()


def verify_zip(path, members):
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP CRC verification failed')
        if len(archive.namelist()) != len(members) or set(archive.namelist()) != set(members):
            raise ValueError('ZIP members differ from allowlist')
        for name, data in members.items():
            if digest(archive.read(name)) != digest(data):
                raise ValueError('ZIP content mismatch: ' + name)


def write_verified_zip(path, members, force=False):
    path = Path(path)
    if path.exists() and not force:
        raise FileExistsError('Output exists; use --force to replace: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gk1-package-', dir=path.parent) as temporary:
        staging = Path(temporary) / 'package.zip'
        with zipfile.ZipFile(staging, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name in sorted(members):
                info = zipfile.ZipInfo(name, date_time=(2026, 9, 22, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, members[name])
        verify_zip(staging, members)
        if force:
            os.replace(staging, path)
        else:
            # Windows rename fails if another process created the destination meanwhile.
            staging.rename(path)
    verify_zip(path, members)


def package(output, force=False):
    build = BASE / 'build'
    manifest_path = build / 'build-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    verify_paths(manifest['inputs'])
    outputs = manifest['outputs']
    names = ('GKThai.Plugin.dll', 'font.ttf')
    if set(outputs) != set(names):
        raise ValueError('Build outputs must contain exactly plugin DLL and font.ttf')
    files = {name: (build / name).read_bytes() for name in names}
    for name, data in files.items():
        if digest(data) != outputs[name]:
            raise ValueError('Build output hash mismatch: ' + name)
    expected = {name: (BASE / 'payload' / name).read_bytes() for name in RESOURCES}
    verify_embedded(embedded_resources(build / 'GKThai.Plugin.dll'), expected)
    metadata = json.loads(expected['metadata.json'])
    if digest(files['font.ttf']) != metadata['font_sha256']:
        raise ValueError('Font differs from embedded payload source')
    if digest(expected['payload.bin']) != metadata['payload_sha256'] or digest(expected['glyphs.png']) != metadata['glyphs_sha256']:
        raise ValueError('Payload hashes differ from metadata')
    members = {'BepInEx/plugins/GKThai/' + name: data for name, data in files.items()}
    members['INSTALL_TH.md'] = (BASE / 'docs/INSTALL_TH.md').read_bytes()
    release = dict(game='Graveyard Keeper 1', version='0.1.0-candidate', status='candidate; automated pristine runtime QA passed, manual multi-scene QA remains',
                   files={name: digest(data) for name, data in members.items()},
                   baseline_sha256=metadata['baseline_sha256'], font_sha256=metadata['font_sha256'],
                   config=metadata['config'], translation_count=metadata['translation_count'],
                   build_manifest_sha256=sha(manifest_path))
    members['manifest.json'] = (json.dumps(release, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    write_verified_zip(output, members, force)
    print(json.dumps({'output': str(output), 'sha256': sha(output), 'members': sorted(members)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=BASE / 'dist/GKThai-0.1.0-candidate.zip')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    package(args.output, args.force)
