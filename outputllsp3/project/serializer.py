"""ZIP assembly, JSON serialisation, and structural validation.

``ProjectSerializer`` handles template unpacking, asset-hash normalisation,
block-graph validation, and writing the final ``.llsp3`` ZIP.
"""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from .blocks import BlockManager
from ..locale import t

if TYPE_CHECKING:
    from . import LLSP3Project

logger = logging.getLogger(__name__)


class ProjectSerializer:
    def __init__(self, project: "LLSP3Project") -> None:
        self._p = project

    # -- template unpacking -----------------------------------------------

    def unpack(self, template_llsp3: Path) -> None:
        logger.debug(t("ser.unpack", template=str(template_llsp3)))
        with zipfile.ZipFile(template_llsp3, "r") as zf:
            zf.extractall(self._p.outer_dir)
        with zipfile.ZipFile(self._p.outer_dir / "scratch.sb3", "r") as zf:
            zf.extractall(self._p.inner_dir)
        self._p.manifest = json.loads(
            (self._p.outer_dir / "manifest.json").read_text(encoding="utf-8")
        )
        self._p.project_json = json.loads(
            (self._p.inner_dir / "project.json").read_text(encoding="utf-8")
        )
        self._p.sprite_index = next(
            i for i, t in enumerate(self._p.project_json["targets"]) if not t.get("isStage")
        )

    # -- cleanup ----------------------------------------------------------

    def cleanup(self) -> None:
        shutil.rmtree(self._p.tmpdir, ignore_errors=True)

    # -- asset normalisation ---------------------------------------------

    def _normalize_asset_hashes(self) -> None:
        logger.debug(t("ser.normalize_assets"))
        asset_fields = ("costumes", "sounds")
        rename_map: dict[str, tuple[str, str]] = {}
        for target in self._p.project_json.get("targets", []):
            for field in asset_fields:
                for asset in target.get(field, []):
                    md5ext = asset.get("md5ext")
                    if not md5ext:
                        continue
                    if md5ext in rename_map:
                        digest, normalized_name = rename_map[md5ext]
                        asset["assetId"] = digest
                        asset["md5ext"] = normalized_name
                        continue
                    asset_path = self._p.inner_dir / md5ext
                    if not asset_path.exists():
                        continue
                    data = asset_path.read_bytes()
                    digest = hashlib.md5(data).hexdigest()
                    ext = asset_path.suffix or (
                        ("." + asset.get("dataFormat", "")) if asset.get("dataFormat") else ""
                    )
                    correct_name = f"{digest}{ext}"
                    if asset_path.name != correct_name:
                        correct_path = self._p.inner_dir / correct_name
                        if not correct_path.exists():
                            asset_path.rename(correct_path)
                        else:
                            asset_path.unlink()
                        asset_path = correct_path
                    rename_map[md5ext] = (digest, asset_path.name)
                    asset["assetId"] = digest
                    asset["md5ext"] = asset_path.name

    # -- structural validation -------------------------------------------

    def validate(self) -> list[str]:
        errs = []
        blocks = self._p.blocks
        is_bool = self._p._blocks.is_boolean_opcode
        for bid, block in blocks.items():
            if block.get("next") is not None and block["next"] not in blocks:
                errs.append(f"{bid}: missing next {block['next']}")
            if block.get("parent") is not None and block["parent"] not in blocks:
                errs.append(f"{bid}: missing parent {block['parent']}")
            for name, spec in block.get("inputs", {}).items():
                if (
                    isinstance(spec, list) and len(spec) >= 2
                    and isinstance(spec[1], str) and spec[1] in blocks
                ):
                    child = blocks[spec[1]]
                    if child.get("parent") != bid:
                        errs.append(
                            f"{bid}.{name}: child {spec[1]} has parent "
                            f"{child.get('parent')} instead of {bid}"
                        )
            opcode = block.get("opcode")
            if opcode in {"operator_or", "operator_and"}:
                for key in ("OPERAND1", "OPERAND2"):
                    spec = block.get("inputs", {}).get(key)
                    if (
                        isinstance(spec, list) and len(spec) >= 2
                        and isinstance(spec[1], str) and spec[1] in blocks
                    ):
                        child_opcode = blocks[spec[1]].get("opcode")
                        if not is_bool(child_opcode):
                            errs.append(
                                f"{bid}.{key}: boolean slot connected to "
                                f"non-boolean opcode {child_opcode}"
                            )
            if opcode == "operator_equals":
                for key in ("OPERAND1", "OPERAND2"):
                    spec = block.get("inputs", {}).get(key)
                    if (
                        isinstance(spec, list) and len(spec) >= 2
                        and isinstance(spec[1], str) and spec[1] in blocks
                    ):
                        child_opcode = blocks[spec[1]].get("opcode")
                        if is_bool(child_opcode):
                            errs.append(
                                f"{bid}.{key}: equals connected to boolean opcode {child_opcode}"
                            )
            if opcode in {"control_if", "control_repeat_until"}:
                spec = block.get("inputs", {}).get("CONDITION")
                if (
                    isinstance(spec, list) and len(spec) >= 2
                    and isinstance(spec[1], str) and spec[1] in blocks
                ):
                    child_opcode = blocks[spec[1]].get("opcode")
                    if not is_bool(child_opcode):
                        errs.append(
                            f"{bid}.CONDITION: control condition connected to "
                            f"non-boolean opcode {child_opcode}"
                        )
        return errs

    # -- save -------------------------------------------------------------

    def save(self, out_path: str | Path) -> Path:
        logger.debug(t("ser.save", out=str(out_path)))
        errs = self.validate()
        if errs:
            raise ValueError("Validation failed:\n" + "\n".join(errs[:50]))
        self._normalize_asset_hashes()

        # --- project.json extensions: auto-detected from opcodes used --------
        extensions = sorted({
            b["opcode"].split("_", 1)[0]
            for b in self._p.blocks.values()
            if "_" in b["opcode"]
            and b["opcode"].split("_", 1)[0] not in BlockManager.BUILTIN_EXTENSION_PREFIXES
        })
        self._p.project_json["extensions"] = extensions

        out_path = Path(out_path)
        project_name = out_path.stem

        # --- sprite name matches output filename -----------------------------
        self._p.sprite["name"] = project_name

        # --- populate monitors from declared show_monitor() calls ------------
        sprite_name = project_name
        monitors: list[dict] = []
        for vid, cfg in self._p._monitors.items():
            pair = self._p.variables.get(vid, ['var', 0])
            display_name = pair[0]
            monitors.append({
                'id': vid,
                'mode': cfg.get('mode', 'default'),
                'opcode': 'data_variable',
                'params': {'VARIABLE': display_name},
                'spriteName': sprite_name,
                'value': pair[1],
                'width': 0,
                'height': 0,
                'x': None,
                'y': None,
                'visible': cfg.get('visible', True),
                'sliderMin': cfg.get('slider_min', 0),
                'sliderMax': cfg.get('slider_max', 100),
                'isDiscrete': cfg.get('discrete', True),
            })
        self._p.project_json['monitors'] = monitors

        (self._p.inner_dir / "project.json").write_text(
            json.dumps(self._p.project_json, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        scratch_sb3 = self._p.outer_dir / "scratch.sb3"
        with zipfile.ZipFile(scratch_sb3, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in sorted(self._p.inner_dir.iterdir(), key=lambda p: p.name):
                zf.write(item, arcname=item.name)

        # --- manifest: fresh timestamps, unique ID, synced extensions --------
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
                  f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z"
        self._p.manifest["name"] = project_name
        self._p.manifest["id"] = secrets.token_urlsafe(9)   # unique per save
        self._p.manifest["created"] = now_iso
        self._p.manifest["lastsaved"] = now_iso
        self._p.manifest["size"] = scratch_sb3.stat().st_size
        self._p.manifest["extensions"] = extensions         # sync with project.json

        (self._p.outer_dir / "manifest.json").write_text(
            json.dumps(self._p.manifest, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name in ["manifest.json", "icon.svg", "scratch.sb3"]:
                zf.write(self._p.outer_dir / name, arcname=name)
        logger.info(t("ser.done", out=str(out_path)))
        return out_path
