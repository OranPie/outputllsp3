"""Smoke tests for all three transpiler modes and the exporter."""
import ast
import os
import tempfile
from pathlib import Path


def _defaults():
    from outputllsp3.workflow import discover_defaults
    return discover_defaults('.')


def _build_py(src: str) -> str:
    """Write *src* to a temp file and return its path."""
    with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
        f.write(src)
        return f.name


# ---------------------------------------------------------------------------
# Python-first transpiler
# ---------------------------------------------------------------------------

PYTHON_FIRST_BASIC = """\
from outputllsp3 import robot, run, port

@run.main
def main():
    robot.use_pair(port.B, port.A)
    robot.stop()
"""

PYTHON_FIRST_WITH_PROC = """\
from outputllsp3 import robot, run, port

@robot.proc
def square(side=20, speed=420):
    for _ in range(4):
        robot.forward_cm(side, speed)
        robot.turn_deg(90, 260)

@run.main
def main():
    robot.use_pair(port.B, port.A)
    square()
    square(30)
    square(speed=350)
"""

PYTHON_FIRST_WITH_RETURN = """\
from outputllsp3 import robot, run, port

@robot.proc
def clamp(val, lo=0, hi=100):
    if val < lo:
        return lo
    if val > hi:
        return hi
    return val

@run.main
def main():
    a = clamp(50)
    b = clamp(-5)
    c = clamp(150, hi=80)
    robot.stop()
"""


def test_pythonfirst_basic():
    from outputllsp3 import transpile_pythonfirst_file, reset_pythonfirst_registry
    reset_pythonfirst_registry()
    d = _defaults()
    py = _build_py(PYTHON_FIRST_BASIC)
    out = py.replace('.py', '.llsp3')
    try:
        transpile_pythonfirst_file(py, template=d['template'], strings=d['strings'], out=out)
        assert Path(out).exists()
        assert Path(out).stat().st_size > 0
    finally:
        os.unlink(py)
        if Path(out).exists():
            os.unlink(out)


def test_pythonfirst_proc_defaults():
    from outputllsp3 import transpile_pythonfirst_file, reset_pythonfirst_registry
    reset_pythonfirst_registry()
    d = _defaults()
    py = _build_py(PYTHON_FIRST_WITH_PROC)
    out = py.replace('.py', '.llsp3')
    try:
        transpile_pythonfirst_file(py, template=d['template'], strings=d['strings'], out=out)
        assert Path(out).exists()
    finally:
        os.unlink(py)
        if Path(out).exists():
            os.unlink(out)


def test_pythonfirst_return_value():
    from outputllsp3 import transpile_pythonfirst_file, reset_pythonfirst_registry
    reset_pythonfirst_registry()
    d = _defaults()
    py = _build_py(PYTHON_FIRST_WITH_RETURN)
    out = py.replace('.py', '.llsp3')
    try:
        transpile_pythonfirst_file(py, template=d['template'], strings=d['strings'], out=out)
        assert Path(out).exists()
    finally:
        os.unlink(py)
        if Path(out).exists():
            os.unlink(out)


# ---------------------------------------------------------------------------
# AST transpiler
# ---------------------------------------------------------------------------

AST_SOURCE = """\
def setup(speed=420):
    pass

def main():
    setup()
    setup(300)
"""


def test_ast_transpiler_basic():
    from outputllsp3 import transpile_python_source
    d = _defaults()
    py = _build_py(AST_SOURCE)
    out = py.replace('.py', '.llsp3')
    try:
        transpile_python_source(py, template=d['template'], strings=d['strings'], out=out)
        assert Path(out).exists()
    finally:
        os.unlink(py)
        if Path(out).exists():
            os.unlink(out)


# ---------------------------------------------------------------------------
# Build-script transpiler
# ---------------------------------------------------------------------------

BUILD_SCRIPT = """\
def build(project, api, ns):
    api.flow.start(
        api.wait.seconds(0.1),
    )
"""


def test_build_script_basic():
    from outputllsp3 import transpile_path
    d = _defaults()
    py = _build_py(BUILD_SCRIPT)
    out = py.replace('.py', '.llsp3')
    try:
        transpile_path(py, template=d['template'], strings=d['strings'], out=out)
        assert Path(out).exists()
    finally:
        os.unlink(py)
        if Path(out).exists():
            os.unlink(out)


# ---------------------------------------------------------------------------
# Exporter (all three styles)
# ---------------------------------------------------------------------------

def _make_llsp3() -> str:
    """Compile a simple python-first program and return the path to the .llsp3."""
    from outputllsp3 import transpile_pythonfirst_file, reset_pythonfirst_registry
    reset_pythonfirst_registry()
    d = _defaults()
    py = _build_py(PYTHON_FIRST_WITH_PROC)
    out = py.replace('.py', '_export_test.llsp3')
    transpile_pythonfirst_file(py, template=d['template'], strings=d['strings'], out=out)
    os.unlink(py)
    return out


def test_export_raw():
    from outputllsp3 import export_llsp3_to_python
    llsp3 = _make_llsp3()
    out = llsp3.replace('.llsp3', '_raw.py')
    try:
        export_llsp3_to_python(llsp3, out, style='raw')
        assert Path(out).exists()
        # Must be valid Python
        ast.parse(Path(out).read_text(encoding='utf-8'))
    finally:
        if Path(llsp3).exists():
            os.unlink(llsp3)
        if Path(out).exists():
            os.unlink(out)


def test_export_builder():
    from outputllsp3 import export_llsp3_to_python
    llsp3 = _make_llsp3()
    out = llsp3.replace('.llsp3', '_builder.py')
    try:
        export_llsp3_to_python(llsp3, out, style='builder')
        assert Path(out).exists()
        ast.parse(Path(out).read_text(encoding='utf-8'))
    finally:
        if Path(llsp3).exists():
            os.unlink(llsp3)
        if Path(out).exists():
            os.unlink(out)


def test_export_pythonfirst():
    from outputllsp3 import export_llsp3_to_python
    llsp3 = _make_llsp3()
    out = llsp3.replace('.llsp3', '_pf.py')
    try:
        export_llsp3_to_python(llsp3, out, style='python-first')
        assert Path(out).exists()
        src = Path(out).read_text(encoding='utf-8')
        ast.parse(src)
        # Defaults must appear in the exported source
        assert 'side=20' in src
        assert 'speed=420' in src
    finally:
        if Path(llsp3).exists():
            os.unlink(llsp3)
        if Path(out).exists():
            os.unlink(out)


def test_export_pythonfirst_roundtrip_defaults():
    """Build with defaults → export python-first → check defaults are preserved."""
    from outputllsp3 import transpile_pythonfirst_file, export_llsp3_to_python, reset_pythonfirst_registry

    src = """\
from outputllsp3 import robot, run, port

@robot.proc
def move(dist=20, speed=420):
    robot.forward_cm(dist, speed)

@run.main
def main():
    move()
    move(speed=300)
"""
    reset_pythonfirst_registry()
    d = _defaults()
    py = _build_py(src)
    llsp3 = py.replace('.py', '_rt.llsp3')
    out_py = py.replace('.py', '_rt_exported.py')
    try:
        transpile_pythonfirst_file(py, template=d['template'], strings=d['strings'], out=llsp3)
        export_llsp3_to_python(llsp3, out_py, style='python-first')
        exported = Path(out_py).read_text(encoding='utf-8')
        ast.parse(exported)
        assert 'dist=20' in exported
        assert 'speed=420' in exported
    finally:
        os.unlink(py)
        for p in (llsp3, out_py):
            if Path(p).exists():
                os.unlink(p)
