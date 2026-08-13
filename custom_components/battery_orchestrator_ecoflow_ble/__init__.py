"""
Puente BLE de EcoFlow para Battery Orchestrator.

Sin flujo de configuracion real (ver config_flow.py) y sin entidades: todo
se dispara mediante SERVICIOS que Battery Orchestrator llama por su cuenta
via la API de Home Assistant — exactamente el mismo patron que ya usa con
Climate Orchestrator (descubrimiento por boton, nunca sondeo de fondo) y
con el cliente Cloud de EcoFlow (ecoflow_cloud.py), solo que aqui, en vez
de REST/MQTT contra la nube, se habla BLE de verdad contra el dispositivo
— incluyendo a traves de un ESPHome Bluetooth Proxy, transparente porque
usamos la integracion `bluetooth` de HA, nunca un adaptador a pelo.

La capa de protocolo (conexion, cifrado, framing) es la libreria `eflib/`
vendorizada tal cual desde `rabits/ha-ef-ble` (Apache-2.0, ver
eflib/NOTICE.md) — aqui solo se orquesta: conectar, leer, mandar comandos
de las tareas de carga/descarga.
"""

from __future__ import annotations

import asyncio
import logging

import voluptuous as vol
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from . import eflib
from .const import (
    ATTR_ADDRESS,
    ATTR_ENABLE,
    ATTR_POWER_LIMIT_W,
    ATTR_TARGET_SOC,
    ATTR_USER_ID,
    CONNECT_TIMEOUT_SECONDS,
    DOMAIN,
    FIRST_DATA_TIMEOUT_SECONDS,
    SERVICE_DISCONNECT,
    SERVICE_DISCOVER,
    SERVICE_GET_STATE,
    SERVICE_SET_CHARGING_TASK,
    SERVICE_SET_DISCHARGING_TASK,
)

_LOGGER = logging.getLogger(__name__)

# Propiedades que se devuelven en "get_state" — nombres tal cual los expone
# la clase Device de eflib para la familia STREAM (stream_ac.py, heredada
# por stream_pro/stream_max/stream_ultra/stream_ac_pro). Una propiedad que
# el dispositivo no ha reportado todavia (o que ese modelo no soporta)
# simplemente viene a None — nunca un cero inventado.
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

_ADDRESS_SCHEMA = {vol.Required(ATTR_ADDRESS): cv.string}
_AUTH_SCHEMA = {**_ADDRESS_SCHEMA, vol.Required(ATTR_USER_ID): cv.string}

GET_STATE_SCHEMA = vol.Schema(_AUTH_SCHEMA)
DISCONNECT_SCHEMA = vol.Schema(_ADDRESS_SCHEMA)
SET_CHARGING_TASK_SCHEMA = vol.Schema({
    **_AUTH_SCHEMA,
    vol.Optional(ATTR_ENABLE): cv.boolean,
    vol.Optional(ATTR_POWER_LIMIT_W): vol.Coerce(float),
    vol.Optional(ATTR_TARGET_SOC): vol.Coerce(float),
})
SET_DISCHARGING_TASK_SCHEMA = vol.Schema({
    **_AUTH_SCHEMA,
    vol.Optional(ATTR_ENABLE): cv.boolean,
    vol.Optional(ATTR_POWER_LIMIT_W): vol.Coerce(float),
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"devices": {}}
    devices: dict[str, eflib.DeviceBase] = hass.data[DOMAIN][entry.entry_id]["devices"]

    async def _ensure_connected(address: str, user_id: str) -> eflib.DeviceBase:
        device = devices.get(address)
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
            devices[address] = device
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
            raise HomeAssistantError(f"No se pudo autenticar con {address} — revisa el user_id")
        return device

    async def handle_discover(call: ServiceCall) -> ServiceResponse:
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
        return {"devices": list(found.values()), "count": len(found)}

    async def handle_get_state(call: ServiceCall) -> ServiceResponse:
        address = call.data[ATTR_ADDRESS]
        user_id = call.data[ATTR_USER_ID]
        is_fresh_connection = not (devices.get(address) and devices[address].is_connected)
        device = await _ensure_connected(address, user_id)
        if is_fresh_connection:
            # da tiempo a que llegue el primer heartbeat del dispositivo -
            # nadie "pide" el estado a demanda, solo se recibe lo que el
            # propio equipo manda por su cuenta.
            await asyncio.sleep(FIRST_DATA_TIMEOUT_SECONDS)
        state = {field: getattr(device, field, None) for field in STREAM_STATE_FIELDS}
        state["address"] = address
        state["sn"] = device.serial_number
        state["name"] = device.name
        return state

    async def handle_set_charging_task(call: ServiceCall) -> ServiceResponse:
        address = call.data[ATTR_ADDRESS]
        user_id = call.data[ATTR_USER_ID]
        try:
            device = await _ensure_connected(address, user_id)
            if not hasattr(device, "enable_charging_task"):
                return {"ok": False, "error": "Este dispositivo no soporta control de tareas de carga"}
            if ATTR_ENABLE in call.data:
                await device.enable_charging_task(call.data[ATTR_ENABLE])
            if ATTR_POWER_LIMIT_W in call.data:
                await device.set_charging_grid_power_limit(call.data[ATTR_POWER_LIMIT_W])
            if ATTR_TARGET_SOC in call.data:
                await device.set_charging_grid_target_soc(call.data[ATTR_TARGET_SOC])
            return {"ok": True}
        except HomeAssistantError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            _LOGGER.exception("Fallo al mandar comando de carga a %s", address)
            return {"ok": False, "error": str(e)}

    async def handle_set_discharging_task(call: ServiceCall) -> ServiceResponse:
        address = call.data[ATTR_ADDRESS]
        user_id = call.data[ATTR_USER_ID]
        try:
            device = await _ensure_connected(address, user_id)
            if not hasattr(device, "enable_discharging_task"):
                return {"ok": False, "error": "Este dispositivo no soporta control de tareas de descarga"}
            if ATTR_ENABLE in call.data:
                await device.enable_discharging_task(call.data[ATTR_ENABLE])
            if ATTR_POWER_LIMIT_W in call.data:
                await device.set_discharging_power_limit(call.data[ATTR_POWER_LIMIT_W])
            return {"ok": True}
        except HomeAssistantError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            _LOGGER.exception("Fallo al mandar comando de descarga a %s", address)
            return {"ok": False, "error": str(e)}

    async def handle_disconnect(call: ServiceCall) -> ServiceResponse:
        address = call.data[ATTR_ADDRESS]
        device = devices.pop(address, None)
        if device is not None:
            await device.disconnect()
        return {"ok": True}

    hass.services.async_register(DOMAIN, SERVICE_DISCOVER, handle_discover, supports_response=SupportsResponse.ONLY)
    hass.services.async_register(
        DOMAIN, SERVICE_GET_STATE, handle_get_state,
        schema=GET_STATE_SCHEMA, supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_CHARGING_TASK, handle_set_charging_task,
        schema=SET_CHARGING_TASK_SCHEMA, supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_DISCHARGING_TASK, handle_set_discharging_task,
        schema=SET_DISCHARGING_TASK_SCHEMA, supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DISCONNECT, handle_disconnect,
        schema=DISCONNECT_SCHEMA, supports_response=SupportsResponse.OPTIONAL,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    entry_data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if entry_data:
        for device in entry_data["devices"].values():
            try:
                await device.disconnect()
            except Exception:
                _LOGGER.exception("Error al desconectar %s durante la descarga", device.address)

    if not hass.data.get(DOMAIN):
        for service in (
            SERVICE_DISCOVER, SERVICE_GET_STATE, SERVICE_SET_CHARGING_TASK,
            SERVICE_SET_DISCHARGING_TASK, SERVICE_DISCONNECT,
        ):
            hass.services.async_remove(DOMAIN, service)
        hass.data.pop(DOMAIN, None)

    return True
