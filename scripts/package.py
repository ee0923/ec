"""Collect only this job's complete package set and record source/patch/dependency hashes."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def collect(root, platform, arch):
    if platform not in ('linux', 'mac', 'win') or arch not in ('x64', 'arm64'):
        raise ValueError('Unknown package target')
    source = root / 'source'
    version = json.loads((source / 'desktop/package.json').read_text())['version']
    prefix = f'Escrcpy-{version}-{platform}'
    # electron-builder 26.15.3 maps architecture names separately for each format.
    appimage_arch = {'x64': 'x86_64', 'arm64': 'arm64'}[arch]
    deb_arch = {'x64': 'amd64', 'arm64': 'arm64'}[arch]
    flatpak_arch = {'x64': 'x86_64', 'arm64': 'aarch64'}[arch]
    suffixes = {
        'linux': [f'-{appimage_arch}.AppImage', f'-{deb_arch}.deb', f'-{flatpak_arch}.flatpak'],
        'mac': [f'-{arch}.dmg', f'-{arch}.zip'],
        'win': [f'-setup-{arch}.exe', f'-portable-{arch}.exe', f'-{arch}.zip'],
    }[platform]
    packages = [source / 'desktop/dist-release' / (prefix + suffix) for suffix in suffixes]
    if not all(path.is_file() and not path.is_symlink() and path.stat().st_size for path in packages):
        found = sorted(p.name for p in (source / 'desktop/dist-release').glob('*') if p.is_file())
        raise ValueError('Missing or empty upstream package set: ' + ', '.join(str(p) for p in packages)
                         + '; available files: ' + ', '.join(found))
    destination = root / 'dist'
    destination.mkdir(exist_ok=False)
    files = []
    for path in packages:
        shutil.copyfile(path, destination / path.name)
        files.append({'name': path.name, 'size': path.stat().st_size, 'sha256': sha(path)})
    shutil.copyfile(source / 'pnpm-lock.yaml', destination / f'pnpm-lock-{platform}-{arch}.yaml')
    info = {
        'source': json.loads((root / 'sources.lock.json').read_text()),
        'customization_sha256': (root / 'customize.sha256').read_text().strip(),
        'dependency_lock_sha256': sha(source / 'pnpm-lock.yaml'),
        'packaging_config_sha256': sha(root / 'scripts/package-config.mjs'),
        'platform': platform, 'arch': arch,
        'build_repository': os.environ.get('GITHUB_REPOSITORY'),
        'build_commit': os.environ.get('GITHUB_SHA'),
        'run_id': os.environ.get('GITHUB_RUN_ID'), 'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
        'signing': 'Upstream defaults; no release certificate or notarization configured',
        'files': files,
    }
    (destination / f'build-info-{platform}-{arch}.json').write_text(json.dumps(info, indent=2) + '\n')
    (destination / f'SHA256SUMS-{platform}-{arch}.txt').write_text(
        ''.join(f"{item['sha256']}  {item['name']}\n" for item in files))
    return info


if __name__ == '__main__':
    collect(ROOT, sys.argv[1], sys.argv[2])
