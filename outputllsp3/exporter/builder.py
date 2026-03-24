"""Builder export strategy.

Produces the same semantics as the raw export but with module structure,
human-readable opcode annotations, and commentary that makes the file
human-editable as a build script.
"""
from __future__ import annotations

import json
from pathlib import Path

from .base import _pyrepr, _summary

# ── Opcode → human-readable label ────────────────────────────────────────────
_OPCODE_LABELS: dict[str, str] = {
    # Events
    'flipperevents_whenProgramStarts':      'when program starts',
    'flipperevents_whenButtonPressed':      'when button pressed',
    # Control
    'control_forever':                      'loop: forever',
    'control_repeat':                       'loop: repeat N times',
    'control_repeat_until':                 'loop: repeat until condition',
    'control_for_each':                     'loop: for each item in list',
    'control_if':                           'if',
    'control_if_else':                      'if / else',
    'control_wait':                         'wait (seconds)',
    'control_wait_until':                   'wait until condition',
    'control_stop':                         'stop script',
    'flippercontrol_stop':                  'stop script',
    # Data / variables
    'data_setvariableto':                   'variable: set',
    'data_changevariableby':                'variable: change by',
    'data_addtolist':                       'list: append item',
    'data_deletealloflist':                 'list: clear',
    'data_insertatlist':                    'list: insert at index',
    'data_replaceitemoflist':               'list: replace item at index',
    'data_deleteoflist':                    'list: delete item at index',
    # Procedures
    'procedures_definition':                'define procedure',
    'procedures_prototype':                 'procedure prototype (internal)',
    'procedures_call':                      'call procedure',
    # Drive / move
    'flippermove_startMoveFor':             'drive: move for distance/time',
    'flippermove_startMove':                'drive: move (open-ended)',
    'flippermove_stopMove':                 'drive: stop',
    'flippermove_setMovementPair':          'drive: set motor pair',
    'flippermove_setSpeed':                 'drive: set speed',
    'flippermove_changeSpeedBy':            'drive: change speed by',
    'flippermoremove_startDualSpeed':       'drive: set individual wheel speeds',
    'flippermoremove_startDualPower':       'drive: set individual wheel powers',
    'flippermoremove_startSteerAtSpeed':    'drive: steer (open-ended)',
    'flippermoremove_steerDistanceAtSpeed': 'drive: steer for distance',
    # Motor
    'flippermotor_motorStartDirection':     'motor: run (direction)',
    'flippermotor_motorStop':               'motor: stop',
    'flippermotor_motorTurnForDirection':   'motor: run for (direction)',
    'flippermotor_motorSetSpeed':           'motor: set speed',
    'flippermotor_motorGoDirectionToPosition': 'motor: go to position',
    'flippermoremotor_motorStartSpeed':     'motor: run at speed',
    'flippermoremotor_motorTurnForSpeed':   'motor: run for (speed)',
    'flippermoremotor_motorSetStopMethod':  'motor: set stop mode',
    'flippermoremotor_motorSetDegreeCounted': 'motor: set relative position',
    # Sensors
    'flippersensors_resetYaw':              'sensor: reset yaw',
    'flippersensors_resetTimer':            'sensor: reset timer',
    # Sound
    'flippersound_beep':                    'sound: beep',
    'flippersound_beepForTime':             'sound: beep for time',
    'flippersound_stopSound':               'sound: stop sound',
    'flippersound_playSound':               'sound: play sound',
    'flippersound_playSoundUntilDone':      'sound: play sound until done',
    # Display (external tile)
    'flipperdisplay_ledMatrix':             'display: show image',
    'flipperdisplay_ledMatrixFor':          'display: show image for time',
    'flipperdisplay_ledMatrixText':         'display: show text',
    'flipperdisplay_ledMatrixOff':          'display: clear pixels',
    'flipperdisplay_ledMatrixOn':           'display: set pixel',
    'flipperdisplay_ledMatrixBrightness':   'display: set brightness',
    'flipperdisplay_centerButtonLight':     'display: center button light',
    # Hub light / display
    'flipperlight_lightDisplayText':        'hub: show text on screen',
    'flipperlight_centerButtonLight':       'hub: set center button color',
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
    lines.append("from collections import OrderedDict")
    lines.append("import json")
    lines.append("")
    lines.append(f'# exported from: {Path(doc.path).name}')
    lines.append("# export style: builder")
    lines.append("# note: exact-reconstruction export shaped for readability.")
    lines.append("#       opcode labels are shown as inline comments.")
    lines.append("#       for a fully readable decompilation use --style python-first.")
    lines.append("")
    lines.append("def _set_block(project, block_id, payload):")
    lines.append('    project.sprite["blocks"][block_id] = payload')
    lines.append("")
    lines.append("def build(project, api, ns, enums):")
    lines.append("    project.clear_code()")
    lines.append("")
    lines.append("    # ── Project summary ──────────────────────────────────────────────────")
    lines.append(f"    # variables: {summary['variables']}")
    lines.append(f"    # lists:     {summary['lists']}")
    lines.append(f"    # blocks:    {summary['blocks']}")
    lines.append(f"    # opcodes:   {summary['opcode_count']} unique")
    for proc in summary["procedures"]:
        lines.append(f"    # procedure: {proc['proccode']}")
    lines.append("")
    lines.append("    # ── High-level hints ─────────────────────────────────────────────────")
    opcode_counts = summary["opcode_counts"]
    if "flipperevents_whenProgramStarts" in opcode_counts:
        lines.append("    # ✓ project has one or more program-start entry stacks")
    if any(op.startswith("procedures_") for op in opcode_counts):
        lines.append("    # ✓ project uses custom procedures (see procedure blocks below)")
    if any(op.startswith("data_") for op in opcode_counts):
        lines.append("    # ✓ project uses variables/lists (recreated below before blocks)")
    lines.append("")

    if variables:
        lines.append("    # ── Variables ────────────────────────────────────────────────────────")
        for vid, pair in variables.items():
            lines.append(f"    project.variables[{vid!r}] = {_pyrepr(pair)}  # name: {pair[0]!r}")
        lines.append("")
    if lists:
        lines.append("    # ── Lists ────────────────────────────────────────────────────────────")
        for lid, pair in lists.items():
            lines.append(f"    project.lists[{lid!r}] = {_pyrepr(pair)}  # name: {pair[0]!r}")
        lines.append("")

    lines.append('    project.sprite["blocks"] = OrderedDict()')
    lines.append("")
    top_ids = {bid for bid, block in blocks.items() if block.get("topLevel")}
    proc_proto_ids = {bid for bid, block in blocks.items() if block.get("opcode") == "procedures_prototype"}
    proc_def_ids = {bid for bid, block in blocks.items() if block.get("opcode") == "procedures_definition"}

    nonlocal_lines = lines

    def emit_group(title: str, pred):
        emitted = False
        for bid, block in blocks.items():
            if pred(bid, block):
                if not emitted:
                    nonlocal_lines.append(f"    # ── {title} ──")
                opcode = block.get("opcode", "?")
                label = _opcode_label(opcode)
                nonlocal_lines.append(
                    f"    _set_block(project, {bid!r}, "
                    f"json.loads({json.dumps(block, ensure_ascii=False)!r}))  # {label}"
                )
                emitted = True
        if emitted:
            nonlocal_lines.append("")

    emit_group("top-level blocks", lambda bid, block: bid in top_ids)
    emit_group(
        "procedure definitions and prototypes",
        lambda bid, block: bid in proc_def_ids or bid in proc_proto_ids,
    )
    emit_group(
        "remaining blocks",
        lambda bid, block: bid not in top_ids and bid not in proc_def_ids and bid not in proc_proto_ids,
    )

    lines.append('    project.sprite["comments"] = OrderedDict()')
    if comments:
        lines.append("    # ── Comments ─────────────────────────────────────────────────────────")
        for cid, comment in comments.items():
            lines.append(
                f"    project.sprite[\"comments\"][{cid!r}] = "
                f"json.loads({json.dumps(comment, ensure_ascii=False)!r})"
            )
        lines.append("")
    return [line for line in lines if line != ""] + [""]
