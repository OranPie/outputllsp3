# outputllsp3

A Python library for building, parsing, and exporting LEGO Education SPIKE App
project files (`.llsp3`).

---

## Overview

SPIKE App programs are stored as `.llsp3` archives — a ZIP-inside-ZIP format
containing a Scratch 3 block graph encoded in JSON.  `outputllsp3` gives you
three complementary ways to work with these files from Python:

| Mode | What you write | API |
|------|---------------|-----|
| **Build script** | `build(project, api, ns)` function | `transpile_path` |
| **Python-first** | `@robot.proc` / `@run.main` decorators | `transpile_pythonfirst_file` |
| **AST transpiler** | SPIKE-Python source file | `transpile_python_source` |
| **Export** | nothing — reads an existing `.llsp3` | `export_llsp3_to_python` |

---

## Installation

```bash
pip install .          # standard
pip install -e .       # editable / development
```

Python ≥ 3.9 required.  No third-party dependencies.

---

## Quick Start

### Python-first (recommended for new programs)

```python
# prog.py
from outputllsp3 import robot, run, port

@robot.proc
def move_square(side=20, speed=420):
    for _ in range(4):
        robot.forward_cm(side, speed)
        robot.turn_deg(90, 260)

@run.main
def main():
    robot.use_pair(port.B, port.A)
    move_square()        # uses defaults
    move_square(30)      # override side
```

```bash
outputllsp3 build-python prog.py --out prog.llsp3
```

### Build script

```python
# build_robot.py
from outputllsp3 import ENUMS

def build(project, api, ns):
    api.flow.start(
        api.move.set_pair("AB"),
        api.robot.straight_cm(30, 420),
        api.robot.turn_deg(90, 260),
        api.robot.stop(),
    )
```

```bash
outputllsp3 build build_robot.py --out robot.llsp3
```

### Export an existing project

```bash
outputllsp3 export-python existing.llsp3 --out decompiled.py --style python-first
```

---

## CLI Reference

Run `outputllsp3 --help` for the full list.  Common sub-commands:

```
build             Compile a build-script Python file/package → .llsp3
build-ast         Compile a SPIKE-Python source file → .llsp3 (AST mode)
build-python      Compile a python-first source file → .llsp3
export-python     Decompile .llsp3 → Python
inspect           Print summary of an .llsp3 file
roundtrip         Copy an .llsp3 with canonical member ordering
doctor            Health-check a workspace directory
init              Scaffold a new workspace
version           Show package version and metadata
changelog         Show the version changelog
features          Show the feature catalogue
docs-index        Show the documentation file index
```

---

## Package Layout

```
outputllsp3/
├── version.py          __version__ constant
├── metadata.py         Package identity, CHANGELOG, PACKAGE_LAYOUT
├── enums.py            Safe enum wrappers (MotorPair, Port, Button, …)
│
├── parser.py           LLSP3Document + parse_llsp3()
├── project.py          LLSP3Project – low-level block builder
├── catalog.py          BlockCatalog – block template registry
├── schema.py           SchemaRegistry – verified-opcode registry
│
├── api.py              API, RobotAPI – high-level facade dataclasses
├── flow.py             FlowBuilder – block sequencing helpers
├── wrapper.py          ScratchWrapper – module-discovery facade
├── spikepython.py      SpikePythonAPI – SPIKE Python library facade
│
├── transpiler.py       Classic build-script transpiler
├── ast_transpiler.py   Python AST → Scratch blocks transpiler
├── pythonfirst.py      Python-first decorator transpiler
│
├── exporter.py         LLSP3 → Python decompiler
│
├── workflow.py         CLI utilities (doctor, init, roundtrip, …)
├── cli.py              CLI entry-point (outputllsp3 command)
│
└── resources/
    ├── ok.llsp3            Minimal LLSP3 template
    ├── full.llsp3          Full template with all blocks
    ├── block_reference.llsp3  Block reference for opcode discovery
    └── strings.json        Scratch block string definitions
```

See [PACKAGE_STRUCTURE.md](PACKAGE_STRUCTURE.md) for a detailed architecture
guide.

---

## Documentation

| Document | Contents |
|----------|----------|
| [README.md](README.md) | This file – overview and quick start |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [PACKAGE_STRUCTURE.md](PACKAGE_STRUCTURE.md) | Architecture and module guide |
| [docs/FACADE_GUIDE.md](docs/FACADE_GUIDE.md) | Daily API usage guide |
| [docs/SPIKE_PYTHON_FACADE.md](docs/SPIKE_PYTHON_FACADE.md) | SpikePython reference |
| [docs/WRAPPER_FACADE.md](docs/WRAPPER_FACADE.md) | ScratchWrapper reference |
| [docs/SPIKE_WRAPPER_MAPPING.md](docs/SPIKE_WRAPPER_MAPPING.md) | Spike ↔ Wrapper compatibility |
| [docs/SCRATCH_MODULES.md](docs/SCRATCH_MODULES.md) | Scratch module coverage |
| [docs/STRICT_VERIFIED.md](docs/STRICT_VERIFIED.md) | Strict verified opcode mode |
| [docs/SPIKE_OFFICIAL_SUPPLEMENT.md](docs/SPIKE_OFFICIAL_SUPPLEMENT.md) | SPIKE app notes |

---

## Examples

See the [`examples/`](examples/) directory:

| File | What it demonstrates |
|------|---------------------|
| `hello_build.py` | Minimal build-script |
| `strict_build.py` | Strict verified mode |
| `python_first_robot.py` | Python-first movement sequence |
| `python_first_defaults.py` | Default parameter values |
| `python_first_return.py` | Return values from procedures |
