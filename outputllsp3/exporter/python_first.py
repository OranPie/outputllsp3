"""Python-first export strategy.

Higher-level decompilation that lifts common patterns to python-first idioms
(``@robot.proc`` / ``@run.main``, ``robot.forward_cm``, …).  The output is
approximate — round-tripping through python-first may not preserve every
low-level block detail, but produces readable programs.
"""
from __future__ import annotations

import json
from pathlib import Path

from .base import _sanitize, _extract_literal, _value_ref

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
        if op == 'operator_mod':
            a = self.render_expr(block.get('inputs', {}).get('NUM1'))
            b = self.render_expr(block.get('inputs', {}).get('NUM2'))
            return f'({a} % {b})'
        if op == 'operator_random':
            from_ = self.render_expr(block.get('inputs', {}).get('FROM'))
            to = self.render_expr(block.get('inputs', {}).get('TO'))
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
            return f'(str({a}) + str({b}))'
        if op == 'operator_length':
            s = self.render_expr(block.get('inputs', {}).get('STRING'))
            return f'len({s})'
        if op == 'operator_letter_of':
            letter = self.render_expr(block.get('inputs', {}).get('LETTER'))
            s = self.render_expr(block.get('inputs', {}).get('STRING'))
            return f'{s}[({letter})-1]'
        if op == 'operator_contains':
            s1 = self.render_expr(block.get('inputs', {}).get('STRING1'))
            s2 = self.render_expr(block.get('inputs', {}).get('STRING2'))
            return f'({s2} in {s1})'
        if op == 'operator_mathop':
            fname = block.get('fields', {}).get('OPERATOR', ['abs'])[0]
            x = self.render_expr(block.get('inputs', {}).get('NUM'))
            return f'{fname}({x})'
        if op == 'flipperoperator_isInBetween':
            value = self.render_expr(block.get('inputs', {}).get('VALUE'))
            lo = self.render_expr(block.get('inputs', {}).get('LOW'))
            hi = self.render_expr(block.get('inputs', {}).get('HIGH'))
            return f'({lo} <= {value} <= {hi})'
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
        if op == 'data_itemnumoflist':
            item = self.render_expr(block.get('inputs', {}).get('ITEM'))
            lst = block.get('fields', {}).get('LIST', ['lst'])[0]
            return f'({_sanitize(lst, "lst")}.index({item}) + 1)'
        if op == 'flippersensors_orientationAxis':
            axis = block.get('fields', {}).get('AXIS', ['yaw'])[0]
            return f'robot.angle({axis!r})'
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
            button = self._menu_value(block.get('inputs', {}).get('BUTTON')) or 'center'
            event = self._menu_value(block.get('inputs', {}).get('EVENT')) or 'pressed'
            return f'robot.button({button!r}) == {event!r}'
        if op == 'flippersensors_distance':
            port_name = self._menu_value(block.get('inputs', {}).get('PORT')) or 'A'
            unit = self._menu_value(block.get('inputs', {}).get('UNIT')) or 'cm'
            return f'robot.distance(port.{port_name}, {unit!r})'
        if op == 'flippersensors_reflectivity':
            port_name = self._menu_value(block.get('inputs', {}).get('PORT')) or 'A'
            return f'robot.reflected_light(port.{port_name})'
        if op == 'flippersensors_color':
            port_name = self._menu_value(block.get('inputs', {}).get('PORT')) or 'A'
            return f'robot.color(port.{port_name})'
        if op == 'flippersensors_isColor':
            port_name = self._menu_value(block.get('inputs', {}).get('PORT')) or 'A'
            color = self._menu_value(block.get('inputs', {}).get('VALUE')) or '0'
            return f'robot.is_color(port.{port_name}, {color!r})'
        if op == 'flippersensors_isDistance':
            port_name = self._menu_value(block.get('inputs', {}).get('PORT')) or 'A'
            comp = self._menu_value(block.get('inputs', {}).get('COMPARATOR')) or 'closer'
            value = self.render_expr(block.get('inputs', {}).get('VALUE'))
            unit = self._menu_value(block.get('inputs', {}).get('UNIT')) or 'cm'
            return f'robot.is_distance(port.{port_name}, {comp!r}, {value}, {unit!r})'
        if op == 'flippersensors_isPressed':
            port_name = self._menu_value(block.get('inputs', {}).get('PORT')) or 'A'
            option = self._menu_value(block.get('inputs', {}).get('OPTION')) or 'pressed'
            return f'robot.is_pressed(port.{port_name}, {option!r})'
        if op == 'flippersensors_force':
            port_name = self._menu_value(block.get('inputs', {}).get('PORT')) or 'A'
            unit = self._menu_value(block.get('inputs', {}).get('UNIT')) or 'percent'
            return f'robot.force(port.{port_name}, {unit!r})'
        if op == 'flippermotor_speed':
            port_name = self._menu_value(block.get('inputs', {}).get('PORT')) or 'A'
            return f'robot.motor_speed(port.{port_name})'
        if op == 'flippermotor_absolutePosition':
            port_name = self._menu_value(block.get('inputs', {}).get('PORT')) or 'A'
            return f'robot.motor_position(port.{port_name})'
        if op == 'flippermoremotor_position':
            port_name = self._menu_value(block.get('inputs', {}).get('PORT')) or 'A'
            return f'robot.motor_relative_position(port.{port_name})'
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
        if op == 'control_forever':
            body = self.render_stmt_chain(_value_ref(ins.get('SUBSTACK')), indent + '    ') or [indent + '    pass']
            return [f'{indent}while True:', *body]
        if op == 'control_repeat_until':
            cond = self.render_expr(ins.get('CONDITION'))
            body = self.render_stmt_chain(_value_ref(ins.get('SUBSTACK')), indent + '    ') or [indent + '    pass']
            return [f'{indent}while not ({cond}):', *body]
        if op == 'control_wait_until':
            cond = self.render_expr(ins.get('CONDITION'))
            return [f'{indent}while not ({cond}):', f'{indent}    run.sleep(0.01)']
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
            port_name = self._menu_value(ins.get('PORT')) or 'A'
            value = self.render_expr(ins.get('VALUE'))
            return [f'{indent}robot.set_motor_position(port.{port_name}, {value})']
        if op == 'flippersensors_resetYaw':
            return [f'{indent}robot.reset_yaw()']
        if op == 'flippersensors_resetTimer':
            return [f'{indent}run.reset_timer()']
        if op == 'flippermotor_motorStartDirection':
            port_name = self._menu_value(ins.get('PORT')) or 'A'
            direction = self._menu_value(ins.get('DIRECTION')) or 'clockwise'
            return [f'{indent}robot.run_motor(port.{port_name}, {direction!r})']
        if op == 'flippermotor_motorStop':
            port_name = self._menu_value(ins.get('PORT')) or 'A'
            return [f'{indent}robot.stop_motor(port.{port_name})']
        if op == 'flippermotor_motorTurnForDirection':
            port_name = self._menu_value(ins.get('PORT')) or 'A'
            direction = self._menu_value(ins.get('DIRECTION')) or 'clockwise'
            value = self.render_expr(ins.get('VALUE'))
            unit = self._menu_value(ins.get('UNIT')) or 'degrees'
            return [f'{indent}robot.run_motor_for(port.{port_name}, {direction!r}, {value}, {unit!r})']
        if op == 'flippermotor_motorGoDirectionToPosition':
            port_name = self._menu_value(ins.get('PORT')) or 'A'
            direction = self._menu_value(ins.get('DIRECTION')) or 'shortest'
            position = self.render_expr(ins.get('POSITION'))
            return [f'{indent}robot.motor_go_to_position(port.{port_name}, {direction!r}, {position})']
        if op == 'flippermotor_motorSetSpeed':
            port_name = self._menu_value(ins.get('PORT')) or 'A'
            speed = self.render_expr(ins.get('SPEED'))
            return [f'{indent}robot.set_motor_speed(port.{port_name}, {speed})']
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
            port_name = self._menu_value(ins.get('PORT')) or 'A'
            matrix = self.render_expr(ins.get('MATRIX'))
            return [f'{indent}robot.show_image(port.{port_name}, {matrix})']
        if op == 'flipperdisplay_ledMatrixFor':
            port_name = self._menu_value(ins.get('PORT')) or 'A'
            matrix = self.render_expr(ins.get('MATRIX'))
            value = self.render_expr(ins.get('VALUE'))
            return [f'{indent}robot.show_image_for(port.{port_name}, {matrix}, {value})']
        if op == 'flipperdisplay_ledMatrixText':
            port_name = self._menu_value(ins.get('PORT')) or 'A'
            text = self.render_expr(ins.get('TEXT'))
            return [f'{indent}robot.show_text(port.{port_name}, {text})']
        if op == 'flipperdisplay_ledMatrixOff':
            port_name = self._menu_value(ins.get('PORT')) or 'A'
            return [f'{indent}robot.turn_off_pixels(port.{port_name})']
        if op == 'flipperdisplay_ledMatrixOn':
            port_name = self._menu_value(ins.get('PORT')) or 'A'
            x = self.render_expr(ins.get('X'))
            y = self.render_expr(ins.get('Y'))
            brightness = self.render_expr(ins.get('BRIGHTNESS'))
            return [f'{indent}robot.set_pixel(port.{port_name}, {x}, {y}, {brightness})']
        if op == 'flipperdisplay_ledMatrixBrightness':
            port_name = self._menu_value(ins.get('PORT')) or 'A'
            brightness = self.render_expr(ins.get('BRIGHTNESS'))
            return [f'{indent}robot.set_pixel_brightness(port.{port_name}, {brightness})']
        if op == 'flipperdisplay_centerButtonLight':
            color = self._menu_value(ins.get('COLOR')) or 'white'
            return [f'{indent}robot.set_center_light({color!r})']
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
        lines.append('import random')
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
        starts = [bid for bid, b in self.blocks.items()
                  if b.get('opcode') == 'flipperevents_whenProgramStarts' and b.get('topLevel')]
        if len(starts) <= 1:
            # Single main function (common case)
            lines.append('@run.main')
            lines.append('def main():')
            if starts:
                body = self.render_stmt_chain(self.blocks[starts[0]].get('next'), '    ')
                if not body:
                    body = ['    pass']
                lines.extend(body)
            else:
                lines.append('    pass')
            lines.append('')
        else:
            # Multiple whenProgramStarts stacks → one named helper per stack,
            # plus a main() that calls them all in parallel (each wrapped in @run.main).
            for i, s in enumerate(starts):
                fn_name = 'main' if i == 0 else f'main_{i}'
                body = self.render_stmt_chain(self.blocks[s].get('next'), '    ')
                if not body:
                    body = ['    pass']
                lines.append('@run.main')
                lines.append(f'def {fn_name}():')
                lines.extend(body)
                lines.append('')
        return lines


def _pythonfirst_lines(doc) -> list[str]:
    return _PFExport(doc).render()


def pythonfirst_lines(doc) -> list[str]:
    """Return source lines for a python-first style export."""
    return _PFExport(doc).render()
