"""LLSP3 → Python decompiler / exporter.

Converts a compiled ``.llsp3`` project back to Python source code.  Three
output styles are supported:

``raw``
    Minimal faithful reconstruction; each block becomes a direct API call.
    Suitable for automated round-trip testing.

``builder``
    Same semantics as ``raw`` but with module structure and commentary that
    makes the file human-editable as a build script.

``python-first``
    Higher-level decompilation that lifts common patterns to python-first
    idioms (``@robot.proc`` / ``@run.main``, ``robot.forward_cm``, …).
    The output is approximate—round-tripping through python-first may not
    preserve every low-level block detail, but produces readable programs.

Public API
----------
- ``export_llsp3_to_python(path, out, *, style)`` – main entry point.
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..parser import parse_llsp3
from ..locale import t
from .raw import raw_lines
from .builder import builder_lines
from .python_first import pythonfirst_lines

logger = logging.getLogger(__name__)

__all__ = ["export_llsp3_to_python"]


def export_llsp3_to_python(path: str, out: str, *, style: str = "raw") -> str:
    """Decompile an ``.llsp3`` project to a Python source file.

    Parameters
    ----------
    path:
        Path to the source ``.llsp3`` file.
    out:
        Destination path for the generated Python source.
    style:
        One of ``"raw"``, ``"builder"``, or ``"python-first"``.
    """
    logger.debug(t("export.start", path=path, style=style))
    doc = parse_llsp3(path)
    logger.debug(t("export.parse", path=path, block_count=len(doc.blocks), var_count=len(doc.variables)))
    if style == "raw":
        lines = raw_lines(doc, style)
    elif style == "builder":
        lines = builder_lines(doc)
    elif style == "python-first":
        lines = pythonfirst_lines(doc)
    else:
        raise ValueError(f"Unsupported export style: {style}")
    logger.debug(t("export.write", out=out))
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info(t("export.done", out=out))
    return str(out)
