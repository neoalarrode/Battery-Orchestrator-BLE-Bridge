# Procedencia de este directorio

Todo el contenido de `eflib/` (excepto este archivo) es una copia **verbatim**,
sin modificar, de la librería `eflib` del proyecto
[rabits/ha-ef-ble](https://github.com/rabits/ha-ef-ble), publicada bajo
licencia **Apache License 2.0** (copia completa en `LICENSE` en este mismo
directorio).

Es la capa de protocolo BLE de bajo nivel (conexión, cifrado, *pairing*,
framing de paquetes, y las claves de cifrado específicas por modelo de
dispositivo) — código ya probado y en uso real, no reimplementado desde cero
aquí. `battery_orchestrator_ecoflow_ble` construye únicamente la capa de
servicios de arriba (fuera de este directorio); no se ha modificado ni una
línea dentro de `eflib/`.

Copyright de esta librería: ver cabeceras de cada archivo y `LICENSE` — no
del autor de `battery_orchestrator_ecoflow_ble`.

Para actualizar esta copia a una versión más reciente de `ha-ef-ble`, basta
con sustituir este directorio entero por el `eflib/` correspondiente de esa
versión — no depende de ningún cambio local.
