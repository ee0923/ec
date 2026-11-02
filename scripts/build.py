"""Build the upstream workspace, then package with the reviewed size profile."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def build(platform, arch):
    if platform not in ('linux', 'mac', 'win') or arch not in ('x64', 'arm64'):
        raise ValueError('Unknown build target')
    source = ROOT / 'source'
    pnpm = shutil.which('pnpm')
    if pnpm is None:
        raise RuntimeError('pnpm must be installed before building')
    subprocess.run([pnpm, 'exec', 'turbo', 'run', 'build', '--filter=escrcpy'], cwd=source, check=True)
    subprocess.run([pnpm, 'exec', 'electron-builder', '--config', str(ROOT / 'scripts/package-config.mjs'),
                    '--publish=never', '--' + platform, '--' + arch], cwd=source / 'desktop', check=True)


if __name__ == '__main__':
    build(*sys.argv[1:])
