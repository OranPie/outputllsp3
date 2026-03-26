"""Python-first export strategy.

Higher-level decompilation that lifts common patterns to python-first idioms
(``@robot.proc`` / ``@run.main``, ``robot.forward_cm``, …).  The output is
approximate — round-tripping through python-first may not preserve every
low-level block detail, but produces readable programs.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from .base import _sanitize, _extract_literal, _value_ref
from ..locale import t

logger = logging.getLogger(__name__)

# ── Module-level helpers ──────────────────────────────────────────────────────

def _join_side(expr: str) -> str:
    """Wrap *expr* in ``str()`` unless it already is a string literal or a str() call."""
    if (expr.startswith("'") or expr.startswith('"')) and not expr.startswith('str('):
        return expr
    if expr.startswith('str(') and expr.endswith(')'):
        return expr
    return f'str({expr})'


def _section(text: str, width: int = 78) -> str:
    """Return a decorated section-header comment line."""
    prefix = f'# ── {text} '
    return prefix + '─' * max(2, width - len(prefix))


# Map from Scratch mathop field value → Python expression template.
# {x} is replaced with the rendered argument.
_MATHOP_MAP: dict[str, str] = {
    'abs':      'abs({x})',
    'floor':    'math.floor({x})',
    'ceiling':  'math.ceil({x})',
    'sqrt':     'math.sqrt({x})',
    'sin':      'math.sin(math.radians({x}))',
    'cos':      'math.cos(math.radians({x}))',
    'tan':      'math.tan(math.radians({x}))',
    'asin':     'math.degrees(math.asin({x}))',
    'acos':     'math.degrees(math.acos({x}))',
    'atan':     'math.degrees(math.atan({x}))',
    'ln':       'math.log({x})',
    'log':      'math.log10({x})',
    'e ^':      'math.exp({x})',
    '10 ^':     '(10 ** ({x}))',
    '2 ^':      '(2 ** ({x}))',
}
# mathop names that require `import math` (all except 'abs' which is builtin)
_MATHOP_NEEDS_MATH: frozenset[str] = frozenset(_MATHOP_MAP) - {'abs', '10 ^', '2 ^'}

# ── Enum value → member-name lookup tables ────────────────────────────────────

# Direction enum (motor rotation + absolute-position path)
_DIRECTION_MAP: dict[str, str] = {
    'clockwise':        'CLOCKWISE',
    'counterclockwise': 'COUNTERCLOCKWISE',
    'shortest':         'SHORTEST',
}

# StopMode enum
_STOP_MODE_MAP: dict[str, str] = {
    'coast': 'COAST',
    'brake': 'BRAKE',
    'hold':  'HOLD',
    # Numeric forms sometimes stored in block fields
    '0':     'COAST',
    '1':     'BRAKE',
    '2':     'HOLD',
}

# Axis enum (orientation IMU + cartesian sensors)
_AXIS_MAP: dict[str, str] = {
    'yaw':   'YAW',
    'pitch': 'PITCH',
    'roll':  'ROLL',
    'x':     'X',
    'y':     'Y',
    'z':     'Z',
}

# Color enum (uppercase Scratch field values)
_COLOR_MAP: dict[str, str] = {
    'black':   'BLACK',
    'violet':  'VIOLET',
    'blue':    'BLUE',
    'azure':   'AZURE',
    'cyan':    'CYAN',
    'green':   'GREEN',
    'yellow':  'YELLOW',
    'orange':  'ORANGE',
    'red':     'RED',
    'magenta': 'MAGENTA',
    'white':   'WHITE',
    'none':    'NONE',
    # Upper-case variants stored directly in block fields
    'BLACK':   'BLACK',
    'VIOLET':  'VIOLET',
    'BLUE':    'BLUE',
    'AZURE':   'AZURE',
    'CYAN':    'CYAN',
    'GREEN':   'GREEN',
    'YELLOW':  'YELLOW',
    'ORANGE':  'ORANGE',
    'RED':     'RED',
    'MAGENTA': 'MAGENTA',
    'WHITE':   'WHITE',
    'NONE':    'NONE',
}

# LightImage — pixel strings (from Appendix L) and uppercase name strings
# → LightImage member name
_PIXEL_TO_IMAGE: dict[str, str] = {
    # Appendix L pixel data
    '0000000909000000909000000': 'HAPPY',
    '0000009090000000909000000': 'SAD',
    '0909099999099990099900090': 'HEART',
    '0000009009000000900900000': 'SMILE',
    '0000060006090900600060000': 'SILLY',
    '9990099900000000909009090': 'FABULOUS',
    '0000009090090900090609060': 'MEH',
    '0000006960069000060609060': 'CONFUSED',
    '0000000009000900900009000': 'YES',
    '9000900090009000900090009': 'NO',
    # Named strings that the builder stores directly in MATRIX fields
    'HEART':        'HEART',
    'HEART_SMALL':  'HEART_SMALL',
    'HAPPY':        'HAPPY',
    'SAD':          'SAD',
    'ANGRY':        'ANGRY',
    'SURPRISED':    'SURPRISED',
    'SILLY':        'SILLY',
    'FABULOUS':     'FABULOUS',
    'MEH':          'MEH',
    'YES':          'YES',
    'NO':           'NO',
    'TRIANGLE':     'TRIANGLE',
    'TRIANGLE_LEFT':'TRIANGLE_LEFT',
    'ARROW_RIGHT':  'ARROW_RIGHT',
    'ARROW_LEFT':   'ARROW_LEFT',
    'ARROW_UP':     'ARROW_UP',
    'ARROW_DOWN':   'ARROW_DOWN',
    'SQUARE':       'SQUARE',
    'SQUARE_SMALL': 'SQUARE_SMALL',
    'TARGET':       'TARGET',
    'TSHIRT':       'TSHIRT',
    'ROLLERSKATE':  'ROLLERSKATE',
    'DUCK':         'DUCK',
    'HOUSE':        'HOUSE',
    'TORTOISE':     'TORTOISE',
    'BUTTERFLY':    'BUTTERFLY',
    'STICKFIGURE':  'STICKFIGURE',
    'GHOST':        'GHOST',
    'SWORD':        'SWORD',
    'GIRAFFE':      'GIRAFFE',
    'SKULL':        'SKULL',
    'UMBRELLA':     'UMBRELLA',
    'SNAKE':        'SNAKE',
    'ROBOT':        'ROBOT',
}


class _PFExport:
    def __init__(self, doc):
        self.doc = doc
        self.blocks = doc.blocks
        # Strip the sprite-name namespace prefix (e.g. "11_pid_robot__") from
        # variable and list display names so the output uses clean short names.
        sprite_name = doc.sprite.get('name', '')
        self._ns_prefix = sprite_name + '__' if sprite_name else ''
        # Build var_names from ALL targets (stage globals + sprite locals) so
        # that global variable references in real SPIKE projects resolve correctly.
        all_vars: dict = {}
        stage_var_ids: set = set()
        for target in doc.project.get('targets', []):
            tvars = target.get('variables', {})
            all_vars.update(tvars)
            if target.get('isStage'):
                stage_var_ids.update(tvars.keys())
        self._stage_var_ids = stage_var_ids
        self.var_names = {
            vid: self._clean_name(pair[0], 'var')
            for vid, pair in all_vars.items()
        }
        self.list_names = {
            lid: self._clean_name(pair[0], 'lst')
            for lid, pair in doc.sprite.get('lists', {}).items()
        }
        logger.debug(t("pf_exp.init", block_count=len(self.blocks), var_count=len(self.var_names)))
        # Build comment lookup: top-level-block-id → list of comment texts.
        # Each Scratch comment has a blockId pointing to the block it's attached to;
        # we walk parent links to find the top-level ancestor, then group texts there.
        # Floating comments (blockId=null) go into _floating_comment_texts.
        self._tl_comment_map: dict[str, list[str]] = {}  # top-level block id → [text, ...]
        self._floating_comment_texts: list[str] = []
        for c in doc.sprite.get('comments', {}).values():
            bid = c.get('blockId')
            text = (c.get('text') or '').strip()
            if not text:
                continue
            if not bid:
                self._floating_comment_texts.append(text)
            else:
                tl = self._toplevel_ancestor(bid)
                if tl:
                    self._tl_comment_map.setdefault(tl, []).append(text)
                else:
                    self._floating_comment_texts.append(text)
        self.proc_defs = self._collect_procedures()
        # Tracking flags — populated during render pass 1
        self._needs_math: bool = False
        self._needs_random: bool = False
        self._needs_direction: bool = False
        self._needs_stop_mode: bool = False
        self._needs_axis: bool = False
        self._needs_color: bool = False
        self._needs_image: bool = False
        self._needs_comparator: bool = False
        self._unknown_exprs: set[str] = set()
        self._unknown_stmts: set[str] = set()

    def _clean_name(self, raw: str, fallback: str) -> str:
        """Strip sprite-namespace prefix then sanitize to a valid Python identifier."""
        if self._ns_prefix and raw.startswith(self._ns_prefix):
            raw = raw[len(self._ns_prefix):]
        return _sanitize(raw, fallback)

    def _toplevel_ancestor(self, block_id: str) -> str | None:
        """Follow parent links to find the top-level ancestor of a block."""
        visited: set[str] = set()
        bid: str | None = block_id
        while bid and bid not in visited:
            visited.add(bid)
            b = self.blocks.get(bid)
            if b is None:
                return None
            if b.get('topLevel'):
                return bid
            parent = b.get('parent')
            if parent is None:
                return bid  # no parent link but not topLevel — return self
            bid = parent
        return None

    def _note_lines(self, top_level_id: str, indent: str = '    ') -> list[str]:
        """Return ``robot.note(...)`` lines for comments attached to *top_level_id*."""
        texts = self._tl_comment_map.get(top_level_id, [])
        lines = []
        for text in texts:
            # Multi-line comment text: use triple-quoted string
            if '\n' in text:
                safe = text.replace('\\', '\\\\').replace('"""', '\\"\\"\\"')
                lines.append(f'{indent}robot.note("""{safe}""")')
            else:
                lines.append(f'{indent}robot.note({text!r})')
        return lines

    def _vname(self, fld_list: list) -> str:
        """Resolve a VARIABLE field list ``[display_name, var_id]`` → clean Python name."""
        vid = fld_list[1] if len(fld_list) > 1 else None
        return self.var_names.get(vid) or self._clean_name(fld_list[0], 'var')

    def _lname(self, fld_list: list) -> str:
        """Resolve a LIST field list ``[display_name, list_id]`` → clean Python name."""
        lid = fld_list[1] if len(fld_list) > 1 else None
        return self.list_names.get(lid) or self._clean_name(fld_list[0], 'lst')

    def _port_name(self, inp) -> str:
        """Extract a port name from a menu input and sanitize it for Python attribute access."""
        raw = self._menu_value(inp) or 'A'
        return _sanitize(raw, 'A')

    def _port_expr(self, inp) -> str:
        """Return the full Python expression for a port input.
        
        For literal port menu values (A, B, BC, …) returns ``port.A``.
        For argument reporters or variable reporters returns just the identifier.
        """
        ref = _value_ref(inp)
        if ref and ref in self.blocks:
            blk = self.blocks[ref]
            op = blk.get('opcode', '')
            if op == 'argument_reporter_string_number':
                fld = blk.get('fields', {}).get('VALUE', ['arg'])
                return _sanitize(fld[0], 'arg')
            if op == 'data_variable':
                fld = blk.get('fields', {}).get('VARIABLE', ['var', None])
                vid = fld[1] if len(fld) > 1 else None
                return self.var_names.get(vid) or _sanitize(fld[0], 'var')
        # Inline variable reference [1/3, [12, name, id], ...]
        if isinstance(inp, list) and len(inp) > 1 and isinstance(inp[1], list) and inp[1][0] in (12, 13):
            inner = inp[1]
            vid = inner[2] if len(inner) > 2 else None
            return self.var_names.get(vid) or _sanitize(inner[1], 'var')
        # Literal port from shadow menu
        raw = self._menu_value(inp) or 'A'
        return f'port.{_sanitize(raw, "A")}'

    def _var_lit(self, val) -> str:
        """Format a variable initial value as a Python literal."""
        if isinstance(val, str):
            return f"'{val}'" if "'" not in val else repr(val)
        if isinstance(val, float) and val == int(val) and abs(val) < 1e15:
            return str(int(val))
        return repr(val)

    # ── Enum-ref helpers ──────────────────────────────────────────────────────

    def _dir(self, val: str) -> str:
        """Convert a raw direction string to a ``Direction.*`` enum reference."""
        member = _DIRECTION_MAP.get(val) or _DIRECTION_MAP.get(val.lower())
        if member:
            self._needs_direction = True
            return f'Direction.{member}'
        return repr(val)

    def _stop(self, val: str) -> str:
        """Convert a raw stop-mode string/int to a ``StopMode.*`` enum reference."""
        member = _STOP_MODE_MAP.get(val) or _STOP_MODE_MAP.get(val.lower())
        if member:
            self._needs_stop_mode = True
            return f'StopMode.{member}'
        return repr(val)

    def _axis(self, val: str) -> str:
        """Convert a raw axis string to an ``Axis.*`` enum reference."""
        member = _AXIS_MAP.get(val) or _AXIS_MAP.get(val.lower())
        if member:
            self._needs_axis = True
            return f'Axis.{member}'
        return repr(val)

    def _color(self, val: str) -> str:
        """Convert a raw color string to a ``Color.*`` enum reference."""
        member = _COLOR_MAP.get(val)
        if member:
            self._needs_color = True
            return f'Color.{member}'
        return repr(val)

    def _image(self, expr_str: str) -> str:
        """Convert a rendered image expression to a ``LightImage.*`` enum reference.

        *expr_str* is already a Python expression string as produced by
        ``render_expr`` — typically a quoted string like ``'HEART'`` or a
        25-character pixel string like ``'0909099999...'``.
        """
        # Unwrap the surrounding quotes from the repr'd string value.
        try:
            import ast as _ast
            val = _ast.literal_eval(expr_str)
        except Exception:
            return expr_str
        if isinstance(val, str):
            member = _PIXEL_TO_IMAGE.get(val)
            if member:
                self._needs_image = True
                return f'LightImage.{member}'
        return expr_str

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
                # Sanitize and deduplicate arg names within this proc.
                # e.g. two args both named '0/1' → '_0_1', '_0_1_2'
                sanitized_args: list[str] = []
                arg_seen: dict[str, int] = {}
                for a in argnames:
                    sa = _sanitize(a, 'arg')
                    arg_seen[sa] = arg_seen.get(sa, 0) + 1
                    if arg_seen[sa] > 1:
                        sa = f'{sa}_{arg_seen[sa]}'
                    sanitized_args.append(sa)
                procs.append({
                    'def_id': bid,
                    'name': _sanitize(name, 'proc'),
                    'argnames': sanitized_args,
                    'argdefaults': argdefaults,
                    'body': b.get('next'),
                })
        # Deduplicate procedure names: if two procs sanitize to the same name,
        # append _2, _3 ... to the later ones.
        name_counts: dict[str, int] = {}
        for p in procs:
            name_counts[p['name']] = name_counts.get(p['name'], 0) + 1
        name_seen: dict[str, int] = {}
        for p in procs:
            n = p['name']
            if name_counts[n] > 1:
                name_seen[n] = name_seen.get(n, 0) + 1
                if name_seen[n] > 1:
                    p['name'] = f'{n}_{name_seen[n]}'
        logger.debug(t("pf_exp.collect_procs", count=len(procs)))
        return procs

    def render_expr(self, ref):
        if ref is None:
            return 'None'
        if isinstance(ref, list):
            # Inline variable [3/2/1, [12, name, id], ...] or list [13, name, id]
            inner = ref[1] if len(ref) > 1 else None
            if isinstance(inner, list) and len(inner) >= 2 and inner[0] in (12, 13):
                vid_or_lid = inner[2] if len(inner) > 2 else None
                if inner[0] == 12:  # variable
                    return self.var_names.get(vid_or_lid) or self._clean_name(inner[1], 'var')
                else:               # list
                    return self.list_names.get(vid_or_lid) or self._clean_name(inner[1], 'lst')
            lit = _extract_literal(ref)
            if lit is not None:
                if isinstance(lit, str) and lit.lstrip('-').replace('.','',1).isdigit():
                    # Normalize to a proper Python numeric literal (strips leading
                    # zeros, trailing dots, etc.)  e.g. '07' → 7, '1.' → 1.0
                    try:
                        val = float(lit)
                        return str(int(val)) if val == int(val) else str(val)
                    except (ValueError, TypeError):
                        pass
                return repr(lit)
            ref = _value_ref(ref)
        if not isinstance(ref, str):
            return repr(ref)
        block = self.blocks.get(ref, {})
        op = block.get('opcode')
        if op == 'data_variable':
            fld = block.get('fields', {}).get('VARIABLE', ['var', None])
            vid = fld[1] if len(fld) > 1 else None
            return self.var_names.get(vid) or self._clean_name(fld[0], 'var')
        if op == 'argument_reporter_string_number':
            fld = block.get('fields', {}).get('VALUE', ['arg'])
            return _sanitize(fld[0], 'arg')
        if op in {'operator_add','operator_subtract','operator_multiply','operator_divide'}:
            a = self.render_expr(block.get('inputs', {}).get('NUM1'))
            b = self.render_expr(block.get('inputs', {}).get('NUM2'))
            sym = {'operator_add':'+','operator_subtract':'-','operator_multiply':'*','operator_divide':'/'}[op]
            return f'({a} {sym} {b})'
        if op == 'operator_mod':
            a = self.render_expr(block.get('inputs', {}).get('NUM1'))
            b = self.render_expr(block.get('inputs', {}).get('NUM2'))
            return f'({a} % {b})'
        if op == 'operator_random':
            from_ = self.render_expr(block.get('inputs', {}).get('FROM'))
            to = self.render_expr(block.get('inputs', {}).get('TO'))
            self._needs_random = True
            return f'random.randint({from_}, {to})'
        if op == 'operator_round':
            x = self.render_expr(block.get('inputs', {}).get('NUM'))
            return f'round({x})'
        if op in {'operator_lt','operator_gt','operator_equals'}:
            a = self.render_expr(block.get('inputs', {}).get('OPERAND1'))
            b = self.render_expr(block.get('inputs', {}).get('OPERAND2'))
            sym = {'operator_lt':'<','operator_gt':'>','operator_equals':'=='}[op]
            return f'({a} {sym} {b})'
        if op == 'operator_and':
            a = self.render_expr(block.get('inputs', {}).get('OPERAND1'))
            b = self.render_expr(block.get('inputs', {}).get('OPERAND2'))
            return f'({a} and {b})'
        if op == 'operator_or':
            a = self.render_expr(block.get('inputs', {}).get('OPERAND1'))
            b = self.render_expr(block.get('inputs', {}).get('OPERAND2'))
            return f'({a} or {b})'
        if op == 'operator_not':
            a = self.render_expr(block.get('inputs', {}).get('OPERAND'))
            return f'(not {a})'
        if op == 'operator_join':
            a = self.render_expr(block.get('inputs', {}).get('STRING1'))
            b = self.render_expr(block.get('inputs', {}).get('STRING2'))
            # Skip empty-string sides (str('') is useless padding)
            a_empty = a in ("''", '""', "''")
            b_empty = b in ("''", '""', "''")
            if a_empty and b_empty:
                return "''"
            if a_empty:
                return _join_side(b)
            if b_empty:
                return _join_side(a)
            return f'{_join_side(a)} + {_join_side(b)}'
        if op == 'operator_length':
            s = self.render_expr(block.get('inputs', {}).get('STRING'))
            return f'len({s})'
        if op == 'operator_letter_of':
            letter = self.render_expr(block.get('inputs', {}).get('LETTER'))
            s = self.render_expr(block.get('inputs', {}).get('STRING'))
            return f'{s}[{letter} - 1]'
        if op == 'operator_contains':
            s1 = self.render_expr(block.get('inputs', {}).get('STRING1'))
            s2 = self.render_expr(block.get('inputs', {}).get('STRING2'))
            return f'({s2} in {s1})'
        if op == 'operator_mathop':
            fname = block.get('fields', {}).get('OPERATOR', ['abs'])[0]
            x = self.render_expr(block.get('inputs', {}).get('NUM'))
            if fname in _MATHOP_MAP:
                if fname in _MATHOP_NEEDS_MATH:
                    self._needs_math = True
                return _MATHOP_MAP[fname].format(x=x)
            # Unknown mathop variant — safe fallback
            return f'{fname}({x})'
        if op == 'flipperoperator_isInBetween':
            value = self.render_expr(block.get('inputs', {}).get('VALUE'))
            lo = self.render_expr(block.get('inputs', {}).get('LOW'))
            hi = self.render_expr(block.get('inputs', {}).get('HIGH'))
            return f'({lo} <= {value} <= {hi})'
        if op == 'data_lengthoflist':
            fld = block.get('fields', {}).get('LIST', ['lst', None])
            lst = self.list_names.get(fld[1] if len(fld) > 1 else None) or self._clean_name(fld[0], 'lst')
            return f'len({lst})'
        if op == 'data_itemoflist':
            idx = self.render_expr(block.get('inputs', {}).get('INDEX'))
            fld = block.get('fields', {}).get('LIST', ['lst', None])
            lst = self.list_names.get(fld[1] if len(fld) > 1 else None) or self._clean_name(fld[0], 'lst')
            return f'{lst}[{idx} - 1]'
        if op == 'data_listcontainsitem':
            item = self.render_expr(block.get('inputs', {}).get('ITEM'))
            fld = block.get('fields', {}).get('LIST', ['lst', None])
            lst = self.list_names.get(fld[1] if len(fld) > 1 else None) or self._clean_name(fld[0], 'lst')
            return f'({item} in {lst})'
        if op == 'data_itemnumoflist':
            item = self.render_expr(block.get('inputs', {}).get('ITEM'))
            fld = block.get('fields', {}).get('LIST', ['lst', None])
            lst = self.list_names.get(fld[1] if len(fld) > 1 else None) or self._clean_name(fld[0], 'lst')
            return f'{lst}.index({item}) + 1'
        if op == 'flippersensors_orientationAxis':
            axis = block.get('fields', {}).get('AXIS', ['yaw'])[0]
            return f'robot.angle({self._axis(axis)})'
        if op == 'flippersensors_timer':
            return 'run.timer()'
        if op == 'flippersensors_loudness':
            return 'run.loudness()'
        if op == 'flippersensors_ismotion':
            motion = self._menu_value(block.get('inputs', {}).get('MOTION')) or 'moving'
            return f'robot.is_moving({motion!r})'
        if op == 'flippersensors_isTilted':
            direction = self._menu_value(block.get('inputs', {}).get('VALUE')) or 'any'
            return f'robot.is_tilted({direction!r})'
        if op == 'flippersensors_isorientation':
            orientation = self._menu_value(block.get('inputs', {}).get('ORIENTATION')) or 'upright'
            return f'robot.is_orientation({orientation!r})'
        if op == 'flippersensors_buttonIsPressed':
            # BUTTON and EVENT are fields, not inputs, in real SPIKE app projects.
            button = block.get('fields', {}).get('BUTTON', ['center'])[0]
            event = block.get('fields', {}).get('EVENT', ['pressed'])[0]
            if event == 'released':
                return f'robot.button_released({button!r})'
            return f'robot.button_pressed({button!r})'
        if op == 'flippersensors_distance':
            port_expr = self._port_expr(block.get('inputs', {}).get('PORT'))
            unit = self._menu_value(block.get('inputs', {}).get('UNIT')) or 'cm'
            return f'robot.distance({port_expr}, {unit!r})'
        if op == 'flippersensors_reflectivity':
            port_expr = self._port_expr(block.get('inputs', {}).get('PORT'))
            return f'robot.reflected_light({port_expr})'
        if op == 'flippersensors_color':
            port_expr = self._port_expr(block.get('inputs', {}).get('PORT'))
            return f'robot.color({port_expr})'
        if op == 'flippersensors_isColor':
            port_expr = self._port_expr(block.get('inputs', {}).get('PORT'))
            color = self._menu_value(block.get('inputs', {}).get('VALUE')) or '0'
            return f'robot.is_color({port_expr}, {self._color(color)})'
        if op == 'flippersensors_isDistance':
            port_expr = self._port_expr(block.get('inputs', {}).get('PORT'))
            comp = self._menu_value(block.get('inputs', {}).get('COMPARATOR')) or 'closer'
            value = self.render_expr(block.get('inputs', {}).get('VALUE'))
            unit = self._menu_value(block.get('inputs', {}).get('UNIT')) or 'cm'
            return f'robot.is_distance({port_expr}, {comp!r}, {value}, {unit!r})'
        if op == 'flippersensors_isPressed':
            port_expr = self._port_expr(block.get('inputs', {}).get('PORT'))
            option = self._menu_value(block.get('inputs', {}).get('OPTION')) or 'pressed'
            return f'robot.is_pressed({port_expr}, {option!r})'
        if op == 'flippersensors_force':
            port_expr = self._port_expr(block.get('inputs', {}).get('PORT'))
            unit = self._menu_value(block.get('inputs', {}).get('UNIT')) or 'percent'
            return f'robot.force({port_expr}, {unit!r})'
        if op == 'flippermotor_speed':
            port_expr = self._port_expr(block.get('inputs', {}).get('PORT'))
            return f'robot.motor_speed({port_expr})'
        if op == 'flippermotor_absolutePosition':
            port_expr = self._port_expr(block.get('inputs', {}).get('PORT'))
            return f'robot.motor_position({port_expr})'
        if op == 'flippermoremotor_position':
            port_expr = self._port_expr(block.get('inputs', {}).get('PORT'))
            return f'robot.motor_relative_position({port_expr})'
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
        # argument_reporter_boolean — same pattern as string_number
        if op == 'argument_reporter_boolean':
            fld = block.get('fields', {}).get('VALUE', ['arg'])
            return _sanitize(fld[0], 'arg')

        # flippermoremotor_power expression
        if op == 'flippermoremotor_power':
            port_expr = self._port_expr(block.get('inputs', {}).get('PORT'))
            return f'robot.motor_power({port_expr})'

        # flippermoremotor_menu_acceleration — shadow menu with value like "3000 3000"
        if op == 'flippermoremotor_menu_acceleration':
            val = block.get('fields', {}).get('acceleration', ['0'])[0]
            first = val.split()[0] if isinstance(val, str) else str(val)
            try:
                n = int(float(first))
                return str(n)
            except (ValueError, TypeError):
                return repr(val)

        # sound_volume expression
        if op == 'sound_volume':
            return 'robot.volume()'

        # flippersensors_isReflectivity — bool expression with comparator
        if op == 'flippersensors_isReflectivity':
            port_expr = self._port_expr(block.get('inputs', {}).get('PORT'))
            comp = block.get('fields', {}).get('COMPARATOR', ['equal'])[0]
            value = self.render_expr(block.get('inputs', {}).get('VALUE'))
            return f'robot.is_reflected_light({port_expr}, {comp!r}, {value})'

        # ── IMU / orientation (flippermoresensors_*) ──────────────────────────
        if op == 'flippermoresensors_orientation':
            return 'robot.orientation()'
        if op == 'flippermoresensors_motion':
            return 'robot.motion()'
        if op == 'flippermoresensors_acceleration':
            axis = block.get('fields', {}).get('AXIS', ['x'])[0]
            return f'robot.acceleration({self._axis(axis)})'
        if op == 'flippermoresensors_angularVelocity':
            axis = block.get('fields', {}).get('AXIS', ['x'])[0]
            return f'robot.angular_velocity({self._axis(axis)})'
        # ── Raw/extra sensor reporters ─────────────────────────────────────────
        if op == 'flippersensors_rawColor':
            port_expr = self._port_expr(block.get('inputs', {}).get('PORT'))
            return f'robot.raw_color({port_expr})'
        if op == 'flippersensors_colorValue':
            port_expr = self._port_expr(block.get('inputs', {}).get('PORT'))
            return f'robot.color_value({port_expr})'
        # ── Hub button pressed (flipperlight / flippersensors variants) ────────
        if op in {'flipperlight_buttonIsPressed', 'flippersensors_hubButtonIsPressed'}:
            button = block.get('fields', {}).get('BUTTON', ['center'])[0]
            return f'robot.hub_button_pressed({button!r})'
        # ── Raw port value ─────────────────────────────────────────────────────
        if op == 'flippermore_port':
            port_expr = self._port_expr(block.get('inputs', {}).get('PORT'))
            return f'robot.port_value({port_expr})'
        # ── Timer (flipperevents_ alias) ───────────────────────────────────────
        if op == 'flipperevents_timer':
            return 'run.timer()'
        # ── Music reporter ─────────────────────────────────────────────────────
        if op == 'flippermusic_getTempo':
            return 'robot.tempo()'

        # Generic SPIKE widget/selector block — no inputs, one field named
        # 'field_{opcode}' (e.g. flippermove_rotation-wheel, custom-icon-direction,
        # multiple-port-selector, etc.).  Return the raw field value as a Python
        # literal so steering, direction and port menus resolve correctly.
        if op and not block.get('inputs'):
            field_key = f'field_{op}'
            raw = block.get('fields', {}).get(field_key)
            if raw and isinstance(raw, list) and raw[0] is not None:
                val = raw[0]
                try:
                    f = float(val)
                    return str(int(f)) if f == int(f) else str(f)
                except (ValueError, TypeError):
                    # Try to map a known image name or pixel string to LightImage.*
                    img = _PIXEL_TO_IMAGE.get(val)
                    if img:
                        self._needs_image = True
                        return f'LightImage.{img}'
                    return repr(val)

        self._unknown_exprs.add(op or 'unknown')
        return f'0  # TODO: {op}'

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
                    target = self._vname(next_block.get('fields', {}).get('VARIABLE', ['var']))
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
            name = self._vname(flds.get('VARIABLE', ['var']))
            return [f'{indent}{name} = {self.render_expr(ins.get("VALUE"))}']
        if op == 'data_changevariableby':
            name = self._vname(flds.get('VARIABLE', ['var']))
            return [f'{indent}{name} += {self.render_expr(ins.get("VALUE"))}']
        if op == 'data_addtolist':
            name = self._lname(flds.get('LIST', ['lst']))
            return [f'{indent}{name}.append({self.render_expr(ins.get("ITEM"))})']
        if op == 'data_deletealloflist':
            name = self._lname(flds.get('LIST', ['lst']))
            return [f'{indent}{name}.clear()']
        if op == 'data_insertatlist':
            name = self._lname(flds.get('LIST', ['lst']))
            idx = self.render_expr(ins.get('INDEX'))
            item = self.render_expr(ins.get('ITEM'))
            return [f'{indent}{name}.insert(({idx})-1, {item})']
        if op == 'data_replaceitemoflist':
            name = self._lname(flds.get('LIST', ['lst']))
            idx = self.render_expr(ins.get('INDEX'))
            item = self.render_expr(ins.get('ITEM'))
            return [f'{indent}{name}[{idx} - 1] = {item}']
        if op == 'data_deleteoflist':
            name = self._lname(flds.get('LIST', ['lst']))
            idx = self.render_expr(ins.get('INDEX'))
            return [f'{indent}del {name}[{idx} - 1]']
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
        if op == 'control_forever':
            body = self.render_stmt_chain(_value_ref(ins.get('SUBSTACK')), indent + '    ') or [indent + '    pass']
            return [f'{indent}while True:', *body]
        if op == 'control_repeat_until':
            cond = self.render_expr(ins.get('CONDITION'))
            body = self.render_stmt_chain(_value_ref(ins.get('SUBSTACK')), indent + '    ') or [indent + '    pass']
            return [f'{indent}while not ({cond}):', *body]
        if op == 'control_wait_until':
            cond = self.render_expr(ins.get('CONDITION'))
            return [f'{indent}run.wait_until(lambda: {cond})']
        if op in {'control_stop', 'flippercontrol_stop'}:
            option = flds.get('STOP_OPTION', ['this script'])[0] if flds.get('STOP_OPTION') else 'this script'
            if option == 'this script':
                return [f'{indent}return']
            return [f'{indent}return  # stop: {option}']
        if op == 'procedures_call':
            bid = self._find_block_id(block)
            return [f'{indent}{self.render_expr(bid)}']
        if op == 'flippermove_stopMove':
            return [f'{indent}robot.stop()']
        if op == 'flippermove_setMovementPair':
            pair = self._menu_value(ins.get('PAIR')) or 'AB'
            if len(pair) >= 2:
                return [f'{indent}robot.use_pair(port.{pair[0]}, port.{pair[1]})']
            return [f'{indent}robot.use_pair({pair!r})']
        if op == 'flippermoremove_startDualSpeed':
            left = self.render_expr(ins.get('LEFT'))
            right = self.render_expr(ins.get('RIGHT'))
            return [f'{indent}robot.drive({left}, {right})']
        if op == 'flippermoremove_startDualPower':
            left = self.render_expr(ins.get('LEFT'))
            right = self.render_expr(ins.get('RIGHT'))
            return [f'{indent}robot.drive_power({left}, {right})']
        if op == 'flippermoremotor_motorSetDegreeCounted':
            port_expr = self._port_expr(ins.get('PORT'))
            value = self.render_expr(ins.get('VALUE'))
            return [f'{indent}robot.set_motor_position({port_expr}, {value})']
        if op == 'flippersensors_resetYaw':
            return [f'{indent}robot.reset_yaw()']
        if op == 'flippersensors_resetTimer':
            return [f'{indent}run.reset_timer()']
        if op == 'flippermotor_motorStartDirection':
            port_expr = self._port_expr(ins.get('PORT'))
            direction = self._menu_value(ins.get('DIRECTION')) or 'clockwise'
            return [f'{indent}robot.run_motor({port_expr}, {self._dir(direction)})']
        if op == 'flippermotor_motorStop':
            port_expr = self._port_expr(ins.get('PORT'))
            return [f'{indent}robot.stop_motor({port_expr})']
        if op == 'flippermotor_motorTurnForDirection':
            port_expr = self._port_expr(ins.get('PORT'))
            direction = self._menu_value(ins.get('DIRECTION')) or 'clockwise'
            value = self.render_expr(ins.get('VALUE'))
            unit = self._menu_value(ins.get('UNIT')) or 'degrees'
            return [f'{indent}robot.run_motor_for({port_expr}, {self._dir(direction)}, {value}, {unit!r})']
        if op == 'flippermotor_motorGoDirectionToPosition':
            port_expr = self._port_expr(ins.get('PORT'))
            direction = self._menu_value(ins.get('DIRECTION')) or 'shortest'
            position = self.render_expr(ins.get('POSITION'))
            return [f'{indent}robot.motor_go_to_position({port_expr}, {self._dir(direction)}, {position})']
        if op == 'flippermotor_motorSetSpeed':
            port_expr = self._port_expr(ins.get('PORT'))
            speed = self.render_expr(ins.get('SPEED'))
            return [f'{indent}robot.set_motor_speed({port_expr}, {speed})']
        if op == 'flippersound_beep':
            note = self.render_expr(ins.get('NOTE'))
            return [f'{indent}robot.beep({note})']
        if op == 'flippersound_beepForTime':
            note = self.render_expr(ins.get('NOTE'))
            duration = self.render_expr(ins.get('DURATION'))
            return [f'{indent}robot.beep_for({note}, {duration})']
        if op == 'flippersound_stopSound':
            return [f'{indent}robot.stop_sound()']
        if op == 'flippersound_playSound':
            sound = self._menu_value(ins.get('SOUND')) or '0'
            return [f'{indent}robot.play_sound({sound!r})']
        if op == 'flippersound_playSoundUntilDone':
            sound = self._menu_value(ins.get('SOUND')) or '0'
            return [f'{indent}robot.play_sound_until_done({sound!r})']
        if op == 'flipperdisplay_ledMatrix':
            port_expr = self._port_expr(ins.get('PORT'))
            matrix = self.render_expr(ins.get('MATRIX'))
            return [f'{indent}robot.show_image({port_expr}, {matrix})']
        if op == 'flipperdisplay_ledMatrixFor':
            port_expr = self._port_expr(ins.get('PORT'))
            matrix = self.render_expr(ins.get('MATRIX'))
            value = self.render_expr(ins.get('VALUE'))
            return [f'{indent}robot.show_image_for({port_expr}, {matrix}, {value})']
        if op == 'flipperdisplay_ledMatrixText':
            port_expr = self._port_expr(ins.get('PORT'))
            text = self.render_expr(ins.get('TEXT'))
            return [f'{indent}robot.show_text({port_expr}, {text})']
        if op == 'flipperdisplay_ledMatrixOff':
            port_expr = self._port_expr(ins.get('PORT'))
            return [f'{indent}robot.turn_off_pixels({port_expr})']
        if op == 'flipperdisplay_ledMatrixOn':
            port_expr = self._port_expr(ins.get('PORT'))
            x = self.render_expr(ins.get('X'))
            y = self.render_expr(ins.get('Y'))
            brightness = self.render_expr(ins.get('BRIGHTNESS'))
            return [f'{indent}robot.set_pixel({port_expr}, {x}, {y}, {brightness})']
        if op == 'flipperdisplay_ledMatrixBrightness':
            port_expr = self._port_expr(ins.get('PORT'))
            brightness = self.render_expr(ins.get('BRIGHTNESS'))
            return [f'{indent}robot.set_pixel_brightness({port_expr}, {brightness})']
        if op == 'flipperdisplay_centerButtonLight':
            color = self._menu_value(ins.get('COLOR')) or 'white'
            return [f'{indent}robot.set_center_light({self._color(color)})']
        # ── Additional motor opcodes (flippermoremotor_*) ─────────────────────
        if op == 'flippermoremotor_motorStartSpeed':
            port_expr = self._port_expr(ins.get('PORT'))
            speed = self.render_expr(ins.get('SPEED'))
            return [f'{indent}robot.run_motor({port_expr}, {speed})']
        if op == 'flippermoremotor_motorTurnForSpeed':
            port_expr = self._port_expr(ins.get('PORT'))
            value = self.render_expr(ins.get('VALUE'))
            unit = self._menu_value(ins.get('UNIT')) or 'degrees'
            speed = self.render_expr(ins.get('SPEED'))
            return [f"{indent}robot.run_motor_for({port_expr}, {value}, '{unit}', speed={speed})"]
        if op == 'flippermoremotor_motorSetStopMethod':
            port_expr = self._port_expr(ins.get('PORT'))
            mode = flds.get('STOP', ['coast'])[0].lower()
            return [f'{indent}robot.set_stop_mode({port_expr}, {self._stop(mode)})']
        if op == 'flippermoremotor_motorSetDegreeCounted':
            port_expr = self._port_expr(ins.get('PORT'))
            value = self.render_expr(ins.get('VALUE'))
            return [f'{indent}robot.set_motor_position({port_expr}, {value})']
        # ── Additional drive/steer opcodes ────────────────────────────────────
        if op == 'flippermoremove_startSteerAtSpeed':
            steering = self.render_expr(ins.get('STEERING'))
            speed = self.render_expr(ins.get('SPEED'))
            return [f'{indent}robot.steer({steering}, {speed})']
        if op == 'flippermoremove_steerDistanceAtSpeed':
            steering = self.render_expr(ins.get('STEERING'))
            dist = self.render_expr(ins.get('DISTANCE'))
            unit = self._menu_value(ins.get('UNIT')) or 'cm'
            speed = self.render_expr(ins.get('SPEED'))
            return [f'{indent}robot.steer_for({steering}, {dist}, {unit!r}, {speed})']
        # ── Hub light ─────────────────────────────────────────────────────────
        if op == 'flipperlight_lightDisplayText':
            text = self.render_expr(ins.get('TEXT'))
            return [f'{indent}robot.show_text({text})']
        if op == 'flipperlight_centerButtonLight':
            color = self._menu_value(ins.get('COLOR')) or 'white'
            return [f'{indent}robot.set_center_light({self._color(color)})']
        # ── Control: for-each loop ────────────────────────────────────────────
        if op == 'control_for_each':
            var = self._vname(flds.get('VARIABLE', ['item']))
            lst = self._lname(flds.get('LIST', ['lst']))
            body = self.render_stmt_chain(_value_ref(ins.get('SUBSTACK')), indent + '    ') or [indent + '    pass']
            return [f'{indent}for {var} in {lst}:', *body]
        # ── Movement (flippermove_*) ──────────────────────────────────────────────
        if op == 'flippermove_move':
            direction = self._menu_value(ins.get('DIRECTION')) or 'forward'
            value = self.render_expr(ins.get('VALUE'))
            unit = flds.get('UNIT', ['cm'])[0]
            return [f'{indent}robot.move({direction!r}, {value}, {unit!r})']
        if op == 'flippermove_steer':
            steering = self.render_expr(ins.get('STEERING'))
            value = self.render_expr(ins.get('VALUE'))
            unit = flds.get('UNIT', ['cm'])[0]
            return [f'{indent}robot.steer({steering}, {value}, {unit!r})']
        if op == 'flippermove_startMove':
            direction = self._menu_value(ins.get('DIRECTION')) or 'forward'
            return [f'{indent}robot.start_move({direction!r})']
        if op == 'flippermove_startSteer':
            steering = self.render_expr(ins.get('STEERING'))
            return [f'{indent}robot.start_steer({steering})']
        if op == 'flippermove_movementSpeed':
            speed = self.render_expr(ins.get('SPEED'))
            return [f'{indent}robot.set_move_speed({speed})']
        if op == 'flippermove_setDistance':
            dist = self.render_expr(ins.get('DISTANCE'))
            unit = flds.get('UNIT', ['cm'])[0]
            return [f'{indent}robot.set_move_scale({dist}, {unit!r})']

        # ── Movement advanced (flippermoremove_*) ─────────────────────────────────
        if op == 'flippermoremove_movementSetAcceleration':
            accel = self.render_expr(ins.get('ACCELERATION'))
            return [f'{indent}robot.set_move_acceleration({accel})']
        if op == 'flippermoremove_movementSetStopMethod':
            mode = flds.get('STOP', ['coast'])[0].lower()
            return [f'{indent}robot.set_move_stop_mode({self._stop(mode)})']

        # ── Motor advanced (flippermoremotor_*) ───────────────────────────────────
        if op == 'flippermoremotor_motorStartPower':
            port_expr = self._port_expr(ins.get('PORT'))
            power = self.render_expr(ins.get('POWER'))
            return [f'{indent}robot.run_motor_power({port_expr}, {power})']
        if op == 'flippermoremotor_motorGoToRelativePosition':
            port_expr = self._port_expr(ins.get('PORT'))
            position = self.render_expr(ins.get('POSITION'))
            speed = self.render_expr(ins.get('SPEED'))
            return [f'{indent}robot.motor_go_to_relative_position({port_expr}, {position}, {speed})']
        if op == 'flippermoremotor_motorSetAcceleration':
            port_expr = self._port_expr(ins.get('PORT'))
            accel = self.render_expr(ins.get('ACCELERATION'))
            return [f'{indent}robot.set_motor_acceleration({port_expr}, {accel})']

        # ── Hub display (flipperlight_*) ───────────────────────────────────────────
        if op == 'flipperlight_lightDisplayOff':
            return [f'{indent}robot.hub_display_off()']
        if op == 'flipperlight_lightDisplayImageOnForTime':
            matrix = self._image(self.render_expr(ins.get('MATRIX')))
            value = self.render_expr(ins.get('VALUE'))
            return [f'{indent}robot.hub_show_image_for({matrix}, {value})']
        if op == 'flipperlight_lightDisplayRotate':
            direction = self._menu_value(ins.get('DIRECTION')) or 'clockwise'
            return [f'{indent}robot.hub_display_rotate({self._dir(direction)})']
        if op == 'flipperlight_lightDisplaySetBrightness':
            brightness = self.render_expr(ins.get('BRIGHTNESS'))
            return [f'{indent}robot.hub_display_brightness({brightness})']
        if op == 'flipperlight_lightDisplaySetOrientation':
            orientation = self._menu_value(ins.get('ORIENTATION')) or 'upright'
            return [f'{indent}robot.hub_display_orientation({orientation!r})']
        if op == 'flipperlight_lightDisplaySetPixel':
            x = self.render_expr(ins.get('X'))
            y = self.render_expr(ins.get('Y'))
            brightness = self.render_expr(ins.get('BRIGHTNESS'))
            return [f'{indent}robot.hub_set_pixel({x}, {y}, {brightness})']
        if op == 'flipperlight_ultrasonicLightUp':
            port_expr = self._port_expr(ins.get('PORT'))
            value = self.render_expr(ins.get('VALUE'))
            return [f'{indent}robot.ultrasonic_light({port_expr}, {value})']

        # ── Control ───────────────────────────────────────────────────────────────
        if op == 'flippercontrol_stopOtherStacks':
            return [f'{indent}run.stop_other_stacks()']

        # ── Broadcasts ────────────────────────────────────────────────────────────
        if op == 'event_broadcast':
            bcast_inp = ins.get('BROADCAST_INPUT')
            if isinstance(bcast_inp, list) and len(bcast_inp) > 1:
                inner = bcast_inp[1]
                if isinstance(inner, list) and len(inner) >= 2 and inner[0] == 11:
                    return [f'{indent}run.broadcast({inner[1]!r})']
            return [f'{indent}run.broadcast(???)  # unknown broadcast']
        if op == 'event_broadcastandwait':
            bcast_inp = ins.get('BROADCAST_INPUT')
            if isinstance(bcast_inp, list) and len(bcast_inp) > 1:
                inner = bcast_inp[1]
                if isinstance(inner, list) and len(inner) >= 2 and inner[0] == 11:
                    return [f'{indent}run.broadcast_and_wait({inner[1]!r})']
            return [f'{indent}run.broadcast_and_wait(???)  # unknown broadcast']

        # ── Sound (standard Scratch sound blocks) ────────────────────────────────
        if op == 'sound_setvolumeto':
            volume = self.render_expr(ins.get('VOLUME'))
            return [f'{indent}robot.set_volume({volume})']
        if op == 'sound_changevolumeby':
            volume = self.render_expr(ins.get('VOLUME'))
            return [f'{indent}robot.change_volume({volume})']
        if op == 'sound_seteffectto':
            effect = flds.get('EFFECT', ['pitch'])[0].lower()
            value = self.render_expr(ins.get('VALUE'))
            return [f'{indent}robot.set_sound_effect({effect!r}, {value})']
        if op == 'sound_changeeffectby':
            effect = flds.get('EFFECT', ['pitch'])[0].lower()
            value = self.render_expr(ins.get('VALUE'))
            return [f'{indent}robot.change_sound_effect({effect!r}, {value})']

        # ── IMU / orientation (flippermoresensors_*) ──────────────────────────
        if op == 'flippermoresensors_setOrientation':
            up   = self._menu_value(ins.get('UP'))   or 'front'
            front = self._menu_value(ins.get('FRONT')) or 'up'
            return [f'{indent}robot.set_orientation({up!r}, {front!r})']

        # ── Hub display — show image permanently (no timer) ───────────────────
        if op == 'flipperlight_lightDisplayImageOn':
            matrix = self._image(self.render_expr(ins.get('MATRIX')))
            return [f'{indent}robot.hub_show_image({matrix})']

        # ── Color matrix accessory (flipperlight_lightColorMatrix*) ───────────
        if op == 'flipperlight_lightColorMatrixImageOn':
            port_expr = self._port_expr(ins.get('PORT'))
            image = self.render_expr(ins.get('IMAGE'))
            return [f'{indent}robot.color_matrix({port_expr}, {image})']
        if op == 'flipperlight_lightColorMatrixImageOnForTime':
            port_expr = self._port_expr(ins.get('PORT'))
            image = self.render_expr(ins.get('IMAGE'))
            duration = self.render_expr(ins.get('VALUE'))
            return [f'{indent}robot.color_matrix_for({port_expr}, {image}, {duration})']
        if op == 'flipperlight_lightColorMatrixOff':
            port_expr = self._port_expr(ins.get('PORT'))
            return [f'{indent}robot.color_matrix_off({port_expr})']
        if op == 'flipperlight_lightColorMatrixSetBrightness':
            port_expr = self._port_expr(ins.get('PORT'))
            brightness = self.render_expr(ins.get('BRIGHTNESS'))
            return [f'{indent}robot.color_matrix_brightness({port_expr}, {brightness})']
        if op == 'flipperlight_lightColorMatrixSetPixel':
            port_expr = self._port_expr(ins.get('PORT'))
            x = self.render_expr(ins.get('X'))
            y = self.render_expr(ins.get('Y'))
            color = self.render_expr(ins.get('COLOR'))
            return [f'{indent}robot.color_matrix_pixel({port_expr}, {x}, {y}, {color})']
        if op == 'flipperlight_lightColorMatrixRotate':
            port_expr = self._port_expr(ins.get('PORT'))
            direction = self._menu_value(ins.get('DIRECTION')) or 'clockwise'
            return [f'{indent}robot.color_matrix_rotate({port_expr}, {self._dir(direction)})']
        if op == 'flipperlight_lightColorMatrixSetOrientation':
            port_expr = self._port_expr(ins.get('PORT'))
            orientation = self._menu_value(ins.get('ORIENTATION')) or 'upright'
            return [f'{indent}robot.color_matrix_orientation({port_expr}, {orientation!r})']

        # ── Misc / flippermore ────────────────────────────────────────────────
        if op == 'flippermore_stopOtherStacks':
            return [f'{indent}run.stop_other_stacks()']

        # ── Timer alias (flipperevents_resetTimer) ────────────────────────────
        if op == 'flipperevents_resetTimer':
            return [f'{indent}run.reset_timer()']

        # ── Opcode aliases: flippermotor_* mirroring flippermoremotor_* ───────
        if op == 'flippermotor_motorSetAcceleration':
            port_expr = self._port_expr(ins.get('PORT'))
            accel = self.render_expr(ins.get('ACCELERATION'))
            return [f'{indent}robot.set_motor_acceleration({port_expr}, {accel})']
        if op == 'flippermotor_motorSetStopMethod':
            port_expr = self._port_expr(ins.get('PORT'))
            mode = flds.get('STOP', ['coast'])[0].lower()
            return [f'{indent}robot.set_stop_mode({port_expr}, {self._stop(mode)})']

        # ── Opcode aliases: flippermove_* mirroring flippermoremove_* ─────────
        if op == 'flippermove_movementSetAcceleration':
            accel = self.render_expr(ins.get('ACCELERATION'))
            return [f'{indent}robot.set_move_acceleration({accel})']
        if op == 'flippermove_movementSetStopMethod':
            mode = flds.get('STOP', ['coast'])[0].lower()
            return [f'{indent}robot.set_move_stop_mode({self._stop(mode)})']
        if op == 'flippermove_startDualSpeed':
            left = self.render_expr(ins.get('LEFT'))
            right = self.render_expr(ins.get('RIGHT'))
            return [f'{indent}robot.drive({left}, {right})']

        # ── Music (flippermusic_*) ─────────────────────────────────────────────
        if op == 'flippermusic_playDrumForBeats':
            drum = self.render_expr(ins.get('DRUM'))
            beats = self.render_expr(ins.get('BEATS'))
            return [f'{indent}robot.play_drum({drum}, {beats})']
        if op == 'flippermusic_playNoteForBeats':
            note = self.render_expr(ins.get('NOTE'))
            beats = self.render_expr(ins.get('BEATS'))
            return [f'{indent}robot.play_note({note}, {beats})']
        if op == 'flippermusic_setTempo':
            tempo = self.render_expr(ins.get('TEMPO'))
            return [f'{indent}robot.set_tempo({tempo})']
        if op == 'flippermusic_setInstrument':
            instrument = self.render_expr(ins.get('INSTRUMENT'))
            return [f'{indent}robot.set_instrument({instrument})']

        # ── Horizontal (icon) mode blocks — motor ─────────────────────────────
        if op == 'horizontalmotor_motorTurnClockwiseRotations':
            port_expr = self._port_expr(ins.get('PORT'))
            rotations = self.render_expr(ins.get('ROTATIONS'))
            return [f'{indent}robot.run_motor_for({port_expr}, {self._dir("clockwise")}, {rotations}, \'rotations\')']
        if op == 'horizontalmotor_motorTurnCounterClockwiseRotations':
            port_expr = self._port_expr(ins.get('PORT'))
            rotations = self.render_expr(ins.get('ROTATIONS'))
            return [f'{indent}robot.run_motor_for({port_expr}, {self._dir("counterclockwise")}, {rotations}, \'rotations\')']
        if op == 'horizontalmotor_motorSetSpeed':
            port_expr = self._port_expr(ins.get('PORT'))
            speed = self.render_expr(ins.get('SPEED'))
            return [f'{indent}robot.set_motor_speed({port_expr}, {speed})']
        if op == 'horizontalmotor_motorStop':
            port_expr = self._port_expr(ins.get('PORT'))
            return [f'{indent}robot.stop_motor({port_expr})']

        # ── Horizontal (icon) mode blocks — movement ──────────────────────────
        if op == 'horizontalmove_moveForward':
            value = self.render_expr(ins.get('VALUE'))
            return [f"{indent}robot.move('forward', {value})"]
        if op == 'horizontalmove_moveBackward':
            value = self.render_expr(ins.get('VALUE'))
            return [f"{indent}robot.move('back', {value})"]
        if op == 'horizontalmove_moveTurnClockwiseRotations':
            rotations = self.render_expr(ins.get('ROTATIONS'))
            return [f"{indent}robot.steer(100, {rotations}, 'rotations')"]
        if op == 'horizontalmove_moveTurnCounterClockwiseRotations':
            rotations = self.render_expr(ins.get('ROTATIONS'))
            return [f"{indent}robot.steer(-100, {rotations}, 'rotations')"]
        if op == 'horizontalmove_moveSetSpeed':
            speed = self.render_expr(ins.get('SPEED'))
            return [f'{indent}robot.set_move_speed({speed})']
        if op == 'horizontalmove_moveStop':
            return [f'{indent}robot.stop()']

        # ── Horizontal (icon) mode — control/display ──────────────────────────
        if op == 'horizontalcontrol_stopOtherStacks':
            return [f'{indent}run.stop_other_stacks()']
        if op == 'horizontaldisplay_ledMatrix':
            matrix = self.render_expr(ins.get('MATRIX'))
            return [f'{indent}robot.hub_show_image({matrix})']
        if op == 'horizontaldisplay_ledImage':
            image = self.render_expr(ins.get('IMAGE'))
            return [f'{indent}robot.hub_show_image({image})']

        self._unknown_stmts.add(op or 'unknown')
        return [f'{indent}pass  # TODO: {op}']

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
        logger.debug(t("pf_exp.render"))
        # ── Pass 1: render all bodies (populates _needs_math/_unknown_*) ──────
        proc_chunks: list[list[str]] = []
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
            body = self.render_stmt_chain(proc['body'], '    ')
            if not body:
                body = ['    pass']
            # Inject robot.note() lines for comments attached to the def block
            note_lines = self._note_lines(proc['def_id'])
            if note_lines:
                body = note_lines + body
            proc_chunks.append(['@robot.proc', f'def {proc["name"]}({args}):', *body, ''])

        # ── Collect all top-level event blocks ────────────────────────────────
        event_chunks: list[list[str]] = []
        main_counter = [0]
        event_counter: dict[str, int] = {}

        def _fn_name(base: str) -> str:
            event_counter[base] = event_counter.get(base, 0) + 1
            n = event_counter[base]
            return base if n == 1 else f'{base}_{n}'

        for bid, b in self.blocks.items():
            if not b.get('topLevel'):
                continue
            evop = b.get('opcode', '')
            raw_body = self.render_stmt_chain(b.get('next'), '    ') or ['    pass']
            # Prepend robot.note() calls for Scratch comments attached to this hat block
            note_lines = self._note_lines(bid)
            body_lines = note_lines + raw_body if note_lines else raw_body

            if evop == 'flipperevents_whenProgramStarts':
                main_counter[0] += 1
                fn = 'main' if main_counter[0] == 1 else f'main_{main_counter[0]}'
                event_chunks.append(['@run.main', f'def {fn}():', *body_lines, ''])

            elif evop == 'flipperevents_whenButton':
                button = b.get('fields', {}).get('BUTTON', ['center'])[0]
                event = b.get('fields', {}).get('EVENT', ['pressed'])[0]
                fn = _fn_name('on_button')
                event_chunks.append([f'@run.when_button({button!r}, {event!r})', f'def {fn}():', *body_lines, ''])

            elif evop == 'flipperevents_whenGesture':
                gesture = b.get('fields', {}).get('EVENT', ['shake'])[0]
                fn = _fn_name('on_gesture')
                event_chunks.append([f'@run.when_gesture({gesture!r})', f'def {fn}():', *body_lines, ''])

            elif evop == 'flipperevents_whenOrientation':
                value = b.get('fields', {}).get('VALUE', ['front'])[0]
                fn = _fn_name('on_orientation')
                event_chunks.append([f'@run.when_orientation({value!r})', f'def {fn}():', *body_lines, ''])

            elif evop == 'flipperevents_whenTilted':
                direction = self._menu_value(b.get('inputs', {}).get('VALUE')) or 'any'
                fn = _fn_name('on_tilted')
                event_chunks.append([f'@run.when_tilted({direction!r})', f'def {fn}():', *body_lines, ''])

            elif evop == 'flipperevents_whenTimer':
                threshold = self.render_expr(b.get('inputs', {}).get('VALUE'))
                fn = _fn_name('on_timer')
                event_chunks.append([f'@run.when_timer({threshold})', f'def {fn}():', *body_lines, ''])

            elif evop == 'flipperevents_whenColor':
                port_expr = self._port_expr(b.get('inputs', {}).get('PORT'))
                option = self._menu_value(b.get('inputs', {}).get('OPTION')) or 'any'
                fn = _fn_name('on_color')
                event_chunks.append([f'@run.when_color({port_expr}, {option!r})', f'def {fn}():', *body_lines, ''])

            elif evop == 'flipperevents_whenPressed':
                port_expr = self._port_expr(b.get('inputs', {}).get('PORT'))
                option = b.get('fields', {}).get('OPTION', ['pressed'])[0]
                fn = _fn_name('on_pressed')
                event_chunks.append([f'@run.when_pressed({port_expr}, {option!r})', f'def {fn}():', *body_lines, ''])

            elif evop == 'flipperevents_whenCondition':
                cond = self.render_expr(b.get('inputs', {}).get('CONDITION'))
                fn = _fn_name('on_condition')
                event_chunks.append([f'@run.when_condition(lambda: {cond})', f'def {fn}():', *body_lines, ''])

            elif evop == 'event_whenbroadcastreceived':
                broadcast = b.get('fields', {}).get('BROADCAST_OPTION', ['message1'])[0]
                fn = _fn_name('on_broadcast')
                event_chunks.append([f'@run.when_broadcast({broadcast!r})', f'def {fn}():', *body_lines, ''])

            elif evop == 'flipperevents_whenBroadcast':
                broadcast = b.get('fields', {}).get('BROADCAST', ['message1'])[0]
                fn = _fn_name('on_broadcast')
                event_chunks.append([f'@run.when_broadcast({broadcast!r})', f'def {fn}():', *body_lines, ''])

            elif evop == 'flipperevents_whenNearOrFar':
                port_expr = self._port_expr(b.get('inputs', {}).get('PORT'))
                option = b.get('fields', {}).get('OPTION', ['near'])[0]
                fn = _fn_name('on_near_or_far')
                event_chunks.append([f'@run.when_near_or_far({port_expr}, {option!r})', f'def {fn}():', *body_lines, ''])

            elif evop == 'flipperevents_whenDistance':
                port_expr = self._port_expr(b.get('inputs', {}).get('PORT'))
                comp = b.get('fields', {}).get('COMPARATOR', ['less_than'])[0]
                value = self.render_expr(b.get('inputs', {}).get('VALUE'))
                fn = _fn_name('on_distance')
                event_chunks.append([f'@run.when_distance({port_expr}, {comp!r}, {value})', f'def {fn}():', *body_lines, ''])

            # ── Horizontal (icon) events ────────────────────────────────────────
            elif evop == 'horizontalevents_whenProgramStarts':
                main_counter[0] += 1
                fn = 'main' if main_counter[0] == 1 else f'main_{main_counter[0]}'
                event_chunks.append(['@run.main', f'def {fn}():', *body_lines, ''])

            elif evop == 'horizontalevents_whenBroadcast':
                broadcast = b.get('fields', {}).get('BROADCAST', ['message1'])[0]
                fn = _fn_name('on_broadcast')
                event_chunks.append([f'@run.when_broadcast({broadcast!r})', f'def {fn}():', *body_lines, ''])

            elif evop == 'horizontalevents_whenCloserThan':
                value = self.render_expr(b.get('inputs', {}).get('VALUE'))
                fn = _fn_name('on_closer_than')
                event_chunks.append([f'@run.when_distance_closer_than({value})', f'def {fn}():', *body_lines, ''])

            elif evop == 'horizontalevents_whenColor':
                color = self._menu_value(b.get('inputs', {}).get('COLOR')) or 'any'
                fn = _fn_name('on_color')
                event_chunks.append([f'@run.when_color(port.A, {color!r})', f'def {fn}():', *body_lines, ''])

            elif evop == 'horizontalevents_whenPressed':
                fn = _fn_name('on_pressed')
                event_chunks.append(["@run.when_pressed(port.A, 'pressed')", f'def {fn}():', *body_lines, ''])

            elif evop == 'horizontalevents_whenTilted':
                direction = b.get('fields', {}).get('DIRECTION', ['any'])[0]
                fn = _fn_name('on_tilted')
                event_chunks.append([f'@run.when_tilted({direction!r})', f'def {fn}():', *body_lines, ''])

            elif evop == 'horizontalevents_whenLouderThan':
                value = self.render_expr(b.get('inputs', {}).get('VALUE'))
                fn = _fn_name('on_louder_than')
                event_chunks.append([f'@run.when_louder_than({value})', f'def {fn}():', *body_lines, ''])

            elif evop in {
                'procedures_definition', 'procedures_prototype',
                'flipperevents_color-selector', 'flipperevents_color-sensor-selector',
                'flipperevents_custom-tilted', 'flipperevents_force-sensor-selector',
            }:
                pass  # handled separately or are menu blocks

            # else: unknown top-level opcode — will appear in unknown_stmts via render_stmt

        # ── Pass 2: assemble file with header determined from pass 1 ──────────
        doc_path = Path(self.doc.path).name
        # Collect all variables: stage globals + sprite locals
        all_proj_vars: dict = {}
        for target in self.doc.project.get('targets', []):
            all_proj_vars.update(target.get('variables', {}))
        var_count = len(all_proj_vars)
        list_count = len(self.doc.sprite.get('lists', {}))
        block_count = len(self.blocks)
        proc_count = len(self.proc_defs)
        lists = self.doc.sprite.get('lists', {})

        import outputllsp3 as _pkg
        lib_version = getattr(_pkg, '__version__', '?')

        out: list[str] = []

        # Module docstring
        stats = (
            f'Blocks: {block_count}'
            + (f'  |  Variables: {var_count}' if var_count else '')
            + (f'  |  Lists: {list_count}' if list_count else '')
            + (f'  |  Procedures: {proc_count}' if proc_count else '')
        )
        out += [
            '"""',
            f'Source:    {doc_path}',
            f'Exported by outputllsp3 {lib_version}  (python-first style)',
            f'Note:      readable approximation — not an exact round-trip',
            '',
            stats,
            '"""',
            '',
        ]

        # Imports — only add what's actually needed
        if self._needs_math:
            out.append('import math')
        if self._needs_random:
            out.append('import random')
        enum_imports = [name for flag, name in [
            (self._needs_direction,  'Direction'),
            (self._needs_stop_mode,  'StopMode'),
            (self._needs_axis,       'Axis'),
            (self._needs_color,      'Color'),
            (self._needs_image,      'LightImage'),
            (self._needs_comparator, 'Comparator'),
        ] if flag]
        base_import = 'from outputllsp3 import robot, run, port'
        if enum_imports:
            base_import += ', ' + ', '.join(enum_imports)
        out += [base_import, '']

        # Placeholder helpers — only when there are actually unknown opcodes
        if self._unknown_exprs or self._unknown_stmts:
            out += [
                'def __expr__(kind, *args):',
                '    """Placeholder for expression opcodes without a python-first mapping."""',
                '    return 0',
                '',
                'def __stmt__(kind, *args):',
                '    """Placeholder for statement opcodes without a python-first mapping."""',
                '    pass',
                '',
            ]

        # Variables section — stage globals first, then sprite locals
        # Skip compiler-generated internal variables (loop control, return helpers).
        _INTERNAL_PATTERNS = ('__break_', '__continue_', '__range_value_', '__return_', '__retval_')

        def _is_internal_var(raw_name: str) -> bool:
            """Return True for compiler-generated internal variables to skip in export."""
            # Matches both plain (__break_N) and namespaced (fn__break_N) forms.
            return any(p in raw_name for p in _INTERNAL_PATTERNS)

        user_proj_vars = {vid: pair for vid, pair in all_proj_vars.items()
                          if not _is_internal_var(pair[0])}
        if user_proj_vars:
            out.append(_section('Variables'))
            stage_vars = {vid: pair for vid, pair in user_proj_vars.items() if vid in self._stage_var_ids}
            sprite_vars = {vid: pair for vid, pair in user_proj_vars.items() if vid not in self._stage_var_ids}
            if stage_vars and sprite_vars:
                out.append('# Global variables (stage):')
            for vid, pair in stage_vars.items():
                name = self.var_names.get(vid) or _sanitize(pair[0], 'var')
                val = pair[1]
                lit = self._var_lit(val)
                out.append(f'{name} = {lit}')
            if stage_vars and sprite_vars:
                out.append('# Sprite variables:')
            for vid, pair in sprite_vars.items():
                name = self.var_names.get(vid) or _sanitize(pair[0], 'var')
                val = pair[1]
                lit = self._var_lit(val)
                out.append(f'{name} = {lit}')
            out.append('')

        # Monitors section — variables visible in the SPIKE App monitor panel
        all_monitors = self.doc.project.get('monitors', [])
        visible_monitors = [m for m in all_monitors if m.get('visible') and m.get('opcode') == 'data_variable']
        if visible_monitors:
            out.append(_section('Monitors'))
            for m in visible_monitors:
                # Resolve to clean Python name via var_names if possible
                var_id = m.get('id', '')
                raw_name = m.get('params', {}).get('VARIABLE', '')
                py_name = self.var_names.get(var_id) or self._clean_name(raw_name, 'var')
                mode = m.get('mode', 'default')
                if mode == 'slider':
                    smin = m.get('sliderMin', 0)
                    smax = m.get('sliderMax', 100)
                    disc = m.get('isDiscrete', True)
                    disc_arg = '' if disc else ', discrete=False'
                    out.append(f'robot.show_monitor({py_name!r}, slider_min={smin}, slider_max={smax}{disc_arg})')
                else:
                    out.append(f'robot.show_monitor({py_name!r})')
            out.append('')

        # Lists section — use clean (namespace-stripped) names
        if lists:
            out.append(_section('Lists'))
            for lid, pair in lists.items():
                py_name = self.list_names[lid]
                orig_name = pair[0]
                comment = f'  # {orig_name}' if py_name != orig_name else ''
                out.append(f'{py_name} = []{comment}')
            out.append('')

        # Floating comments (not attached to any specific block)
        if self._floating_comment_texts:
            out.append(_section('Notes'))
            for text in self._floating_comment_texts:
                if '\n' in text:
                    safe = text.replace('\\', '\\\\').replace('"""', '\\"\\"\\"')
                    out.append(f'robot.note("""{safe}""", floating=True)')
                else:
                    out.append(f'robot.note({text!r}, floating=True)')
            out.append('')

        # Procedures section
        if proc_chunks:
            out.append(_section('Procedures'))
            out.append('')
            for chunk in proc_chunks:
                out.extend(chunk)

        # Entry points and event handlers
        has_main = any(c[0] == '@run.main' for c in event_chunks)
        has_events = any(c[0] != '@run.main' for c in event_chunks)

        if has_main:
            out.append(_section('Entry point(s)'))
            out.append('')
            for chunk in event_chunks:
                if chunk[0] == '@run.main':
                    out.extend(chunk)

        if has_events:
            out.append(_section('Event handlers'))
            out.append('')
            for chunk in event_chunks:
                if chunk[0] != '@run.main':
                    out.extend(chunk)

        if not event_chunks:
            out.append(_section('Entry point(s)'))
            out.append('')
            out.extend(['@run.main', 'def main():', '    pass', ''])

        # Unknown opcodes summary (diagnostic footer)
        if self._unknown_stmts or self._unknown_exprs:
            out.append(_section('Unmapped opcodes'))
            out.append('# These opcodes have no python-first mapping; they appear as "pass  # TODO:" above.')
            if self._unknown_stmts:
                out.append('#   statements:  ' + ', '.join(sorted(self._unknown_stmts)))
            if self._unknown_exprs:
                out.append('#   expressions: ' + ', '.join(sorted(self._unknown_exprs)))
            out.append('')

        logger.info(t("pf_exp.done", proc_count=len(proc_chunks), event_count=len(event_chunks)))
        return out


def _pythonfirst_lines(doc) -> list[str]:
    return _PFExport(doc).render()


def pythonfirst_lines(doc) -> list[str]:
    """Return source lines for a python-first style export."""
    return _PFExport(doc).render()
