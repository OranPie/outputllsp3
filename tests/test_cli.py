"""Smoke tests for CLI sub-commands."""
import json
import os
import tempfile
from pathlib import Path


def _run_cli(*args):
    """Run outputllsp3 CLI with the given args and return (rc, stdout)."""
    import io
    import sys
    from outputllsp3.cli import main

    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    rc = 1
    try:
        rc = main(list(args))
    except SystemExit as e:
        rc = int(e.code) if e.code is not None else 0
    finally:
        sys.stdout = old_stdout
    return rc, buf.getvalue()


def test_cli_version():
    rc, out = _run_cli('version')
    assert rc == 0
    data = json.loads(out)
    assert data['name'] == 'outputllsp3'
    assert 'version' in data


def test_cli_features():
    rc, out = _run_cli('features')
    assert rc == 0
    data = json.loads(out)
    assert 'core' in data
    assert 'workflow' in data


def test_cli_changelog():
    rc, out = _run_cli('changelog')
    assert rc == 0
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) > 0
    assert 'version' in data[0]
    assert 'notes' in data[0]


def test_cli_bundled_paths():
    rc, out = _run_cli('bundled-paths')
    assert rc == 0
    data = json.loads(out)
    assert 'template' in data
    assert 'strings' in data
    for key, path in data.items():
        assert Path(path).exists(), f"Bundled path missing: {key}={path}"


def test_cli_doctor():
    rc, out = _run_cli('doctor', '.')
    assert rc == 0
    data = json.loads(out)
    assert 'package' in data
    assert 'template' in data


def test_cli_docs_index():
    rc, out = _run_cli('docs-index')
    assert rc == 0
    data = json.loads(out)
    assert 'docs' in data
    assert 'README' in data['docs']


def test_cli_verified_opcodes():
    rc, out = _run_cli('verified-opcodes')
    assert rc == 0
    data = json.loads(out)
    assert isinstance(data, list)
    assert 'flipperevents_whenProgramStarts' in data


def test_cli_autodiscover():
    rc, out = _run_cli('autodiscover', '.')
    assert rc == 0
    data = json.loads(out)
    assert 'template' in data


def test_cli_build_python():
    """build-python sub-command compiles a python-first file."""
    from outputllsp3 import reset_pythonfirst_registry
    reset_pythonfirst_registry()

    src = """\
from outputllsp3 import robot, run, port

@run.main
def main():
    robot.use_pair(port.B, port.A)
    robot.stop()
"""
    with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
        f.write(src)
        py = f.name
    out = py.replace('.py', '.llsp3')
    try:
        rc, stdout = _run_cli('build-python', py, '--out', out)
        assert rc == 0, f"build-python failed: {stdout}"
        assert Path(out).exists()
    finally:
        os.unlink(py)
        if Path(out).exists():
            os.unlink(out)


def test_cli_inspect():
    """inspect sub-command prints summary JSON for a bundled .llsp3."""
    from outputllsp3.workflow import bundled_paths
    template = str(bundled_paths()['template'])
    rc, out = _run_cli('inspect', template)
    assert rc == 0
    data = json.loads(out)
    assert 'block_count' in data


def test_cli_export_python():
    """export-python sub-command decompiles a project to Python."""
    from outputllsp3 import transpile_pythonfirst_file, reset_pythonfirst_registry
    from outputllsp3.workflow import discover_defaults
    reset_pythonfirst_registry()
    d = discover_defaults('.')

    src = """\
from outputllsp3 import robot, run, port

@run.main
def main():
    robot.use_pair(port.B, port.A)
    robot.stop()
"""
    with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
        f.write(src)
        py = f.name
    llsp3 = py.replace('.py', '.llsp3')
    out_py = py.replace('.py', '_exported.py')
    try:
        transpile_pythonfirst_file(py, template=d['template'], strings=d['strings'], out=llsp3)
        rc, stdout = _run_cli('export-python', llsp3, '--out', out_py, '--style', 'python-first')
        assert rc == 0, f"export-python failed: {stdout}"
        assert Path(out_py).exists()
    finally:
        os.unlink(py)
        for p in (llsp3, out_py):
            if Path(p).exists():
                os.unlink(p)
