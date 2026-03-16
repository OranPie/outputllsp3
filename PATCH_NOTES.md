# OutputLLSP3 library v29 patch notes

This patch focuses on LLSP3 projects that look structurally valid but are rejected by the LEGO SPIKE app.

## Main fixes

1. Boolean block typing
   - Added boolean-aware input handling in `project.py`.
   - `operator_or`, `operator_and`, and `operator_not` now use boolean slots instead of numeric slots.
   - Non-boolean values passed into boolean slots are coerced into a valid boolean block instead of being wired directly.

2. Python-first boolean lowering
   - Added support for `ast.BoolOp` (`and` / `or`) and `not` in expression/condition lowering.
   - Rewrote condition negation to use `operator_not` instead of `eq(bool_expr, 0)`.
   - Reworked loop guard generation so it does not build invalid boolean-vs-numeric comparisons.

3. Parent pointer repair
   - `add_block()` now attaches referenced child blocks back to the owning parent when the child parent is still unset or placeholder-only.
   - This prevents large numbers of orphaned reporter/menu blocks inside generated expressions.

4. Extension list cleanup
   - `save()` now excludes Scratch core prefixes from exported `project.json.extensions`:
     `argument`, `control`, `data`, `operator`, `procedures`.

5. Template monitor cleanup
   - `clear_code()` now clears `project_json["monitors"]` so stale template monitors do not leak into generated projects.

6. Asset hash normalization
   - `save()` now normalizes embedded asset filenames and `assetId/md5ext` pairs to the real MD5 of the file contents.
   - Shared assets referenced by multiple targets are handled consistently.

7. Validation improvements
   - Added extra validation for:
     - missing child-parent relationships
     - boolean slots wired to non-boolean blocks
     - `operator_equals` wired directly to boolean blocks
     - control conditions wired to non-boolean blocks

## Files changed

- `outputllsp3/project.py`
- `outputllsp3/api.py`
- `outputllsp3/pythonfirst.py`

## Smoke-checked

- Python syntax compilation for the three edited files
- Python-first transpilation of the bundled `examples/python_first_robot.py`
- Export sanity checks on the generated `.llsp3`:
  - cleaned extension list
  - empty/stale monitors removed
  - corrected asset hash naming
  - zero parent-pointer mismatches
  - zero boolean-shape mismatches in a sample output
