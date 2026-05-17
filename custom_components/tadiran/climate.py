"""Tadiran AC climate platform."""
from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    FAN_TO_WIND,
    HVAC_TO_MODE,
    MODE_TO_HVAC,
    TEMP_MAX,
    TEMP_MIN,
    WIND_TO_FAN,
)
from .coordinator import TadiranCoordinator

# After a command, mask polled state that disagrees with what we just sent
# for this many *consecutive* polls. Anchored to poll boundaries (rather than
# wall-clock seconds) so transitions only happen when fresh data arrives,
# avoiding mid-window dead zones where the UI flips to a stale polled value.
# With the default 30s poll interval, 3 = up to ~90s of cloud-shadow lag.
_PENDING_MAX_DISAGREEMENTS = 3

# When the user changes multiple controls in HA in quick succession (e.g.
# temp + fan together), each fires a separate service call. Coalesce all
# changes that arrive within this window into a single PUT — the Tadiran
# cloud can lose one of two PUTs sent back-to-back, but accepts a single
# multi-item body atomically.
_BATCH_WINDOW_SECONDS = 0.2


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TadiranCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        TadiranClimate(coordinator, device_id) for device_id in coordinator.data
    )


def _normalize_temp(value: Any) -> float | None:
    """Tadiran sometimes returns int Celsius, sometimes tenths-of-degree.
    Range -200..600 in the schema is tenths; observed live values are degrees.
    Treat |value|>60 as tenths."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if abs(v) > 60:
        return v / 10
    return v


class TadiranClimate(CoordinatorEntity[TadiranCoordinator], ClimateEntity):
    """A single Tadiran AC."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = TEMP_MIN
    _attr_max_temp = TEMP_MAX
    _attr_target_temperature_step = 1
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
        HVACMode.HEAT_COOL,
    ]
    _attr_fan_modes = list(WIND_TO_FAN.values())
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: TadiranCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = device_id
        # field name -> (commanded value, number of polls the cloud has
        # disagreed with us). Cleared when cloud agrees or count exceeds
        # _PENDING_MAX_DISAGREEMENTS.
        self._pending: dict[str, tuple[Any, int]] = {}
        # Accumulator for the debounced batch PUT.
        self._batch_buffer: dict[str, Any] = {}
        self._batch_task: asyncio.Task | None = None

        dev = self._device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=dev.get("name") or "Tadiran AC",
            manufacturer="Tadiran",
            model=dev.get("description") or dev.get("model_id"),
        )

    @property
    def _device(self) -> dict[str, Any]:
        return self.coordinator.data.get(self._device_id, {})

    @property
    def _config(self) -> dict[str, Any]:
        base = self._device.get("configurations", {}) or {}
        if not self._pending:
            return base
        merged = dict(base)
        for key, (value, _count) in self._pending.items():
            merged[key] = value
        return merged

    @property
    def available(self) -> bool:
        if not super().available or not self._device:
            return False
        return bool(self._config.get("online", True))

    @property
    def current_temperature(self) -> float | None:
        return _normalize_temp(self._config.get("temp_current"))

    @property
    def target_temperature(self) -> float | None:
        return _normalize_temp(self._config.get("temp_set"))

    @property
    def hvac_mode(self) -> HVACMode | None:
        if not self._config.get("power"):
            return HVACMode.OFF
        return MODE_TO_HVAC.get(self._config.get("mode", "").upper())

    @property
    def fan_mode(self) -> str | None:
        return WIND_TO_FAN.get(self._config.get("wind_speed", "").upper())

    # ---- Commands ----

    async def _send(self, updates: dict[str, Any]) -> None:
        # Optimistic state goes to _pending immediately so the UI is responsive
        # even though the actual PUT is debounced.
        for key, value in updates.items():
            self._pending[key] = (value, 0)
            self._batch_buffer[key] = value
        self.async_write_ha_state()
        if self._batch_task is None or self._batch_task.done():
            self._batch_task = self.hass.async_create_task(self._flush_batch())

    async def _flush_batch(self) -> None:
        await asyncio.sleep(_BATCH_WINDOW_SECONDS)
        to_send = self._batch_buffer
        self._batch_buffer = {}
        if not to_send:
            return
        await self.coordinator.api.update_device_shadow(self._device_id, to_send)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._send({"power": False})
            return
        mode_str = HVAC_TO_MODE.get(hvac_mode)
        if mode_str is None:
            return
        await self._send({"power": True, "mode": mode_str})

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        await self._send({"temp_set": int(round(float(temp)))})

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        wind = FAN_TO_WIND.get(fan_mode)
        if wind is None:
            return
        await self._send({"wind_speed": wind})

    async def async_turn_on(self) -> None:
        await self._send({"power": True})

    async def async_turn_off(self) -> None:
        await self._send({"power": False})

    @callback
    def _handle_coordinator_update(self) -> None:
        # Drop pending overrides as the cloud agrees, or after enough
        # consecutive disagreeing polls to assume the command failed.
        if self._pending:
            base = self._device.get("configurations", {}) or {}
            for key in list(self._pending):
                value, disagreements = self._pending[key]
                if base.get(key) == value:
                    del self._pending[key]
                elif disagreements >= _PENDING_MAX_DISAGREEMENTS:
                    del self._pending[key]
                else:
                    self._pending[key] = (value, disagreements + 1)
        self.async_write_ha_state()
