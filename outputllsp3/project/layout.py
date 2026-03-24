"""Auto-layout manager for top-level and procedure block positioning.

``LayoutManager`` tracks block positions so callers don't need to
hard-code canvas coordinates.  ``FlowBuilder.start()`` and
``FlowBuilder.procedure()`` use it automatically when no explicit
``x``/``y`` is supplied.

Public API
----------
- ``LayoutManager``  – tracks and dispenses next available positions
"""
from __future__ import annotations


class LayoutManager:
    """Dispenses canvas positions for start blocks and procedure definitions.

    Start blocks are stacked vertically in a left column (x ≈ -220).
    Procedure definitions are placed horizontally in a right section (y ≈ 160).

    Parameters
    ----------
    start_x:
        X coordinate for all ``whenProgramStarts`` hat blocks.
    start_y_initial:
        Y coordinate for the first start block.
    start_y_step:
        Vertical spacing between consecutive start blocks.
    proc_x_initial:
        X coordinate for the first procedure definition.
    proc_x_step:
        Horizontal spacing between consecutive procedure definitions.
    proc_y:
        Y coordinate shared by all procedure definitions.
    """

    def __init__(
        self,
        *,
        start_x: int = -220,
        start_y_initial: int = 90,
        start_y_step: int = 500,
        proc_x_initial: int = 700,
        proc_x_step: int = 400,
        proc_y: int = 160,
    ) -> None:
        self._start_x = start_x
        self._start_y = start_y_initial
        self._start_y_step = start_y_step
        self._proc_x = proc_x_initial
        self._proc_x_step = proc_x_step
        self._proc_y = proc_y

    # ------------------------------------------------------------------
    # Start blocks
    # ------------------------------------------------------------------

    def next_start(self) -> tuple[int, int]:
        """Return ``(x, y)`` for the next ``whenProgramStarts`` hat block."""
        pos = (self._start_x, self._start_y)
        self._start_y += self._start_y_step
        return pos

    # ------------------------------------------------------------------
    # Procedure definitions
    # ------------------------------------------------------------------

    def next_procedure(self) -> tuple[int, int]:
        """Return ``(x, y)`` for the next procedure definition block."""
        pos = (self._proc_x, self._proc_y)
        self._proc_x += self._proc_x_step
        return pos

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset all counters to their initial values."""
        self.__init__(
            start_x=self._start_x,
            start_y_initial=90,
            start_y_step=self._start_y_step,
            proc_x_initial=700,
            proc_x_step=self._proc_x_step,
            proc_y=self._proc_y,
        )
