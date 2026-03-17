"""Parse LLSP3 (and legacy LLSP) project archives into structured Python objects.

An ``.llsp3`` file is a ZIP-inside-ZIP:

  project.llsp3 (ZIP)
  ├── manifest.json   – project metadata (name, type, …)
  └── scratch.sb3 (ZIP)
      └── project.json – Scratch VM project tree (targets, blocks, variables, …)

Public API
----------
- ``LLSP3Document``  – dataclass holding parsed manifest + project data; provides
  convenience properties ``sprite``, ``blocks``, ``variables``, ``summary()``,
  ``opcode_counts()``, ``procedure_names()``.
- ``parse_llsp3(path)``  – parse a ``.llsp3`` / ``.llsp`` file and return an
  ``LLSP3Document``.
"""
from __future__ import annotations

import io
import json
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class LLSP3Document:
    path: str
    manifest: dict[str, Any]
    project: dict[str, Any]

    @property
    def sprite(self) -> dict[str, Any]:
        for target in self.project.get("targets", []):
            if not target.get("isStage"):
                return target
        raise ValueError("No sprite target found in project.json")

    @property
    def blocks(self) -> dict[str, dict[str, Any]]:
        return self.sprite.get("blocks", {})

    @property
    def variables(self) -> dict[str, list[Any]]:
        return self.sprite.get("variables", {})

    @property
    def lists(self) -> dict[str, list[Any]]:
        return self.sprite.get("lists", {})

    def opcode_counts(self) -> Counter:
        return Counter(b.get("opcode") for b in self.blocks.values())

    def procedure_names(self) -> list[str]:
        names: list[str] = []
        for block in self.blocks.values():
            if block.get("opcode") == "procedures_prototype":
                names.append(block.get("mutation", {}).get("proccode", ""))
        return names

    def summary(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "block_count": len(self.blocks),
            "variable_count": len(self.variables),
            "list_count": len(self.lists),
            "list_names": [pair[0] for pair in self.lists.values()],
            "opcode_count": len(self.opcode_counts()),
            "procedure_count": len(self.procedure_names()),
            "procedures": self.procedure_names(),
        }


def parse_llsp3(path: str | Path) -> LLSP3Document:
    """Parse an LLSP3 (or LLSP) project file and return a structured document.

    Both ``.llsp3`` and the older ``.llsp`` extension are supported; they use
    the same zip-inside-zip format.

    Args:
        path: Path to the ``.llsp3`` or ``.llsp`` file.

    Returns:
        An :class:`LLSP3Document` containing the manifest and project data.

    Raises:
        FileNotFoundError: If *path* does not exist.
        zipfile.BadZipFile: If the file is not a valid LLSP3 archive.
        KeyError: If required files (``manifest.json``, ``scratch.sb3``,
            ``project.json``) are missing from the archive.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"LLSP3 file not found: {path}")
    path_str = str(path)
    try:
        with zipfile.ZipFile(path_str, "r") as outer:
            if "manifest.json" not in outer.namelist():
                raise KeyError(f"manifest.json not found in {path.name}")
            manifest = json.loads(outer.read("manifest.json").decode("utf-8"))
            if "scratch.sb3" not in outer.namelist():
                raise KeyError(f"scratch.sb3 not found in {path.name}")
            scratch_sb3 = outer.read("scratch.sb3")
    except zipfile.BadZipFile as exc:
        raise zipfile.BadZipFile(f"Not a valid LLSP3 archive: {path.name}") from exc
    try:
        with zipfile.ZipFile(io.BytesIO(scratch_sb3), "r") as inner:
            if "project.json" not in inner.namelist():
                raise KeyError(f"project.json not found inside scratch.sb3 in {path.name}")
            project = json.loads(inner.read("project.json").decode("utf-8"))
    except zipfile.BadZipFile as exc:
        raise zipfile.BadZipFile(f"scratch.sb3 inside {path.name} is not a valid zip") from exc
    return LLSP3Document(path=path_str, manifest=manifest, project=project)
