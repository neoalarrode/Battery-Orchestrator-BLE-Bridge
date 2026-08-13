<h1 align="center">Battery Orchestrator — EcoFlow BLE Bridge</h1>

<p align="center">
  Home Assistant integration, no entities or manual configuration — just
  services that <a href="https://github.com/neoalarrode/Battery-Orchestrator">Battery Orchestrator</a>
  calls on its own to manage EcoFlow batteries directly over Bluetooth
  (including through an ESPHome Bluetooth Proxy).
</p>

<p align="center">
  🇬🇧 English · <a href="README.md">🇪🇸 Leer en español</a>
</p>

---

⚠️ **Status: v0.1.0, not yet verified against real hardware.** The
low-level BLE protocol (`eflib/`) is an unmodified copy of
[rabits/ha-ef-ble](https://github.com/rabits/ha-ef-ble) (Apache-2.0),
already proven in production by that project — but the service layer
connecting it to Battery Orchestrator is new and hasn't been tested
against a real EcoFlow device yet. Only install it if you're helping
verify it.

## What it does

No config-flow fields, no entities, no sensors — everything goes through
5 **services** that Battery Orchestrator calls via the Home Assistant API,
same philosophy already used for Climate Orchestrator zone discovery:
never polls anything on its own, only responds when asked.

- `battery_orchestrator_ecoflow_ble.discover` — EcoFlow devices currently visible over Bluetooth (no connection made).
- `battery_orchestrator_ecoflow_ble.get_state` — SOC, power, and charging/discharging task state for a device.
- `battery_orchestrator_ecoflow_ble.set_charging_task` / `set_discharging_task` — enable/disable, power limit, target SOC.
- `battery_orchestrator_ecoflow_ble.disconnect` — closes the BLE connection.

## Installation

1. HACS → ⋮ → Custom repositories → add
   `https://github.com/neoalarrode/Battery-Orchestrator-EcoFlow-BLE` as type **Integration**.
2. Install and restart Home Assistant.
3. **Settings → Devices & services → Add integration** → search
   "Battery Orchestrator - EcoFlow BLE Bridge" → click "Submit" (no field to fill in).
4. Set up your EcoFlow BLE batteries from Battery Orchestrator, not from here.

## Your EcoFlow account `userId`

The control services need the numeric `userId` of your EcoFlow account
(the mobile app one) for pairing — not the password, just an identifier.
Battery Orchestrator will ask you to get it once (e.g. by temporarily
installing [rabits/ha-ef-ble](https://github.com/rabits/ha-ef-ble) and
copying the `userId` from its config entry) and stores it itself for next
time.

## License

© 2026 Eric Larrodé. All rights reserved — see [LICENSE](LICENSE).
The `custom_components/battery_orchestrator_ecoflow_ble/eflib/` folder is
the exception: an unmodified copy of `rabits/ha-ef-ble`, Apache-2.0
licensed (see the notice inside that folder).
