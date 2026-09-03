"""Constantes del puente BLE generico para Battery Orchestrator."""

DOMAIN = "battery_orchestrator_ble_bridge"

SERVICE_DISCOVER = "discover"
SERVICE_GET_STATE = "get_state"
SERVICE_SET_CHARGING_TASK = "set_charging_task"
SERVICE_SET_DISCHARGING_TASK = "set_discharging_task"
SERVICE_DISCONNECT = "disconnect"
# Cuatro controles adicionales (reserva de emergencia, vertido a red,
# salidas AC, limite de importacion de red) -- mismo patron que los dos
# de carga/descarga de arriba, ver Battery Orchestrator (ecoflow_ble.py).
SERVICE_SET_BACKUP_RESERVE = "set_backup_reserve"
SERVICE_SET_FEED_GRID = "set_feed_grid"
SERVICE_SET_OUTLET = "set_outlet"
SERVICE_SET_GRID_IMPORT_LIMIT = "set_grid_import_limit"

ATTR_BRAND = "brand"
ATTR_ADDRESS = "address"
ATTR_CREDENTIALS = "credentials"
ATTR_ENABLE = "enable"
ATTR_POWER_LIMIT_W = "power_limit_w"
ATTR_TARGET_SOC = "target_soc"
ATTR_PCT = "pct"
ATTR_OUTLET = "outlet"
ATTR_WATTS = "watts"

# Marca por defecto cuando la llamada no la indica — hoy es la unica que
# existe, pero el campo "brand" ya esta en todos los servicios desde el
# principio para que sumar la siguiente marca sea "escribir su adaptador
# y darlo de alta en brands/__init__.py", nunca cambiar la forma de los
# servicios que Battery Orchestrator ya llama.
DEFAULT_BRAND = "ecoflow"

# Cuanto esperar a que la conexion termine el handshake de autenticacion
# antes de rendirse — el pairing BLE + intercambio de claves puede tardar
# unos segundos de verdad, sobre todo a traves de un ESPHome BT Proxy (un
# salto de red de mas frente a un adaptador local).
CONNECT_TIMEOUT_SECONDS = 25

# Cuanto esperar, tras ya estar conectado y autenticado, a que llegue AL
# MENOS un dato de estado antes de devolver "sin datos todavia" en vez de
# esperar para siempre — el dispositivo manda sus heartbeats por su cuenta,
# no se piden a demanda.
FIRST_DATA_TIMEOUT_SECONDS = 8
