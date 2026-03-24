"""Classic build-script transpiler: load a Python module and call ``build()``.

This is the original transpilation path.  A *build script* is a plain Python
module (or package) that defines a ``build(project, api, ns)`` function.
``transpile_path`` resolves the appropriate template / strings resources,
loads the module, calls ``build``, and saves the result.

Entry points
------------
- ``transpile_path(path, …)``    – auto-detect file vs. package and dispatch
- ``transpile_file(path, …)``    – compile a single ``.py`` build script
- ``transpile_package(path, …)`` – compile a Python package (calls ``build`` in
  ``__init__.py``, provides sub-modules as the ``ns`` namespace argument)
- ``transpile_module(module, …)``– compile an already-imported ``ModuleType``
- ``autodiscover(base)``         – search upward for ``ok.llsp3`` / ``strings.json``
"""
from __future__ import annotations

import importlib
import importlib.util
import logging
import re
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

from .api import API
from .project import LLSP3Project
from .workflow import discover_defaults
from .locale import t
from .pythonfirst import transpile_pythonfirst_file

logger = logging.getLogger(__name__)


def autodiscover(base: str | Path) -> dict[str, Path | None]:
    base = Path(base)
    candidates = [base, *base.parents]
    def find(name: str):
        for d in candidates:
            p = d / name
            if p.exists():
                return p
        return None
    return {
        "template": find("ok.llsp3") or find("ok.llsp"),
        "strings": find("strings.json"),
        "full": find("full.llsp3") or find("full.llsp"),
    }


def _load_module_from_file(path: str | Path) -> ModuleType:
    path = Path(path).resolve()
    logger.debug(t("transpile.load_module", path=path))
    spec = importlib.util.spec_from_file_location("outputllsp3_user_module", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    module.__outputllsp3_namespace__ = path.stem
    module.__outputllsp3_source_path__ = str(path)
    spec.loader.exec_module(module)
    return module


def _sanitize_namespace(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "__", value).strip("_")

def _load_package(path: str | Path) -> tuple[ModuleType, Any]:
    path = Path(path).resolve()
    logger.debug(t("transpile.load_package", path=path))
    pkg_name = path.name
    sys.path.insert(0, str(path.parent))
    module = importlib.import_module(pkg_name)
    tree = SimpleNamespace()
    for py in sorted(path.rglob("*.py")):
        rel = py.relative_to(path).with_suffix("")
        parts = rel.parts
        mod_name = ".".join((pkg_name, *parts))
        mod = importlib.import_module(mod_name)
        alias = pkg_name if parts == ("__init__",) else pkg_name + "__" + "__".join([p for p in parts if p != "__init__"])
        mod.__outputllsp3_namespace__ = _sanitize_namespace(alias)
        mod.__outputllsp3_source_path__ = str(py)
        cur = tree
        for part in parts[:-1]:
            if not hasattr(cur, part):
                setattr(cur, part, SimpleNamespace())
            cur = getattr(cur, part)
        setattr(cur, parts[-1], mod)
    module.__outputllsp3_namespace__ = _sanitize_namespace(pkg_name)
    return module, tree


def transpile_module(module: ModuleType, *, template: str | Path, strings: str | Path, out: str | Path, sprite_name: str = "OutputLLSP3 Generated", namespace: Any = None, function_namespace: bool = False, strict_verified: bool = False) -> Path:
    mod_name = getattr(module, '__name__', '?')
    logger.debug(t("transpile.module.start", module=mod_name))
    build = getattr(module, "build", None)
    if not callable(build):
        raise AttributeError("module/package must define build(project, api=None, ns=None)")
    project = LLSP3Project(template, strings, sprite_name=sprite_name)
    project.set_default_namespace(getattr(module, "__outputllsp3_namespace__", ""), function_namespace=function_namespace)
    project.set_strict_verified(strict_verified)
    api = API(project)
    try:
        logger.debug(t("transpile.module.build_call", module=mod_name))
        build(project, api, namespace)
        logger.debug(t("transpile.module.save", out=out))
        result = project.save(out)
        logger.info(t("transpile.module.done", out=result))
        return result
    finally:
        project.cleanup()


def transpile_file(path: str | Path, *, template: str | Path, strings: str | Path, out: str | Path, sprite_name: str = "OutputLLSP3 Generated", function_namespace: bool = False, strict_verified: bool = False) -> Path:
    logger.debug(t("transpile.file.start", path=path))
    mod = _load_module_from_file(path)
    return transpile_module(mod, template=template, strings=strings, out=out, sprite_name=sprite_name, namespace=mod, function_namespace=function_namespace, strict_verified=strict_verified)


def transpile_package(path: str | Path, *, template: str | Path, strings: str | Path, out: str | Path, sprite_name: str | None = None, function_namespace: bool = False, strict_verified: bool = False) -> Path:
    logger.debug(t("transpile.package.start", path=path))
    mod, ns = _load_package(path)
    return transpile_module(mod, template=template, strings=strings, out=out, sprite_name=sprite_name or Path(path).name, namespace=ns, function_namespace=function_namespace, strict_verified=strict_verified)


def transpile_path(path: str | Path, *, template: str | Path | None = None, strings: str | Path | None = None, out: str | Path, sprite_name: str | None = None, function_namespace: bool = False, strict_verified: bool = False) -> Path:
    path = Path(path)
    logger.debug(t("transpile.start", path=path))
    auto = discover_defaults(path if path.is_dir() else path.parent)
    template = Path(template) if template else auto['template']
    strings = Path(strings) if strings else auto['strings']
    logger.debug(t("transpile.autodiscover", template=template, strings=strings))
    if path.is_dir():
        return transpile_package(path, template=template, strings=strings, out=out, sprite_name=sprite_name, function_namespace=function_namespace, strict_verified=strict_verified)
    return transpile_file(path, template=template, strings=strings, out=out, sprite_name=sprite_name or path.stem, function_namespace=function_namespace, strict_verified=strict_verified)


def transpile(
    source: str | Path,
    *,
    mode: str = "auto",
    out: str | Path,
    template: str | Path | None = None,
    strings: str | Path | None = None,
    sprite_name: str | None = None,
    function_namespace: bool = False,
    strict_verified: bool = False,
) -> Path:
    """Unified transpilation entry point — replaces the six individual functions.

    Parameters
    ----------
    source:
        Path to a ``.py`` file, a Python package directory, or a
        python-first style ``.py`` file.
    mode:
        ``'auto'`` (default) – detect the transpilation style from file content.
        ``'python_first'``   – python-first decorator style (``@robot.proc`` / ``@run.main``).
        ``'build_script'``   – classic build-script style (module defines ``build()``).
        ``'ast'``            – raw Python-to-Scratch AST transpilation.
    out:
        Output path for the generated ``.llsp3`` file.
    template, strings:
        Optional paths; discovered automatically when omitted.
    sprite_name:
        Sprite name in the generated project (defaults to stem of source path).
    function_namespace, strict_verified:
        Forwarded to the underlying transpiler.

    Returns
    -------
    Path
        The path of the written ``.llsp3`` file.
    """
    source = Path(source)
    logger.debug(t("transpile.start", path=source))

    resolved_mode = mode
    if resolved_mode == "auto":
        resolved_mode = _detect_transpile_mode(source)
        logger.debug("transpile: auto-detected mode=%s for %s", resolved_mode, source)

    if resolved_mode == "python_first":
        return transpile_pythonfirst_file(
            source,
            template=template,
            strings=strings,
            out=out,
            sprite_name=sprite_name,
            strict_verified=strict_verified,
        )

    if resolved_mode == "ast":
        from .ast_transpiler import transpile_python_source
        return transpile_python_source(
            source,
            template=template,
            strings=strings,
            out=out,
            sprite_name=sprite_name,
            function_namespace=function_namespace,
        )

    # build_script (default)
    return transpile_path(
        source,
        template=template,
        strings=strings,
        out=out,
        sprite_name=sprite_name,
        function_namespace=function_namespace,
        strict_verified=strict_verified,
    )


def _detect_transpile_mode(source: Path) -> str:
    """Heuristically detect the transpilation mode from file/directory contents.

    Rules (checked in priority order):
    1. Directory → always ``'build_script'`` (package with build()).
    2. File contains ``@robot.proc`` or ``@run.main`` → ``'python_first'``.
    3. File contains ``def build(`` → ``'build_script'``.
    4. Fallback → ``'ast'``.
    """
    if source.is_dir():
        return "build_script"
    try:
        text = source.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "build_script"
    if "@robot.proc" in text or "@run.main" in text:
        return "python_first"
    if "def build(" in text:
        return "build_script"
    return "ast"
