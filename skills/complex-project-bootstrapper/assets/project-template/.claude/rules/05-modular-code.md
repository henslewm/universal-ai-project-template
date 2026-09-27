# Modular Code

- Before firmware work, read the `MODULES.md` index beside the sources and open only the modules that own the state you are changing. Don't read the whole sketch folder by default.
- Treat each module's header as its contract; change the header only when the contract changes.
- Add new behavior to its owning module or a new module; keep an Arduino `.ino` to `setup()`/`loop()`.
- Update `MODULES.md` in the same change whenever a module, public function or ownership changes.
- Firmware: bump a build identifier for every flashed build and record the ELF hash in evidence.
