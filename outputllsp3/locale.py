"""Localization support for outputllsp3.

Provides a lightweight message catalog with translations for UI-facing strings
(CLI messages, log messages, and user-visible labels).  The built-in catalogs
are ``en`` (English, default) and ``zh_CN`` (Simplified Chinese).

Public API
----------
- ``set_locale(lang)``   – switch the active locale (e.g. ``'zh_CN'``)
- ``get_locale()``       – return the current locale string
- ``t(key, **kwargs)``   – translate *key* using the active catalog, with
  optional ``str.format`` interpolation.
- ``available_locales()`` – list all registered locale codes.
"""
from __future__ import annotations

_current_locale: str = "en"

# ---------------------------------------------------------------------------
# Message catalogs
# ---------------------------------------------------------------------------

_CATALOGS: dict[str, dict[str, str]] = {
    "en": {
        # transpiler logging
        "transpile.start": "Transpiling {path}",
        "transpile.file.start": "Transpiling file {path}",
        "transpile.package.start": "Transpiling package {path}",
        "transpile.module.start": "Transpiling module {module}",
        "transpile.module.build_call": "Calling build() on module {module}",
        "transpile.module.save": "Saving project to {out}",
        "transpile.module.done": "Transpile complete → {out}",
        "transpile.autodiscover": "Auto-discovered resources: template={template}, strings={strings}",
        "transpile.load_module": "Loading module from {path}",
        "transpile.load_package": "Loading package from {path}",
        # ast transpiler
        "ast.start": "AST transpiling {path}",
        "ast.parse": "Parsed AST for {path} ({count} top-level nodes)",
        "ast.function": "Compiling function {name} ({arg_count} args)",
        "ast.save": "Saving AST-transpiled project to {out}",
        "ast.done": "AST transpile complete → {out}",
        "ast.note": "AST note: {msg}",
        # pythonfirst
        "pf.start": "Python-first transpiling {path}",
        "pf.parse": "Parsed source for {path} ({count} top-level nodes)",
        "pf.proc": "Compiling @robot.proc {name} ({arg_count} args)",
        "pf.main": "Compiling @run.main {name}",
        "pf.save": "Saving python-first project to {out}",
        "pf.done": "Python-first transpile complete → {out}",
        "pf.note": "Python-first note: {msg}",
        # exporter
        "export.start": "Exporting {path} to Python (style={style})",
        "export.parse": "Parsed {path}: {block_count} blocks, {var_count} variables",
        "export.write": "Writing exported Python to {out}",
        "export.done": "Export complete → {out}",
        # CLI
        "cli.ok_wrote": "[OK] wrote {path}",
        "cli.ok_init": "[OK] initialized {path}",
        # parser
        "parser.start": "Parsing {path}",
        "parser.open": "Opening outer zip {path}",
        "parser.manifest": "Read manifest.json from {path}",
        "parser.scratch": "Read scratch.sb3 from {path}",
        "parser.project": "Read project.json",
        "parser.done": "Parsed {path}: {block_count} blocks, {var_count} vars, {proc_count} procedures",
        # serializer
        "ser.unpack": "Unpacking template {template}",
        "ser.normalize_assets": "Normalizing asset hashes",
        "ser.save": "Saving project to {out}",
        "ser.done": "Saved project to {out}",
        # procedures
        "proc.define": "Defining procedure {name} ({arg_count} args)",
        "proc.call": "Calling procedure {name}",
        "proc.attach": "Attaching body to procedure {name} ({block_count} blocks)",
        # variables
        "var.add": "Adding variable {name}",
        "var.monitor": "Registering monitor for {name}",
        # blocks
        "block.add": "add_block {opcode} → {bid}",
        "block.chain": "Chaining {count} blocks under {container}",
        # python_first exporter
        "pf_exp.init": "PythonFirstExporter: {block_count} blocks, {var_count} vars",
        "pf_exp.collect_procs": "Collected {count} procedure definitions",
        "pf_exp.render": "Rendering python-first export",
        "pf_exp.done": "Python-first render: {proc_count} procs, {event_count} events",
        # stdlib
        "stdlib.install": "Installing stdlib group {group}",
        # workflow
        "workflow.discover": "Discovering defaults from {base}",
        "workflow.init": "Initializing workspace at {target}",
        "workflow.doctor": "Running doctor on {base}",
        "workflow.roundtrip": "Roundtrip {in_path} → {out_path}",
        # flow
        "flow.start": "FlowBuilder.start()",
        "flow.procedure": "FlowBuilder.procedure {name} ({arg_count} args)",
        "flow.chain": "FlowBuilder.chain under {parent}",
        # project
        "project.init": "LLSP3Project init: template={template}",
        "project.save": "Saving project to {out}",
        "project.clear": "Clearing project code",
        # layout
        "layout.start": "next_start → ({x}, {y})",
        "layout.event": "next_event → ({x}, {y})",
        "layout.proc": "next_procedure → ({x}, {y})",
    },
    "zh_CN": {
        # transpiler logging
        "transpile.start": "正在转译 {path}",
        "transpile.file.start": "正在转译文件 {path}",
        "transpile.package.start": "正在转译包 {path}",
        "transpile.module.start": "正在转译模块 {module}",
        "transpile.module.build_call": "正在调用模块 {module} 的 build()",
        "transpile.module.save": "正在保存项目到 {out}",
        "transpile.module.done": "转译完成 → {out}",
        "transpile.autodiscover": "自动发现资源: 模板={template}, 字符串={strings}",
        "transpile.load_module": "正在加载模块 {path}",
        "transpile.load_package": "正在加载包 {path}",
        # ast transpiler
        "ast.start": "正在进行 AST 转译 {path}",
        "ast.parse": "已解析 {path} 的 AST（{count} 个顶层节点）",
        "ast.function": "正在编译函数 {name}（{arg_count} 个参数）",
        "ast.save": "正在保存 AST 转译项目到 {out}",
        "ast.done": "AST 转译完成 → {out}",
        "ast.note": "AST 注释: {msg}",
        # pythonfirst
        "pf.start": "正在进行 Python-first 转译 {path}",
        "pf.parse": "已解析 {path} 的源码（{count} 个顶层节点）",
        "pf.proc": "正在编译 @robot.proc {name}（{arg_count} 个参数）",
        "pf.main": "正在编译 @run.main {name}",
        "pf.save": "正在保存 Python-first 项目到 {out}",
        "pf.done": "Python-first 转译完成 → {out}",
        "pf.note": "Python-first 注释: {msg}",
        # exporter
        "export.start": "正在导出 {path} 为 Python（样式={style}）",
        "export.parse": "已解析 {path}: {block_count} 个积木块, {var_count} 个变量",
        "export.write": "正在写入导出的 Python 到 {out}",
        "export.done": "导出完成 → {out}",
        # CLI
        "cli.ok_wrote": "[完成] 已写入 {path}",
        "cli.ok_init": "[完成] 已初始化 {path}",
        # parser
        "parser.start": "正在解析 {path}",
        "parser.open": "打开外层 zip {path}",
        "parser.manifest": "已读取 {path} 的 manifest.json",
        "parser.scratch": "已读取 {path} 的 scratch.sb3",
        "parser.project": "已读取 project.json",
        "parser.done": "已解析 {path}: {block_count} 个积木块, {var_count} 个变量, {proc_count} 个过程",
        # serializer
        "ser.unpack": "正在解压模板 {template}",
        "ser.normalize_assets": "正在规范化资产哈希",
        "ser.save": "正在保存项目到 {out}",
        "ser.done": "已保存项目到 {out}",
        # procedures
        "proc.define": "定义过程 {name}（{arg_count} 个参数）",
        "proc.call": "调用过程 {name}",
        "proc.attach": "为过程 {name} 附加主体（{block_count} 个积木块）",
        # variables
        "var.add": "添加变量 {name}",
        "var.monitor": "注册监视器 {name}",
        # blocks
        "block.add": "add_block {opcode} → {bid}",
        "block.chain": "在 {container} 下链接 {count} 个积木块",
        # python_first exporter
        "pf_exp.init": "PythonFirstExporter: {block_count} 个积木块, {var_count} 个变量",
        "pf_exp.collect_procs": "已收集 {count} 个过程定义",
        "pf_exp.render": "正在渲染 python-first 导出",
        "pf_exp.done": "python-first 渲染完成: {proc_count} 个过程, {event_count} 个事件",
        # stdlib
        "stdlib.install": "正在安装标准库组 {group}",
        # workflow
        "workflow.discover": "从 {base} 搜索默认资源",
        "workflow.init": "正在初始化工作区 {target}",
        "workflow.doctor": "正在检查 {base}",
        "workflow.roundtrip": "往返转换 {in_path} → {out_path}",
        # flow
        "flow.start": "FlowBuilder.start()",
        "flow.procedure": "FlowBuilder.procedure {name}（{arg_count} 个参数）",
        "flow.chain": "FlowBuilder.chain 在 {parent} 下",
        # project
        "project.init": "LLSP3Project 初始化: template={template}",
        "project.save": "正在保存项目到 {out}",
        "project.clear": "清除项目代码",
        # layout
        "layout.start": "next_start → ({x}, {y})",
        "layout.event": "next_event → ({x}, {y})",
        "layout.proc": "next_procedure → ({x}, {y})",
    },
}


def set_locale(lang: str) -> None:
    """Switch the active locale.  Accepted values: ``'en'``, ``'zh_CN'``."""
    global _current_locale
    if lang not in _CATALOGS:
        raise ValueError(f"Unknown locale {lang!r}; available: {sorted(_CATALOGS)}")
    _current_locale = lang


def get_locale() -> str:
    """Return the currently active locale code."""
    return _current_locale


def t(key: str, **kwargs: object) -> str:
    """Translate *key* using the active catalog.

    Falls back to the English catalog if the key is missing from the active
    locale, and to the raw *key* if it is missing everywhere.
    """
    catalog = _CATALOGS.get(_current_locale, _CATALOGS["en"])
    template = catalog.get(key) or _CATALOGS["en"].get(key) or key
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


def available_locales() -> list[str]:
    """Return a sorted list of all registered locale codes."""
    return sorted(_CATALOGS)
