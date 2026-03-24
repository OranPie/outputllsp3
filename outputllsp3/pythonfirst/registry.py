"""Decorator registry and entry-point for Python-first transpilation.

Provides:
- ``reset_pythonfirst_registry()`` – compatibility no-op
- ``transpile_pythonfirst_file()`` – compile a Python-first source file to
  an ``.llsp3`` project
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..project import LLSP3Project
from ..workflow import discover_defaults
from ..locale import t

logger = logging.getLogger(__name__)


def reset_pythonfirst_registry() -> None:
    """No-op kept for backward compatibility; tracing mode was removed."""
    return None


def transpile_pythonfirst_file(
    path: str | Path,
    *,
    template: str | Path | None = None,
    strings: str | Path | None = None,
    out: str | Path = None,
    sprite_name: str | None = None,
    strict_verified: bool = False,
):
    """Compile a Python-first decorated source file to an ``.llsp3`` project.

    Parameters
    ----------
    path:
        Path to the Python source file containing ``@robot.proc`` /
        ``@run.main`` decorated functions.
    template:
        Override the ``.llsp3`` template ZIP.  Defaults to the bundled
        template discovered by :func:`~outputllsp3.workflow.discover_defaults`.
    strings:
        Override the ``strings.json`` opcode catalog.  Defaults to the
        bundled catalog.
    out:
        Destination path for the generated ``.llsp3`` file.
    sprite_name:
        Name to embed in the project for the generated sprite.  Defaults to
        the output file stem.
    strict_verified:
        When ``True``, all opcodes are checked against the bundled schema
        before saving.
    """
    from .compiler import PythonFirstContext, _load_source

    path = Path(path)
    logger.debug(t("pf.start", path=path))
    defaults = discover_defaults(path.parent)
    template = Path(template) if template else defaults["template"]
    strings = Path(strings) if strings else defaults["strings"]
    out = Path(out)
    project = LLSP3Project(template, strings, sprite_name=sprite_name or out.stem)
    project.set_default_namespace(path.stem)
    project.set_strict_verified(strict_verified)
    ctx = PythonFirstContext(project, path)
    try:
        ctx.transpile(_load_source(path))
        logger.debug(t("pf.save", out=out))
        result = project.save(out)
        logger.info(t("pf.done", out=result))
        return result
    finally:
        project.cleanup()
