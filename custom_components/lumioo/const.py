"""Constants for the Lumioo integration."""

DOMAIN = "lumioo"

DEFAULT_NAME = "Lumioo"

DATA = "data"
COORDINATOR_PLANT = "coordinator_plant"
COORDINATOR_SOLAR = "coordinator_solar"
COORDINATOR_TRACKERS = "coordinator_trackers"
COORDINATOR_METER = "coordinator_meter"
UPDATE_LISTENER = "update_listener"

SIGNAL_LUMIOO_UPDATE_RECEIVED = "lumioo_update_received_{}_{}_{}"

DEBOUNCE_COOLDOWN = 1800  # Seconds

DEVICE_TYPES = {
    "plant": "Plant",
    "solar": "Solar forecast",
    "trackers": "Tracker",
    "meter": "Meter",
}
