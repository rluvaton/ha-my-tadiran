"""The Tadiran AC integration."""
from __future__ import annotations

import logging

from homeassistant.components.persistent_notification import (
    async_create as async_create_notification,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TadiranAPI, TadiranAPIError, TadiranAuthError
from .const import CONF_ORG_ID, CONF_REFRESH_TOKEN, DOMAIN, KNOWN_TESTED_MODELS
from .coordinator import TadiranCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CLIMATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tadiran from a config entry."""
    session = async_get_clientsession(hass)
    api = TadiranAPI(session)
    api.refresh_token = entry.data[CONF_REFRESH_TOKEN]
    api.org_id = entry.data.get(CONF_ORG_ID)

    try:
        await api.refresh()
    except TadiranAuthError as err:
        raise ConfigEntryAuthFailed(f"Token refresh failed: {err}") from err
    except TadiranAPIError as err:
        raise ConfigEntryNotReady(f"Cognito unreachable: {err}") from err

    coordinator = TadiranCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    _warn_on_untested_models(hass, coordinator.data)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _warn_on_untested_models(
    hass: HomeAssistant, devices: dict[str, dict]
) -> None:
    """Notify the user about any AC whose model hasn't been verified."""
    for device_id, device in devices.items():
        model_id = device.get("model_id") or ""
        if not model_id or model_id in KNOWN_TESTED_MODELS:
            continue
        name = device.get("name") or device_id
        description = device.get("description") or "unknown"
        _LOGGER.warning(
            "Tadiran AC '%s' reports untested model_id=%s (%s). "
            "Please open an issue at "
            "https://github.com/rluvaton/ha-my-tadiran/issues",
            name,
            model_id,
            description,
        )
        async_create_notification(
            hass,
            (
                f"The Tadiran AC **{name}** reports model "
                f"`{model_id}` ({description}). "
                "This integration has only been verified against a "
                "Ducted Inverter AC; some controls may misbehave on "
                "other models.\n\n"
                "Please [open an issue]"
                "(https://github.com/rluvaton/ha-my-tadiran/issues) "
                "with the model details so support can be extended."
            ),
            title="Tadiran AC: untested model",
            notification_id=f"tadiran_untested_model_{model_id}",
        )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
