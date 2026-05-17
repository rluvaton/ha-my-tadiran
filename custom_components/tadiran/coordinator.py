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

# The Tadiran API serializes some booleans as real JSON bool and others as
# the strings "true"/"false". Coerce these fields at ingestion so downstream
# code can assume Python bool.
_BOOL_FIELDS = frozenset(
    {"power", "online", "light", "turbo", "mute", "swing_ud", "swing_lr"}
)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return bool(value)


def _normalize_configurations(cfg: dict[str, Any]) -> dict[str, Any]:
    out = dict(cfg)
    for field in _BOOL_FIELDS:
        if field in out:
            out[field] = _coerce_bool(out[field])
    return out


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

        result: dict[str, dict[str, Any]] = {}
        for device in devices:
            normalized = dict(device)
            if "configurations" in normalized:
                normalized["configurations"] = _normalize_configurations(
                    normalized["configurations"]
                )
            result[device["device_id"]] = normalized
        return result
