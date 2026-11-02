"""Publish a validated platform immediately to this run's shared prerelease."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate(root, identity, env):
    targets = {f'{platform}-{arch}' for platform in ('linux', 'mac', 'win') for arch in ('x64', 'arm64')}
    if identity not in targets:
        raise ValueError('Unknown package target')
    if (not env.get('GH_TOKEN') or env.get('GH_REPO') != env.get('GITHUB_REPOSITORY')
            or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', env.get('GH_REPO', ''))):
        raise ValueError('Current build repository and token are required')
    if (not re.fullmatch(r'[0-9a-f]{40}', env.get('GITHUB_SHA', ''))
            or any(not re.fullmatch(r'[1-9][0-9]*', env.get(key, '')) for key in ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT'))):
        raise ValueError('Current build identity is required')
    lock = json.loads((root / 'sources.lock.json').read_text())
    version = lock['ref'].removeprefix('v')
    if lock['name'] != 'Escrcpy' or not re.fullmatch(r'[0-9][0-9A-Za-z.+-]*', version):
        raise ValueError('Invalid locked release version')
    dist = root / 'dist'
    if dist.is_symlink() or any(p.is_symlink() or not p.is_file() for p in dist.iterdir()):
        raise ValueError('Only regular package files may be published')
    info_name = f'build-info-{identity}.json'
    sums_name = f'SHA256SUMS-{identity}.txt'
    lock_name = f'pnpm-lock-{identity}.yaml'
    info = json.loads((dist / info_name).read_text())
    if (info['source'] != lock or info['platform'] + '-' + info['arch'] != identity
            or info['customization_sha256'] != (root / 'customize.sha256').read_text().strip()
            or info['build_repository'] != env['GH_REPO'] or info['build_commit'] != env['GITHUB_SHA']
            or str(info['run_id']) != env['GITHUB_RUN_ID'] or str(info['run_attempt']) != env['GITHUB_RUN_ATTEMPT']
            or info['dependency_lock_sha256'] != sha(dist / lock_name)
            or info['packaging_config_sha256'] != sha(root / 'scripts/package-config.mjs')):
        raise ValueError('Package provenance does not match this run')
    packages = {}
    for line in (dist / sums_name).read_text().splitlines():
        digest, name = line.split('  ', 1)
        if (not re.fullmatch(r'[0-9a-f]{64}', digest)
                or not re.fullmatch(r'Escrcpy-[A-Za-z0-9.+_-]+', name)
                or name in packages or sha(dist / name) != digest):
            raise ValueError('Invalid or changed package checksum')
        packages[name] = digest
    records = info['files']
    if (not packages or len(records) != len(packages)
            or {p['name']: p['sha256'] for p in records} != packages
            or any(p['size'] <= 0 or (dist / p['name']).stat().st_size != p['size'] for p in records)):
        raise ValueError('Manifest does not match package provenance')
    allowed = set(packages) | {info_name, sums_name, lock_name}
    if {p.name for p in dist.iterdir()} != allowed:
        raise ValueError('Unexpected files in package directory')
    tag = f"escrcpy-v{version}-{env['GITHUB_RUN_ID']}-{env['GITHUB_RUN_ATTEMPT']}"
    marker = f"<!-- escrcpy-build:{env['GH_REPO']}:{env['GITHUB_RUN_ID']}:{env['GITHUB_RUN_ATTEMPT']}:{env['GITHUB_SHA']} -->"
    return tag, marker, [dist / name for name in sorted(allowed)]


def publish(root, identity, env):
    tag, marker, files = validate(root, identity, env)

    def gh(*args):
        return subprocess.run(['gh', 'release', *args, '--repo', env['GH_REPO']],
                              env=env, text=True, capture_output=True)

    for attempt in range(1, 6):
        viewed = gh('view', tag, '--json', 'body')
        ready = False
        if viewed.returncode == 0:
            if marker not in json.loads(viewed.stdout)['body']:
                raise ValueError('Existing release belongs to a different build')
            ready = True
        else:
            created = gh('create', tag, '--target', env['GITHUB_SHA'], '--prerelease', '--title', tag,
                         '--notes', 'Packages are uploaded as each platform completes. '
                         'Checksums, build provenance and dependency locks are included.\n\n' + marker)
            ready = created.returncode == 0
        if ready:
            uploaded = gh('upload', tag, *(str(path) for path in files), '--clobber')
            if uploaded.returncode == 0:
                print('Published ' + identity + ': https://github.com/' + env['GH_REPO'] + '/releases/tag/' + tag)
                return
        if attempt < 5:
            time.sleep(attempt * 5)
    raise RuntimeError('Release publication failed after 5 attempts')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: publish-release.py PLATFORM-ARCH')
    publish(Path(__file__).resolve().parents[1], sys.argv[1], dict(os.environ))
