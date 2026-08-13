# Changelog

## 0.2.1
`get_state` ahora incluye `pv_power`: la potencia solar que la propia batería recibe por sus puertos MPPT integrados (paneles cableados directo a la batería, sin pasar por AC) — muchos STREAM (Max, Ultra, Pro, AC Pro, Microinverter...) los tienen, con nombres de campo distintos según el modelo en `eflib`; se resuelve solo con lo que ese modelo concreto reporte, `None` si no tiene ningún puerto MPPT.

## 0.2.0 — sin verificar
Reestructuración pedida para que el puente sea genérico de verdad, no solo por dentro: dominio renombrado de `battery_orchestrator_ecoflow_ble` a **`battery_orchestrator_ble_bridge`**, y los 5 servicios ahora llevan un campo `brand` (por ahora solo `"ecoflow"`) y un objeto `credentials` de forma libre en vez de un `user_id` fijo pensado solo para EcoFlow.
- Nueva carpeta `brands/` con una interfaz común (`brands/base.py`) y un adaptador por marca — `brands/ecoflow/adapter.py` es hoy la ÚNICA pieza que sabe de EcoFlow por su nombre, con `eflib/` (Apache-2.0, sin modificar) vendorizada justo al lado.
- Sumar una marca nueva a partir de ahora: escribir su adaptador + vendorizar su librería en `brands/<marca>/`, darlo de alta en `brands/__init__.py` — un update de este puente y un update de Battery Orchestrator bastan, sin repositorio nuevo.
- **Repositorio renombrado** de `Battery-Orchestrator-EcoFlow-BLE` a `Battery-Orchestrator-BLE-Bridge` para que el nombre no ate el puente a una sola marca.

## 0.1.0 — sin verificar
Primera versión: 5 servicios (`discover`, `get_state`, `set_charging_task`, `set_discharging_task`, `disconnect`), sin flujo de configuración con campos ni entidades — todo se dispara desde Battery Orchestrator.

- `custom_components/battery_orchestrator_ecoflow_ble/eflib/`: copia sin modificar de la librería `eflib` de [rabits/ha-ef-ble](https://github.com/rabits/ha-ef-ble) (Apache-2.0) — conexión, cifrado/*pairing*, framing de paquetes y modelos de dispositivo, código ya probado en producción por ese proyecto.
- `__init__.py`/`config_flow.py`/`const.py`: capa nueva de orquestación (conexión persistente por dispositivo, servicios) — **esta parte SÍ es nueva y todavía no se ha probado contra un dispositivo EcoFlow real.**

**Pendiente de verificar**: descubrimiento por BLE (incluido a través de un ESPHome Bluetooth Proxy), *pairing*/autenticación con el `userId` de la cuenta, lectura de estado, y los comandos de control de las tareas de carga/descarga.
