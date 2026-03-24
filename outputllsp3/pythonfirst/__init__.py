"""Python-first decorator-based transpiler.

The *python-first* mode lets authors write LEGO SPIKE programs in idiomatic
Python using a small set of decorators and runtime helpers, then compiles them
directly to ``.llsp3`` projects:

.. code-block:: python

    from outputllsp3 import robot, run, port, ls

    @robot.proc
    def move_square(side=20, speed=420):
        for _ in range(4):
            robot.forward_cm(side, speed)
            robot.turn_deg(90, 260)

    @run.main
    def main():
        robot.use_pair(port.B, port.A)
        move_square()          # all defaults
        move_square(30)        # override side

Public API
----------
- ``robot``  – ``@robot.proc`` decorator + movement helpers namespace
- ``run``    – ``@run.main`` decorator + sleep helpers
- ``port``   – port constants (``port.A`` … ``port.F``)
- ``ls``     – list declaration helper (``ls.list(name)``)
- ``PythonFirstContext`` – low-level AST compiler class
- ``transpile_pythonfirst_file(path, …)`` – compile and save ``.llsp3``
- ``reset_pythonfirst_registry()`` – no-op kept for backward compatibility
"""
from .runtime import robot, run, port, ls, _RobotModule, _RunModule, _PortModule, _ListModule
from .compiler import PythonFirstContext, LoopContext, ReturnContext, UnsupportedNode, _load_source
from .registry import transpile_pythonfirst_file, reset_pythonfirst_registry

__all__ = [
    "robot",
    "run",
    "port",
    "ls",
    "PythonFirstContext",
    "LoopContext",
    "ReturnContext",
    "UnsupportedNode",
    "transpile_pythonfirst_file",
    "reset_pythonfirst_registry",
]
