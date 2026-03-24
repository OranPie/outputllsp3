"""Standard library of reusable SPIKE procedure templates.

Each ``install_*`` function adds a small set of named procedures (and any
supporting variables) to an existing :class:`~outputllsp3.api.API` object.
Procedures follow the Scratch convention: they cannot return values directly,
so results are written to dedicated *result variables* that the caller reads
back after the call.

Usage
-----
::

    from outputllsp3 import LLSP3Project, API
    from outputllsp3.stdlib import install_math, install_timing, install_display

    project = LLSP3Project()
    api = API(project)

    install_math(api)       # adds Clamp / MapRange / Sign procedures
    install_timing(api)     # adds WaitOrTimeout procedure
    install_display(api)    # adds Countdown / FlashText procedures

    f  = api.flow
    v  = api.vars
    sl = api.stdlib          # fluent alias wired automatically by API

    f.start(
        # clamp sensor yaw to motor speed range
        f.call("Clamp", api.sensor.yaw(), -100, 100),
        api.motor.run("A", sl.clamp),           # sl.clamp → MATH_CLAMP reporter
        # wait until a button press or 3 second timeout
        v.set("WAIT_DONE", 0, namespace="_stdlib"),
        f.call("WaitOrTimeout", 3000),
        # display countdown from 5
        f.call("Countdown", 5),
    )

Default variable namespace
--------------------------
All variables created by the stdlib use ``namespace="_stdlib"`` by default.
Pass a different *ns* keyword argument to avoid name collisions when you
install stdlib functions multiple times for different purposes::

    install_math(api, ns="pid_math")
    install_math(api, ns="sensor_math")

Result variables exposed by :class:`StdLib`
-------------------------------------------
After calling the install helpers (or the fluent methods on :class:`StdLib`),
you can read result variable reporters via the shorthand properties:

- ``api.stdlib.clamp``      → reporter for ``MATH_CLAMP``
- ``api.stdlib.map_result`` → reporter for ``MATH_MAP``
- ``api.stdlib.sign``       → reporter for ``MATH_SIGN``
- ``api.stdlib.wait_done``  → reporter for ``WAIT_DONE``

Setting ``WAIT_DONE``
---------------------
``WaitOrTimeout`` polls ``WAIT_DONE`` (default ``0``) until it becomes ``1``
or the timeout elapses.  Set it to ``0`` *before* calling the procedure, and
to ``1`` from another hat (e.g. a button-press event handler)::

    # main hat
    f.start(
        v.set("WAIT_DONE", 0, namespace="_stdlib"),
        f.call("WaitOrTimeout", 5000),   # wait up to 5 s
        api.motor.run("A", 50),
    )

    # button-press event hat
    f.when("button", button="left",
        v.set("WAIT_DONE", 1, namespace="_stdlib"),
    )
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .api import API

__all__ = [
    "install_math",
    "install_timing",
    "install_display",
    "install_all",
    "StdLib",
]

# ---------------------------------------------------------------------------
# Math procedures: Clamp, MapRange, Sign
# ---------------------------------------------------------------------------

def install_math(api: "API", *, ns: str = "_stdlib") -> dict[str, Any]:
    """Install ``Clamp``, ``MapRange``, and ``Sign`` procedures.

    Result variables (all in *ns* namespace):

    - ``MATH_CLAMP`` — written by ``Clamp(value, lo, hi)``
    - ``MATH_MAP``   — written by ``MapRange(v, from_lo, from_hi, to_lo, to_hi)``
    - ``MATH_SIGN``  — written by ``Sign(value)``  (−1, 0, or 1)

    Returns a mapping of procedure names → definition block IDs.
    """
    V, O, F, P = api.vars, api.ops, api.flow, api.project

    V.add("MATH_CLAMP", 0, namespace=ns)
    V.add("MATH_MAP", 0, namespace=ns)
    V.add("MATH_SIGN", 0, namespace=ns)

    # -- Clamp(value, lo, hi) -------------------------------------------
    # Sets MATH_CLAMP = max(lo, min(value, hi))
    clamp_id = F.procedure(
        "Clamp", ["value", "lo", "hi"],
        V.set("MATH_CLAMP", P.arg("value"), namespace=ns),
        F.if_(O.lt(P.arg("value"), P.arg("lo")),
              V.set("MATH_CLAMP", P.arg("lo"), namespace=ns)),
        F.if_(O.gt(P.arg("value"), P.arg("hi")),
              V.set("MATH_CLAMP", P.arg("hi"), namespace=ns)),
    )

    # -- MapRange(v, from_lo, from_hi, to_lo, to_hi) --------------------
    # Sets MATH_MAP = (v - from_lo) / (from_hi - from_lo) * (to_hi - to_lo) + to_lo
    # Each P.arg() call must be a fresh block — block IDs cannot be shared.
    map_id = F.procedure(
        "MapRange", ["v", "from_lo", "from_hi", "to_lo", "to_hi"],
        V.set("MATH_MAP",
              O.add(
                  O.mul(
                      O.div(
                          O.sub(P.arg("v"),       P.arg("from_lo")),
                          O.sub(P.arg("from_hi"), P.arg("from_lo")),
                      ),
                      O.sub(P.arg("to_hi"), P.arg("to_lo")),
                  ),
                  P.arg("to_lo"),
              ),
              namespace=ns),
    )

    # -- Sign(value) ----------------------------------------------------
    # Sets MATH_SIGN to −1, 0, or +1
    sign_id = F.procedure(
        "Sign", ["value"],
        V.set("MATH_SIGN", 0, namespace=ns),
        F.if_(O.gt(P.arg("value"), 0), V.set("MATH_SIGN", 1, namespace=ns)),
        F.if_(O.lt(P.arg("value"), 0), V.set("MATH_SIGN", -1, namespace=ns)),
    )

    return {
        "Clamp":    clamp_id,
        "MapRange": map_id,
        "Sign":     sign_id,
    }


# ---------------------------------------------------------------------------
# Timing procedures: WaitOrTimeout
# ---------------------------------------------------------------------------

def install_timing(api: "API", *, ns: str = "_stdlib") -> dict[str, Any]:
    """Install the ``WaitOrTimeout`` procedure.

    ``WaitOrTimeout(timeout_ms)`` polls the ``WAIT_DONE`` variable (in *ns*)
    until it equals ``1`` or the elapsed time exceeds *timeout_ms* milliseconds.
    The elapsed time is tracked in ``WAIT_ELAPSED`` (also in *ns*).

    **Protocol:**

    1. Set ``WAIT_DONE = 0`` before calling.
    2. Call ``WaitOrTimeout(timeout_ms)``.
    3. A separate event hat sets ``WAIT_DONE = 1`` when the condition is met.

    Returns a mapping of procedure names → definition block IDs.
    """
    V, O, F, W, P = api.vars, api.ops, api.flow, api.wait, api.project

    V.add("WAIT_DONE", 0, namespace=ns)
    V.add("WAIT_ELAPSED", 0, namespace=ns)

    done_var    = V.get("WAIT_DONE", namespace=ns)
    elapsed_var = V.get("WAIT_ELAPSED", namespace=ns)

    # repeat until WAIT_DONE == 1  OR  WAIT_ELAPSED >= timeout_ms
    # "WAIT_ELAPSED >= timeout_ms" expressed as NOT(WAIT_ELAPSED < timeout_ms)
    condition = O.or_(
        O.eq(done_var, 1),
        O.not_(O.lt(elapsed_var, P.arg("timeout_ms"))),
    )

    wait_id = F.procedure(
        "WaitOrTimeout", ["timeout_ms"],
        V.set("WAIT_ELAPSED", 0, namespace=ns),
        F.repeat_until(
            condition,
            W.seconds(0.02),
            V.change("WAIT_ELAPSED", 20, namespace=ns),
        ),
    )

    return {"WaitOrTimeout": wait_id}


# ---------------------------------------------------------------------------
# Display procedures: Countdown, FlashText
# ---------------------------------------------------------------------------

def install_display(api: "API", *, ns: str = "_stdlib") -> dict[str, Any]:
    """Install ``Countdown`` and ``FlashText`` display procedures.

    ``Countdown(n)``
        Shows ``n``, ``n-1``, … ``0`` on the hub display with 1-second pauses,
        then clears the display.  Good for race starts or timed challenges.

    ``FlashText(text, times)``
        Flashes *text* on the display *times* times (0.3 s on / 0.2 s off).
        Useful for communicating state at the end of a run.

    Returns a mapping of procedure names → definition block IDs.
    """
    V, O, F, L, W, P = api.vars, api.ops, api.flow, api.light, api.wait, api.project

    V.add("DISP_I", 0, namespace=ns)
    V.add("BLINK_I", 0, namespace=ns)

    # -- Countdown(n) ---------------------------------------------------
    # Shows n, n-1, …, 0 (1 s each) then clears
    # Each V.get() call creates a fresh reporter block (block IDs are single-parent).
    countdown_id = F.procedure(
        "Countdown", ["n"],
        V.set("DISP_I", P.arg("n"), namespace=ns),
        F.repeat_until(
            O.lt(V.get("DISP_I", namespace=ns), 0),
            L.show_text(V.get("DISP_I", namespace=ns)),
            W.seconds(1),
            V.change("DISP_I", -1, namespace=ns),
        ),
        L.clear(),
    )

    # -- FlashText(text, times) -----------------------------------------
    # Show text for 0.3 s, off for 0.2 s, repeat `times` times
    blink_var = V.get("BLINK_I", namespace=ns)
    flash_id = F.procedure(
        "FlashText", ["text", "times"],
        V.set("BLINK_I", P.arg("times"), namespace=ns),
        F.repeat_until(
            O.lt(blink_var, 1),
            L.show_text(P.arg("text")),
            W.seconds(0.3),
            L.clear(),
            W.seconds(0.2),
            V.change("BLINK_I", -1, namespace=ns),
        ),
    )

    return {
        "Countdown": countdown_id,
        "FlashText": flash_id,
    }


# ---------------------------------------------------------------------------
# Convenience: install_all
# ---------------------------------------------------------------------------

def install_all(api: "API", *, ns: str = "_stdlib") -> dict[str, Any]:
    """Install all stdlib procedure groups (math, timing, display).

    Equivalent to calling :func:`install_math`, :func:`install_timing`, and
    :func:`install_display` in sequence.  Returns a combined name→id dict.
    """
    results: dict[str, Any] = {}
    results.update(install_math(api, ns=ns))
    results.update(install_timing(api, ns=ns))
    results.update(install_display(api, ns=ns))
    return results


# ---------------------------------------------------------------------------
# StdLib — fluent façade wired into API.__post_init__
# ---------------------------------------------------------------------------

class StdLib:
    """Fluent wrapper around the stdlib install functions.

    Obtained via ``api.stdlib``.  Each method is idempotent: calling it a
    second time is a no-op.

    Example::

        api.stdlib.math().timing().display()

        # or all at once:
        api.stdlib.all()

    After installing, read result variable reporters via properties::

        clamp_speed = api.stdlib.clamp         # MATH_CLAMP reporter
        mapped      = api.stdlib.map_result    # MATH_MAP reporter
    """

    def __init__(self, api: "API", *, ns: str = "_stdlib") -> None:
        self._api = api
        self._ns  = ns
        self._installed: dict[str, dict[str, Any]] = {}

    # -- install methods (idempotent) ------------------------------------

    def math(self) -> "StdLib":
        """Install Clamp, MapRange, Sign.  Idempotent."""
        if "math" not in self._installed:
            self._installed["math"] = install_math(self._api, ns=self._ns)
        return self

    def timing(self) -> "StdLib":
        """Install WaitOrTimeout.  Idempotent."""
        if "timing" not in self._installed:
            self._installed["timing"] = install_timing(self._api, ns=self._ns)
        return self

    def display(self) -> "StdLib":
        """Install Countdown, FlashText.  Idempotent."""
        if "display" not in self._installed:
            self._installed["display"] = install_display(self._api, ns=self._ns)
        return self

    def all(self) -> "StdLib":
        """Install all stdlib groups.  Idempotent."""
        self.math().timing().display()
        return self

    # -- result variable reporters --------------------------------------

    @property
    def clamp(self) -> str:
        """Reporter block for ``MATH_CLAMP`` (set by ``Clamp``)."""
        return self._api.vars.get("MATH_CLAMP", namespace=self._ns)

    @property
    def map_result(self) -> str:
        """Reporter block for ``MATH_MAP`` (set by ``MapRange``)."""
        return self._api.vars.get("MATH_MAP", namespace=self._ns)

    @property
    def sign(self) -> str:
        """Reporter block for ``MATH_SIGN`` (set by ``Sign``)."""
        return self._api.vars.get("MATH_SIGN", namespace=self._ns)

    @property
    def wait_done(self) -> str:
        """Reporter block for ``WAIT_DONE`` semaphore."""
        return self._api.vars.get("WAIT_DONE", namespace=self._ns)

    def set_wait_done(self, value: Any = 1) -> str:
        """Emit a ``set WAIT_DONE = value`` block (use in event handlers)."""
        return self._api.vars.set("WAIT_DONE", value, namespace=self._ns)

    def reset_wait(self) -> str:
        """Emit ``set WAIT_DONE = 0`` (use before calling WaitOrTimeout)."""
        return self._api.vars.set("WAIT_DONE", 0, namespace=self._ns)

    # -- diagnostics ----------------------------------------------------

    def installed_groups(self) -> list[str]:
        """Return the list of stdlib groups that have been installed."""
        return list(self._installed.keys())

    def proc_ids(self) -> dict[str, Any]:
        """Return a flat name→id dict for all installed procedures."""
        result: dict[str, Any] = {}
        for group in self._installed.values():
            result.update(group)
        return result

    def __repr__(self) -> str:
        groups = self.installed_groups() or ["(none)"]
        return f"StdLib(ns={self._ns!r}, installed={groups})"
