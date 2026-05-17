"""The Tadiran AC integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TadiranAPI, TadiranAPIError, TadiranAuthError
from .const import CONF_ORG_ID, CONF_REFRESH_TOKEN, DOMAIN
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

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
