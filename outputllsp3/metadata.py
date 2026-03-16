from __future__ import annotations

PACKAGE_NAME = "outputllsp3"
from .version import __version__

VERSION = __version__
UPDATED_AT = "2026-03-15"
DOCS_UPDATED_AT = "2026-03-15"
PACKAGE_LAYOUT = {
    "core": ["catalog.py", "parser.py", "project.py", "schema.py"],
    "authoring": ["api.py", "flow.py", "wrapper.py", "spikepython.py", "enums.py"],
    "transpile": ["transpiler.py", "ast_transpiler.py"],
    "workflow": ["workflow.py", "cli.py"],
    "resources": ["resources/ok.llsp3", "resources/full.llsp3", "resources/block_reference.llsp3", "resources/strings.json"],
}
FEATURES = {
    "core": [
        "parse .llsp/.llsp3",
        "build llsp3 from python build scripts",
        "export llsp3 back to python (raw, builder, and python-first styles)",
        "strict verified opcode mode",
        "bundled ok/full/block_reference/strings resources",
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
        "api.namespace() scoped variable prefixing",
    ],
}
CHANGELOG = [
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
