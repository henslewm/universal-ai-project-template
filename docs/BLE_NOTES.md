# BLE notes

Hardware-facing lessons from a composite BLE HID project (template issue #51):

- A pinned-core defect can look like a descriptor or host problem. Print the actual GATT handles,
  and log raw stack events (including ones the framework wrapper ignores), before editing report
  maps or blaming the host. Add observation-only diagnostics before any fix.
- Arduino-ESP32 3.3.12 with NimBLE silently drops a second characteristic with the same UUID, for
  example a second HID input report (0x2A4D). Its handle stays 0xFFFF.
- A Windows desktop process pairs a BLE peripheral through exact-address
  `BluetoothLEDevice.FromBluetoothAddressAsync` and custom `ConfirmOnly` pairing. Association
  endpoint enumeration and plain `PairAsync()` are unreliable without pairing UI.
- Leaving a peripheral mode must end the host link, not only advertising.
