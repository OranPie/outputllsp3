# Strict Verified Mode

Strict verified mode enables an extra layer of build-time validation that
rejects any opcode not present in the bundled `block_reference.llsp3`
template.  This prevents generating projects that are structurally valid JSON
but silently rejected or broken by the SPIKE app at runtime.

---

## Enabling Strict Mode

### Python API

```python
from outputllsp3 import LLSP3Project, API

project = LLSP3Project('ok.llsp3', 'strings.json')
project.set_strict_verified(True)
api = API(project)

# Any use of an unverified opcode now raises ValueError immediately
```

### Build-script transpiler

```bash
outputllsp3 build my_robot.py --out robot.llsp3 --strict-verified
```

### Python-first transpiler

```bash
outputllsp3 build-python prog.py --out prog.llsp3 --strict-verified
```

---

## How It Works

1. `project.set_strict_verified(True)` loads (or reuses the cached singleton)
   `SchemaRegistry` from `bundled_schema()`.
2. On every `project.add_block(opcode, …)` call, the opcode is looked up in
   the registry.
3. If the opcode is not in the registry, `ValueError` is raised with the
   unknown opcode name so the build fails early.

---

## Verified Opcode List

Run the CLI to dump all verified opcodes:

```bash
outputllsp3 verified-opcodes           # sorted list
outputllsp3 verified-opcodes --full    # full metadata dict
outputllsp3 verified-opcodes --out verified.json  # save to file
```

The verified set is derived by opening `resources/block_reference.llsp3` and
extracting every opcode found in `project.json`.

---

## When to Use Strict Mode

- **Development**: Always enable when writing new transpiler code to catch
  typos in opcode strings.
- **CI / automated builds**: Enable in CI to prevent regressions.
- **Production**: Optional — valid generated projects work without it; strict
  mode only adds extra safety.

---

## Caveats

- The bundled `block_reference.llsp3` covers the opcodes present in a
  particular SPIKE app version.  New opcodes introduced in a newer app version
  may trigger false-positive failures until the resource is updated.
- Internal Scratch prefixes (`argument`, `control`, `data`, `operator`,
  `procedures`) are not SPIKE extensions and are always allowed; strict mode
  does not filter them.
