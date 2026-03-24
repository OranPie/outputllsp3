"""Builder export strategy.

Produces the same semantics as the raw export but with module structure,
human-readable opcode annotations, and commentary that makes the file
human-editable as a build script.
"""
from __future__ import annotations

from pathlib import Path

from .base import (_pyrepr, _summary, _block_hint, _val_repr, _BLOCK_KEY_ORDER,
                   _build_stack_groups, _linear_chain_labels)

# ── Opcode → human-readable label ────────────────────────────────────────────
_OPCODE_LABELS: dict[str, str] = {
    # ── Events ────────────────────────────────────────────────────────────────
    'flipperevents_whenProgramStarts':                  'event: when program starts',
    'flipperevents_whenButton':                         'event: when hub button',
    'flipperevents_whenGesture':                        'event: when gesture',
    'flipperevents_whenOrientation':                    'event: when orientation',
    'flipperevents_whenTilted':                         'event: when tilted',
    'flipperevents_whenTimer':                          'event: when timer',
    'flipperevents_whenColor':                          'event: when color detected',
    'flipperevents_whenPressed':                        'event: when force sensor pressed',
    'flipperevents_whenCondition':                      'event: when condition',
    'flipperevents_whenNearOrFar':                      'event: when near or far',
    'flipperevents_whenDistance':                       'event: when distance',
    'flipperevents_whenBroadcast':                      'event: when broadcast (SPIKE)',
    'event_whenbroadcastreceived':                      'event: when broadcast received',
    'flipperevents_resetTimer':                         'sensor: reset timer',
    'horizontalevents_whenProgramStarts':               'event: when program starts (icon)',
    'horizontalevents_whenBroadcast':                   'event: when broadcast (icon)',
    'horizontalevents_whenCloserThan':                  'event: when closer than (icon)',
    'horizontalevents_whenColor':                       'event: when color (icon)',
    'horizontalevents_whenPressed':                     'event: when pressed (icon)',
    'horizontalevents_whenTilted':                      'event: when tilted (icon)',
    'horizontalevents_whenLouderThan':                  'event: when louder than (icon)',
    # ── Control ───────────────────────────────────────────────────────────────
    'control_forever':                                  'loop: forever',
    'control_repeat':                                   'loop: repeat N times',
    'control_repeat_until':                             'loop: repeat until condition',
    'control_for_each':                                 'loop: for each item in list',
    'control_if':                                       'if',
    'control_if_else':                                  'if / else',
    'control_wait':                                     'wait (seconds)',
    'control_wait_until':                               'wait until condition',
    'control_stop':                                     'stop script',
    'flippercontrol_stop':                              'stop script (SPIKE)',
    'flippercontrol_stopOtherStacks':                   'stop: other stacks',
    'flippermore_stopOtherStacks':                      'stop: other stacks (alias)',
    'horizontalcontrol_stopOtherStacks':                'stop: other stacks (icon)',
    # ── Data / variables ──────────────────────────────────────────────────────
    'data_setvariableto':                               'variable: set',
    'data_changevariableby':                            'variable: change by',
    'data_variable':                                    'variable: read',
    'data_addtolist':                                   'list: append item',
    'data_deletealloflist':                             'list: clear',
    'data_insertatlist':                                'list: insert at index',
    'data_replaceitemoflist':                           'list: replace item at index',
    'data_deleteoflist':                                'list: delete item at index',
    'data_listcontents':                                'list: contents',
    'data_itemoflist':                                  'list: item at index',
    'data_lengthoflist':                                'list: length',
    'data_listcontainsitem':                            'list: contains item?',
    'data_itemnumoflist':                               'list: find item index',
    # ── Procedures ────────────────────────────────────────────────────────────
    'procedures_definition':                            'procedure: define',
    'procedures_prototype':                             'procedure: prototype',
    'procedures_call':                                  'procedure: call',
    'argument_reporter_string_number':                  'procedure: arg (number/string)',
    'argument_reporter_boolean':                        'procedure: arg (boolean)',
    # ── Drive / move ──────────────────────────────────────────────────────────
    'flippermove_move':                                 'drive: move for distance',
    'flippermove_steer':                                'drive: steer for distance',
    'flippermove_startMove':                            'drive: start moving',
    'flippermove_startSteer':                           'drive: start steering',
    'flippermove_stopMove':                             'drive: stop',
    'flippermove_setMovementPair':                      'drive: set motor pair',
    'flippermove_movementSpeed':                        'drive: set speed',
    'flippermove_setDistance':                          'drive: set movement scale',
    'flippermove_movementSetAcceleration':              'drive: set acceleration',
    'flippermove_movementSetStopMethod':                'drive: set stop method',
    'flippermove_startDualSpeed':                       'drive: dual speed',
    'flippermoremove_startDualSpeed':                   'drive: dual speed (advanced)',
    'flippermoremove_startDualPower':                   'drive: dual power (advanced)',
    'flippermoremove_startSteerAtSpeed':                'drive: steer (open-ended)',
    'flippermoremove_steerDistanceAtSpeed':             'drive: steer for distance',
    'flippermoremove_movementSetAcceleration':          'drive: set acceleration (advanced)',
    'flippermoremove_movementSetStopMethod':            'drive: set stop method (advanced)',
    'horizontalmove_moveForward':                       'drive: forward (icon)',
    'horizontalmove_moveBackward':                      'drive: backward (icon)',
    'horizontalmove_moveTurnClockwiseRotations':        'drive: turn CW (icon)',
    'horizontalmove_moveTurnCounterClockwiseRotations': 'drive: turn CCW (icon)',
    'horizontalmove_moveSetSpeed':                      'drive: set speed (icon)',
    'horizontalmove_moveStop':                          'drive: stop (icon)',
    # ── Motor ─────────────────────────────────────────────────────────────────
    'flippermotor_motorStartDirection':                 'motor: run (direction)',
    'flippermotor_motorStop':                           'motor: stop',
    'flippermotor_motorTurnForDirection':               'motor: run for (direction)',
    'flippermotor_motorSetSpeed':                       'motor: set speed',
    'flippermotor_motorGoDirectionToPosition':          'motor: go to position',
    'flippermotor_motorSetAcceleration':                'motor: set acceleration',
    'flippermotor_motorSetStopMethod':                  'motor: set stop method',
    'flippermotor_speed':                               'motor: read speed',
    'flippermotor_absolutePosition':                    'motor: read abs position',
    'flippermoremotor_motorStartSpeed':                 'motor: run at speed',
    'flippermoremotor_motorTurnForSpeed':               'motor: run for (speed)',
    'flippermoremotor_motorSetStopMethod':              'motor: set stop method',
    'flippermoremotor_motorSetDegreeCounted':           'motor: set relative position',
    'flippermoremotor_motorStartPower':                 'motor: run at power',
    'flippermoremotor_motorGoToRelativePosition':       'motor: go to relative position',
    'flippermoremotor_motorSetAcceleration':            'motor: set acceleration',
    'flippermoremotor_position':                        'motor: read relative position',
    'flippermoremotor_power':                           'motor: read power',
    'horizontalmotor_motorTurnClockwiseRotations':      'motor: CW rotations (icon)',
    'horizontalmotor_motorTurnCounterClockwiseRotations': 'motor: CCW rotations (icon)',
    'horizontalmotor_motorSetSpeed':                    'motor: set speed (icon)',
    'horizontalmotor_motorStop':                        'motor: stop (icon)',
    # ── Sensors ───────────────────────────────────────────────────────────────
    'flippersensors_resetYaw':                          'sensor: reset yaw',
    'flippersensors_resetTimer':                        'sensor: reset timer',
    'flippersensors_distance':                          'sensor: distance',
    'flippersensors_reflectivity':                      'sensor: reflected light %',
    'flippersensors_color':                             'sensor: color',
    'flippersensors_isColor':                           'sensor: is color?',
    'flippersensors_isDistance':                        'sensor: is distance?',
    'flippersensors_isPressed':                         'sensor: is force pressed?',
    'flippersensors_force':                             'sensor: force value',
    'flippersensors_ismotion':                          'sensor: is moving?',
    'flippersensors_isTilted':                          'sensor: is tilted?',
    'flippersensors_isorientation':                     'sensor: is orientation?',
    'flippersensors_orientationAxis':                   'sensor: orientation angle',
    'flippersensors_timer':                             'sensor: timer value',
    'flippersensors_loudness':                          'sensor: loudness',
    'flippersensors_rawColor':                          'sensor: raw color',
    'flippersensors_colorValue':                        'sensor: color value',
    'flippersensors_buttonIsPressed':                   'sensor: hub button pressed?',
    'flippersensors_hubButtonIsPressed':                'sensor: hub button pressed?',
    'flippersensors_isReflectivity':                    'sensor: is reflectivity?',
    'flippermoresensors_orientation':                   'sensor: IMU orientation',
    'flippermoresensors_motion':                        'sensor: IMU motion',
    'flippermoresensors_acceleration':                  'sensor: IMU acceleration',
    'flippermoresensors_angularVelocity':               'sensor: IMU angular velocity',
    'flippermoresensors_setOrientation':                'sensor: set IMU orientation',
    'flippermore_port':                                 'sensor: port raw value',
    # ── Sound ─────────────────────────────────────────────────────────────────
    'flippersound_beep':                                'sound: beep (note)',
    'flippersound_beepForTime':                         'sound: beep for time',
    'flippersound_stopSound':                           'sound: stop',
    'flippersound_playSound':                           'sound: play file',
    'flippersound_playSoundUntilDone':                  'sound: play file until done',
    'sound_setvolumeto':                                'sound: set volume',
    'sound_changevolumeby':                             'sound: change volume by',
    'sound_seteffectto':                                'sound: set effect',
    'sound_changeeffectby':                             'sound: change effect by',
    'sound_volume':                                     'sound: read volume',
    # ── Music ─────────────────────────────────────────────────────────────────
    'flippermusic_playDrumForBeats':                    'music: play drum for beats',
    'flippermusic_playNoteForBeats':                    'music: play note for beats',
    'flippermusic_setTempo':                            'music: set tempo',
    'flippermusic_setInstrument':                       'music: set instrument',
    'flippermusic_getTempo':                            'music: read tempo',
    # ── Display (external tile) ───────────────────────────────────────────────
    'flipperdisplay_ledMatrix':                         'display: show image',
    'flipperdisplay_ledMatrixFor':                      'display: show image for time',
    'flipperdisplay_ledMatrixText':                     'display: show text',
    'flipperdisplay_ledMatrixOff':                      'display: clear pixels',
    'flipperdisplay_ledMatrixOn':                       'display: set pixel',
    'flipperdisplay_ledMatrixBrightness':               'display: set brightness',
    'flipperdisplay_centerButtonLight':                 'display: center button light',
    # ── Hub light / display ────────────────────────────────────────────────────
    'flipperlight_lightDisplayText':                    'hub: show text',
    'flipperlight_lightDisplayOff':                     'hub: display off',
    'flipperlight_lightDisplayImageOnForTime':          'hub: show image for time',
    'flipperlight_lightDisplayImageOn':                 'hub: show image (permanent)',
    'flipperlight_lightDisplayRotate':                  'hub: rotate display',
    'flipperlight_lightDisplaySetBrightness':           'hub: set display brightness',
    'flipperlight_lightDisplaySetOrientation':          'hub: set display orientation',
    'flipperlight_lightDisplaySetPixel':                'hub: set pixel',
    'flipperlight_centerButtonLight':                   'hub: center button color',
    'flipperlight_ultrasonicLightUp':                   'hub: ultrasonic light',
    'flipperlight_buttonIsPressed':                     'hub: button pressed?',
    'flipperlight_lightColorMatrixImageOn':             'color-matrix: show image',
    'flipperlight_lightColorMatrixImageOnForTime':      'color-matrix: show for time',
    'flipperlight_lightColorMatrixOff':                 'color-matrix: off',
    'flipperlight_lightColorMatrixSetBrightness':       'color-matrix: set brightness',
    'flipperlight_lightColorMatrixSetPixel':            'color-matrix: set pixel',
    'flipperlight_lightColorMatrixRotate':              'color-matrix: rotate',
    'flipperlight_lightColorMatrixSetOrientation':      'color-matrix: set orientation',
    'horizontaldisplay_ledMatrix':                      'display: show image (icon)',
    'horizontaldisplay_ledImage':                       'display: show icon',
    # ── Operators ─────────────────────────────────────────────────────────────
    'operator_add':                                     'op: +',
    'operator_subtract':                                'op: -',
    'operator_multiply':                                'op: *',
    'operator_divide':                                  'op: /',
    'operator_mod':                                     'op: mod',
    'operator_random':                                  'op: random',
    'operator_equals':                                  'op: ==',
    'operator_lt':                                      'op: <',
    'operator_gt':                                      'op: >',
    'operator_and':                                     'op: and',
    'operator_or':                                      'op: or',
    'operator_not':                                     'op: not',
    'operator_join':                                    'op: join strings',
    'operator_letter_of':                               'op: letter of string',
    'operator_length':                                  'op: string length',
    'operator_contains':                                'op: string contains?',
    'operator_round':                                   'op: round',
    'operator_mathop':                                  'op: math function',
    'flipperoperator_isInBetween':                      'op: is in between?',
}


def _opcode_label(opcode: str) -> str:
    return _OPCODE_LABELS.get(opcode, opcode)


def builder_lines(doc) -> list[str]:
    """Return source lines for a builder-style export."""
    sprite = doc.sprite
    blocks = sprite.get("blocks", {})
    variables = sprite.get("variables", {})
    lists = sprite.get("lists", {})
    comments = sprite.get("comments", {})
    summary = _summary(doc)

    lines: list[str] = []

    # ── File header ────────────────────────────────────────────────────────────
    lines.append(f'# Source:  {Path(doc.path).name}')
    lines.append('# Style:   builder  (round-trip reconstruction with human-readable labels)')
    lines.append('# Tip:     for a fully readable decompilation use --style python-first')
    lines.append('')
    lines.append('from collections import OrderedDict')
    lines.append('')

    # ── Project summary ────────────────────────────────────────────────────────
    stats: list[str] = [f'blocks: {summary["blocks"]}']
    if summary['variables']:
        stats.append(f'variables: {summary["variables"]}')
    if summary['lists']:
        stats.append(f'lists: {summary["lists"]}')
    if summary['procedures']:
        stats.append(f'procedures: {len(summary["procedures"])}')
    lines.append(f'# {" | ".join(stats)}')
    for proc in summary['procedures']:
        lines.append(f'#   procedure: {proc["proccode"]}')
    unique_ops = summary['opcode_count']
    lines.append(f'# {unique_ops} unique opcodes')

    opcode_counts = summary['opcode_counts']
    hints: list[str] = []
    if 'flipperevents_whenProgramStarts' in opcode_counts or \
            'horizontalevents_whenProgramStarts' in opcode_counts:
        hints.append('has program-start stack(s)')
    if any(op.startswith('procedures_') for op in opcode_counts):
        hints.append('uses custom procedures')
    if any(op.startswith('data_') for op in opcode_counts):
        hints.append('uses variables/lists')
    if hints:
        lines.append('# ✓ ' + '  ✓ '.join(hints))
    lines.append('')

    lines.append('def _set_block(project, block_id, payload):')
    lines.append('    project.sprite["blocks"][block_id] = payload')
    lines.append('')
    lines.append('def build(project, api, ns, enums):')
    lines.append('    project.clear_code()')
    lines.append('')

    # ── Variables ──────────────────────────────────────────────────────────────
    if variables:
        lines.append('    # ── Variables ' + '─' * 62)
        for vid, pair in variables.items():
            name, val = pair[0], pair[1]
            if isinstance(val, str):
                lit = f"'{val}'" if "'" not in val else repr(val)
            else:
                lit = repr(val)
            lines.append(f'    project.variables[{vid!r}] = [{name!r}, {lit}]'
                         f'  # {name} = {lit}')
        lines.append('')

    # ── Lists ──────────────────────────────────────────────────────────────────
    if lists:
        lines.append('    # ── Lists ' + '─' * 65)
        for lid, pair in lists.items():
            name = pair[0]
            lines.append(f'    project.lists[{lid!r}] = [{name!r}, []]  # {name}')
        lines.append('')

    lines.append('    project.sprite["blocks"] = OrderedDict()')
    lines.append('')

    # ── Build stack groups: one section per top-level root ────────────────────
    stack_groups = _build_stack_groups(blocks)
    total_stacks = len(stack_groups)

    def _emit_block(bid: str, block: dict) -> None:
        opcode = block.get('opcode', '?')
        label = _opcode_label(opcode)
        comment = _block_hint(opcode, block, label)
        lines.append(f'    _set_block(project, {bid!r}, {{  # {comment}')
        ordered = [k for k in _BLOCK_KEY_ORDER if k in block] + \
                  [k for k in block if k not in _BLOCK_KEY_ORDER]
        for key in ordered:
            val = block[key]
            if key == 'shadow' and val is False:
                continue
            if key == 'topLevel' and val is False:
                continue
            if key == 'comment' and val is None:
                continue
            if key == 'mutation' and not val:
                continue
            lines.append(f"        '{key}': {_val_repr(val)},")
        lines.append('    })')

    for stack_idx, (root_bid, group_bids) in enumerate(stack_groups, 1):
        if root_bid is None:
            # Orphaned blocks with no top-level parent
            lines.append(f'    # ── Orphaned blocks ' + '─' * 54)
            for bid in group_bids:
                _emit_block(bid, blocks[bid])
            lines.append('')
            continue

        root_block = blocks[root_bid]
        root_op = root_block.get('opcode', '?')
        root_label = _opcode_label(root_op)

        # ── Section header ────────────────────────────────────────────────────
        is_proc = root_op == 'procedures_definition'
        if is_proc:
            # Find the procedure prototype to get the name
            proto_id = (root_block.get('inputs', {}).get('custom_block', [None, None]) or [None, None])[1]
            proccode = ''
            if proto_id and proto_id in blocks:
                proccode = blocks[proto_id].get('mutation', {}).get('proccode', '')
            section = f'procedure: {proccode}' if proccode else 'procedure definition'
        else:
            section = f'stack {stack_idx}/{total_stacks}: {root_label}'

        bar_len = max(2, 72 - len(section))
        lines.append(f'    # ══ {section} {"═" * bar_len}')

        # ── Chain summary: root → … along next-links ─────────────────────────
        chain_labels, chain_depth = _linear_chain_labels(root_bid, blocks, _opcode_label, max_steps=5)
        chain_str = ' → '.join(chain_labels)
        if chain_depth > len(chain_labels):
            chain_str += f' → … ({chain_depth} blocks total)'
        else:
            noun = 'block' if chain_depth == 1 else 'blocks'
            chain_str += f'  ({chain_depth} {noun})'
        lines.append(f'    #   {chain_str}')
        lines.append('')

        # ── Emit every block in this stack ────────────────────────────────────
        for bid in group_bids:
            _emit_block(bid, blocks[bid])
        lines.append('')

    # ── Comments ───────────────────────────────────────────────────────────────
    lines.append('    project.sprite["comments"] = OrderedDict()')
    if comments:
        lines.append('    # ── Comments ' + '─' * 62)
        for cid, comment in comments.items():
            lines.append(f'    project.sprite["comments"][{cid!r}] = {{')
            for k, v in comment.items():
                lines.append(f"        '{k}': {_val_repr(v)},")
            lines.append('    }')
        lines.append('')

    return [line for line in lines if line != ''] + ['']
