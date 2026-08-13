# Changelog

## 0.1.0 — sin verificar
Primera versión: 5 servicios (`discover`, `get_state`, `set_charging_task`, `set_discharging_task`, `disconnect`), sin flujo de configuración con campos ni entidades — todo se dispara desde Battery Orchestrator.

- `custom_components/battery_orchestrator_ecoflow_ble/eflib/`: copia sin modificar de la librería `eflib` de [rabits/ha-ef-ble](https://github.com/rabits/ha-ef-ble) (Apache-2.0) — conexión, cifrado/*pairing*, framing de paquetes y modelos de dispositivo, código ya probado en producción por ese proyecto.
- `__init__.py`/`config_flow.py`/`const.py`: capa nueva de orquestación (conexión persistente por dispositivo, servicios) — **esta parte SÍ es nueva y todavía no se ha probado contra un dispositivo EcoFlow real.**

**Pendiente de verificar**: descubrimiento por BLE (incluido a través de un ESPHome Bluetooth Proxy), *pairing*/autenticación con el `userId` de la cuenta, lectura de estado, y los comandos de control de las tareas de carga/descarga.
