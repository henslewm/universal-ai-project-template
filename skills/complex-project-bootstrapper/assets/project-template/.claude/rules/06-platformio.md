# PlatformIO

- Every Arduino/ESP32 project keeps a root `platformio.ini`. Create or update it by following `docs/PLATFORMIO.md`.
- Base it on observed hardware (`esptool flash-id`) and the pinned Arduino core. Arduino-ESP32 3.x requires a pinned pioarduino release URL; stock `espressif32@6.x` is core 2.0.x.
- Select ports by USB VID:PID (`hwgrep://`), not COM numbers. Keep the default environment's log level compatible with the project's boot/log rules.
- Verify with `pio run` before relying on it, and record which toolchain produced any flashed ELF.
