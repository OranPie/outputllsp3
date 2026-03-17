from __future__ import annotations

import json
import keyword
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .parser import parse_llsp3


def _pyrepr(obj: Any) -> str:
    return repr(obj)


def _summary(doc) -> dict[str, Any]:
    blocks = doc.blocks
    opcode_counts = Counter(b.get('opcode') for b in blocks.values())
    procedures: list[dict[str, Any]] = []
    top_levels: list[dict[str, Any]] = []
    for bid, block in blocks.items():
        if block.get('opcode') == 'procedures_prototype':
            procedures.append({
                'id': bid,
                'proccode': block.get('mutation', {}).get('proccode', ''),
                'argnames': json.loads(block.get('mutation', {}).get('argumentnames', '[]')) if block.get('mutation') else [],
            })
        if block.get('topLevel'):
            top_levels.append({
                'id': bid,
                'opcode': block.get('opcode'),
                'x': block.get('x'),
                'y': block.get('y'),
            })
    return {
        'variables': len(doc.variables),
        'lists': len(doc.sprite.get('lists', {})),
        'blocks': len(blocks),
        'opcode_count': len(opcode_counts),
        'top_levels': top_levels,
        'procedures': procedures,
        'opcode_counts': dict(sorted(opcode_counts.items())),
    }


def _sanitize(name: str, fallback: str = 'v') -> str:
    name = re.sub(r'[^A-Za-z0-9_]+', '_', name).strip('_') or fallback
    if name[0].isdigit():
        name = '_' + name
    if keyword.iskeyword(name):
        name += '_'
    return name


def _extract_literal(inp):
    if isinstance(inp, list) and inp and inp[0] == 1 and len(inp) > 1 and isinstance(inp[1], list) and len(inp[1]) == 2:
        return inp[1][1]
    return None


def _value_ref(inp):
    if isinstance(inp, list) and inp:
        if inp[0] in (2, 3) and len(inp) > 1 and isinstance(inp[1], str):
            return inp[1]
        if inp[0] == 1 and len(inp) > 1 and isinstance(inp[1], str):
            return inp[1]
    return None


def _raw_lines(doc, style: str) -> list[str]:
    sprite = doc.sprite
    blocks = sprite.get('blocks', {})
    variables = sprite.get('variables', {})
    lists = sprite.get('lists', {})
    comments = sprite.get('comments', {})
    summary = _summary(doc)

    lines: list[str] = []
    lines.append('from collections import OrderedDict')
    lines.append('import json')
    lines.append('')
    lines.append(f'# exported from: {Path(doc.path).name}')
    lines.append(f'# export style: {style}')
    lines.append('# note: this is an exact-reconstruction export, not a decompiler back to the original human-authored source.')
    lines.append('')
    lines.append('def build(project, api, ns, enums):')
    lines.append('    project.clear_code()')
    lines.append('')
    lines.append('    # summary')
    lines.append(f"    # variables: {summary['variables']}")
    lines.append(f"    # lists: {summary['lists']}")
    lines.append(f"    # blocks: {summary['blocks']}")
    lines.append(f"    # unique opcodes: {summary['opcode_count']}")
    for proc in summary['procedures']:
        lines.append(f"    # procedure: {proc['proccode']}")
    for top in summary['top_levels']:
        lines.append(f"    # top-level: {top['id']} -> {top['opcode']} @ ({top['x']}, {top['y']})")
    lines.append('')

    if variables:
        lines.append('    # variables')
        for vid, pair in variables.items():
            lines.append(f'    project.variables[{vid!r}] = {_pyrepr(pair)}')
        lines.append('')
    if lists:
        lines.append('    # lists')
        for lid, pair in lists.items():
            lines.append(f'    project.lists[{lid!r}] = {_pyrepr(pair)}')
        lines.append('')

    lines.append('    # blocks (exact reconstruction)')
    lines.append('    project.sprite["blocks"] = OrderedDict()')
    for bid, block in blocks.items():
        payload = json.dumps(block, ensure_ascii=False)
        lines.append(f'    project.sprite["blocks"][{bid!r}] = json.loads({payload!r})')
    lines.append('')
    lines.append('    # comments')
    lines.append('    project.sprite["comments"] = OrderedDict()')
    for cid, comment in comments.items():
        payload = json.dumps(comment, ensure_ascii=False)
        lines.append(f'    project.sprite["comments"][{cid!r}] = json.loads({payload!r})')
    lines.append('')
    return lines


def _builder_lines(doc) -> list[str]:
    sprite = doc.sprite
    blocks = sprite.get('blocks', {})
    variables = sprite.get('variables', {})
    lists = sprite.get('lists', {})
    comments = sprite.get('comments', {})
    summary = _summary(doc)

    lines: list[str] = []
    lines.append('from collections import OrderedDict')
    lines.append('import json')
    lines.append('')
    lines.append(f'# exported from: {Path(doc.path).name}')
    lines.append('# export style: builder')
    lines.append('# note: this is still an exact export, but shaped to be easier to read and edit than the raw dump.')
    lines.append('')
    lines.append('def _set_block(project, block_id, payload):')
    lines.append('    project.sprite["blocks"][block_id] = payload')
    lines.append('')
    lines.append('def build(project, api, ns, enums):')
    lines.append('    project.clear_code()')
    lines.append('')
    lines.append('    # summary')
    lines.append(f"    # variables: {summary['variables']}")
    lines.append(f"    # lists: {summary['lists']}")
    lines.append(f"    # blocks: {summary['blocks']}")
    lines.append(f"    # unique opcodes: {summary['opcode_count']}")
    for proc in summary['procedures']:
        lines.append(f"    # procedure: {proc['proccode']}")
    lines.append('')
    lines.append('    # high-level hints')
    opcode_counts = summary['opcode_counts']
    if 'flipperevents_whenProgramStarts' in opcode_counts:
        lines.append('    # hint: project has one or more program-start entry stacks')
    if any(op.startswith('procedures_') for op in opcode_counts):
        lines.append('    # hint: project uses custom procedures; see procedure comments above')
    if any(op.startswith('data_') for op in opcode_counts):
        lines.append('    # hint: project uses variables/lists; resources are recreated first, then blocks are restored exactly')
    lines.append('')

    if variables:
        lines.append('    # recreate variables with original ids/names')
        for vid, pair in variables.items():
            lines.append(f'    project.variables[{vid!r}] = {_pyrepr(pair)}')
        lines.append('')
    if lists:
        lines.append('    # recreate lists with original ids/names')
        for lid, pair in lists.items():
            lines.append(f'    project.lists[{lid!r}] = {_pyrepr(pair)}')
        lines.append('')

    lines.append('    project.sprite["blocks"] = OrderedDict()')
    lines.append('')
    top_ids = {bid for bid, block in blocks.items() if block.get('topLevel')}
    proc_proto_ids = {bid for bid, block in blocks.items() if block.get('opcode') == 'procedures_prototype'}
    proc_def_ids = {bid for bid, block in blocks.items() if block.get('opcode') == 'procedures_definition'}

    def emit_group(title: str, pred):
        emitted = False
        for bid, block in blocks.items():
            if pred(bid, block):
                nonlocal_lines.append(f'    # {title}' if not emitted else '')
                nonlocal_lines.append(f'    _set_block(project, {bid!r}, json.loads({json.dumps(block, ensure_ascii=False)!r}))')
                emitted = True
        if emitted:
            nonlocal_lines.append('')

    nonlocal_lines = lines
    emit_group('top-level blocks', lambda bid, block: bid in top_ids)
    emit_group('procedure definitions and prototypes', lambda bid, block: bid in proc_def_ids or bid in proc_proto_ids)
    emit_group('remaining blocks', lambda bid, block: bid not in top_ids and bid not in proc_def_ids and bid not in proc_proto_ids)

    lines.append('    project.sprite["comments"] = OrderedDict()')
    if comments:
        lines.append('    # comments')
        for cid, comment in comments.items():
            lines.append(f'    project.sprite["comments"][{cid!r}] = json.loads({json.dumps(comment, ensure_ascii=False)!r})')
        lines.append('')
    return [line for line in lines if line != ''] + ['']


class _PFExport:
    def __init__(self, doc):
        self.doc = doc
        self.blocks = doc.blocks
        self.var_names = {vid: _sanitize(pair[0], 'var') for vid, pair in doc.variables.items()}
        self.list_names = {lid: _sanitize(pair[0], 'lst') for lid, pair in doc.sprite.get('lists', {}).items()}
        self.proc_defs = self._collect_procedures()

    def _collect_procedures(self):
        procs = []
        for bid, b in self.blocks.items():
            if b.get('opcode') == 'procedures_definition':
                custom = b.get('inputs', {}).get('custom_block')
                proto_id = custom[1] if isinstance(custom, list) and len(custom) > 1 else None
                proto = self.blocks.get(proto_id, {})
                mut = proto.get('mutation', {})
                argnames = []
                try:
                    argnames = json.loads(mut.get('argumentnames', '[]'))
                except Exception:
                    argnames = []
                argdefaults_raw: list[str] = []
                try:
                    argdefaults_raw = json.loads(mut.get('argumentdefaults', '[]'))
                except Exception:
                    argdefaults_raw = []
                # Convert default strings to Python values (numbers or strings).
                # An empty string means "no default for this param".
                def _parse_default(s: str):
                    if not s:
                        return None
                    try:
                        v = float(s)
                        return int(v) if v == int(v) else v
                    except (ValueError, TypeError):
                        return s
                argdefaults = [_parse_default(argdefaults_raw[i]) if i < len(argdefaults_raw) else None for i in range(len(argnames))]
                name = (mut.get('proccode') or 'procedure').split(' %s')[0]
                procs.append({
                    'def_id': bid,
                    'name': _sanitize(name, 'proc'),
                    'argnames': [_sanitize(a, 'arg') for a in argnames],
                    'argdefaults': argdefaults,
                    'body': b.get('next'),
                })
        return procs

    def render_expr(self, ref):
        if ref is None:
            return 'None'
        if isinstance(ref, list):
            lit = _extract_literal(ref)
            if lit is not None:
                if isinstance(lit, str) and lit.lstrip('-').replace('.','',1).isdigit():
                    return lit
                return repr(lit)
            ref = _value_ref(ref)
        if not isinstance(ref, str):
            return repr(ref)
        block = self.blocks.get(ref, {})
        op = block.get('opcode')
        if op == 'data_variable':
            fld = block.get('fields', {}).get('VARIABLE', ['var'])
            return _sanitize(fld[0], 'var')
        if op == 'argument_reporter_string_number':
            fld = block.get('fields', {}).get('VALUE', ['arg'])
            return _sanitize(fld[0], 'arg')
        if op in {'operator_add','operator_subtract','operator_multiply','operator_divide'}:
            a = self.render_expr(block.get('inputs', {}).get('NUM1'))
            b = self.render_expr(block.get('inputs', {}).get('NUM2'))
            sym = {'operator_add':'+','operator_subtract':'-','operator_multiply':'*','operator_divide':'/'}[op]
            return f'({a} {sym} {b})'
        if op in {'operator_lt','operator_gt','operator_equals'}:
            a = self.render_expr(block.get('inputs', {}).get('OPERAND1'))
            b = self.render_expr(block.get('inputs', {}).get('OPERAND2'))
            sym = {'operator_lt':'<','operator_gt':'>','operator_equals':'=='}[op]
            return f'({a} {sym} {b})'
        if op == 'operator_mathop':
            fname = block.get('fields', {}).get('OPERATOR', ['abs'])[0]
            x = self.render_expr(block.get('inputs', {}).get('NUM'))
            return f'{fname}({x})'
        if op == 'data_lengthoflist':
            lst = block.get('fields', {}).get('LIST', ['lst'])[0]
            return f'len({_sanitize(lst, "lst")})'
        if op == 'data_itemoflist':
            idx = self.render_expr(block.get('inputs', {}).get('INDEX'))
            lst = block.get('fields', {}).get('LIST', ['lst'])[0]
            return f'{_sanitize(lst,"lst")}[({idx})-1]'
        if op == 'data_listcontainsitem':
            item = self.render_expr(block.get('inputs', {}).get('ITEM'))
            lst = block.get('fields', {}).get('LIST', ['lst'])[0]
            return f'({item} in {_sanitize(lst, "lst")})'
        if op == 'flippersensors_orientationAxis':
            axis = block.get('fields', {}).get('AXIS', ['yaw'])[0]
            return f'__expr__("orientation", {axis!r})'
        if op == 'flippermoremotor_position':
            port_name = self._menu_value(block.get('inputs', {}).get('PORT')) or 'A'
            return f'__expr__("motor_relative_position", {port_name!r})'
        if op == 'procedures_call':
            mut = block.get('mutation', {})
            raw_name = (mut.get('proccode') or 'proc').split(' %s')[0]
            name = _sanitize(raw_name, 'proc')
            argids = []
            try:
                argids = json.loads(mut.get('argumentids','[]'))
            except Exception:
                argids = []
            args = [self.render_expr(block.get('inputs', {}).get(aid)) for aid in argids]
            common = {
                'MoveStraightCm': 'robot.forward_cm',
                'MoveStraightDeg': 'robot.forward_deg',
                'TurnDeg': 'robot.turn_deg',
                'PivotLeftDeg': 'robot.pivot_left',
                'PivotRightDeg': 'robot.pivot_right',
                'StopDrive': 'robot.stop',
            }
            call_name = common.get(raw_name, name)
            return f'{call_name}({", ".join(args)})'
        return f'__expr__({(op or "unknown")!r})'

    def _is_return_guard_if(self, block: dict) -> bool:
        """Return True if *block* is a ``control_if`` that guards a return flag check.

        The compiled form is: ``control_if(operator_equals(data_variable(__return_*), 0), ...)``
        """
        if block.get('opcode') != 'control_if':
            return False
        cond_ref = _value_ref(block.get('inputs', {}).get('CONDITION'))
        if not cond_ref or cond_ref not in self.blocks:
            return False
        eq_blk = self.blocks[cond_ref]
        if eq_blk.get('opcode') != 'operator_equals':
            return False
        op1_ref = _value_ref(eq_blk.get('inputs', {}).get('OPERAND1'))
        if not op1_ref or op1_ref not in self.blocks:
            return False
        var_blk = self.blocks[op1_ref]
        if var_blk.get('opcode') != 'data_variable':
            return False
        var_name = var_blk.get('fields', {}).get('VARIABLE', [''])[0]
        return var_name.startswith('__return_')

    def _retval_source_proc(self, value_input) -> str | None:
        """If *value_input* is a reference to a ``data_variable`` whose name starts
        with ``__retval_``, return the proc-name suffix; otherwise return None."""
        ref = _value_ref(value_input)
        if not ref or ref not in self.blocks:
            return None
        blk = self.blocks[ref]
        if blk.get('opcode') != 'data_variable':
            return None
        var_name = blk.get('fields', {}).get('VARIABLE', [''])[0]
        if var_name.startswith('__retval_'):
            return var_name[len('__retval_'):]
        return None

    def render_stmt_chain(self, start_id, indent='    '):
        lines = []
        cur = start_id
        seen = set()
        while cur and cur not in seen and cur in self.blocks:
            seen.add(cur)
            block = self.blocks[cur]
            op = block.get('opcode')
            flds = block.get('fields', {})
            ins = block.get('inputs', {})
            next_id = block.get('next')
            next_block = self.blocks.get(next_id) if next_id else None

            # ── Pattern 1: procedures_call followed by target = __retval_*  ──────
            # Compile both as: target = proc_name(args)
            if op == 'procedures_call' and next_block and next_block.get('opcode') == 'data_setvariableto':
                proc_part = self._retval_source_proc(next_block.get('inputs', {}).get('VALUE'))
                if proc_part is not None:
                    target_raw = next_block.get('fields', {}).get('VARIABLE', ['var'])[0]
                    target = _sanitize(target_raw, 'var')
                    proc_call_str = self.render_expr(cur)
                    lines.append(f'{indent}{target} = {proc_call_str}')
                    cur = next_block.get('next')
                    continue

            # ── Pattern 2: __return_* = 0 initialiser – skip it  ────────────────
            if op == 'data_setvariableto':
                var_name = flds.get('VARIABLE', [''])[0]
                if var_name.startswith('__return_'):
                    lit = _extract_literal(ins.get('VALUE'))
                    if str(lit) == '0':
                        cur = next_id
                        continue

            # ── Pattern 3: return-guard control_if blocks  ───────────────────────
            # Two consecutive guards encode  `return value`:
            #   guard1 → SUBSTACK: __retval_X = value
            #   guard2 → SUBSTACK: __return_X = 1
            # A single guard whose SUBSTACK is __return_X = 1 encodes bare `return`.
            # Any other guard: unwrap and render contents directly.
            if self._is_return_guard_if(block):
                substack_ref = _value_ref(ins.get('SUBSTACK'))
                sub_blk = self.blocks.get(substack_ref) if substack_ref else None
                if sub_blk and sub_blk.get('opcode') == 'data_setvariableto' and sub_blk.get('next') is None:
                    sub_var = sub_blk.get('fields', {}).get('VARIABLE', [''])[0]
                    # Sub-pattern 3a: guard holds __retval_* – check if next guard holds __return_*
                    if sub_var.startswith('__retval_') and next_block and self._is_return_guard_if(next_block):
                        next_ss_ref = _value_ref(next_block.get('inputs', {}).get('SUBSTACK'))
                        next_sub = self.blocks.get(next_ss_ref) if next_ss_ref else None
                        if (next_sub and next_sub.get('opcode') == 'data_setvariableto' and
                                next_sub.get('fields', {}).get('VARIABLE', [''])[0].startswith('__return_')):
                            val_str = self.render_expr(sub_blk.get('inputs', {}).get('VALUE'))
                            lines.append(f'{indent}return {val_str}')
                            cur = next_block.get('next')
                            continue
                    # Sub-pattern 3b: guard holds __return_* = 1 → bare return
                    if sub_var.startswith('__return_') and str(_extract_literal(
                            sub_blk.get('inputs', {}).get('VALUE'))) == '1':
                        lines.append(f'{indent}return')
                        cur = next_id
                        continue
                # Sub-pattern 3c: regular return-guard – just unwrap the contents
                if substack_ref:
                    lines.extend(self.render_stmt_chain(substack_ref, indent))
                cur = next_id
                continue

            lines.extend(self.render_stmt(block, indent))
            cur = next_id
        return lines

    def render_stmt(self, block, indent='    '):
        op = block.get('opcode')
        ins = block.get('inputs', {})
        flds = block.get('fields', {})
        if op == 'data_setvariableto':
            name = _sanitize(flds.get('VARIABLE',['var'])[0], 'var')
            return [f'{indent}{name} = {self.render_expr(ins.get("VALUE"))}']
        if op == 'data_changevariableby':
            name = _sanitize(flds.get('VARIABLE',['var'])[0], 'var')
            return [f'{indent}{name} += {self.render_expr(ins.get("VALUE"))}']
        if op == 'data_addtolist':
            name = _sanitize(flds.get('LIST',['lst'])[0], 'lst')
            return [f'{indent}{name}.append({self.render_expr(ins.get("ITEM"))})']
        if op == 'data_deletealloflist':
            name = _sanitize(flds.get('LIST',['lst'])[0], 'lst')
            return [f'{indent}{name}.clear()']
        if op == 'data_insertatlist':
            name = _sanitize(flds.get('LIST',['lst'])[0], 'lst')
            idx = self.render_expr(ins.get('INDEX'))
            item = self.render_expr(ins.get('ITEM'))
            return [f'{indent}{name}.insert(({idx})-1, {item})']
        if op == 'data_replaceitemoflist':
            name = _sanitize(flds.get('LIST',['lst'])[0], 'lst')
            idx = self.render_expr(ins.get('INDEX'))
            item = self.render_expr(ins.get('ITEM'))
            return [f'{indent}{name}[({idx})-1] = {item}']
        if op == 'data_deleteoflist':
            name = _sanitize(flds.get('LIST',['lst'])[0], 'lst')
            idx = self.render_expr(ins.get('INDEX'))
            return [f'{indent}del {name}[({idx})-1]']
        if op == 'control_wait':
            dur = self.render_expr(ins.get('DURATION'))
            return [f'{indent}run.sleep({dur})']
        if op == 'control_if':
            cond = self.render_expr(ins.get('CONDITION'))
            body = self.render_stmt_chain(_value_ref(ins.get('SUBSTACK')), indent + '    ')
            if not body:
                body = [indent + '    pass']
            return [f'{indent}if {cond}:', *body]
        if op == 'control_if_else':
            cond = self.render_expr(ins.get('CONDITION'))
            body1 = self.render_stmt_chain(_value_ref(ins.get('SUBSTACK')), indent + '    ') or [indent + '    pass']
            body2 = self.render_stmt_chain(_value_ref(ins.get('SUBSTACK2')), indent + '    ') or [indent + '    pass']
            return [f'{indent}if {cond}:', *body1, f'{indent}else:', *body2]
        if op == 'control_repeat':
            times = self.render_expr(ins.get('TIMES'))
            body = self.render_stmt_chain(_value_ref(ins.get('SUBSTACK')), indent + '    ') or [indent + '    pass']
            return [f'{indent}for _ in range({times}):', *body]
        if op == 'control_repeat_until':
            cond = self.render_expr(ins.get('CONDITION'))
            body = self.render_stmt_chain(_value_ref(ins.get('SUBSTACK')), indent + '    ') or [indent + '    pass']
            return [f'{indent}while not ({cond}):', *body]
        if op == 'procedures_call':
            return [f'{indent}{self.render_expr(block.get("id", None) or block.get("self_ref", None) or [3, self._find_block_id(block), None])}']
        if op == 'flippermove_stopMove':
            return [f'{indent}robot.stop()']
        if op == 'flippersensors_resetYaw':
            return [f'{indent}__stmt__("reset_yaw")']
        if op == 'flippermove_setMovementPair':
            pair = self._menu_value(ins.get('PAIR'))
            return [f'{indent}__stmt__("set_motor_pair", {pair!r})']
        if op == 'flippermoremove_startDualSpeed':
            left = self.render_expr(ins.get('LEFT'))
            right = self.render_expr(ins.get('RIGHT'))
            return [f'{indent}__stmt__("drive_speed", {left}, {right})']
        if op == 'flippermoremove_startDualPower':
            left = self.render_expr(ins.get('LEFT'))
            right = self.render_expr(ins.get('RIGHT'))
            return [f'{indent}__stmt__("drive_power", {left}, {right})']
        if op == 'flippermoremotor_motorSetDegreeCounted':
            port_name = self._menu_value(ins.get('PORT')) or 'A'
            value = self.render_expr(ins.get('VALUE'))
            return [f'{indent}__stmt__("set_relative_position", {port_name!r}, {value})']
        # fallbacks for well-known procedure names
        if op == 'procedures_call':
            return [f'{indent}{self.render_expr([3, self._find_block_id(block), None])}']
        return [f'{indent}__stmt__({op!r})']

    def _find_block_id(self, block_obj):
        for bid, blk in self.blocks.items():
            if blk is block_obj:
                return bid
        return ''

    def _menu_value(self, inp):
        ref = _value_ref(inp)
        if not ref or ref not in self.blocks:
            return None
        blk = self.blocks[ref]
        fields = blk.get('fields', {})
        if not fields:
            return None
        first = next(iter(fields.values()))
        if isinstance(first, list) and first:
            return first[0]
        return None

    def render(self):
        lines = []
        lines.append('from outputllsp3 import robot, run, port, ls')
        lines.append('')
        lines.append(f'# exported from: {Path(self.doc.path).name}')
        lines.append('# export style: python-first')
        lines.append('# note: this is an approximate, readable decompilation. For exact reconstruction use --style raw or --style builder.')
        lines.append('')
        lines.append('def __expr__(kind, *args):')
        lines.append('    """Placeholder helper for expressions that do not have a verified high-level python-first mapping yet."""')
        lines.append('    return 0')
        lines.append('')
        lines.append('def __stmt__(kind, *args):')
        lines.append('    """Placeholder helper for statements that do not have a verified high-level python-first mapping yet."""')
        lines.append('    return None')
        lines.append('')
        # variables / lists
        for _, pair in self.doc.variables.items():
            name = _sanitize(pair[0], 'var')
            val = pair[1]
            lines.append(f'{name} = {repr(val)}')
        for _, pair in self.doc.sprite.get('lists', {}).items():
            name = _sanitize(pair[0], 'lst')
            lines.append(f'{name} = ls.list({pair[0]!r})')
        if self.doc.variables or self.doc.sprite.get('lists', {}):
            lines.append('')
        for proc in self.proc_defs:
            argnames = proc['argnames']
            argdefaults = proc.get('argdefaults', [])
            param_parts = []
            for i, aname in enumerate(argnames):
                default = argdefaults[i] if i < len(argdefaults) else None
                if default is not None:
                    param_parts.append(f'{aname}={repr(default)}')
                else:
                    param_parts.append(aname)
            args = ', '.join(param_parts)
            lines.append('@robot.proc')
            lines.append(f'def {proc["name"]}({args}):')
            body = self.render_stmt_chain(proc['body'], '    ')
            if not body:
                body = ['    pass']
            lines.extend(body)
            lines.append('')
        # top-level main from whenProgramStarts stacks
        starts = [bid for bid, b in self.blocks.items() if b.get('opcode') == 'flipperevents_whenProgramStarts' and b.get('topLevel')]
        lines.append('@run.main')
        lines.append('def main():')
        if starts:
            body = []
            for s in starts:
                body.extend(self.render_stmt_chain(self.blocks[s].get('next'), '    '))
            if not body:
                body = ['    pass']
            lines.extend(body)
        else:
            lines.append('    pass')
        lines.append('')
        return lines


def _pythonfirst_lines(doc) -> list[str]:
    return _PFExport(doc).render()


def export_llsp3_to_python(path: str, out: str, *, style: str = 'raw') -> str:
    doc = parse_llsp3(path)
    if style == 'raw':
        lines = _raw_lines(doc, style)
    elif style == 'builder':
        lines = _builder_lines(doc)
    elif style == 'python-first':
        lines = _pythonfirst_lines(doc)
    else:
        raise ValueError(f'Unsupported export style: {style}')
    Path(out).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return str(out)
