"""Prepare a separate tested checkout. Never mutate or restart a running trader."""
import os
from pathlib import Path
import re
import subprocess
import sys


def prepare(root, version):
    if not re.fullmatch(r'v\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+)?', version):
        raise ValueError('Use an exact release tag, for example v0.2.0-beta.1')
    target = root / 'releases' / version
    if target.exists():
        raise ValueError('Release directory already exists; preserve it and inspect before retrying')
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    subprocess.run(['git', 'clone', '--depth', '1', '--branch', version,
                    'https://github.com/worldclasstom/prop-firm-agent.git', str(target)], check=True)
    subprocess.run([sys.executable, '-m', 'venv', str(target / '.venv')], check=True)
    python = str(target / '.venv' / 'bin' / 'python')
    env = dict(os.environ)
    env.pop('PROPR_API_KEY', None)
    env['PROPFIRM_HOME'] = str(target / '.test-state')
    subprocess.run([python, '-m', 'pip', 'install', str(target)], env=env, check=True)
    subprocess.run([python, '-m', 'unittest', 'discover', '-s', str(target / 'tests'), '-v'],
                   cwd=target, env=env, check=True)
    return target
