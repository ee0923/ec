"""Use a native runner per architecture, retaining every upstream package target."""
import json
import sys

TARGETS = [
    {'id': 'linux-x64', 'os': 'ubuntu-24.04', 'platform': 'linux', 'arch': 'x64'},
    {'id': 'linux-arm64', 'os': 'ubuntu-24.04-arm', 'platform': 'linux', 'arch': 'arm64'},
    {'id': 'mac-x64', 'os': 'macos-15-intel', 'platform': 'mac', 'arch': 'x64'},
    {'id': 'mac-arm64', 'os': 'macos-15', 'platform': 'mac', 'arch': 'arm64'},
    {'id': 'win-x64', 'os': 'windows-2025', 'platform': 'win', 'arch': 'x64'},
    {'id': 'win-arm64', 'os': 'windows-11-arm', 'platform': 'win', 'arch': 'arm64'},
]


def select(target):
    if target not in ('all', 'linux', 'mac', 'win'):
        raise ValueError('Unknown build target')
    return {'include': [item for item in TARGETS if target in ('all', item['platform'])]}


if __name__ == '__main__':
    print('matrix=' + json.dumps(select(sys.argv[1] if len(sys.argv) > 1 else 'all'), separators=(',', ':')))
