"""
Flujo de configuracion — deliberadamente de UN SOLO PASO, sin ningun campo
que rellenar: toda la configuracion de verdad (que baterias, que user_id,
que hacer con cada una) vive en Battery Orchestrator, no aqui. Esto solo
existe para que Home Assistant tenga una entrada de configuracion desde la
que cargar la integracion y registrar los servicios — "instalar y pulsar
Enviar", nada mas.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class BatteryOrchestratorEcoflowBleConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        # Instancia unica: no tiene sentido tener dos puentes BLE a la vez.
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Battery Orchestrator — Puente BLE EcoFlow", data={})

        return self.async_show_form(step_id="user")
