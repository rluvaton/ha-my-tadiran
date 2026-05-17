"""DataUpdateCoordinator for the Tadiran integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TadiranAPI, TadiranAPIError, TadiranAuthError
from .const import CONF_REFRESH_TOKEN, DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class TadiranCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Polls Tadiran for all devices; exposes them keyed by device_id."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: TadiranAPI,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
        )
        self.api = api
        self.entry = entry

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            devices = await self.api.get_devices()
        except TadiranAuthError as err:
            raise UpdateFailed(f"Auth failed: {err}") from err
        except TadiranAPIError as err:
            raise UpdateFailed(str(err)) from err

        # Persist a rotated refresh_token if Cognito gave us a new one.
        if self.api.refresh_token != self.entry.data.get(CONF_REFRESH_TOKEN):
            self.hass.config_entries.async_update_entry(
                self.entry,
                data={**self.entry.data, CONF_REFRESH_TOKEN: self.api.refresh_token},
            )

        return {d["device_id"]: d for d in devices}
