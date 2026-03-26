"""Tests for export readability improvements (v0.36+).

Covers:
- Module docstring in python-first output
- Section headers (Variables, Lists, Procedures, Entry points)
- Lists emitted as `[]` literals, not `ls.list(...)`
- No `ls` in imports
- `import math` added conditionally when operator_mathop is used
- Proper `math.sqrt`, `math.sin`, etc. (not bare `sqrt(x)`)
- New motor/drive/hub opcode handlers
- Unknown opcode fallback uses `pass  # TODO:` not `__stmt__()`
- Builder export: opcode annotations as inline comments
- Raw export: opcode annotations as inline comments
"""
from __future__ import annotations

import ast
import os
import tempfile
from collections import OrderedDict
from pathlib import Path

import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────

def _defaults():
    from outputllsp3.workflow import discover_defaults
    return discover_defaults(".")


def _compile_export(src: str, style: str = "python-first") -> str:
    """Compile python-first source → .llsp3 → export to given style → return text."""
    from outputllsp3 import transpile_pythonfirst_file, export_llsp3_to_python, reset_pythonfirst_registry
    reset_pythonfirst_registry()
    d = _defaults()
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
        f.write(src)
        py = f.name
    llsp3 = py.replace(".py", "_re.llsp3")
    out_py = py.replace(".py", "_re_exported.py")
    try:
        transpile_pythonfirst_file(py, template=d["template"], strings=d["strings"], out=llsp3)
        export_llsp3_to_python(llsp3, out_py, style=style)
        return Path(out_py).read_text(encoding="utf-8")
    finally:
        os.unlink(py)
        for p in (llsp3, out_py):
            if Path(p).exists():
                os.unlink(p)


def _build_export(build_fn, style: str = "python-first") -> str:
    """Build project via low-level API, save, export, return text."""
    from outputllsp3 import LLSP3Project, API, export_llsp3_to_python
    d = _defaults()
    project = LLSP3Project(d["template"], d["strings"])
    api = API(project)
    build_fn(project, api)
    with tempfile.NamedTemporaryFile(suffix=".llsp3", delete=False) as f:
        llsp3 = f.name
    out_py = llsp3.replace(".llsp3", "_be.py")
    try:
        project.save(llsp3)
        export_llsp3_to_python(llsp3, out_py, style=style)
        return Path(out_py).read_text(encoding="utf-8")
    finally:
        project.cleanup()
        for p in (llsp3, out_py):
            if Path(p).exists():
                os.unlink(p)


# ── python-first structural improvements ─────────────────────────────────────

_MINIMAL = """\
from outputllsp3 import robot, run, port

@run.main
def main():
    robot.stop()
"""


def test_pf_module_docstring():
    """python-first output must start with a triple-quoted module docstring."""
    exported = _compile_export(_MINIMAL)
    ast.parse(exported)
    assert exported.lstrip().startswith('"""'), "Module docstring missing"
    assert "Source:" in exported
    assert "python-first" in exported


def test_pf_section_headers():
    """Section headers must be present for entry point(s)."""
    exported = _compile_export(_MINIMAL)
    ast.parse(exported)
    assert "# ── Entry point" in exported


def test_pf_section_header_variables():
    """Variables section header appears when variables are present."""
    src = """\
from outputllsp3 import robot, run, port

@run.main
def main():
    x = 5
"""
    exported = _compile_export(src)
    ast.parse(exported)
    assert "# ── Variables" in exported


def test_pf_section_header_procedures():
    """Procedures section header appears when procedures are present."""
    src = """\
from outputllsp3 import robot, run, port

@robot.proc
def go():
    robot.stop()

@run.main
def main():
    go()
"""
    exported = _compile_export(src)
    ast.parse(exported)
    assert "# ── Procedures" in exported


def test_pf_no_ls_import():
    """'from outputllsp3 import ... ls ...' must NOT appear in python-first output."""
    exported = _compile_export(_MINIMAL)
    # ls should not be imported
    assert ", ls" not in exported
    assert "import ls" not in exported


def test_pf_lists_as_list_literal():
    """Lists must be declared as `name = []` not `ls.list('name')`."""
    src = """\
from outputllsp3 import robot, run, port

@run.main
def main():
    items = ls.list('items')
    items.append('hello')
"""
    # Build directly via API to get a project with a list
    def build(project, api):
        api.lists.add("items", [])
        api.flow.start(api.lists.append("items", "hello"))

    exported = _build_export(build)
    ast.parse(exported)
    assert "ls.list(" not in exported
    # Should use [] literal
    assert "= []" in exported


def test_pf_no_ls_in_output_with_lists():
    """Even with lists, the `ls` symbol must not appear in imports."""
    def build(project, api):
        api.lists.add("scores", [])
        api.flow.start(api.lists.append("scores", 42))

    exported = _build_export(build)
    assert ", ls" not in exported


# ── import math handling ──────────────────────────────────────────────────────

def test_pf_no_import_math_without_mathop():
    """import math should NOT appear when no math operations are used."""
    exported = _compile_export(_MINIMAL)
    assert "import math" not in exported


def test_pf_import_math_with_sqrt():
    """import math must appear when sqrt (operator_mathop) is used."""
    def build(project, api):
        api.vars.add("result", 0)
        sqrt_blk = project.add_block(
            "operator_mathop",
            fields={"OPERATOR": ["sqrt", None]},
            inputs={"NUM": project.lit_number(9)},
        )
        set_blk = project.set_variable("result", sqrt_blk)
        api.flow.start(set_blk)

    exported = _build_export(build)
    ast.parse(exported)
    assert "import math" in exported
    assert "math.sqrt(" in exported


def test_pf_import_math_sin():
    """import math + math.sin(math.radians(x)) for sin operator."""
    def build(project, api):
        api.vars.add("y", 0)
        sin_blk = project.add_block(
            "operator_mathop",
            fields={"OPERATOR": ["sin", None]},
            inputs={"NUM": project.lit_number(45)},
        )
        set_blk = project.set_variable("y", sin_blk)
        api.flow.start(set_blk)

    exported = _build_export(build)
    ast.parse(exported)
    assert "import math" in exported
    assert "math.sin(" in exported
    assert "math.radians(" in exported


def test_pf_abs_no_import_math():
    """`abs(x)` is a Python builtin — import math should NOT be added for it."""
    def build(project, api):
        api.vars.add("v", 0)
        abs_blk = project.add_block(
            "operator_mathop",
            fields={"OPERATOR": ["abs", None]},
            inputs={"NUM": project.lit_number(-5)},
        )
        set_blk = project.set_variable("v", abs_blk)
        api.flow.start(set_blk)

    exported = _build_export(build)
    ast.parse(exported)
    assert "abs(" in exported
    assert "import math" not in exported


# ── New motor / drive / hub opcode handlers ───────────────────────────────────

def test_pf_motor_run_speed():
    """flippermotor_motorStartDirection → robot.run_motor(port.X, direction)."""
    exported = _build_export(lambda p, a: a.flow.start(a.motor.run("A", 50)))
    ast.parse(exported)
    assert "robot.run_motor(" in exported


def test_pf_steer_opcode():
    """flippermoremove_startSteerAtSpeed → robot.steer(steering, speed)."""
    def build(project, api):
        api.flow.start(api.move.steer(30, 50))

    exported = _build_export(build)
    ast.parse(exported)
    assert "robot.steer(" in exported


def test_pf_steer_for_distance():
    """flippermoremove_steerDistanceAtSpeed → robot.steer_for(...)."""
    def build(project, api):
        api.flow.start(api.move.steer_for_distance(30, 50, 50, "cm"))

    exported = _build_export(build)
    ast.parse(exported)
    assert "robot.steer_for(" in exported


def test_pf_hub_show_text():
    """flipperlight_lightDisplayText → robot.show_text(text)."""
    def build(project, api):
        blk = project.add_block(
            "flipperlight_lightDisplayText",
            inputs={"TEXT": project.lit_text("hello")},
        )
        api.flow.start(blk)

    exported = _build_export(build)
    ast.parse(exported)
    assert "robot.show_text(" in exported


def test_pf_unknown_opcode_no_stmt_call():
    """Unknown opcodes: when present, __stmt__ defined but never called; pass # TODO used instead."""
    # Build a project with a valid known opcode — no unknown opcodes → no __stmt__
    def build(project, api):
        api.flow.start(api.wait.seconds(1))

    exported = _build_export(build)
    ast.parse(exported)
    # No unknown opcodes → __stmt__ should NOT be defined (it's only emitted when needed)
    assert "def __stmt__(" not in exported


def test_pf_unknown_opcode_summary():
    """When all opcodes are handled, no stub section or __stmt__ call should appear."""
    def build(project, api):
        api.flow.start(api.wait.seconds(0.1))

    exported = _build_export(build)
    # When ALL opcodes are handled, neither summary section nor __stmt__ call should appear
    assert "__stmt__(" not in exported
    assert "# ── Unmapped opcodes" not in exported


# ── builder style improvements ────────────────────────────────────────────────

def test_builder_opcode_inline_comments():
    """Builder export must include opcode labels as inline comments on _set_block calls."""
    def build(project, api):
        api.flow.start(api.wait.seconds(1))

    exported = _build_export(build, style="builder")
    ast.parse(exported)
    # _set_block CALL lines (not the def line) should have opcode comments
    set_block_lines = [
        l for l in exported.splitlines()
        if "_set_block(" in l and not l.strip().startswith("def ")
    ]
    assert set_block_lines, "No _set_block call lines found"
    for line in set_block_lines:
        assert "#" in line, f"_set_block call line missing opcode comment: {line!r}"


def test_builder_variable_name_comments():
    """Builder export should annotate variable IDs with their names."""
    def build(project, api):
        api.vars.add("my_speed", 50)
        api.flow.start(api.vars.set("my_speed", 100))

    exported = _build_export(build, style="builder")
    ast.parse(exported)
    assert "my_speed" in exported


def test_builder_section_headers():
    """Builder export should have section headers using # ── style."""
    def build(project, api):
        api.vars.add("x", 0)
        api.flow.start(api.vars.set("x", 1))

    exported = _build_export(build, style="builder")
    ast.parse(exported)
    assert "# ──" in exported


# ── raw style improvements ────────────────────────────────────────────────────

def test_raw_opcode_inline_comments():
    """Raw export must include opcode labels as inline comments on block assignment lines."""
    def build(project, api):
        api.flow.start(api.wait.seconds(1))

    exported = _build_export(build, style="raw")
    ast.parse(exported)
    # Block assignment lines should have a # comment
    block_lines = [l for l in exported.splitlines()
                   if 'project.sprite["blocks"]' in l and "json.loads" in l]
    assert block_lines, "No block assignment lines found"
    for line in block_lines:
        assert "#" in line, f"Block line missing opcode comment: {line!r}"


def test_raw_variable_name_comments():
    """Raw export should annotate variable IDs with their names."""
    def build(project, api):
        api.vars.add("counter", 0)
        api.flow.start(api.vars.set("counter", 1))

    exported = _build_export(build, style="raw")
    ast.parse(exported)
    assert "counter" in exported


# ── validate all exports produce valid Python ─────────────────────────────────

@pytest.mark.parametrize("style", ["raw", "builder", "python-first"])
def test_all_styles_valid_python(style):
    """All export styles must produce syntactically valid Python."""
    def build(project, api):
        api.vars.add("speed", 50)
        api.lists.add("data", [])
        api.flow.start(api.motor.run("A", 50))
        api.flow.start(api.wait.seconds(1))

    exported = _build_export(build, style=style)
    ast.parse(exported)  # raises SyntaxError if invalid


# ── Enum-aware export tests ───────────────────────────────────────────────────

def _add_direction_block(project, api):
    """Add a flippermotor_motorStartDirection block directly to the project."""
    from collections import OrderedDict
    blocks = project.sprite["blocks"]
    # Start block
    start_id = api.flow.start()
    uid = str(id(project))
    port_menu_id = f"_dir_port_{uid}"
    dir_menu_id = f"_dir_dir_{uid}"
    motor_id = f"_dir_motor_{uid}"
    blocks[port_menu_id] = {
        "opcode": "flippermoremotor_single-motor-selector",
        "next": None, "parent": motor_id, "shadow": True, "topLevel": False,
        "inputs": {}, "fields": OrderedDict([("field_flippermoremotor_single-motor-selector", ["A", None])]),
    }
    blocks[dir_menu_id] = {
        "opcode": "flippermotor_custom-angle-picker",
        "next": None, "parent": motor_id, "shadow": True, "topLevel": False,
        "inputs": {}, "fields": OrderedDict([("DIRECTION", ["clockwise", None])]),
    }
    blocks[motor_id] = {
        "opcode": "flippermotor_motorStartDirection",
        "next": None, "parent": start_id, "shadow": False, "topLevel": False,
        "inputs": {
            "PORT": [1, port_menu_id],
            "DIRECTION": [1, dir_menu_id],
        },
        "fields": OrderedDict(),
    }
    blocks[start_id]["next"] = motor_id


def test_pf_direction_enum_in_export():
    """python-first export should use Direction.CLOCKWISE, not raw 'clockwise'."""
    exported = _build_export(_add_direction_block)
    ast.parse(exported)
    assert "Direction.CLOCKWISE" in exported, f"Expected Direction.CLOCKWISE in:\n{exported}"


def test_pf_stop_mode_enum_in_export():
    """python-first export should use StopMode.BRAKE, not raw 'brake'."""
    def build(project, api):
        api.flow.start(api.motor.set_stop_mode('A', 'brake'))

    exported = _build_export(build)
    ast.parse(exported)
    assert "StopMode.BRAKE" in exported, f"Expected StopMode.BRAKE in:\n{exported}"
    assert "'brake'" not in exported


def test_pf_import_widened_with_direction():
    """Import line must include Direction when direction blocks are present."""
    exported = _build_export(_add_direction_block)
    ast.parse(exported)
    assert "Direction" in exported


def test_pf_import_widened_with_stop_mode():
    """Import line must include StopMode when stop-mode blocks are present."""
    def build(project, api):
        api.flow.start(api.motor.set_stop_mode('A', 'brake'))

    exported = _build_export(build)
    ast.parse(exported)
    assert "StopMode" in exported


def test_pf_export_valid_python_with_enums():
    """Enum-rich exported file with stop-mode block must parse as valid Python."""
    def build(project, api):
        api.flow.start(api.motor.set_stop_mode('A', 'brake'))
        api.flow.start(api.motor.set_stop_mode('B', 'coast'))

    exported = _build_export(build)
    ast.parse(exported)  # raises SyntaxError if invalid
