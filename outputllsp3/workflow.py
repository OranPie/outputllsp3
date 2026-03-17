"""CLI workflow utilities: resource discovery, workspace init, doctor, roundtrip.

This module provides the Python-level implementation for each ``outputllsp3``
sub-command, plus pure-Python helpers used by both the CLI and programmatic
callers.

Public API
----------
- ``bundled_paths()``          – paths to all bundled resource files
- ``discover_defaults(base)``  – search upward from *base* for workspace
  resources; falls back to bundled copies
- ``doctor_report(base)``      – structured health-check of a workspace
- ``init_workspace(dir, …)``   – scaffold a new robot programming workspace
- ``roundtrip_llsp3(in, out)`` – copy an llsp3, preserving canonical ordering
- ``docs_index()``             – structured documentation file index
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from importlib import resources
import zipfile

from .metadata import package_info, CHANGELOG


def _resource_path(name: str) -> Path:
    return Path(resources.files('outputllsp3.resources').joinpath(name))


def bundled_paths() -> dict[str, Path]:
    return {
        'template': _resource_path('ok.llsp3'),
        'strings': _resource_path('strings.json'),
        'full': _resource_path('full.llsp3'),
        'block_reference': _resource_path('block_reference.llsp3'),
    }


def discover_defaults(base: str | Path = '.') -> dict[str, Path]:
    base = Path(base).resolve()
    candidates = [base, *base.parents]
    def find(*names: str):
        for d in candidates:
            for n in names:
                p = d / n
                if p.exists():
                    return p
                p2 = d / 'refs' / n
                if p2.exists():
                    return p2
        return None
    bundled = bundled_paths()
    return {
        'template': find('ok.llsp3', 'ok.llsp') or bundled['template'],
        'strings': find('strings.json') or bundled['strings'],
        'full': find('full.llsp3', 'full.llsp') or bundled['full'],
        'block_reference': find('block_reference.llsp3') or bundled['block_reference'],
    }


def doctor_report(base: str | Path = '.') -> dict:
    base = Path(base)
    found = discover_defaults(base)
    package_dirs = [p for p in [base, *base.iterdir()] if p.is_dir()] if base.exists() and base.is_dir() else []
    build_candidates = []
    for p in package_dirs:
        init_py = p / '__init__.py'
        if init_py.exists():
            build_candidates.append(str(p))
    py_files = sorted(str(p) for p in base.glob('*.py')) if base.exists() and base.is_dir() else []
    return {
        'package': package_info(),
        'base': str(base.resolve()) if base.exists() else str(base),
        'template': str(found['template']),
        'strings': str(found['strings']),
        'full': str(found['full']),
        'block_reference': str(found['block_reference']),
        'package_candidates': build_candidates,
        'python_files': py_files,
        'changelog_head': CHANGELOG[0],
    }


def docs_index() -> dict:
    return {
        'updated_at': package_info()['docs_updated_at'],
        'docs': {
            'README': 'README.md',
            'CHANGELOG': 'CHANGELOG.md',
            'PACKAGE_STRUCTURE': 'PACKAGE_STRUCTURE.md',
            'docs/FACADE_GUIDE.md': 'daily facade guide',
            'docs/SPIKE_PYTHON_FACADE.md': 'spike facade reference',
            'docs/WRAPPER_FACADE.md': 'wrapper facade reference',
            'docs/SPIKE_WRAPPER_MAPPING.md': 'spike to wrapper mapping',
            'docs/SCRATCH_MODULES.md': 'scratch module coverage',
            'docs/STRICT_VERIFIED.md': 'strict verified mode',
            'docs/SPIKE_OFFICIAL_SUPPLEMENT.md': 'official spike supplement notes',
        },
    }


def init_workspace(target_dir: str | Path, package_name: str = 'robot_pkg', *, include_resources: bool = True) -> Path:
    target_dir = Path(target_dir)
    pkg = target_dir / package_name
    missions = pkg / 'missions'
    missions.mkdir(parents=True, exist_ok=True)
    (pkg / '__init__.py').write_text(
        "from outputllsp3 import ENUMS\n\n"
        "def build(project, api, ns):\n"
        "    runtime = api.drivebase.install_pid_runtime(\n"
        "        motor_pair=ENUMS.MotorPair.AB,\n"
        "        wheel_diameter_mm=62.4,\n"
        "        left_dir=1,\n"
        "        right_dir=-1,\n"
        "    )\n\n"
        "    api.flow.start(\n"
        "        api.move.set_pair(runtime['motor_pair']),\n"
        "        ns.missions.demo.demo_sequence(api, runtime),\n"
        "    )\n",
        encoding='utf-8'
    )
    (missions / '__init__.py').write_text('', encoding='utf-8')
    (missions / 'demo.py').write_text(
        "def demo_sequence(api, runtime):\n"
        "    return [\n"
        "        api.flow.call(runtime['move_straight_cm'], 30, api.vars.get('SPEED_MID')),\n"
        "        api.wait.ms(200),\n"
        "        api.flow.call(runtime['turn_deg'], 90, api.vars.get('SPEED_TURN')),\n"
        "        api.wait.ms(200),\n"
        "    ]\n",
        encoding='utf-8'
    )
    (target_dir / 'README.outputllsp3.md').write_text(
        "# OutputLLSP3 workspace\n\n"
        "Updated: " + package_info()['docs_updated_at'] + "\n\n"
        "## Daily workflow\n\n"
        "1. Run `outputllsp3 doctor .`\n"
        "2. Edit the package in `" + package_name + "`\n"
        "3. Build with `outputllsp3 build " + package_name + " --out out.llsp3`\n"
        "4. Inspect with `outputllsp3 inspect out.llsp3 --opcodes`\n"
        "5. Check docs with `outputllsp3 docs-index`\n",
        encoding='utf-8'
    )
    if include_resources:
        refs = target_dir / 'refs'
        refs.mkdir(exist_ok=True)
        for key, src in bundled_paths().items():
            shutil.copy2(src, refs / src.name)
    return pkg


def roundtrip_llsp3(in_path: str | Path, out_path: str | Path) -> Path:
    in_path = Path(in_path)
    out_path = Path(out_path)
    with zipfile.ZipFile(in_path, 'r') as zf:
        files = {name: zf.read(name) for name in zf.namelist()}
    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in ['manifest.json', 'icon.svg', 'scratch.sb3']:
            if name in files:
                zf.writestr(name, files[name])
        for name, data in files.items():
            if name not in {'manifest.json', 'icon.svg', 'scratch.sb3'}:
                zf.writestr(name, data)
    return out_path
