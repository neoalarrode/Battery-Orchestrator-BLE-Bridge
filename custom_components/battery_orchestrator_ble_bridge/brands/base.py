"""
Interfaz que tiene que cumplir CUALQUIER adaptador de marca — este puente
nunca habla el protocolo de un fabricante directamente, siempre a traves
de una clase que implemente estos 5 metodos. Sumar una marca nueva el dia
de manana es escribir una clase asi (con su propia libreria vendorizada
al lado, ver brands/ecoflow/) y darla de alta en `brands/__init__.py` —
nunca hace falta tocar `__init__.py` ni los servicios de HA que Battery
Orchestrator ya llama.

`credentials` es SIEMPRE un dict de forma libre — cada marca mete ahi lo
que necesite (EcoFlow: {"user_id": "..."}; una marca futura con otro
esquema de autenticacion usaria sus propias claves) sin que el puente en
si tenga que saber nada de su forma.

`device` es un objeto opaco para el puente: lo que devuelva
`ensure_connected` de una marca es exactamente lo que se le pasa de vuelta
a `get_state`/`set_charging_task`/`set_discharging_task`/`disconnect` de
esa MISMA marca — cada adaptador decide su propio tipo interno.
"""

from __future__ import annotations

from typing import Any, Protocol

from homeassistant.core import HomeAssistant


class BrandAdapter(Protocol):
    async def discover(self, hass: HomeAssistant) -> list[dict]:
        """Dispositivos de esta marca vistos por Bluetooth ahora mismo,
        sin conectar a ninguno — [{"address":, "sn":, "name":}, ...]."""
        ...

    async def ensure_connected(self, hass: HomeAssistant, address: str, credentials: dict) -> Any:
        """Conecta (o reutiliza la conexion ya abierta) y devuelve el
        objeto "device" de esta marca, ya autenticado. Lanza
        HomeAssistantError con un mensaje claro si no se puede."""
        ...

    def get_state(self, device: Any) -> dict:
        """Ultimo estado conocido de `device` — solo lo que ya se sabe,
        nunca fuerza una lectura nueva contra el dispositivo."""
        ...

    async def set_charging_task(
        self, device: Any, enable: bool | None, power_limit_w: float | None, target_soc: float | None,
    ) -> bool:
        """`False` (nunca una excepcion) si esta marca/modelo no soporta
        esto — quien llama decide que hacer con eso."""
        ...

    async def set_discharging_task(
        self, device: Any, enable: bool | None, power_limit_w: float | None,
    ) -> bool:
        ...

    async def disconnect(self, device: Any) -> None:
        ...
