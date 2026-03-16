from __future__ import annotations

import inspect
from pathlib import Path

from dataclasses import dataclass
from typing import Any


@dataclass
class FlowBuilder:
    project: Any

    def _caller_reference(self) -> str:
        for frame_info in inspect.stack()[2:]:
            filename = frame_info.filename.replace('\\', '/')
            if '/outputllsp3/' in filename or filename.endswith('/outputllsp3/flow.py'):
                continue
            return f"reference: {Path(frame_info.filename).name}:{frame_info.lineno}::{frame_info.function}"
        return "reference: generated"


    def _flat(self, *items: Any) -> list[str]:
        out: list[str] = []
        for item in items:
            if item is None:
                continue
            if isinstance(item, (list, tuple)):
                out.extend(self._flat(*item))
            else:
                out.append(item)
        return out

    def start(self, *body: Any, x: int = -220, y: int = 90, add_reference_comment: bool = True) -> str:
        start = self.project.add_block("flipperevents_whenProgramStarts", top_level=True, x=x, y=y)
        first = self.project.chain(start, self._flat(*body))
        self.project.blocks[start]["next"] = first
        if add_reference_comment:
            self.project.add_comment(start, self._caller_reference(), x=x + 220, y=y - 10, width=300, height=90)
        return start

    def if_(self, condition: str, *body: Any) -> str:
        return self.project.if_block(condition, *self._flat(*body))

    def repeat_until(self, condition: str, *body: Any) -> str:
        return self.project.repeat_until(condition, *self._flat(*body))

    def repeat(self, times: Any, *body: Any) -> str:
        return self.project.repeat(times, *self._flat(*body))

    def procedure(self, name: str, args: list[str], *body: Any, x: int = 700, y: int = 160, add_reference_comment: bool = True) -> str:
        defid = self.project.define_procedure(name, args, x=x, y=y)
        self.project.attach_procedure_body(name, *self._flat(*body))
        if add_reference_comment:
            self.project.add_comment(defid, self._caller_reference(), x=x + 220, y=y - 10, width=320, height=90)
        return defid

    def call(self, name: str, *args: Any) -> str:
        return self.project.call_procedure(name, list(args))

    def chain(self, parent: str, *body: Any) -> str | None:
        first = self.project.chain(parent, self._flat(*body))
        self.project.blocks[parent]["next"] = first
        return first

    def seq(self, *items: Any) -> list[str]:
        return self._flat(*items)

    def do(self, *items: Any) -> list[str]:
        return self.seq(*items)

    def proc(self, name: str, args: list[str], *body: Any, x: int = 700, y: int = 160, add_reference_comment: bool = True) -> str:
        return self.procedure(name, args, *body, x=x, y=y, add_reference_comment=add_reference_comment)

    def comment(self, block_id: str, text: str, *, x: int | None = None, y: int | None = None, width: int = 260, height: int = 120) -> str:
        return self.project.add_comment(block_id, text, x=x, y=y, width=width, height=height)
