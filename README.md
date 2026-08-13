<h1 align="center">Battery Orchestrator — Puente BLE EcoFlow</h1>

<p align="center">
  Integración de Home Assistant, sin entidades ni configuración manual —
  solo servicios que <a href="https://github.com/neoalarrode/Battery-Orchestrator">Battery Orchestrator</a>
  llama por su cuenta para gestionar baterías EcoFlow directamente por
  Bluetooth (incluido a través de un ESPHome Bluetooth Proxy).
</p>

<p align="center">
  🇪🇸 Español · <a href="README.en.md">🇬🇧 Read in English</a>
</p>

---

⚠️ **Estado: v0.1.0, sin verificar contra hardware real todavía.** El
protocolo BLE de bajo nivel (`eflib/`) es una copia sin modificar de
[rabits/ha-ef-ble](https://github.com/rabits/ha-ef-ble) (Apache-2.0), ya
probado en producción por ese proyecto — pero la capa de servicios que
conecta eso con Battery Orchestrator es nueva y todavía no se ha probado
contra un dispositivo EcoFlow de verdad. Instálalo solo si vas a ayudar a
verificarlo.

## Qué hace

No tiene flujo de configuración con campos, ni entidades, ni sensores —
todo pasa por 5 **servicios** que Battery Orchestrator llama vía la API de
Home Assistant, con la misma filosofía que ya usa para descubrir zonas de
Climate Orchestrator: nunca sondea nada por su cuenta, solo responde
cuando se le pide.

- `battery_orchestrator_ecoflow_ble.discover` — dispositivos EcoFlow vistos por Bluetooth ahora mismo (sin conectar).
- `battery_orchestrator_ecoflow_ble.get_state` — SOC, potencia y estado de las tareas de carga/descarga de un dispositivo.
- `battery_orchestrator_ecoflow_ble.set_charging_task` / `set_discharging_task` — activar/desactivar, límite de potencia, SOC objetivo.
- `battery_orchestrator_ecoflow_ble.disconnect` — cierra la conexión BLE.

## Instalación

1. HACS → ⋮ → Repositorios personalizados → añade
   `https://github.com/neoalarrode/Battery-Orchestrator-EcoFlow-BLE` como tipo **Integración**.
2. Instala y reinicia Home Assistant.
3. **Ajustes → Dispositivos y servicios → Añadir integración** → busca
   "Battery Orchestrator - Puente BLE EcoFlow" → pulsa "Enviar" (no hay
   ningún campo que rellenar).
4. Configura tus baterías EcoFlow por BLE desde Battery Orchestrator, no
   desde aquí.

## El `userId` de tu cuenta EcoFlow

Los servicios de control necesitan el `userId` numérico de tu cuenta
EcoFlow (la de la app móvil) para el *pairing* — no es la contraseña, es
un identificador. Battery Orchestrator te pedirá que lo consigas una vez
(instalando temporalmente [rabits/ha-ef-ble](https://github.com/rabits/ha-ef-ble)
y copiando el `userId` de su configuración, por ejemplo) y lo guarda él
mismo para las siguientes veces.

## Licencia

© 2026 Eric Larrodé. Todos los derechos reservados — ver [LICENSE](LICENSE).
La carpeta `custom_components/battery_orchestrator_ecoflow_ble/eflib/` es
la excepción: copia sin modificar de `rabits/ha-ef-ble`, licencia Apache-2.0
(ver el aviso dentro de esa carpeta).
