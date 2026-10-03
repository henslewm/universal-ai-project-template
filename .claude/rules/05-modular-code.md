---
paths:
  - "**/MODULES.md"
  - "**/*.ino"
  - "**/*.cpp"
  - "**/*.h"
---

# Modular Code

- Before firmware work, read the `MODULES.md` index beside the sources and open only the modules that own the state you are changing. Don't read the whole sketch folder by default.
- Treat each module's header as its contract; change the header only when the contract changes.
- Add new behavior to its owning module or a new module; keep an Arduino `.ino` to `setup()`/`loop()`.
- Start a new index from `templates/software-hardware/MODULES.md`.
- Update `MODULES.md` in the same change whenever a module, public function or ownership changes.
- Firmware: bind hardware evidence to the runtime `elf_sha256` the firmware prints (the ELF hash embedded in the app image), and record the ELF hash of every flashed build. Any build label is injected at build time, never hard-coded (see `docs/PLATFORMIO.md`).
