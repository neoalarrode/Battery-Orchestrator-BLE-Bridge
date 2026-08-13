<h1 align="center">Battery Orchestrator — BLE Bridge</h1>

<p align="center">
  Home Assistant integration, no entities or manual configuration — just
  generic services (with a "brand" field) that
  <a href="https://github.com/neoalarrode/Battery-Orchestrator">Battery Orchestrator</a>
  calls on its own to manage batteries directly over Bluetooth (including
  through an ESPHome Bluetooth Proxy).
</p>

<p align="center">
  🇬🇧 English · <a href="README.md">🇪🇸 Leer en español</a>
</p>

---

⚠️ **Status: v0.2.0, not yet verified against real hardware.**

## Designed for more than one brand from day one

This bridge's 5 services are generic — they take a `brand` field
("ecoflow" for now, the only supported brand) and a free-form
`credentials` object, not a hardcoded EcoFlow-only `user_id`. Internally,
each brand is an isolated **adapter** in its own folder (`brands/<brand>/`)
implementing 5 common methods
(`discover`/`ensure_connected`/`get_state`/`set_charging_task`/`set_discharging_task`).

Adding a new brand tomorrow means: writing its adapter (with its own
protocol library vendored alongside it, same as `eflib/` for EcoFlow) and
registering it in `brands/__init__.py` — **an update to this bridge and an
update to Battery Orchestrator is all it takes**, no new repository, no
reinstalling anything different in Home Assistant.

The EcoFlow brand (`brands/ecoflow/`) uses `eflib/`, an unmodified copy of
[rabits/ha-ef-ble](https://github.com/rabits/ha-ef-ble) (Apache-2.0) — the
connection, encryption/pairing, and packet framing are already proven in
production by that project; what's new here is only the adapter
connecting them to the generic pattern above, and **that part hasn't been
tested against real hardware yet**.

## What it does

- `battery_orchestrator_ble_bridge.discover` — devices of a brand currently visible over Bluetooth (no connection made).
- `battery_orchestrator_ble_bridge.get_state` — SOC, power, and charging/discharging task state for a device.
- `battery_orchestrator_ble_bridge.set_charging_task` / `set_discharging_task` — enable/disable, power limit, target SOC.
- `battery_orchestrator_ble_bridge.disconnect` — closes the BLE connection.

## Installation

1. HACS → ⋮ → Custom repositories → add
   `https://github.com/neoalarrode/Battery-Orchestrator-BLE-Bridge` as type **Integration**.
2. Install and restart Home Assistant.
3. **Settings → Devices & services → Add integration** → search
   "Battery Orchestrator - BLE Bridge" → click "Submit" (no field to fill in).
4. Set up your BLE batteries from Battery Orchestrator, not from here.

## EcoFlow credentials

EcoFlow's control services need `{"user_id": "..."}` in `credentials` —
the numeric `userId` of your EcoFlow account (the mobile app one), not the
password. Battery Orchestrator will ask you to get it once (e.g. by
temporarily installing [rabits/ha-ef-ble](https://github.com/rabits/ha-ef-ble)
and copying the `userId` from its config entry) and stores it itself for
next time.

## License

© 2026 Eric Larrodé. All rights reserved — see [LICENSE](LICENSE).
The `custom_components/battery_orchestrator_ble_bridge/brands/ecoflow/eflib/`
folder is the exception: an unmodified copy of `rabits/ha-ef-ble`,
Apache-2.0 licensed (see the notice inside that folder).
