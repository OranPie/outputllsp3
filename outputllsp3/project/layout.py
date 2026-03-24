"""Auto-layout manager for top-level and procedure block positioning.

``LayoutManager`` tracks block positions so callers don't need to
hard-code canvas coordinates.  ``FlowBuilder.start()`` and
``FlowBuilder.procedure()`` use it automatically when no explicit
``x``/``y`` is supplied.

Canvas layout
-------------
Three visual regions are used:

  Left column   (x ≈ -220) : ``whenProgramStarts`` entry points
  Middle column (x ≈ +250) : other event-handler hat blocks
  Right grid    (x ≥  700) : custom procedure definitions, arranged
                              in rows; wraps when a row limit is reached

Public API
----------
- ``LayoutManager``               – tracks and dispenses positions
- ``LayoutManager.next_start()``  – position for a program-start block
- ``LayoutManager.next_event()``  – position for any other event hat
- ``LayoutManager.next_procedure()`` – position for a procedure def
- ``LayoutManager.relayout(blocks)`` – post-process to eliminate
                                       overlap based on actual stack depths
"""
from __future__ import annotations

# ── Canvas constants (approximate SPIKE editor pixel values) ─────────────────
_BLOCK_H = 72      # canvas pixels per block line (averaged across block types)
_HAT_EXTRA = 20    # extra height for hat/event hat blocks
_STACK_GAP = 80    # minimum vertical gap between consecutive stacks


class LayoutManager:
    """Dispenses canvas positions for start, event, and procedure blocks.

    Three visual regions are supported:

    * **Start column** (``start_x``, default -220) – ``whenProgramStarts``
      blocks stacked vertically.
    * **Event column** (``event_x``, default +250) – other event hats
      (whenButton, whenGesture, etc.) also stacked vertically.
    * **Procedure grid** (``proc_x_initial`` onwards, default 700) –
      procedure definitions laid out in rows; wraps to a new row after
      ``proc_x_wrap`` pixels.

    Parameters
    ----------
    start_x:
        X coordinate for all ``whenProgramStarts`` hat blocks.
    start_y_initial:
        Y coordinate of the first start/event block.
    start_y_step:
        Fixed vertical spacing used for *initial* placement (before
        ``relayout`` is called).  ``relayout`` overrides this with
        stack-depth-aware spacing.
    event_x:
        X coordinate for non-start event handler hat blocks.
    proc_x_initial:
        X coordinate of the first procedure definition.
    proc_x_step:
        Horizontal spacing between consecutive procedures in a row.
    proc_x_wrap:
        Maximum X before wrapping procedures to a new row.
    proc_y:
        Y coordinate of the first procedure row.
    proc_y_step:
        Vertical distance between procedure rows.
    """

    def __init__(
        self,
        *,
        start_x: int = -220,
        start_y_initial: int = 90,
        start_y_step: int = 500,
        event_x: int = 250,
        proc_x_initial: int = 700,
        proc_x_step: int = 400,
        proc_x_wrap: int = 2000,
        proc_y: int = 160,
        proc_y_step: int = 600,
    ) -> None:
        self._start_x = start_x
        self._start_y = start_y_initial
        self._start_y_step = start_y_step
        self._event_x = event_x
        self._event_y = start_y_initial
        self._proc_x = proc_x_initial
        self._proc_x_step = proc_x_step
        self._proc_x_wrap = proc_x_wrap
        self._proc_y = proc_y
        self._proc_y_step = proc_y_step

        # Keep true initials for reset()
        self._ini = dict(
            start_x=start_x,
            start_y=start_y_initial,
            start_y_step=start_y_step,
            event_x=event_x,
            proc_x=proc_x_initial,
            proc_x_step=proc_x_step,
            proc_x_wrap=proc_x_wrap,
            proc_y=proc_y,
            proc_y_step=proc_y_step,
        )

    # ── Start blocks ─────────────────────────────────────────────────────────

    def next_start(self) -> tuple[int, int]:
        """Return ``(x, y)`` for the next ``whenProgramStarts`` hat block.

        Blocks are stacked vertically in the left column.
        """
        pos = (self._start_x, self._start_y)
        self._start_y += self._start_y_step
        return pos

    # ── Event handler blocks ─────────────────────────────────────────────────

    def next_event(self) -> tuple[int, int]:
        """Return ``(x, y)`` for the next non-start event handler hat block.

        Events (whenButton, whenGesture, etc.) are placed in a second
        column to the right of the starts column, keeping them visually
        distinct from program entry points.
        """
        pos = (self._event_x, self._event_y)
        self._event_y += self._start_y_step
        return pos

    # ── Procedure definitions ─────────────────────────────────────────────────

    def next_procedure(self) -> tuple[int, int]:
        """Return ``(x, y)`` for the next procedure definition block.

        Procedures are arranged in a grid: they advance rightward along
        a row and wrap to a new row when ``proc_x_wrap`` is exceeded.
        """
        pos = (self._proc_x, self._proc_y)
        self._proc_x += self._proc_x_step
        if self._proc_x >= self._proc_x_wrap:
            self._proc_x = self._ini['proc_x']
            self._proc_y += self._proc_y_step
        return pos

    # ── Post-process layout ───────────────────────────────────────────────────

    def relayout(self, blocks: dict) -> None:
        """Re-compute positions for all top-level blocks based on actual stack depths.

        After all blocks have been added, call this to eliminate gaps and
        overlaps that result from the fixed-step initial placement.  Each
        stack's y-reservation is derived from its linear chain length
        (blocks connected via ``next`` pointers).

        * Start blocks     → left column, variable vertical spacing
        * Event hat blocks → middle column, same algorithm
        * Procedure defs   → right grid, row-wrapped placement

        Parameters are read from the values passed to ``__init__``.
        """
        starts: list[str] = []
        events: list[str] = []
        procs: list[str] = []

        for bid, block in blocks.items():
            if not block.get('topLevel'):
                continue
            op = block.get('opcode', '')
            if op == 'procedures_definition':
                procs.append(bid)
            elif op in {'flipperevents_whenProgramStarts',
                        'horizontalevents_whenProgramStarts'}:
                starts.append(bid)
            else:
                events.append(bid)

        def _stack_reserve(bid: str) -> int:
            """Pixels to reserve for this stack (hat + chain depth)."""
            depth = 0
            cur: str | None = bid
            seen: set[str] = set()
            while cur and cur not in seen and cur in blocks:
                seen.add(cur)
                depth += 1
                cur = blocks[cur].get('next')
            return _HAT_EXTRA + max(1, depth) * _BLOCK_H

        # ── Start column ──────────────────────────────────────────────────────
        y = self._ini['start_y']
        for bid in starts:
            blocks[bid]['x'] = self._ini['start_x']
            blocks[bid]['y'] = y
            y += _stack_reserve(bid) + _STACK_GAP

        # ── Event column ──────────────────────────────────────────────────────
        y = self._ini['start_y']
        for bid in events:
            blocks[bid]['x'] = self._ini['event_x']
            blocks[bid]['y'] = y
            y += _stack_reserve(bid) + _STACK_GAP

        # ── Procedure grid ────────────────────────────────────────────────────
        px = self._ini['proc_x']
        py = self._ini['proc_y']
        for bid in procs:
            blocks[bid]['x'] = px
            blocks[bid]['y'] = py
            px += self._ini['proc_x_step']
            if px >= self._ini['proc_x_wrap']:
                px = self._ini['proc_x']
                py += self._ini['proc_y_step']

    # ── Reset ─────────────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Reset all position counters to their original initial values."""
        ini = self._ini
        self.__init__(
            start_x=ini['start_x'],
            start_y_initial=ini['start_y'],
            start_y_step=ini['start_y_step'],
            event_x=ini['event_x'],
            proc_x_initial=ini['proc_x'],
            proc_x_step=ini['proc_x_step'],
            proc_x_wrap=ini['proc_x_wrap'],
            proc_y=ini['proc_y'],
            proc_y_step=ini['proc_y_step'],
        )
