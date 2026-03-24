"""Package metadata: version, layout, feature catalogue, and changelog.

This module is the single source of truth for package identity information
and is intentionally import-cycle-free (only imports from ``.version``).
"""
from __future__ import annotations

PACKAGE_NAME = "outputllsp3"
from .version import __version__

VERSION = __version__
UPDATED_AT = "2026-03-18"
DOCS_UPDATED_AT = "2026-03-18"

# ---------------------------------------------------------------------------
# Declared package layout – all modules grouped by subsystem.
# ---------------------------------------------------------------------------
PACKAGE_LAYOUT = {
    "infrastructure": [
        "version.py",     # __version__ constant
        "metadata.py",    # package identity, CHANGELOG, FEATURES, PACKAGE_LAYOUT
        "enums.py",       # safe enum wrappers (MotorPair, Port, Button, …)
        "locale.py",      # i18n / l10n support (en, zh_CN catalogs; set_locale/t)
    ],
    "core": [
        "parser.py",                         # LLSP3Document + parse_llsp3() – reads .llsp/.llsp3 archives
        "project/__init__.py",               # LLSP3Project coordinator (delegates to sub-managers)
        "project/blocks.py",                 # BlockManager – block creation, chains, operators
        "project/variables.py",              # VariableManager – variables, lists, namespace
        "project/procedures.py",             # ProcedureManager – custom blocks define/call/attach
        "project/serializer.py",             # ProjectSerializer – validate, ZIP I/O, asset hashes
        "catalog.py",                        # BlockCatalog – block-template registry built from strings.json
        "schema.py",                         # SchemaRegistry / bundled_schema – verified-opcode registry
    ],
    "authoring": [
        "api.py",         # API, RobotAPI – high-level facade dataclasses (VarsAPI, OpsAPI, …)
        "builder.py",     # SpikeBuilder – fluent typed sub-namespace facade over API
        "flow.py",        # FlowBuilder – block-sequencing helpers (chain, seq, procedure, …)
        "wrapper.py",     # ScratchWrapper – module-discovery facade over LLSP3Project
        "spikepython.py", # SpikePythonAPI – SPIKE Python library facade (hub, motors, sensors)
    ],
    "transpile": [
        "transpiler.py",                       # Classic build-script transpiler (transpile_path/file/module/package)
        "ast_transpiler.py",                   # Python AST → Scratch blocks (transpile_python_source)
        "pythonfirst/__init__.py",             # Python-first package entry point
        "pythonfirst/runtime.py",              # Runtime stub classes (_RobotModule, _RunModule, etc.)
        "pythonfirst/registry.py",             # Decorator registry + transpile_pythonfirst_file entry point
        "pythonfirst/compiler.py",             # AST compiler (PythonFirstContext, LoopContext, ReturnContext)
    ],
    "export": [
        "exporter/__init__.py",   # LLSP3 → Python entry point (export_llsp3_to_python)
        "exporter/base.py",       # Shared helpers (_summary, _sanitize, _extract_literal, _value_ref)
        "exporter/raw.py",        # Raw export strategy (exact block reconstruction)
        "exporter/builder.py",    # Builder export strategy (human-editable exact export)
        "exporter/python_first.py", # Python-first export strategy (_PFExport decompiler)
    ],
    "workflow": [
        "workflow.py",    # CLI utilities (discover_defaults, doctor_report, init_workspace, roundtrip_llsp3)
        "cli.py",         # CLI entry-point (outputllsp3 command with all sub-commands)
    ],
    "resources": [
        "resources/ok.llsp3",            # Minimal LLSP3 template used as base for generated projects
        "resources/full.llsp3",          # Full LLSP3 template with all blocks available
        "resources/block_reference.llsp3", # Block reference template for opcode discovery
        "resources/strings.json",        # Scratch block string definitions (labels, menus)
    ],
}

FEATURES = {
    "core": [
        "parse .llsp/.llsp3",
        "build llsp3 from python build scripts",
        "export llsp3 back to python (raw, builder, and python-first styles)",
        "strict verified opcode mode",
        "bundled ok/full/block_reference/strings resources",
    ],
    "transpile": [
        "classic build-script transpiler (module/file/package)",
        "python AST → scratch blocks transpiler",
        "python-first decorator transpiler (@robot.proc / @run.main)",
        "default parameter values for custom procedures",
        "custom procedure return values via retval variables",
        "keyword arguments at call sites",
    ],
    "workflow": [
        "doctor",
        "init",
        "roundtrip",
        "bundled-paths",
        "verified-opcodes",
        "docs-index",
        "features",
        "version",
        "changelog",
    ],
    "facades": [
        "wrapper facade",
        "spike facade",
        "schema-backed module discovery",
        "expanded safe enums",
        "short aliases: api.v/o/m/s/f/db/e",
        "flow.chain/seq/comment helpers",
        "flow.if_else/forever/wait_until/stop helpers",
        "api.namespace() scoped variable prefixing",
        "verbose transpiler logging via Python logging module",
        "zh_CN (Simplified Chinese) localization",
        "OpsAPI: mod, round, join, length_of, letter_of, str_contains, random, mathop",
        "SensorAPI: pitch, roll, timer, loudness, button_pressed, color, distance, force, reflectivity",
        "MotorAPI: run, run_power, stop, run_for_degrees, run_for_seconds, set_stop_mode, absolute_position, speed",
        "LightAPI: show_text, show_image, show_image_for, set_pixel, clear, set_brightness, set_center_button",
        "SoundAPI: beep, beep_for, play, play_until_done, stop",
        "MoveAPI: steer, steer_for_distance",
        "python-first robot helpers: show_text, show_image, beep, reset_yaw, run_motor, stop_motor, angle, color, distance, force",
    ],
}
CHANGELOG = [
    {"version": "0.35.0", "date": "2026-03-18", "notes": [
        "OpsAPI: added mod, round, join, length_of, letter_of, str_contains, random, mathop helpers.",
        "SensorAPI: added pitch, roll, timer, reset_timer, loudness, button_pressed, color, is_color, distance, is_distance, force, is_pressed, reflectivity.",
        "MotorAPI: added run, run_power, stop, run_for_degrees, run_for_seconds, set_stop_mode, absolute_position, speed.",
        "New LightAPI facade: show_text, show_image, show_image_for, set_pixel, clear, set_brightness, set_center_button.",
        "New SoundAPI facade: beep, beep_for, play, play_until_done, stop.",
        "MoveAPI: added steer and steer_for_distance helpers.",
        "FlowBuilder: added wait_until and stop helpers.",
        "LLSP3Project: added mod, round_, join, length_of, letter_of, str_contains, random, wait_until, stop_all low-level methods.",
        "Python-first: added robot.show_text, robot.show_image, robot.clear_display, robot.beep, robot.stop_sound, robot.reset_yaw, robot.run_motor, robot.stop_motor, robot.motor_run_for_degrees.",
        "Python-first: added expression helpers robot.angle, robot.motor_relative_position, robot.motor_speed, robot.color, robot.distance, robot.force, robot.reflectivity.",
        "New public API exports: LightAPI, SoundAPI.",
    ]},
    {"version": "0.34.0", "date": "2026-03-18", "notes": [
        "Added verbose transpiler logging via Python logging module in all transpiler modules (transpiler, ast_transpiler, pythonfirst, exporter).",
        "Added zh_CN (Simplified Chinese) localization: new locale.py with message catalogs; set_locale('zh_CN') switches all log/UI messages to Chinese.",
        "New public API: set_locale(), get_locale(), t(), available_locales() exported from package root.",
        "FlowBuilder: added if_else(condition, then_body, else_body) helper for control_if_else blocks.",
        "FlowBuilder: added forever(*body) helper for control_forever blocks.",
        "LLSP3Project: added if_else_block() and forever() low-level methods.",
        "CLI: added --verbose / -v flag to enable DEBUG-level transpiler logging.",
        "CLI: added --locale flag to switch UI/log message language (en, zh_CN).",
    ]},
    {"version": "0.33.0", "date": "2026-03-17", "notes": [
        "Enhanced llsp3-to-Python export flow (python-first style) with many new opcode mappings.",
        "render_expr: added operator_and/or/not, operator_mod, operator_random (→ random.randint), operator_round, operator_join, operator_length, operator_letter_of, operator_contains.",
        "render_expr: added flipperoperator_isInBetween (→ lo <= v <= hi), data_itemnumoflist.",
        "render_expr: added sensor reporters: flippersensors_orientationAxis (→ robot.angle), flippersensors_timer, flippersensors_loudness, flippersensors_buttonIsPressed, flippersensors_ismotion, flippersensors_isTilted, flippersensors_isorientation, flippersensors_distance, flippersensors_reflectivity, flippersensors_color, flippersensors_isColor, flippersensors_isDistance, flippersensors_isPressed, flippersensors_force.",
        "render_expr: added flippermotor_speed, flippermotor_absolutePosition, flippermoremotor_position (→ robot.motor_relative_position).",
        "render_stmt: added control_forever (→ while True:), control_stop/flippercontrol_stop (→ return), control_wait_until (→ while not: run.sleep(0.01)).",
        "render_stmt: replaced __stmt__ placeholders with real calls: flippermove_setMovementPair → robot.use_pair(port.X, port.Y), flippermoremove_startDualSpeed → robot.drive, flippermoremove_startDualPower → robot.drive_power, flippermoremotor_motorSetDegreeCounted → robot.set_motor_position, flippersensors_resetYaw → robot.reset_yaw.",
        "render_stmt: added motor opcodes: flippermotor_motorStartDirection, flippermotor_motorStop, flippermotor_motorTurnForDirection, flippermotor_motorGoDirectionToPosition, flippermotor_motorSetSpeed.",
        "render_stmt: added sound opcodes: flippersound_beep, flippersound_beepForTime, flippersound_stopSound, flippersound_playSound, flippersound_playSoundUntilDone.",
        "render_stmt: added display opcodes: flipperdisplay_ledMatrix, flipperdisplay_ledMatrixFor, flipperdisplay_ledMatrixText, flipperdisplay_ledMatrixOff, flipperdisplay_ledMatrixOn, flipperdisplay_ledMatrixBrightness, flipperdisplay_centerButtonLight.",
        "render_stmt: fixed duplicate/broken procedures_call case (was relying on undocumented block.get('id') fallback).",
        "render: multiple whenProgramStarts stacks each become a separate @run.main-decorated function.",
        "render: added `import random` to the generated header.",
        "parser.LLSP3Document: added `lists` property for symmetry with `variables`.",
        "parser.LLSP3Document.summary(): added `list_count` and `list_names` fields.",
    ]},
    {"version": "0.32.0", "date": "2026-03-17", "notes": [
        "Added default parameter value support for @robot.proc procedures in python-first mode and AST transpiler.",
        "Params with defaults (e.g. `def move(speed=420, dist=20):`) store their defaults in the Scratch `argumentdefaults` mutation field.",
        "Calls with fewer args than params have missing positional args filled from the proc's stored defaults at the call site.",
        "Keyword arguments at call sites (e.g. `move(dist=30)`) are now supported and matched to the declared parameter order.",
        "project.py `define_procedure()` accepts an optional `defaults` list; `call_procedure()` applies defaults for missing args.",
        "flow.py `procedure()` accepts an optional `defaults` keyword argument.",
        "Exporter (python-first style) reads `argumentdefaults` from proc mutations and emits `def proc(a, b=default):` in the decompiled output.",
    ]},
    {"version": "0.31.0", "date": "2026-03-17", "notes": [
        "Added custom function return value support for @robot.proc procedures in python-first mode.",
        "Each proc that uses `return value` gets a unique `__retval_<proc>` variable (readable after the call) and a `__return_<proc>` flag that guards subsequent statements so they are skipped after return.",
        "Direct assignment from a proc call (`result = my_proc(args)`) is automatically lowered to call + retval read.",
        "Return inside a loop also sets the loop break flag so the loop exits immediately.",
        "Proc calls used inside expressions (not as a direct assignment RHS) fall back to reading the retval variable from the last call, with a compile note.",
        "Added the same return-value support to the AST transpiler (ast_transpiler.py).",
        "Exporter (python-first style) recognises the __retval_*/__return_* patterns and emits clean `return value` and `result = proc(args)` in the decompiled output.",
    ]},
    {"version": "0.29.0", "date": "2026-03-16", "notes": [
        "Fixed NameError in pythonfirst const_eval when a BoolOp expression appeared at module level.",
        "Fixed parent-pointer validation error when using `not (x == y)` in python-first mode (negate_condition Eq now uses not_(eq(...)) instead of a shared-reference or()).",
        "Fixed negate_condition fallback in python-first mode to use operator_not instead of eq(value, 0), avoiding 'equals connected to boolean opcode' validation errors.",
        "Fixed ast_transpiler negate_condition Eq case (was always returning True via gt(1,0); now uses not_(eq(...))).",
        "Fixed ast_transpiler negate_condition fallback from UnsupportedNode to graceful not_() wrapper.",
        "parser.parse_llsp3 now accepts .llsp files (same format as .llsp3), gives clearer error messages for missing archive members.",
        "Added export_llsp3_to_python to the public __all__ export list.",
    ]},
    {"version": "0.28.0", "date": "2026-03-15", "notes": [
        "python-first export now emits valid Python placeholders instead of invalid comment-like expression stubs.",
        "python-first export recognizes more drivebase and sensor patterns and lifts common procedure calls to robot.* helpers when possible.",
    ]},
    {"version": "0.26.0", "date": "2026-03-15", "notes": [
        "export-python now supports builder style for a cleaner, more editable exact reconstruction export.",
        "exported builder files include summary and high-level hints while preserving exact reconstruction semantics.",
    ]},
    {"version": "0.24.0", "date": "2026-03-15", "notes": [
        "Python-first range(start, stop, step) now lowers through a range-to-while strategy for constant non-zero integer steps, supporting dynamic start/stop expressions.",
        "Old build(project, api, ns, enums) compatibility remains supported.",
    ]},
    {"version": "0.23.0", "date": "2026-03-15", "notes": [
        "Python-first adds list.insert() and list.remove() lowering.",
        "Old build(project, api, ns, enums) compatibility remains supported.",
    ]},
    {"version": "0.21.0", "date": "2026-03-15", "notes": [
        "Python-first adds range(start, stop, step) for constant integer steps and higher-level list helpers (.contains/.get/.set).",
        "Old build(project, api, ns, enums) compatibility remains supported.",
    ]},
    {"version": "0.20.0", "date": "2026-03-15", "notes": [
        "Python-first adds while-else, `in`/`not in` as expressions, and more stable while break/continue lowering.",
        "Old build(project, api, ns, enums) compatibility remains supported.",
    ]},
    {"version": "0.19.0", "date": "2026-03-15", "notes": [
        "Python-first adds enumerate(list), while condition, and loop break/continue lowering.",
        "Old build(project, api, ns, enums) compatibility remains supported.",
    ]},
    {"version": "0.14.0", "date": "2026-03-15", "notes": [
        "python-first AST adds else, while condition, list setitem, and list iteration",
        "added ergonomic api aliases and scoped namespace helper",
        "added flow.chain/seq/comment helpers",
        "kept old build(project, api, ns, enums) compatibility while extending python-first lowering",
    ]},
    {"version": "0.12.0", "date": "2026-03-15", "notes": [
        "strict verified mode for non-fabricated block opcodes",
    ]},
]

def package_info() -> dict:
    return {
        "name": PACKAGE_NAME,
        "version": VERSION,
        "updated_at": UPDATED_AT,
        "docs_updated_at": DOCS_UPDATED_AT,
        "layout": PACKAGE_LAYOUT,
        "features": FEATURES,
    }
