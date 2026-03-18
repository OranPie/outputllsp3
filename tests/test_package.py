"""Smoke tests: verify the package-level public API is importable and correct."""
import sys
import types


def test_version_exists():
    import outputllsp3
    assert isinstance(outputllsp3.__version__, str)
    assert outputllsp3.__version__


def test_all_exports_present():
    """Every name in __all__ must resolve as a non-None attribute."""
    import outputllsp3
    missing = [name for name in outputllsp3.__all__ if getattr(outputllsp3, name, None) is None]
    assert missing == [], f"Missing exports: {missing}"


def test_all_exports_count():
    """Sanity check: we expect at least 40 public symbols."""
    import outputllsp3
    assert len(outputllsp3.__all__) >= 40


def test_package_info():
    import outputllsp3
    info = outputllsp3.package_info()
    assert info['name'] == 'outputllsp3'
    assert info['version'] == outputllsp3.__version__
    assert 'layout' in info
    assert 'features' in info


def test_package_layout_complete():
    """PACKAGE_LAYOUT must mention all subsystems."""
    from outputllsp3.metadata import PACKAGE_LAYOUT
    required_groups = {'infrastructure', 'core', 'authoring', 'transpile', 'export', 'workflow', 'resources'}
    assert required_groups == set(PACKAGE_LAYOUT.keys()), (
        f"PACKAGE_LAYOUT groups mismatch: {set(PACKAGE_LAYOUT.keys())} != {required_groups}"
    )


def test_package_layout_all_modules_listed():
    """Every .py file in outputllsp3/ (except __init__.py) must appear in PACKAGE_LAYOUT."""
    from pathlib import Path
    from outputllsp3.metadata import PACKAGE_LAYOUT

    pkg_dir = Path(__file__).parent.parent / 'outputllsp3'
    actual = {p.name for p in pkg_dir.glob('*.py') if p.name not in ('__init__.py',)}

    all_declared = set()
    for files in PACKAGE_LAYOUT.values():
        for f in files:
            if f.endswith('.py') and '/' not in f:
                all_declared.add(f)

    missing = actual - all_declared
    assert not missing, f"Modules not in PACKAGE_LAYOUT: {missing}"


def test_legacy_aliases():
    """Backward-compat aliases WrapperAPI and SPIKEAPI must resolve."""
    import outputllsp3
    assert outputllsp3.WrapperAPI is outputllsp3.ScratchWrapper
    assert outputllsp3.SPIKEAPI is outputllsp3.SpikePythonAPI


def test_docstring_on_package():
    import outputllsp3
    assert outputllsp3.__doc__ is not None
    assert len(outputllsp3.__doc__) > 20


def test_module_docstrings():
    """Every module in the package should have a module-level docstring."""
    from pathlib import Path
    import importlib

    pkg_dir = Path(__file__).parent.parent / 'outputllsp3'
    missing = []
    for py_file in sorted(pkg_dir.glob('*.py')):
        if py_file.name.startswith('_'):
            continue
        mod_name = f'outputllsp3.{py_file.stem}'
        try:
            mod = importlib.import_module(mod_name)
            if not mod.__doc__:
                missing.append(py_file.name)
        except Exception as exc:
            missing.append(f'{py_file.name} (import error: {exc})')
    assert missing == [], f"Modules without docstrings: {missing}"


def test_locale_exports():
    """set_locale, get_locale, t, available_locales must be importable."""
    import outputllsp3
    assert callable(outputllsp3.set_locale)
    assert callable(outputllsp3.get_locale)
    assert callable(outputllsp3.t)
    assert callable(outputllsp3.available_locales)


def test_locale_in_all():
    """Locale symbols must be in __all__."""
    import outputllsp3
    for name in ("set_locale", "get_locale", "t", "available_locales"):
        assert name in outputllsp3.__all__
