# ScratchWrapper Facade Reference

`ScratchWrapper` provides a schema-backed, module-oriented view over an
`LLSP3Project`.  It lets callers enumerate Scratch modules (groups of opcodes
sharing a prefix) and invoke blocks without knowing raw opcode strings.

---

## Overview

```python
from outputllsp3 import ScratchWrapper, LLSP3Project

project = LLSP3Project('ok.llsp3', 'strings.json')
wrapper = ScratchWrapper(project)
```

---

## `available_modules(verified_only=False)`

Returns a list of module name prefixes derived from the loaded opcodes:

```python
modules = wrapper.available_modules()
# → ['flippermove', 'flippermotor', 'flippermoremotor', ...]

verified = wrapper.available_modules(verified_only=True)
# → only modules with opcodes present in the block-reference template
```

---

## `describe(module, name=None)`

Return metadata for a module or a specific block within it:

```python
wrapper.describe('flippermove')
# → {'module': 'flippermove', 'blocks': [...]}

wrapper.describe('flippermove', 'move')
# → {'opcode': 'flippermove_move', 'label': '...', 'args': [...]}
```

---

## `invoke(opcode, **kwargs)`

Generate a block by providing its opcode and input/field values as keyword
arguments.  Returns the block ID:

```python
block_id = wrapper.invoke('flippermove_move', DISTANCE=30, SPEED=420)
```

This is lower-level than the `API` facades and useful for opcodes that are
not yet covered by named helpers.

---

## CLI Usage

The `modules` and `describe` sub-commands expose the wrapper from the CLI:

```bash
outputllsp3 modules
outputllsp3 modules --module flippermove
outputllsp3 describe flippermove move
outputllsp3 modules --verified-only
```

---

## Relationship to SchemaRegistry

`ScratchWrapper` uses `SchemaRegistry` / `bundled_schema()` internally to
power the `verified_only` filter and to validate opcode existence.  For direct
opcode verification, use `bundled_schema().is_verified(opcode)`.
