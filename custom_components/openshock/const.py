"""Constants for the OpenShock integration."""

from __future__ import annotations

DOMAIN = "openshock"
PLATFORMS = ["button", "sensor", "number"]

CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"
CONF_POLL_INTERVAL = "poll_interval"

DEFAULT_BASE_URL = "https://api.openshock.app"
DEFAULT_POLL_INTERVAL = 15

DATA_COORDINATOR = "coordinator"
DATA_DEFAULTS = "defaults"

SERVICE_SEND_COMMAND = "send_command"
SERVICE_STOP_ALL = "stop_all"

ATTR_SHOCKER_ID = "shocker_id"
ATTR_COMMAND = "command"
ATTR_INTENSITY = "intensity"
ATTR_DURATION_MS = "duration_ms"

COMMAND_SHOCK = "shock"
COMMAND_VIBRATE = "vibrate"
COMMAND_SOUND = "sound"
COMMAND_STOP = "stop"
VALID_COMMANDS = [COMMAND_SHOCK, COMMAND_VIBRATE, COMMAND_SOUND, COMMAND_STOP]

DEFAULT_INTENSITY = 50
DEFAULT_DURATION_MS = 1000
