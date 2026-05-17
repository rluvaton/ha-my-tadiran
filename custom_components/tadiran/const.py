"""Constants for the Tadiran AC integration."""
from __future__ import annotations

from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    HVACMode,
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_OFF,
    SWING_VERTICAL,
)

DOMAIN = "tadiran"

COGNITO_URL = "https://cognito-idp.eu-west-1.amazonaws.com/"
COGNITO_CLIENT_ID = "312eed498hlvku8pdup0lvfpir"

TADIRAN_BASE_URL = "https://api.tadiran-iot.co.il"

ORG_ID_IL = "tenant-f365f952-9143-4004-95b6-5042aed5b7cd"
ORG_ID_EU = "tenant-a978a082-5052-47ff-baa3-9514a14699cd"

CONF_PHONE = "phone"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_ORG_ID = "org_id"
CONF_SESSION = "session"

DEFAULT_SCAN_INTERVAL_SECONDS = 30

# Tadiran mode string <-> HA HVACMode
MODE_TO_HVAC: dict[str, HVACMode] = {
    "COOL": HVACMode.COOL,
    "HEAT": HVACMode.HEAT,
    "DRY": HVACMode.DRY,
    "FAN": HVACMode.FAN_ONLY,
    "AUTO": HVACMode.HEAT_COOL,
}
HVAC_TO_MODE: dict[HVACMode, str] = {v: k for k, v in MODE_TO_HVAC.items()}

# Tadiran wind_speed <-> HA fan mode
WIND_TO_FAN: dict[str, str] = {
    "LOW": FAN_LOW,
    "MEDIUM": FAN_MEDIUM,
    "HIGH": FAN_HIGH,
    "AUTO": FAN_AUTO,
}
FAN_TO_WIND: dict[str, str] = {v: k for k, v in WIND_TO_FAN.items()}

# HA swing modes
SWING_MODES = [SWING_OFF, SWING_VERTICAL, SWING_HORIZONTAL, SWING_BOTH]

TEMP_MIN = 16
TEMP_MAX = 30
