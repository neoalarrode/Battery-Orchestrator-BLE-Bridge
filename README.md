<h1 align="center">Battery Orchestrator — Puente BLE</h1>

<p align="center">
  Integración de Home Assistant, sin entidades ni configuración manual —
  solo servicios genéricos (con un campo "marca") que
  <a href="https://github.com/neoalarrode/Battery-Orchestrator">Battery Orchestrator</a>
  llama por su cuenta para gestionar baterías directamente por Bluetooth
  (incluido a través de un ESPHome Bluetooth Proxy).
</p>

<p align="center">
  🇪🇸 Español · <a href="README.en.md">🇬🇧 Read in English</a>
</p>

---

⚠️ **Estado: v0.2.0, sin verificar contra hardware real todavía.**

## Diseñado para más de una marca desde el principio

Los 5 servicios de este puente son genéricos — llevan un campo `brand`
("ecoflow" por ahora, la única marca soportada) y un objeto `credentials`
de forma libre, no un `user_id` fijo pensado solo para EcoFlow. Por dentro,
cada marca es un **adaptador** aislado en su propia carpeta
(`brands/<marca>/`) que implementa 5 métodos comunes
(`discover`/`ensure_connected`/`get_state`/`set_charging_task`/`set_discharging_task`).

Sumar una marca nueva el día de mañana es: escribir su adaptador (con su
propia librería de protocolo al lado, vendorizada igual que `eflib/` para
EcoFlow) y darlo de alta en `brands/__init__.py` — **un update de este
puente y un update de Battery Orchestrator bastan**, sin repositorio
nuevo ni reinstalar nada distinto en Home Assistant.

La marca EcoFlow (`brands/ecoflow/`) usa `eflib/`, una copia sin modificar
de [rabits/ha-ef-ble](https://github.com/rabits/ha-ef-ble) (Apache-2.0) —
la conexión, el cifrado/*pairing* y el framing de paquetes ya están
probados en producción por ese proyecto; lo nuevo aquí es solo el
adaptador que los conecta con el patrón genérico de arriba, y **esa parte
todavía no se ha probado contra un dispositivo real**.

## Qué hace

- `battery_orchestrator_ble_bridge.discover` — dispositivos de una marca vistos por Bluetooth ahora mismo (sin conectar).
- `battery_orchestrator_ble_bridge.get_state` — SOC, potencia y estado de las tareas de carga/descarga de un dispositivo.
- `battery_orchestrator_ble_bridge.set_charging_task` / `set_discharging_task` — activar/desactivar, límite de potencia, SOC objetivo.
- `battery_orchestrator_ble_bridge.disconnect` — cierra la conexión BLE.

## Instalación

1. HACS → ⋮ → Repositorios personalizados → añade
   `https://github.com/neoalarrode/Battery-Orchestrator-BLE-Bridge` como tipo **Integración**.
2. Instala y reinicia Home Assistant.
3. **Ajustes → Dispositivos y servicios → Añadir integración** → busca
   "Battery Orchestrator - Puente BLE" → pulsa "Enviar" (no hay ningún
   campo que rellenar).
4. Configura tus baterías por BLE desde Battery Orchestrator, no desde aquí.

## Las credenciales de EcoFlow

Los servicios de control de EcoFlow necesitan `{"user_id": "..."}` en
`credentials` — el `userId` numérico de tu cuenta EcoFlow (la de la app
móvil), no la contraseña. Battery Orchestrator te pedirá que lo consigas
una vez (instalando temporalmente
[rabits/ha-ef-ble](https://github.com/rabits/ha-ef-ble) y copiando el
`userId` de su configuración, por ejemplo) y lo guarda él mismo para las
siguientes veces.

## Licencia

© 2026 Eric Larrodé. Todos los derechos reservados — ver [LICENSE](LICENSE).
La carpeta `custom_components/battery_orchestrator_ble_bridge/brands/ecoflow/eflib/`
es la excepción: copia sin modificar de `rabits/ha-ef-ble`, licencia
Apache-2.0 (ver el aviso dentro de esa carpeta).
