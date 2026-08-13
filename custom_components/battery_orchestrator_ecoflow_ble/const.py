"""Constantes del puente BLE de EcoFlow para Battery Orchestrator."""

DOMAIN = "battery_orchestrator_ecoflow_ble"

SERVICE_DISCOVER = "discover"
SERVICE_GET_STATE = "get_state"
SERVICE_SET_CHARGING_TASK = "set_charging_task"
SERVICE_SET_DISCHARGING_TASK = "set_discharging_task"
SERVICE_DISCONNECT = "disconnect"

ATTR_ADDRESS = "address"
ATTR_USER_ID = "user_id"
ATTR_ENABLE = "enable"
ATTR_POWER_LIMIT_W = "power_limit_w"
ATTR_TARGET_SOC = "target_soc"

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
