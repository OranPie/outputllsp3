"""outputllsp3 – Parser, transpiler, exporter, and builder for LLSP3 projects.

Package layout
--------------
infrastructure  version, metadata, enums
core            parser, project, catalog, schema
authoring       api, flow, wrapper, spikepython
transpile       transpiler, ast_transpiler, pythonfirst
export          exporter
workflow        workflow, cli

Quick-start examples
--------------------
Build from a build script::

    from outputllsp3 import transpile_path
    transpile_path('my_robot/', out='my_robot.llsp3')

Build using the python-first style::

    from outputllsp3 import robot, run, port, transpile_pythonfirst_file
    # (write your @robot.proc / @run.main file, then:)
    transpile_pythonfirst_file('prog.py', out='prog.llsp3')

Export a project back to Python::

    from outputllsp3 import export_llsp3_to_python
    export_llsp3_to_python('prog.llsp3', 'prog_out.py', style='python-first')
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------
from .version import __version__
from .metadata import package_info
from .enums import (
    ENUMS,
    MotorPair,
    MotorPort,
    Port,
    Button,
    MotorPairId,
    OrientationAxis,
    LightImage,
    ColorValue,
)
from .locale import set_locale, get_locale, t, available_locales

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
from .parser import LLSP3Document, parse_llsp3
from .project import LLSP3Project
from .catalog import BlockCatalog
from .schema import SchemaRegistry, bundled_schema

# ---------------------------------------------------------------------------
# Authoring facades
# ---------------------------------------------------------------------------
from .api import API, RobotAPI
from .flow import FlowBuilder
from .wrapper import ScratchWrapper
from .spikepython import SpikePythonAPI

# Legacy aliases kept for backward compatibility
WrapperAPI = ScratchWrapper
SPIKEAPI = SpikePythonAPI

# ---------------------------------------------------------------------------
# Transpilers
# ---------------------------------------------------------------------------
from .transpiler import (
    autodiscover,
    transpile_file,
    transpile_module,
    transpile_package,
    transpile_path,
)
from .ast_transpiler import transpile_python_source
from .pythonfirst import robot, run, port, ls, transpile_pythonfirst_file, reset_pythonfirst_registry

# ---------------------------------------------------------------------------
# Exporter
# ---------------------------------------------------------------------------
from .exporter import export_llsp3_to_python

# ---------------------------------------------------------------------------
# Workflow utilities
# ---------------------------------------------------------------------------
from .workflow import (
    bundled_paths,
    discover_defaults,
    doctor_report,
    init_workspace,
    roundtrip_llsp3,
)

# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------
__all__ = [
    # Infrastructure
    "__version__",
    "package_info",
    "ENUMS",
    "MotorPair",
    "MotorPort",
    "Port",
    "Button",
    "MotorPairId",
    "OrientationAxis",
    "LightImage",
    "ColorValue",
    "set_locale",
    "get_locale",
    "t",
    "available_locales",
    # Core
    "LLSP3Document",
    "parse_llsp3",
    "LLSP3Project",
    "BlockCatalog",
    "SchemaRegistry",
    "bundled_schema",
    # Authoring
    "API",
    "RobotAPI",
    "FlowBuilder",
    "ScratchWrapper",
    "SpikePythonAPI",
    "WrapperAPI",   # legacy alias
    "SPIKEAPI",     # legacy alias
    # Transpilers
    "autodiscover",
    "transpile_file",
    "transpile_module",
    "transpile_package",
    "transpile_path",
    "transpile_python_source",
    "robot",
    "run",
    "port",
    "ls",
    "transpile_pythonfirst_file",
    "reset_pythonfirst_registry",
    # Exporter
    "export_llsp3_to_python",
    # Workflow
    "bundled_paths",
    "discover_defaults",
    "doctor_report",
    "init_workspace",
    "roundtrip_llsp3",
]
