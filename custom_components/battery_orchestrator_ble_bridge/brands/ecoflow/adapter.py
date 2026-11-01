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
    # Potencia que sale por los enchufes Schuko de ESTA unidad
    # (`pow_get_schuko1/2`, mapeados por eflib como `ac_power_1/2` segun el
    # modelo: Max solo el 1, Pro/Ultra/AC Pro los dos). `grid_power` es lo
    # que la unidad toma de red, enchufes incluidos: Battery Orchestrator los
    # resta para saber cuanto entra de verdad en la bateria.
    "ac_power_1",
    "ac_power_2",
    # Modo de medicion (smart_meter / semi_automated) y carga base que entrega
    # en semiautomatico -- ver set_energy_monitoring_mode/set_base_load.
    "energy_monitoring_mode",
    "base_load_power",
    "load_power_enabled",
    "feed_grid",
    "feed_grid_pow_limit",
    "charging_task_enabled",
    "charging_grid_power_limit",
    "charging_grid_target_soc",
    "discharging_task_enabled",
    "discharging_power_limit",
    # Especificaciones de ESTA bateria (no cambian de un ciclo a otro,
    # pero se leen igual que el resto del estado) -- para que Battery
    # Orchestrator pueda ofrecer autorrellenar capacidad y limites de
    # potencia al dar de alta la bateria, en vez de que el usuario tenga
    # que teclearlos a mano.
    "battery_full_energy_wh",
    "max_ac_in_power",
    "max_ac_out_power",
    "energy_backup_battery_level",
]


class EcoflowBrandAdapter:
    def __init__(self):
        self._devices: dict[str, eflib.DeviceBase] = {}
        # Un candado por equipo para conectar. BUG REAL (1-nov, STREAM Ultra X):
        # dos llamadas a la vez (Battery Orchestrator lee cada 10 s, su ciclo
        # manda ordenes cada 30 s) y la segunda veia la conexion de la primera
        # A MEDIO AUTENTICAR, la tomaba por rota y la cortaba ("conexion a
        # medias -- forzando desconexion"): 29 cortes provocados en 12 min, y las
        # ordenes que iban por ella se perdian o llegaban decenas de segundos
        # tarde.
        self._connect_locks: dict[str, asyncio.Lock] = {}

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
        lock = self._connect_locks.setdefault(address, asyncio.Lock())
        async with lock:
            return await self._ensure_connected_locked(hass, address, credentials)

    async def _ensure_connected_locked(self, hass: HomeAssistant, address: str, credentials: dict) -> eflib.DeviceBase:
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
            # BUG REAL, CONFIRMADO EN PRODUCCION: `device` sobrevive en
            # `self._devices` mientras HA Core siga vivo (este adaptador
            # es un singleton de la propia integracion) -- un reinicio del
            # ADDON que llama a este servicio (Battery Orchestrator) NO
            # reinicia HA Core, asi que si esa peticion se corto a medias
            # (el addon murio mientras `device.connect()` seguia
            # esperando), el objeto `Connection` interno de `device` se
            # queda a medio negociar para siempre — `connect()` (ver
            # devicebase.py) solo crea una `Connection` nueva si
            # `self._conn is None`, asi que el SIGUIENTE intento reutiliza
            # ese mismo objeto roto y se cuelga otra vez, indefinidamente,
            # hasta reiniciar la maquina entera (que si reinicia HA Core y
            # limpia el singleton). Sintoma real: "No se pudo conectar con
            # <address> en 25s" en CADA intento tras un reinicio del addon,
            # resuelto solo con un reinicio completo del host.
            #
            # Arreglo: si no esta conectado de verdad pero SI quedo un
            # intento de conexion a medias (`connection_state is not
            # None`), forzar un disconnect limpio primero -- eso pone
            # `self._conn = None` (ver disconnect() en devicebase.py), asi
            # que el siguiente connect() de mas abajo crea una Connection
            # fresca en vez de reutilizar la rota.
            if device.connection_state is not None and not device.is_connected:
                _LOGGER.warning(
                    "%s tenia una conexion a medias de un intento anterior — forzando "
                    "desconexion antes de reconectar, en vez de reutilizarla",
                    address,
                )
                try:
                    await device.disconnect()
                except Exception:
                    _LOGGER.debug("Fallo desconectando %s antes de reconectar (se ignora, se reconecta igual)", address, exc_info=True)
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
        mode = state.get("energy_monitoring_mode")
        if mode is not None and hasattr(mode, "state_name"):
            state["energy_monitoring_mode"] = mode.state_name
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

    async def set_backup_reserve(self, device: eflib.DeviceBase, pct: float) -> bool:
        if not hasattr(device, "set_energy_backup_battery_level"):
            return False
        await device.set_energy_backup_battery_level(pct)
        return True

    async def set_feed_grid(self, device: eflib.DeviceBase, enable: bool) -> bool:
        if not hasattr(device, "enable_feed_grid"):
            return False
        await device.enable_feed_grid(enable)
        return True

    async def set_outlet(self, device: eflib.DeviceBase, outlet: int, enable: bool) -> bool:
        # Solo el STREAM AC Pro tiene dos salidas AC independientes -- el
        # resto de modelos no expone `enable_ac_1`/`enable_ac_2` en absoluto.
        method_name = f"enable_ac_{outlet}"
        if not hasattr(device, method_name):
            return False
        await getattr(device, method_name)(enable)
        return True

    async def set_grid_import_limit(self, device: eflib.DeviceBase, watts: float) -> bool:
        if not hasattr(device, "set_grid_in_pow_limit"):
            return False
        await device.set_grid_in_pow_limit(watts)
        return True

    async def set_energy_monitoring_mode(self, device: eflib.DeviceBase, mode: str) -> bool:
        """`smart_meter` (sigue al contador vinculado en la app) o
        `semi_automated` (entrega la carga base fijada)."""
        if not hasattr(device, "set_energy_monitoring_mode"):
            return False
        enum_cls = type(getattr(device, "energy_monitoring_mode", None))
        modes = {"smart_meter": "SMART_METER", "semi_automated": "SEMI_AUTOMATED"}
        if mode not in modes or not hasattr(enum_cls, modes[mode]):
            return False
        await device.set_energy_monitoring_mode(getattr(enum_cls, modes[mode]))
        return True

    async def set_base_load(self, device: eflib.DeviceBase, watts: float) -> bool:
        """Carga base del modo semiautomatico. eflib solo la cambia si el equipo
        ya tiene una franja de carga base (`set_load_power` conserva su horario);
        recien restablecido no tiene ninguna, asi que se crea una de todo el dia
        con el mismo mensaje que usa eflib."""
        if not hasattr(device, "set_load_power"):
            return False
        watts = max(0, int(round(watts)))
        if getattr(device, "load_power_enabled", False):
            return bool(await device.set_load_power(watts))
        from .eflib.pb import bk_series_pb2
        await device._send_config_packet(
            bk_series_pb2.ConfigWrite(
                cfg_day_resident_load_list=bk_series_pb2.DayResidentLoadList(
                    load=[bk_series_pb2.ResidentLoad(load_power=watts, start_min=0, end_min=1440)]
                )
            )
        )
        return True

    async def disconnect(self, device: eflib.DeviceBase) -> None:
        await device.disconnect()
        self._devices = {addr: d for addr, d in self._devices.items() if d is not device}
