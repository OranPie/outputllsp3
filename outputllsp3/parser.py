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
        raise ValueError("No sprite target found")

    @property
    def blocks(self) -> dict[str, dict[str, Any]]:
        return self.sprite.get("blocks", {})

    @property
    def variables(self) -> dict[str, list[Any]]:
        return self.sprite.get("variables", {})

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
            "opcode_count": len(self.opcode_counts()),
            "procedure_count": len(self.procedure_names()),
            "procedures": self.procedure_names(),
        }


def parse_llsp3(path: str | Path) -> LLSP3Document:
    path = str(path)
    with zipfile.ZipFile(path, "r") as outer:
        manifest = json.loads(outer.read("manifest.json").decode("utf-8"))
        scratch_sb3 = outer.read("scratch.sb3")
    with zipfile.ZipFile(io.BytesIO(scratch_sb3), "r") as inner:
        project = json.loads(inner.read("project.json").decode("utf-8"))
    return LLSP3Document(path=path, manifest=manifest, project=project)
