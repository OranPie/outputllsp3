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

    def when(
        self,
        event_type: str,
        *body: Any,
        x: int | None = None,
        y: int | None = None,
        **kwargs: Any,
    ) -> str:
        """Create an event handler hat block.

        The returned block ID is a top-level hat that fires when the named
        event occurs.  Body blocks are chained directly below it.  Position is
        drawn from ``layout.next_event()`` unless *x*/*y* are provided.

        Parameters
        ----------
        event_type : str
            Type of event.  Supported values and their extra kwargs:

            ``'button'``       – ``button='left'|'right'|'center'|'any'``,
                                 ``action='pressed'|'released'``
            ``'gesture'``      – ``gesture='tapped'|'doubletapped'|'shake'|'freefall'``
            ``'orientation'``  – ``value='front'|'back'|'up'|'upside-down'|'leftside-up'|'rightside-up'``
            ``'tilted'``       – ``direction='any'|'front'|'back'|'leftside'|'rightside'``
            ``'timer'``        – ``threshold=5.0``
            ``'color'``        – ``port=Port.A``, ``color='any'|'red'|'blue'|...``
            ``'force'``        – ``port=Port.A``,
                                 ``option='pressed'|'hardpressed'|'released'|'pressurechanged'``
            ``'near'``         – ``port=Port.A``  (closer-than distance event)
            ``'far'``          – ``port=Port.A``  (farther-than distance event)
            ``'distance'``     – ``port=Port.A``,
                                 ``comparator='less_than'|'greater_than'``,
                                 ``value=10``
            ``'broadcast'``    – ``message='my_message'``
            ``'condition'``    – ``condition=<boolean_block_id>``
        *body : block IDs
            Blocks to run when the event fires.
        x, y : int, optional
            Canvas position (auto-assigned from layout if omitted).
        **kwargs
            Event-specific keyword arguments (see table above).

        Returns
        -------
        str
            The hat block ID.
        """
        if x is None or y is None:
            ax, ay = self.layout.next_event() if self.layout is not None else (250, 90)
            x = ax if x is None else x
            y = ay if y is None else y

        proj = self.project
        ev = event_type.lower()

        # ── Helper: shadow menu block ──────────────────────────────────────────
        def _menu(opcode: str, field_key: str, value: Any) -> str:
            return proj.add_block(opcode, shadow=True,
                                  fields={field_key: [str(value), None]})

        def _port(raw: Any) -> str:
            """Normalise Port enum / plain string to a letter like 'A'."""
            return raw.value if hasattr(raw, 'value') else str(raw)

        # ── Hat block per event type ───────────────────────────────────────────
        if ev == 'button':
            btn = kwargs.get('button', 'left')
            evt = kwargs.get('action', kwargs.get('event', 'pressed'))
            hat = proj.add_block(
                'flipperevents_whenButton', top_level=True, x=x, y=y,
                fields={'BUTTON': [btn, None], 'EVENT': [evt, None]},
            )

        elif ev == 'gesture':
            gest = kwargs.get('gesture', 'tapped')
            hat = proj.add_block(
                'flipperevents_whenGesture', top_level=True, x=x, y=y,
                fields={'EVENT': [gest, None]},
            )

        elif ev == 'orientation':
            val = kwargs.get('value', 'front')
            hat = proj.add_block(
                'flipperevents_whenOrientation', top_level=True, x=x, y=y,
                fields={'VALUE': [val, None]},
            )

        elif ev == 'tilted':
            direction = kwargs.get('direction', 'any')
            tilt_m = _menu('flipperevents_custom-tilted',
                           'field_flipperevents_custom-tilted', direction)
            hat = proj.add_block(
                'flipperevents_whenTilted', top_level=True, x=x, y=y,
                inputs={'VALUE': proj.ref_menu(tilt_m)},
            )

        elif ev == 'timer':
            threshold = kwargs.get('threshold', 5.0)
            hat = proj.add_block(
                'flipperevents_whenTimer', top_level=True, x=x, y=y,
                inputs={'VALUE': proj.lit_number(threshold)},
            )

        elif ev == 'color':
            port = _port(kwargs.get('port', 'A'))
            color = str(kwargs.get('color', 'any'))
            port_m = _menu('flipperevents_color-sensor-selector',
                           'field_flipperevents_color-sensor-selector', port)
            color_m = _menu('flipperevents_color-selector',
                            'field_flipperevents_color-selector', color)
            hat = proj.add_block(
                'flipperevents_whenColor', top_level=True, x=x, y=y,
                inputs={
                    'PORT': proj.ref_menu(port_m),
                    'OPTION': proj.ref_menu(color_m),
                },
            )

        elif ev in ('force', 'pressed'):
            port = _port(kwargs.get('port', 'A'))
            option = kwargs.get('option', 'pressed')
            port_m = _menu('flipperevents_force-sensor-selector',
                           'field_flipperevents_force-sensor-selector', port)
            hat = proj.add_block(
                'flipperevents_whenPressed', top_level=True, x=x, y=y,
                inputs={'PORT': proj.ref_menu(port_m)},
                fields={'OPTION': [option, None]},
            )

        elif ev in ('near', 'far', 'near_or_far'):
            # Map near/far to whenDistance with appropriate comparator
            port = _port(kwargs.get('port', 'A'))
            default_cmp = 'less_than' if ev == 'near' else 'greater_than'
            comparator = kwargs.get('comparator', default_cmp)
            value = kwargs.get('value', 10)
            port_m = _menu('flipperevents_distance-sensor-selector',
                           'field_flipperevents_distance-sensor-selector', port)
            hat = proj.add_block(
                'flipperevents_whenDistance', top_level=True, x=x, y=y,
                inputs={
                    'PORT': proj.ref_menu(port_m),
                    'VALUE': proj._num_input(value),
                },
                fields={'COMPARATOR': [comparator, None]},
            )

        elif ev == 'distance':
            port = _port(kwargs.get('port', 'A'))
            comparator = kwargs.get('comparator', 'less_than')
            value = kwargs.get('value', 10)
            port_m = _menu('flipperevents_distance-sensor-selector',
                           'field_flipperevents_distance-sensor-selector', port)
            hat = proj.add_block(
                'flipperevents_whenDistance', top_level=True, x=x, y=y,
                inputs={
                    'PORT': proj.ref_menu(port_m),
                    'VALUE': proj._num_input(value),
                },
                fields={'COMPARATOR': [comparator, None]},
            )

        elif ev in ('broadcast', 'message'):
            # Use standard Scratch broadcast-receive (registered in catalog)
            message = kwargs.get('message', 'message1')
            hat = proj.add_block(
                'event_whenbroadcastreceived', top_level=True, x=x, y=y,
                fields={'BROADCAST_OPTION': [message, None]},
            )

        elif ev == 'condition':
            cond = kwargs.get('condition')
            inputs = {}
            if cond is not None:
                inputs['CONDITION'] = proj.ref_bool(cond)
            hat = proj.add_block(
                'flipperevents_whenCondition', top_level=True, x=x, y=y,
                inputs=inputs,
            )

        else:
            raise ValueError(
                f"Unknown event_type {event_type!r}.  Valid values: "
                "button, gesture, orientation, tilted, timer, color, "
                "force, near, far, distance, broadcast, condition"
            )

        # Chain body blocks below the hat
        first = proj.chain(hat, self._flat(*body))
        proj.blocks[hat]['next'] = first
        return hat

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
