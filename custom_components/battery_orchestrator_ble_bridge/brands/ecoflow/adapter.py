"""
Adaptador de marca para EcoFlow — implementa `brands.base.BrandAdapter`
por encima de `eflib/` (vendorizada tal cual desde rabits/ha-ef-ble,
Apache-2.0, ver eflib/NOTICE.md). Este archivo es la UNICA parte
especifica de EcoFlow que el puente conoce por su nombre — todo lo demas
(`__init__.py`, los servicios de HA) solo ve la interfaz generica.

`credentials` para esta marca: `{"user_id": "<userId numerico de la
cuenta EcoFlow>"}` — nunca la contraseña, ver el propio Battery
Orchestrator para el porque.
"""

from __future__ import annotations

import asyncio
import logging

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from ...const import CONNECT_TIMEOUT_SECONDS
from . import eflib

_LOGGER = logging.getLogger(__name__)

# Propiedades que se devuelven en "get_state" — nombres tal cual los
# expone la clase Device de eflib para la familia STREAM (stream_ac.py,
# heredada por stream_pro/stream_max/stream_ultra/stream_ac_pro). Una
# propiedad que el dispositivo no ha reportado todavia (o que ese modelo
# no soporta) simplemente viene a None — nunca un cero inventado.
STREAM_STATE_FIELDS = [
    "battery_level",
    "battery_level_main",
    "battery_power",
    "grid_power",
    "charging_task_enabled",
    "charging_grid_power_limit",
    "charging_grid_target_soc",
    "discharging_task_enabled",
    "discharging_power_limit",
    "energy_backup_battery_level",
]


class EcoflowBrandAdapter:
    def __init__(self):
        self._devices: dict[str, eflib.DeviceBase] = {}

    async def discover(self, hass: HomeAssistant) -> list[dict]:
        found: dict[str, dict] = {}
        for info in bluetooth.async_discovered_service_info(hass, connectable=True):
            try:
                device = eflib.NewDevice(info.device, info.advertisement)
            except Exception:  # anuncio BLE que no se pudo interpretar - se ignora, no tumba el descubrimiento
                continue
            if device is None or eflib.is_unsupported(device):
                continue
            found[device.address] = {
                "address": device.address,
                "sn": device.serial_number,
                "name": device.name,
            }
        return list(found.values())

    async def ensure_connected(self, hass: HomeAssistant, address: str, credentials: dict) -> eflib.DeviceBase:
        user_id = (credentials or {}).get("user_id")
        device = self._devices.get(address)
        if device is not None and device.is_connected:
            return device

        ble_dev = bluetooth.async_ble_device_from_address(hass, address, connectable=True)
        info = bluetooth.async_last_service_info(hass, address, connectable=True)
        if ble_dev is None or info is None:
            raise HomeAssistantError(
                f"No se ve {address} por Bluetooth ahora mismo — comprueba que esta "
                "encendido y al alcance del adaptador o del ESPHome BT Proxy."
            )

        if device is None:
            new_device = eflib.NewDevice(ble_dev, info.advertisement)
            if new_device is None or eflib.is_unsupported(new_device):
                raise HomeAssistantError(f"{address} no es un dispositivo EcoFlow reconocido")
            device = new_device
            self._devices[address] = device
        else:
            device.update_ble_device(ble_dev)

        _LOGGER.info("Conectando por BLE a %s (%s)", device.device, address)
        await device.connect(user_id=user_id)
        try:
            async with asyncio.timeout(CONNECT_TIMEOUT_SECONDS):
                state = await device.wait_until_authenticated_or_error(raise_on_error=True)
        except TimeoutError as e:
            raise HomeAssistantError(
                f"No se pudo conectar con {address} en {CONNECT_TIMEOUT_SECONDS}s"
            ) from e
        if not state.authenticated:
            raise HomeAssistantError(f"No se pudo autenticar con {address} — revisa el userId")
        return device

    def get_state(self, device: eflib.DeviceBase) -> dict:
        state = {field: getattr(device, field, None) for field in STREAM_STATE_FIELDS}
        state["pv_power"] = self._pv_power_total(device)
        state["pv_channels"] = self._pv_channels(device)
        state["sn"] = device.serial_number
        state["name"] = device.name
        return state

    @staticmethod
    def _pv_channels(device: eflib.DeviceBase) -> dict[str, dict]:
        """
        Puertos MPPT de ESTA bateria, uno por uno -- los STREAM traen
        entre 0 y 4 segun el modelo (`pv_power_1`..`pv_power_4` en
        eflib), y en una misma bateria pueden ir conectados paneles de
        zonas/orientaciones distintas, cada uno con su propia previsión.
        `supported` distingue "este modelo no tiene este puerto" (no
        aparece ni como atributo en su clase) de "lo tiene pero todavia
        no ha reportado nada" (`power_w: None` con `supported: true`) --
        para que el menu de alta en Configuración → Solar solo ofrezca
        puertos que existen de verdad en ESTE modelo concreto.
        """
        channels = {}
        for i in (1, 2, 3, 4):
            attr = f"pv_power_{i}"
            supported = hasattr(device, attr)
            val = getattr(device, attr, None) if supported else None
            channels[str(i)] = {
                "supported": supported,
                "power_w": float(val) if val is not None else None,
            }
        return channels

    @classmethod
    def _pv_power_total(cls, device: eflib.DeviceBase) -> float | None:
        """
        Suma de TODOS los puertos MPPT de esta bateria -- comoda para
        quien solo quiera un numero agregado (ver `pv_power`); para
        vincular paneles de zonas distintas por separado se usa
        `pv_channels` en su lugar. Usa `pv_power_sum` si el modelo lo
        trae (mas fiable, lo suma el propio dispositivo); si no, suma a
        mano los canales que ese modelo SI tenga. `None` si el modelo no
        tiene ningun puerto MPPT -- nunca un cero inventado.
        """
        if hasattr(device, "pv_power_sum"):
            val = getattr(device, "pv_power_sum")
            return float(val) if val is not None else None
        channels = [getattr(device, f"pv_power_{i}", None) for i in (1, 2, 3, 4)]
        known = [c for c in channels if c is not None]
        return float(sum(known)) if known else None

    async def set_charging_task(
        self, device: eflib.DeviceBase, enable: bool | None, power_limit_w: float | None, target_soc: float | None,
    ) -> bool:
        if not hasattr(device, "enable_charging_task"):
            return False
        if enable is not None:
            await device.enable_charging_task(enable)
        if power_limit_w is not None:
            await device.set_charging_grid_power_limit(power_limit_w)
        if target_soc is not None:
            await device.set_charging_grid_target_soc(target_soc)
        return True

    async def set_discharging_task(
        self, device: eflib.DeviceBase, enable: bool | None, power_limit_w: float | None,
    ) -> bool:
        if not hasattr(device, "enable_discharging_task"):
            return False
        if enable is not None:
            await device.enable_discharging_task(enable)
        if power_limit_w is not None:
            await device.set_discharging_power_limit(power_limit_w)
        return True

    async def disconnect(self, device: eflib.DeviceBase) -> None:
        await device.disconnect()
        self._devices = {addr: d for addr, d in self._devices.items() if d is not device}
