# SPIKE App — Official API Supplement Notes

This document records reverse-engineered details about the LEGO Education
SPIKE app's internal block system that are relevant to `outputllsp3`.

For the comprehensive deep-dive, see the root-level
[spike-scratch-reverse-engineering.md](../spike-scratch-reverse-engineering.md).

---

## File Format

An `.llsp3` file is a **ZIP archive** containing:

```
project.llsp3  (ZIP)
├── manifest.json     Required — project metadata
├── scratch.sb3       Required — inner ZIP containing project.json
│   └── project.json  Scratch 3 VM project (targets, blocks, variables, …)
└── (optional assets — sound files, costumes)
```

The outer archive uses standard Deflate compression.

---

## `manifest.json` Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Project UUID |
| `name` | string | Display name shown in the app |
| `type` | string | `"scratch"` for block programs |
| `autoDelete` | bool | Whether to auto-delete on app exit |
| `state` | object | Scratch VM saved state |
| `description` | string | Optional user description |

---

## `project.json` Schema (relevant subset)

```json
{
  "targets": [
    {
      "isStage": true,
      "variables": {},
      "lists": {}
    },
    {
      "isStage": false,
      "name": "Sprite1",
      "variables": { "<id>": ["name", value] },
      "lists": { "<id>": ["name", [items]] },
      "blocks": { "<id>": { "opcode": "...", ... } }
    }
  ],
  "extensions": ["flippermove", "flippermotor", ...],
  "monitors": []
}
```

- Variables and lists live on the **non-stage target** (sprite).
- Extension strings must match the prefix of the opcodes used; `outputllsp3`
  derives the extension list automatically from block opcodes at save time.
- Core Scratch prefixes (`argument`, `control`, `data`, `operator`,
  `procedures`) are excluded from the extensions array.

---

## Block Structure

Each block in `blocks` is:

```json
{
  "opcode": "flippermove_stopMove",
  "next": "<next-block-id or null>",
  "parent": "<parent-block-id or null>",
  "inputs": {
    "INPUT_NAME": [1, "<block-id or literal>"]
  },
  "fields": {
    "FIELD_NAME": ["VALUE", null]
  },
  "shadow": false,
  "topLevel": false
}
```

Top-level hat blocks have `"topLevel": true` and `"x"` / `"y"` canvas
positions.

---

## Custom Procedure Mutation

The `procedures_prototype` block carries a `mutation` object:

```json
{
  "tagName": "mutation",
  "children": [],
  "proccode": "move_square %s %s",
  "argumentids": "[\"id1\",\"id2\"]",
  "argumentnames": "[\"side\",\"speed\"]",
  "argumentdefaults": "[\"20\",\"420\"]",
  "warp": "false"
}
```

- `proccode` — display name with `%s` placeholders for each parameter
- `argumentids` — JSON-encoded array of stable IDs (used to wire inputs)
- `argumentnames` — JSON-encoded array of human-readable parameter names
- `argumentdefaults` — JSON-encoded array of default value strings
  (empty string = no default; numeric strings are rendered as numbers by the app)
- `warp` — `"true"` for run-without-screen-refresh; `"false"` otherwise

---

## Known Validation Rules (from app source)

1. `operator_or` / `operator_and` / `operator_not` **must** use boolean input
   slots (input type `2`), not generic value slots (input type `1`).
2. `operator_equals` connected directly to a boolean slot causes a shape-type
   error; wrap with a boolean block.
3. Every non-top-level block must have a valid `parent` pointing to a block
   that exists in the same `blocks` map.
4. The `extensions` array must list every module prefix used by any opcode in
   the project, excluding the core Scratch prefixes.
5. Asset `assetId` and `md5ext` fields must match the actual MD5 hash of the
   asset file contents.

---

## App Version

This package was validated against SPIKE app version **18.0.1** (macOS).
Later versions may introduce additional opcodes or change mutation schemas.
