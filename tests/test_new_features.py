"""Tests for locale, verbose logging, and improved programming interface."""
import ast
import logging
import os
import tempfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Locale tests
# ---------------------------------------------------------------------------

def test_locale_defaults_to_en():
    from outputllsp3.locale import get_locale
    assert get_locale() == "en"


def test_set_locale_zh_CN():
    from outputllsp3.locale import set_locale, get_locale, t
    old = get_locale()
    try:
        set_locale("zh_CN")
        assert get_locale() == "zh_CN"
        msg = t("transpile.start", path="/tmp/test.py")
        assert "正在转译" in msg
    finally:
        set_locale(old)


def test_set_locale_back_to_en():
    from outputllsp3.locale import set_locale, get_locale, t
    old = get_locale()
    try:
        set_locale("zh_CN")
        set_locale("en")
        msg = t("transpile.start", path="/tmp/test.py")
        assert "Transpiling" in msg
    finally:
        set_locale(old)


def test_set_locale_invalid():
    from outputllsp3.locale import set_locale
    import pytest
    with pytest.raises(ValueError):
        set_locale("xx_INVALID")


def test_available_locales():
    from outputllsp3.locale import available_locales
    locales = available_locales()
    assert "en" in locales
    assert "zh_CN" in locales


def test_t_fallback_to_en():
    from outputllsp3.locale import set_locale, get_locale, t
    old = get_locale()
    try:
        set_locale("zh_CN")
        # Use a key that exists only in en
        msg = t("nonexistent.key.xyz")
        # Should return the raw key as fallback
        assert msg == "nonexistent.key.xyz"
    finally:
        set_locale(old)


def test_t_interpolation():
    from outputllsp3.locale import t
    msg = t("transpile.start", path="myrobot.py")
    assert "myrobot.py" in msg


def test_zh_CN_all_keys_present():
    """Every key in the en catalog should also exist in zh_CN."""
    from outputllsp3.locale import _CATALOGS
    en_keys = set(_CATALOGS["en"])
    zh_keys = set(_CATALOGS["zh_CN"])
    missing = en_keys - zh_keys
    assert not missing, f"zh_CN missing keys: {missing}"


# ---------------------------------------------------------------------------
# Verbose transpiler logging tests
# ---------------------------------------------------------------------------

def _defaults():
    from outputllsp3.workflow import discover_defaults
    return discover_defaults('.')


def test_verbose_logging_pythonfirst(caplog):
    """transpile_pythonfirst_file emits debug log messages."""
    from outputllsp3 import transpile_pythonfirst_file, reset_pythonfirst_registry
    from outputllsp3.locale import set_locale, get_locale
    old_locale = get_locale()
    set_locale("en")
    reset_pythonfirst_registry()
    d = _defaults()
    src = """\
from outputllsp3 import robot, run, port

@run.main
def main():
    robot.stop()
"""
    with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
        f.write(src)
        py = f.name
    out = py.replace('.py', '.llsp3')
    try:
        with caplog.at_level(logging.DEBUG, logger="outputllsp3.pythonfirst"):
            transpile_pythonfirst_file(py, template=d['template'], strings=d['strings'], out=out)
        assert any("Python-first" in r.message for r in caplog.records)
    finally:
        set_locale(old_locale)
        os.unlink(py)
        if Path(out).exists():
            os.unlink(out)


def test_verbose_logging_ast(caplog):
    """transpile_python_source emits debug log messages."""
    from outputllsp3 import transpile_python_source
    from outputllsp3.locale import set_locale, get_locale
    old_locale = get_locale()
    set_locale("en")
    d = _defaults()
    src = """\
def main():
    pass
"""
    with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
        f.write(src)
        py = f.name
    out = py.replace('.py', '.llsp3')
    try:
        with caplog.at_level(logging.DEBUG, logger="outputllsp3.ast_transpiler"):
            transpile_python_source(py, template=d['template'], strings=d['strings'], out=out)
        assert any("AST" in r.message for r in caplog.records)
    finally:
        set_locale(old_locale)
        os.unlink(py)
        if Path(out).exists():
            os.unlink(out)


def test_verbose_logging_exporter(caplog):
    """export_llsp3_to_python emits debug log messages."""
    from outputllsp3 import transpile_pythonfirst_file, export_llsp3_to_python, reset_pythonfirst_registry
    from outputllsp3.locale import set_locale, get_locale
    old_locale = get_locale()
    set_locale("en")
    reset_pythonfirst_registry()
    d = _defaults()
    src = """\
from outputllsp3 import robot, run, port

@run.main
def main():
    robot.stop()
"""
    with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
        f.write(src)
        py = f.name
    llsp3 = py.replace('.py', '.llsp3')
    out_py = py.replace('.py', '_exported.py')
    try:
        transpile_pythonfirst_file(py, template=d['template'], strings=d['strings'], out=llsp3)
        with caplog.at_level(logging.DEBUG, logger="outputllsp3.exporter"):
            export_llsp3_to_python(llsp3, out_py, style='python-first')
        assert any("Export" in r.message for r in caplog.records)
    finally:
        set_locale(old_locale)
        os.unlink(py)
        for p in (llsp3, out_py):
            if Path(p).exists():
                os.unlink(p)


def test_verbose_logging_build_script(caplog):
    """transpile_path emits debug log messages."""
    from outputllsp3 import transpile_path
    from outputllsp3.locale import set_locale, get_locale
    old_locale = get_locale()
    set_locale("en")
    d = _defaults()
    src = """\
def build(project, api, ns):
    api.flow.start(api.wait.seconds(0.1))
"""
    with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
        f.write(src)
        py = f.name
    out = py.replace('.py', '.llsp3')
    try:
        with caplog.at_level(logging.DEBUG, logger="outputllsp3.transpiler"):
            transpile_path(py, template=d['template'], strings=d['strings'], out=out)
        assert any("Transpil" in r.message for r in caplog.records)
    finally:
        set_locale(old_locale)
        os.unlink(py)
        if Path(out).exists():
            os.unlink(out)


# ---------------------------------------------------------------------------
# Programming interface improvements (FlowBuilder.if_else / forever)
# ---------------------------------------------------------------------------

def test_flow_if_else():
    """FlowBuilder.if_else produces a control_if_else block."""
    from outputllsp3 import LLSP3Project, API
    from outputllsp3.workflow import discover_defaults

    d = discover_defaults('.')
    project = LLSP3Project(d['template'], d['strings'])
    api = API(project)

    cond = api.ops.gt(api.vars.add('x', 5), 3)
    blk = api.flow.if_else(
        cond,
        [api.wait.seconds(0.1)],
        [api.wait.seconds(0.2)],
    )
    assert blk
    assert project.blocks[blk]['opcode'] == 'control_if_else'
    # Verify both substacks are populated
    inputs = project.blocks[blk].get('inputs', {})
    assert 'SUBSTACK' in inputs
    assert 'SUBSTACK2' in inputs
    project.cleanup()


def test_flow_forever():
    """FlowBuilder.forever produces a control_forever block."""
    from outputllsp3 import LLSP3Project, API
    from outputllsp3.workflow import discover_defaults

    d = discover_defaults('.')
    project = LLSP3Project(d['template'], d['strings'])
    api = API(project)

    blk = api.flow.forever(api.wait.seconds(0.1))
    assert blk
    assert project.blocks[blk]['opcode'] == 'control_forever'
    inputs = project.blocks[blk].get('inputs', {})
    assert 'SUBSTACK' in inputs
    project.cleanup()


def test_flow_if_else_saves():
    """A project using if_else can be saved and read back."""
    from outputllsp3 import LLSP3Project, API, parse_llsp3
    from outputllsp3.workflow import discover_defaults

    d = discover_defaults('.')
    project = LLSP3Project(d['template'], d['strings'])
    api = API(project)

    cond = api.ops.lt(1, 2)
    blk = api.flow.if_else(cond, [api.wait.seconds(0.1)], [api.wait.seconds(0.2)])
    api.flow.start(blk)

    with tempfile.NamedTemporaryFile(suffix='.llsp3', delete=False) as f:
        out = f.name
    try:
        project.save(out)
        doc = parse_llsp3(out)
        opcodes = [b.get('opcode') for b in doc.blocks.values()]
        assert 'control_if_else' in opcodes
    finally:
        project.cleanup()
        if Path(out).exists():
            os.unlink(out)


# ---------------------------------------------------------------------------
# CLI --verbose and --locale flags
# ---------------------------------------------------------------------------

def test_cli_verbose_flag():
    """CLI --verbose flag should not break normal operation."""
    import io
    import sys
    from outputllsp3.cli import main
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        rc = main(['--verbose', 'version'])
    except SystemExit as e:
        rc = int(e.code) if e.code is not None else 0
    finally:
        sys.stdout = old_stdout
    assert rc == 0


def test_cli_locale_flag():
    """CLI --locale zh_CN flag should not break normal operation."""
    from outputllsp3.locale import set_locale, get_locale
    import io
    import sys
    old = get_locale()
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        from outputllsp3.cli import main
        rc = main(['--locale', 'zh_CN', 'version'])
    except SystemExit as e:
        rc = int(e.code) if e.code is not None else 0
    finally:
        sys.stdout = old_stdout
        set_locale(old)
    assert rc == 0
