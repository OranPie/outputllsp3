"""Block-sequencing helpers that sit between ``API`` and ``LLSP3Project``.

``FlowBuilder`` is a thin adapter used by ``API.flow`` and ``API.f``.  It
provides high-level helpers for constructing control-flow graphs:

- ``start(*body)``                   – attach a ``whenProgramStarts`` hat block
- ``procedure(name, args, *body)``   – define a custom Scratch procedure
- ``call(name, *args)``              – generate a ``procedures_call`` block
- ``if_(cond, *body)``               – ``control_if``
- ``if_else(cond, *then, **else_)``  – ``control_if_else``
- ``repeat(times, *body)``           – ``control_repeat``
- ``repeat_until(cond, *body)``      – ``control_repeat_until``
- ``chain(parent, *body)``           – attach a block sequence to a parent
- ``seq(*items)``                    – flatten a mixed list of IDs / lists
- ``comment(text, …)``               – attach a floating comment to a block
- ``for_loop(var, start, end, *body)`` – counted loop with auto-incrementing variable
- ``while_loop(condition, *body)``   – repeat while condition is true
- ``cond(condition, a, b)``          – inline if/else expression block

All methods return block IDs (strings) so they compose naturally with each
other and with the rest of the ``API`` facade.
"""
from __future__ import annotations

import inspect
from pathlib import Path

from dataclasses import dataclass
from typing import Any


@dataclass
class FlowBuilder:
    project: Any
    layout: Any = None  # LayoutManager | None

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

    def start(self, *body: Any, x: int | None = None, y: int | None = None, add_reference_comment: bool = True) -> str:
        if x is None or y is None:
            ax, ay = self.layout.next_start() if self.layout is not None else (-220, 90)
            x = ax if x is None else x
            y = ay if y is None else y
        start = self.project.add_block("flipperevents_whenProgramStarts", top_level=True, x=x, y=y)
        first = self.project.chain(start, self._flat(*body))
        self.project.blocks[start]["next"] = first
        if add_reference_comment:
            self.project.add_comment(start, self._caller_reference(), x=x + 220, y=y - 10, width=300, height=90)
        return start

    def if_(self, condition: str, *body: Any) -> str:
        return self.project.if_block(condition, *self._flat(*body))

    def if_else(self, condition: str, then_body: list[Any] | tuple[Any, ...], else_body: list[Any] | tuple[Any, ...]) -> str:
        """``control_if_else`` – if/else with two branches."""
        return self.project.if_else_block(condition, tuple(self._flat(*then_body)), tuple(self._flat(*else_body)))

    def forever(self, *body: Any) -> str:
        """``control_forever`` – infinite loop."""
        return self.project.forever(*self._flat(*body))

    def wait_until(self, condition: str) -> str:
        """``control_wait_until`` – block until condition is true."""
        return self.project.wait_until(condition)

    def stop(self) -> str:
        """``control_stop`` – stop all scripts."""
        return self.project.stop_all()

    def repeat_until(self, condition: str, *body: Any) -> str:
        return self.project.repeat_until(condition, *self._flat(*body))

    def repeat(self, times: Any, *body: Any) -> str:
        return self.project.repeat(times, *self._flat(*body))

    def procedure(self, name: str, args: list[str], *body: Any, defaults: list[Any] | None = None, x: int | None = None, y: int | None = None, add_reference_comment: bool = True) -> str:
        if x is None or y is None:
            ax, ay = self.layout.next_procedure() if self.layout is not None else (700, 160)
            x = ax if x is None else x
            y = ay if y is None else y
        defid = self.project.define_procedure(name, args, x=x, y=y, defaults=defaults)
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

    def proc(self, name: str, args: list[str], *body: Any, x: int | None = None, y: int | None = None, add_reference_comment: bool = True) -> str:
        return self.procedure(name, args, *body, x=x, y=y, add_reference_comment=add_reference_comment)

    def comment(self, block_id: str, text: str, *, x: int | None = None, y: int | None = None, width: int = 260, height: int = 120) -> str:
        return self.project.add_comment(block_id, text, x=x, y=y, width=width, height=height)

    def for_loop(self, var_name: str, start: Any, end: Any, *body: Any, step: Any = 1) -> list[str]:
        """Create a counted loop using a variable as counter.

        Emits: set var=start, repeat_until(var > end, *body + change_var(var, step))
        Returns a flat list of block IDs: [set_block, repeat_block].
        """
        set_id = self.project.set_variable(var_name, start)
        over = self.project.gt(self.project.variable(var_name), end)
        increment = self.project.change_variable(var_name, step)
        loop = self.project.repeat_until(over, *self._flat(*body), increment)
        return [set_id, loop]

    def while_loop(self, condition: str, *body: Any) -> str:
        """Repeat until NOT condition — sugar for repeat_until(not_(condition), body)."""
        return self.project.repeat_until(self.project.not_(condition), *self._flat(*body))

    def cond(self, condition: str, if_true: Any, if_false: Any) -> str:
        """Inline conditional: generates an ``if_else`` block and returns its ID.

        Both ``if_true`` and ``if_false`` should be single block IDs (expressions).
        The result ID can be used as an input to another block.
        """
        return self.project.if_else_block(condition, (if_true,), (if_false,))
