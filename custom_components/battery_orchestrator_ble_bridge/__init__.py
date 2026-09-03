"""
Puente BLE GENERICO para Battery Orchestrator.

Sin flujo de configuracion real (ver config_flow.py) y sin entidades: todo
se dispara mediante SERVICIOS que Battery Orchestrator llama por su
cuenta via la API de Home Assistant — mismo patron que ya usa con
Climate Orchestrator (descubrimiento por boton, nunca sondeo de fondo).

"Generico" de verdad: los 5 servicios de aqui abajo llevan un campo
"brand" — hoy solo existe el adaptador "ecoflow" (ver brands/), pero
sumar una marca nueva el dia de manana es escribir su propio adaptador y
darlo de alta en `brands/__init__.py`, sin tocar ESTE archivo ni la forma
de los servicios que Battery Orchestrator ya sabe llamar — un update de
este puente y un update de Battery Orchestrator bastan, sin repositorios
nuevos ni reinstalar nada distinto en Home Assistant.
"""

from __future__ import annotations

import asyncio
import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .brands import BRANDS
from .const import (
    ATTR_ADDRESS,
    ATTR_BRAND,
    ATTR_CREDENTIALS,
    ATTR_ENABLE,
    ATTR_OUTLET,
    ATTR_PCT,
    ATTR_POWER_LIMIT_W,
    ATTR_TARGET_SOC,
    ATTR_WATTS,
    DEFAULT_BRAND,
    DOMAIN,
    FIRST_DATA_TIMEOUT_SECONDS,
    SERVICE_DISCONNECT,
    SERVICE_DISCOVER,
    SERVICE_GET_STATE,
    SERVICE_SET_BACKUP_RESERVE,
    SERVICE_SET_CHARGING_TASK,
    SERVICE_SET_DISCHARGING_TASK,
    SERVICE_SET_FEED_GRID,
    SERVICE_SET_GRID_IMPORT_LIMIT,
    SERVICE_SET_OUTLET,
)

_LOGGER = logging.getLogger(__name__)

_BRAND_FIELD = {vol.Optional(ATTR_BRAND, default=DEFAULT_BRAND): vol.In(BRANDS.keys())}
_ADDRESS_SCHEMA = {**_BRAND_FIELD, vol.Required(ATTR_ADDRESS): cv.string}
_AUTH_SCHEMA = {**_ADDRESS_SCHEMA, vol.Required(ATTR_CREDENTIALS): dict}

DISCOVER_SCHEMA = vol.Schema(_BRAND_FIELD)
GET_STATE_SCHEMA = vol.Schema(_AUTH_SCHEMA)
DISCONNECT_SCHEMA = vol.Schema({**_ADDRESS_SCHEMA, vol.Optional(ATTR_CREDENTIALS): dict})
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
SET_BACKUP_RESERVE_SCHEMA = vol.Schema({**_AUTH_SCHEMA, vol.Required(ATTR_PCT): vol.Coerce(float)})
SET_FEED_GRID_SCHEMA = vol.Schema({**_AUTH_SCHEMA, vol.Required(ATTR_ENABLE): cv.boolean})
SET_OUTLET_SCHEMA = vol.Schema({
    **_AUTH_SCHEMA,
    vol.Required(ATTR_OUTLET): vol.In([1, 2]),
    vol.Required(ATTR_ENABLE): cv.boolean,
})
SET_GRID_IMPORT_LIMIT_SCHEMA = vol.Schema({**_AUTH_SCHEMA, vol.Required(ATTR_WATTS): vol.Coerce(float)})


def _get_adapter(brand: str):
    adapter = BRANDS.get(brand)
    if adapter is None:
        raise HomeAssistantError(f"Marca \"{brand}\" no reconocida por este puente")
    return adapter


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    async def handle_discover(call: ServiceCall) -> ServiceResponse:
        adapter = _get_adapter(call.data.get(ATTR_BRAND, DEFAULT_BRAND))
        devices = await adapter.discover(hass)
        return {"devices": devices, "count": len(devices)}

    async def handle_get_state(call: ServiceCall) -> ServiceResponse:
        adapter = _get_adapter(call.data.get(ATTR_BRAND, DEFAULT_BRAND))
        address = call.data[ATTR_ADDRESS]
        credentials = call.data[ATTR_CREDENTIALS]
        device = await adapter.ensure_connected(hass, address, credentials)
        state = adapter.get_state(device)
        if not any(v is not None for v in state.values()):
            # Conexion recien abierta y todavia sin ningun heartbeat -
            # nadie "pide" el estado a demanda, solo se recibe lo que el
            # propio equipo manda por su cuenta, asi que se da un respiro
            # antes de rendirse con "sin datos".
            await asyncio.sleep(FIRST_DATA_TIMEOUT_SECONDS)
            state = adapter.get_state(device)
        state[ATTR_ADDRESS] = address
        return state

    async def handle_set_charging_task(call: ServiceCall) -> ServiceResponse:
        adapter = _get_adapter(call.data.get(ATTR_BRAND, DEFAULT_BRAND))
        address = call.data[ATTR_ADDRESS]
        credentials = call.data[ATTR_CREDENTIALS]
        try:
            device = await adapter.ensure_connected(hass, address, credentials)
            ok = await adapter.set_charging_task(
                device,
                enable=call.data.get(ATTR_ENABLE),
                power_limit_w=call.data.get(ATTR_POWER_LIMIT_W),
                target_soc=call.data.get(ATTR_TARGET_SOC),
            )
            if not ok:
                return {"ok": False, "error": "Esta marca/modelo no soporta control de tareas de carga"}
            return {"ok": True}
        except HomeAssistantError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            _LOGGER.exception("Fallo al mandar comando de carga a %s", address)
            return {"ok": False, "error": str(e)}

    async def handle_set_discharging_task(call: ServiceCall) -> ServiceResponse:
        adapter = _get_adapter(call.data.get(ATTR_BRAND, DEFAULT_BRAND))
        address = call.data[ATTR_ADDRESS]
        credentials = call.data[ATTR_CREDENTIALS]
        try:
            device = await adapter.ensure_connected(hass, address, credentials)
            ok = await adapter.set_discharging_task(
                device,
                enable=call.data.get(ATTR_ENABLE),
                power_limit_w=call.data.get(ATTR_POWER_LIMIT_W),
            )
            if not ok:
                return {"ok": False, "error": "Esta marca/modelo no soporta control de tareas de descarga"}
            return {"ok": True}
        except HomeAssistantError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            _LOGGER.exception("Fallo al mandar comando de descarga a %s", address)
            return {"ok": False, "error": str(e)}

    async def handle_set_backup_reserve(call: ServiceCall) -> ServiceResponse:
        adapter = _get_adapter(call.data.get(ATTR_BRAND, DEFAULT_BRAND))
        address = call.data[ATTR_ADDRESS]
        credentials = call.data[ATTR_CREDENTIALS]
        try:
            device = await adapter.ensure_connected(hass, address, credentials)
            ok = await adapter.set_backup_reserve(device, call.data[ATTR_PCT])
            if not ok:
                return {"ok": False, "error": "Esta marca/modelo no soporta reserva de emergencia"}
            return {"ok": True}
        except HomeAssistantError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            _LOGGER.exception("Fallo al mandar reserva de emergencia a %s", address)
            return {"ok": False, "error": str(e)}

    async def handle_set_feed_grid(call: ServiceCall) -> ServiceResponse:
        adapter = _get_adapter(call.data.get(ATTR_BRAND, DEFAULT_BRAND))
        address = call.data[ATTR_ADDRESS]
        credentials = call.data[ATTR_CREDENTIALS]
        try:
            device = await adapter.ensure_connected(hass, address, credentials)
            ok = await adapter.set_feed_grid(device, call.data[ATTR_ENABLE])
            if not ok:
                return {"ok": False, "error": "Esta marca/modelo no soporta vertido a red"}
            return {"ok": True}
        except HomeAssistantError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            _LOGGER.exception("Fallo al mandar vertido a red a %s", address)
            return {"ok": False, "error": str(e)}

    async def handle_set_outlet(call: ServiceCall) -> ServiceResponse:
        adapter = _get_adapter(call.data.get(ATTR_BRAND, DEFAULT_BRAND))
        address = call.data[ATTR_ADDRESS]
        credentials = call.data[ATTR_CREDENTIALS]
        try:
            device = await adapter.ensure_connected(hass, address, credentials)
            ok = await adapter.set_outlet(device, call.data[ATTR_OUTLET], call.data[ATTR_ENABLE])
            if not ok:
                return {"ok": False, "error": "Esta marca/modelo no soporta esta salida AC"}
            return {"ok": True}
        except HomeAssistantError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            _LOGGER.exception("Fallo al mandar salida AC a %s", address)
            return {"ok": False, "error": str(e)}

    async def handle_set_grid_import_limit(call: ServiceCall) -> ServiceResponse:
        adapter = _get_adapter(call.data.get(ATTR_BRAND, DEFAULT_BRAND))
        address = call.data[ATTR_ADDRESS]
        credentials = call.data[ATTR_CREDENTIALS]
        try:
            device = await adapter.ensure_connected(hass, address, credentials)
            ok = await adapter.set_grid_import_limit(device, call.data[ATTR_WATTS])
            if not ok:
                return {"ok": False, "error": "Esta marca/modelo no soporta limite de importacion de red"}
            return {"ok": True}
        except HomeAssistantError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            _LOGGER.exception("Fallo al mandar limite de importacion de red a %s", address)
            return {"ok": False, "error": str(e)}

    async def handle_disconnect(call: ServiceCall) -> ServiceResponse:
        adapter = _get_adapter(call.data.get(ATTR_BRAND, DEFAULT_BRAND))
        # No hay forma generica de "esta ya conectado" sin conectar, asi
        # que solo se desconecta si el adaptador ya tenia algo abierto —
        # cada adaptador decide eso puertas adentro; si no habia nada,
        # simplemente no hace nada.
        try:
            device = await adapter.ensure_connected(hass, call.data[ATTR_ADDRESS], call.data.get(ATTR_CREDENTIALS) or {})
            await adapter.disconnect(device)
        except HomeAssistantError:
            pass
        return {"ok": True}

    hass.services.async_register(DOMAIN, SERVICE_DISCOVER, handle_discover, schema=DISCOVER_SCHEMA, supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, SERVICE_GET_STATE, handle_get_state, schema=GET_STATE_SCHEMA, supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, SERVICE_SET_CHARGING_TASK, handle_set_charging_task, schema=SET_CHARGING_TASK_SCHEMA, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_SET_DISCHARGING_TASK, handle_set_discharging_task, schema=SET_DISCHARGING_TASK_SCHEMA, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_SET_BACKUP_RESERVE, handle_set_backup_reserve, schema=SET_BACKUP_RESERVE_SCHEMA, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_SET_FEED_GRID, handle_set_feed_grid, schema=SET_FEED_GRID_SCHEMA, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_SET_OUTLET, handle_set_outlet, schema=SET_OUTLET_SCHEMA, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_SET_GRID_IMPORT_LIMIT, handle_set_grid_import_limit, schema=SET_GRID_IMPORT_LIMIT_SCHEMA, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_DISCONNECT, handle_disconnect, schema=DISCONNECT_SCHEMA, supports_response=SupportsResponse.OPTIONAL)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    for service in (
        SERVICE_DISCOVER, SERVICE_GET_STATE, SERVICE_SET_CHARGING_TASK,
        SERVICE_SET_DISCHARGING_TASK, SERVICE_SET_BACKUP_RESERVE,
        SERVICE_SET_FEED_GRID, SERVICE_SET_OUTLET, SERVICE_SET_GRID_IMPORT_LIMIT,
        SERVICE_DISCONNECT,
    ):
        hass.services.async_remove(DOMAIN, service)
    return True
