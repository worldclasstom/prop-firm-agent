"""Derive the release tag from the package version; used by .github/workflows/release.yml.

Prints the tag and whether it is a pre-release. Exits non-zero when pyproject.toml
and propfirm/__init__.py disagree, so a half-bumped version never ships.
"""
import json
import re
import sys
import tomllib
from pathlib import Path

PATTERN = re.compile(r'^(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?$')
LABELS = {'a': 'alpha', 'b': 'beta', 'rc': 'rc'}


def tag_for(version: str) -> tuple[str, bool]:
    """PEP 440 release version to the repository's tag form: 0.2.0b9 -> v0.2.0-beta.9."""
    match = PATTERN.match(version)
    if not match:
        raise ValueError('Unsupported version form: ' + version)
    major, minor, patch, label, number = match.groups()
    tag = 'v%s.%s.%s' % (major, minor, patch)
    if label:
        tag += '-%s.%s' % (LABELS[label], number)
    return tag, label is not None


def repository_version(root: Path) -> str:
    project = tomllib.loads((root / 'pyproject.toml').read_text())['project']['version']
    module = (root / 'propfirm' / '__init__.py').read_text()
    found = re.search(r'^__version__\s*=\s*"([^"]+)"', module, re.MULTILINE)
    if not found or found.group(1) != project:
        raise ValueError('pyproject.toml version %s does not match propfirm.__version__' % project)
    return project


def main(argv):
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[1]
    tag, prerelease = tag_for(repository_version(root))
    print(json.dumps({'tag': tag, 'prerelease': prerelease}))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
