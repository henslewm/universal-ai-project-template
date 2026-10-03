# MODULES

Index of firmware modules, kept beside the sources. Read this first and open only the module that
owns the state you are changing. Update it in the same change as any module, public function or
ownership change (`.claude/rules/05-modular-code.md`). The rows below are placeholders.

| Module | Owns state | Header | Public functions | Notes |
|---|---|---|---|---|
| `example_module` | `g_example_state` (written only here) | `example_module.h` | `exampleInit()`, `exampleStep()` | Depends on: none. |

Columns:

- **Module**: one single-responsibility unit (a `.h`/`.cpp` pair).
- **Owns state**: variables or hardware resources only this module writes.
- **Header**: path to the header; it is the module's contract.
- **Public functions**: the API other modules may call.
- **Notes**: dependencies, timing limits, build flags.

The `.ino` holds only `setup()` and `loop()` and is not a module.
