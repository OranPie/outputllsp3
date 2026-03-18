"""Command-line interface for outputllsp3.

All sub-commands are implemented as ``cmd_*`` functions and registered with
``argparse``.  The ``main()`` function is the console-scripts entry point
declared in ``setup.cfg``.

Sub-commands
------------
======================  =====================================================
build                   Compile a build-script Python file/package → .llsp3
build-ast               Compile a SPIKE-Python source file → .llsp3 (AST mode)
build-python            Compile a python-first source file → .llsp3
export-python           Decompile an .llsp3 → Python (raw / builder / python-first)
inspect                 Print block/variable/procedure summary for an .llsp3
roundtrip               Copy an .llsp3 with canonical member ordering
autodiscover            Show discovered template/strings paths for a workspace
doctor                  Health-check a workspace directory
init                    Scaffold a new robot programming workspace
bundled-paths           Show paths to bundled resource files
verified-opcodes        Dump the verified opcode registry
docs-index              Dump the documentation file index
features                Dump the feature list
version                 Show package version and metadata
changelog               Show the version changelog
modules                 List available Scratch modules
describe                Describe one module or block by name
======================  =====================================================
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .catalog import BlockCatalog
from .parser import parse_llsp3
from .transpiler import autodiscover, transpile_path
from .ast_transpiler import transpile_python_source
from .pythonfirst import transpile_pythonfirst_file
from .workflow import bundled_paths, doctor_report, init_workspace, roundtrip_llsp3, discover_defaults, docs_index
from .project import LLSP3Project
from .schema import bundled_schema
from .exporter import export_llsp3_to_python
from .metadata import package_info, FEATURES, CHANGELOG
from .locale import set_locale, available_locales


def _wrapper_for(base: str | None = None, strict_verified: bool = False):
    defaults = discover_defaults(base or '.')
    project = LLSP3Project(defaults['template'], defaults['strings'])
    project.set_strict_verified(strict_verified)
    from .wrapper import ScratchWrapper
    wrapper = ScratchWrapper(project)
    return project, wrapper




def cmd_export_python(args):
    out = export_llsp3_to_python(args.path, args.out, style=args.style)
    print(f'[OK] wrote {out}')
    return 0

def cmd_modules(args):
    project, wrapper = _wrapper_for(args.base, strict_verified=args.verified_only)
    try:
        if args.module:
            print(json.dumps(wrapper.describe(args.module), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(wrapper.available_modules(verified_only=args.verified_only), ensure_ascii=False, indent=2))
        return 0
    finally:
        project.cleanup()


def cmd_describe(args):
    project, wrapper = _wrapper_for(args.base, strict_verified=args.verified_only)
    try:
        print(json.dumps(wrapper.describe(args.module, args.name), ensure_ascii=False, indent=2))
        return 0
    finally:
        project.cleanup()


def cmd_inspect(args):
    doc = parse_llsp3(args.path)
    print(json.dumps(doc.summary(), ensure_ascii=False, indent=2))
    if args.opcodes:
        print(json.dumps(doc.opcode_counts(), ensure_ascii=False, indent=2))
    return 0


def cmd_catalog(args):
    catalog = BlockCatalog(args.strings)
    Path(args.out).write_text(json.dumps(catalog.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'[OK] wrote {args.out}')
    return 0


def cmd_build(args):
    out = transpile_path(args.path, template=args.template, strings=args.strings, out=args.out, sprite_name=args.sprite_name, function_namespace=args.function_namespace, strict_verified=args.strict_verified)
    print(f'[OK] wrote {out}')
    return 0


def cmd_build_ast(args):
    out = transpile_python_source(args.path, template=args.template, strings=args.strings, out=args.out, sprite_name=args.sprite_name, function_namespace=args.function_namespace)
    print(f'[OK] wrote {out}')
    return 0


def cmd_build_python(args):
    out = transpile_pythonfirst_file(args.path, template=args.template, strings=args.strings, out=args.out, sprite_name=args.sprite_name, strict_verified=args.strict_verified)
    print(f'[OK] wrote {out}')
    return 0


def cmd_autodiscover(args):
    info = autodiscover(args.path)
    print(json.dumps({k: str(v) if v else None for k, v in info.items()}, ensure_ascii=False, indent=2))
    return 0


def cmd_doctor(args):
    print(json.dumps(doctor_report(args.path), ensure_ascii=False, indent=2))
    return 0


def cmd_init(args):
    out = init_workspace(args.dir, package_name=args.name, include_resources=not args.no_resources)
    print(f'[OK] initialized {out}')
    return 0


def cmd_roundtrip(args):
    out = roundtrip_llsp3(args.path, args.out)
    print(f'[OK] wrote {out}')
    return 0


def cmd_bundled(args):
    print(json.dumps({k: str(v) for k, v in bundled_paths().items()}, ensure_ascii=False, indent=2))
    return 0


def cmd_verified_opcodes(args):
    data = bundled_schema().to_dict()
    if args.out:
        Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"[OK] wrote {args.out}")
        return 0
    print(json.dumps(data if args.full else sorted(data), ensure_ascii=False, indent=2))
    return 0


def cmd_docs_index(args):
    print(json.dumps(docs_index(), ensure_ascii=False, indent=2))
    return 0


def cmd_features(args):
    print(json.dumps(FEATURES, ensure_ascii=False, indent=2))
    return 0


def cmd_version(args):
    print(json.dumps(package_info(), ensure_ascii=False, indent=2))
    return 0


def cmd_changelog(args):
    print(json.dumps(CHANGELOG, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='OutputLLSP3 workflow-first parser + transpiler')
    p.add_argument('--verbose', '-v', action='store_true', help='Enable verbose transpiler logging')
    p.add_argument('--locale', choices=available_locales(), default=None, help='Set locale for messages (e.g. zh_CN)')
    sub = p.add_subparsers(dest='cmd', required=True)

    ep = sub.add_parser('export-python')
    ep.add_argument('path')
    ep.add_argument('--out', required=True)
    ep.add_argument('--style', default='raw', choices=['raw', 'builder', 'python-first'])
    ep.set_defaults(func=cmd_export_python)

    i = sub.add_parser('inspect')
    i.add_argument('path')
    i.add_argument('--opcodes', action='store_true')
    i.set_defaults(func=cmd_inspect)

    c = sub.add_parser('catalog')
    c.add_argument('--strings', required=True)
    c.add_argument('--out', required=True)
    c.set_defaults(func=cmd_catalog)

    a = sub.add_parser('autodiscover')
    a.add_argument('path', nargs='?', default='.')
    a.set_defaults(func=cmd_autodiscover)

    d = sub.add_parser('doctor')
    d.add_argument('path', nargs='?', default='.')
    d.set_defaults(func=cmd_doctor)

    init = sub.add_parser('init')
    init.add_argument('dir')
    init.add_argument('--name', default='robot_pkg')
    init.add_argument('--no-resources', action='store_true')
    init.set_defaults(func=cmd_init)

    bund = sub.add_parser('bundled-paths')
    bund.set_defaults(func=cmd_bundled)

    v = sub.add_parser('verified-opcodes')
    v.add_argument('--full', action='store_true')
    v.add_argument('--out')
    v.set_defaults(func=cmd_verified_opcodes)

    docs = sub.add_parser('docs-index')
    docs.set_defaults(func=cmd_docs_index)

    feat = sub.add_parser('features')
    feat.set_defaults(func=cmd_features)

    ver = sub.add_parser('version')
    ver.set_defaults(func=cmd_version)

    ch = sub.add_parser('changelog')
    ch.set_defaults(func=cmd_changelog)

    b = sub.add_parser('build')
    b.add_argument('path')
    b.add_argument('--template')
    b.add_argument('--strings')
    b.add_argument('--out', required=True)
    b.add_argument('--sprite-name')
    b.add_argument('--function-namespace', action='store_true')
    b.add_argument('--strict-verified', action='store_true')
    b.set_defaults(func=cmd_build)

    ba = sub.add_parser('build-ast')
    ba.add_argument('path')
    ba.add_argument('--template')
    ba.add_argument('--strings')
    ba.add_argument('--out', required=True)
    ba.add_argument('--sprite-name')
    ba.add_argument('--function-namespace', action='store_true')
    ba.set_defaults(func=cmd_build_ast)

    bp = sub.add_parser('build-python')
    bp.add_argument('path')
    bp.add_argument('--template')
    bp.add_argument('--strings')
    bp.add_argument('--out', required=True)
    bp.add_argument('--sprite-name')
    bp.add_argument('--strict-verified', action='store_true')
    bp.set_defaults(func=cmd_build_python)

    rt = sub.add_parser('roundtrip')
    rt.add_argument('path')
    rt.add_argument('--out', required=True)
    rt.set_defaults(func=cmd_roundtrip)

    m = sub.add_parser('modules')
    m.add_argument('--base', default='.')
    m.add_argument('--module')
    m.add_argument('--verified-only', action='store_true')
    m.set_defaults(func=cmd_modules)

    desc = sub.add_parser('describe')
    desc.add_argument('module')
    desc.add_argument('name')
    desc.add_argument('--base', default='.')
    desc.add_argument('--verified-only', action='store_true')
    desc.set_defaults(func=cmd_describe)

    args = p.parse_args(argv)
    if args.locale:
        set_locale(args.locale)
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(name)s %(message)s')
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
