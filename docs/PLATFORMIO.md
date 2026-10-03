# PlatformIO configuration rules (Arduino / ESP32)

Every Arduino or ESP32 firmware project keeps a root `platformio.ini` next to its Arduino IDE/CLI instructions. Generate it from observed hardware and the project's pinned toolchain, never from a copied example. The software-hardware profile (`templates/software-hardware/PROFILE.md`) requires these rules.

## Generation rules

1. **Identify the hardware first.** Run `esptool --port <port> flash-id` (read-only; it resets the board) and record the chip, revision, flash size and embedded PSRAM line as a comment at the top of the ini. Never assume PSRAM or flash size from a board name.
2. **Match the platform to the pinned Arduino core.**
   - Arduino-ESP32 **2.0.x**: `platform = espressif32@<exact 6.x>`.
   - Arduino-ESP32 **3.x**: stock `espressif32` does not ship 3.x. Use a pinned pioarduino release URL, for example `https://github.com/pioarduino/platform-espressif32/releases/download/55.03.312-1/platform-espressif32.zip` (tag `55.03.312-1` = Arduino v3.3.12 / ESP-IDF v5.5.5).
   - Never use `latest`, a branch, or a floating range for a pinned core.
   - Look up the tag with `gh api repos/pioarduino/platform-espressif32/releases`; release names state the Arduino version.
3. **Memory from the observed chip.**
   - `board_build.arduino.memory_type`: `qio_opi` for octal PSRAM (ESP32-S3 R8/R16 parts, esptool shows "Embedded PSRAM 8MB (AP_3v3)"); `qio_qspi` for quad or no PSRAM.
   - Add `-DBOARD_HAS_PSRAM` only when PSRAM exists.
   - Set `board_upload.flash_size` and `board_build.partitions` from the detected flash size. Set `board_upload.maximum_size` to the **application partition** size in that partition table (e.g. `app0` = `0x640000` = 6553600 in `default_16MB.csv`), never the physical flash size.
4. **Serial and ports.**
   - Set `-DARDUINO_USB_CDC_ON_BOOT=1` only when the console is the chip's native USB (ESP32-S3/C3 USB-Serial/JTAG, VID:PID `303A:1001`).
   - Select ports by hardware ID (`upload_port = hwgrep://303A:1001`), not COM numbers.
   - `monitor_speed` equals the sketch's `Serial.begin()` baud.
5. **Source layout.** If the sketch is not in `src/`, set `[platformio] src_dir` to the sketch folder. Exactly one `.ino` tree may be under `src_dir`; evidence or archived sketches must stay outside it.
6. **Environments.**
   - The default `dev` environment must respect the project's boot and log requirements. Use `CORE_DEBUG_LEVEL=1` when a quiet boot is required.
   - Put verbose logs (`=4`) in a separate `debug` environment.
   - `release` uses `=0`.
7. **Compiler flags.** Don't override the C++ standard unless the code needs it. Arduino-ESP32 3.x already uses `-std=gnu++2b`, so forcing `gnu++17` is a downgrade.
8. **Monitor.** Include `monitor_filters = esp32_exception_decoder, time` so crashes decode against the exact ELF.
9. **Ignore output.** Add `.pio/` to `.gitignore`.
10. **Keep builds equivalent.** Record the arduino-cli FQBN and `--build-property` values that produce the same configuration, and state which toolchain produced any flashed artifact. A PlatformIO ELF and an arduino-cli ELF are different artifacts.
11. **Bind evidence to the artifact itself.**
    - The firmware prints the ELF SHA-256 that `elf2image --elf-sha256-offset 0xb0` embeds in the app image, `esp_app_get_description()->app_elf_sha256` (snippet below). arduino-cli and PlatformIO/pioarduino both set this offset.
    - Evidence compares that runtime value with the recorded ELF hash. It changes with every input: sources, flags, board options, core and scripts.
    - An optional readable label can be passed as `-DFIRMWARE_BUILD_ID="..."`. It is never proof of identity: a pre-build label cannot see flags or the installed core.
12. **Verify before relying on it.** `pio run -e <default>` must succeed. For hardware claims, upload, run the project's smoke test and record the runtime `elf_sha256` and the ELF SHA-256. A successful compile is not hardware verification.

## Example

`templates/software-hardware/platformio.example.ini` is a complete Arduino-ESP32 2.0.x variant (stock `espressif32` 6.x, LittleFS, `dev`/`debug`/`release` environments) for the same board. Like the one below, it illustrates the rules and is never copied into a project.

ESP32-S3 N16R8 (16 MB flash, embedded 8 MB octal PSRAM), console on native USB, Arduino-ESP32 3.3.12:

```ini
[platformio]
default_envs = dev
src_dir = firmware/MySketch

[env]
platform = https://github.com/pioarduino/platform-espressif32/releases/download/55.03.312-1/platform-espressif32.zip
board = esp32-s3-devkitc-1
framework = arduino
board_build.arduino.memory_type = qio_opi
board_build.flash_mode = qio
board_build.f_flash = 80000000L
board_upload.flash_size = 16MB
board_upload.maximum_size = 6553600   ; app0 of default_16MB.csv
board_build.partitions = default_16MB.csv
build_flags =
    -DBOARD_HAS_PSRAM
    -DARDUINO_USB_CDC_ON_BOOT=1
upload_port  = hwgrep://303A:1001
monitor_port = hwgrep://303A:1001
monitor_speed = 115200            ; equals Serial.begin(115200) in the sketch below
monitor_filters = esp32_exception_decoder, time

[env:dev]
build_flags = ${env.build_flags} -DCORE_DEBUG_LEVEL=1

[env:debug]
build_flags = ${env.build_flags} -DCORE_DEBUG_LEVEL=4

[env:release]
build_flags = ${env.build_flags} -DCORE_DEBUG_LEVEL=0
```

Equivalent arduino-cli command:

```powershell
arduino-cli compile -b esp32:esp32:esp32s3:CDCOnBoot=cdc,PSRAM=opi,FlashMode=qio,FlashSize=16M `
  --build-property build.partitions=default_16MB --build-property upload.maximum_size=6553600 firmware/MySketch
```

To add an optional label with arduino-cli, append `--build-property "compiler.cpp.extra_flags='-DFIRMWARE_BUILD_ID=\"<label>\"'"`. The single quotes are needed to keep the double quotes through arduino-cli's argument splitter. Verified on hardware in the downstream project described in issue #51.

Firmware side (Arduino-ESP32 3.x / ESP-IDF 5.x): print the runtime artifact identity, plus the optional label with a visible fallback. The `.ino` holds only `setup()` and `loop()`, so the printer lives in its own module, `build_identity.h` plus `build_identity.cpp`. Arduino's automatic `.ino` preprocessing (includes and generated prototypes) does not reach a `.cpp` file. So the module includes the Arduino declarations itself (`Serial` from `Arduino.h`, `ESP_ARDUINO_VERSION_STR` from `esp_arduino_version.h`), and the `.ino` includes the module's header to call it.

```cpp
// build_identity.h
#pragma once
void printBuildIdentity();
```

```cpp
// MySketch.ino
#include "build_identity.h"

void setup() {
  Serial.begin(115200);
  printBuildIdentity();
}

void loop() {}
```

```cpp
// build_identity.cpp
#include "build_identity.h"
#include <Arduino.h>
#include "esp_arduino_version.h"
#include "esp_app_desc.h"   // core 3.x (ESP-IDF 5.x) only; see the 2.0.x note below
#ifndef FIRMWARE_BUILD_ID
#define FIRMWARE_BUILD_ID "unlabeled"
#endif

void printBuildIdentity() {
  char elf[65];
  const uint8_t* sha = esp_app_get_description()->app_elf_sha256;
  for (int i = 0; i < 32; ++i) snprintf(elf + 2 * i, 3, "%02x", sha[i]);
  Serial.printf("Build: %s core=%s elf_sha256=%s\n", FIRMWARE_BUILD_ID, ESP_ARDUINO_VERSION_STR, elf);
}
```

The `esp_app_desc.h` include and `esp_app_get_description()` are for Arduino-ESP32 3.x (ESP-IDF 5.x). The ESP-IDF 4.4 headers behind Arduino-ESP32 2.0.x are not reproduced in this repository, so no 2.0.x header or function name is given here and none was verified offline. On a 2.0.x core, take the app description from that core's own ESP-IDF headers and confirm that `app_elf_sha256` equals the ELF SHA-256 on hardware before relying on it.

Downstream, the printed `elf_sha256` equalled the SHA-256 of the flashed `firmware.elf` exactly.
