"""Config flow for Tadiran AC: phone -> SMS OTP -> store refresh_token."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TadiranAPI, TadiranAuthError, TadiranInvalidOTP
from .const import (
    CONF_ORG_ID,
    CONF_PHONE,
    CONF_REFRESH_TOKEN,
    CONF_SESSION,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema({vol.Required(CONF_PHONE): str})
STEP_OTP_SCHEMA = vol.Schema({vol.Required("otp"): str})


class TadiranConfigFlow(ConfigFlow, domain=DOMAIN):
    """Two-step setup: collect phone, then OTP."""

    VERSION = 1

    def __init__(self) -> None:
        self._phone: str | None = None
        self._session: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            phone = user_input[CONF_PHONE].strip()
            if not phone.startswith("+") or len(phone) < 8:
                errors["base"] = "invalid_phone"
            else:
                await self.async_set_unique_id(phone)
                self._abort_if_unique_id_configured()

                api = TadiranAPI(async_get_clientsession(self.hass))
                try:
                    self._session = await api.initiate_otp(phone)
                except TadiranAuthError as err:
                    _LOGGER.warning("initiate_otp failed: %s", err)
                    errors["base"] = "cannot_connect"
                else:
                    self._phone = phone
                    return await self.async_step_otp()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_otp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            assert self._phone is not None
            assert self._session is not None
            otp = user_input["otp"].strip()

            api = TadiranAPI(async_get_clientsession(self.hass))
            try:
                await api.verify_otp(self._phone, self._session, otp)
            except TadiranInvalidOTP:
                errors["base"] = "invalid_otp"
            except TadiranAuthError as err:
                _LOGGER.warning("verify_otp failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"Tadiran ({self._phone})",
                    data={
                        CONF_PHONE: self._phone,
                        CONF_REFRESH_TOKEN: api.refresh_token,
                        CONF_ORG_ID: api.org_id,
                    },
                )

        return self.async_show_form(
            step_id="otp",
            data_schema=STEP_OTP_SCHEMA,
            errors=errors,
            description_placeholders={"phone": self._phone or ""},
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        self._phone = entry_data[CONF_PHONE]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Re-trigger OTP for the same phone when refresh_token is revoked."""
        errors: dict[str, str] = {}
        assert self._phone is not None

        if user_input is not None:
            api = TadiranAPI(async_get_clientsession(self.hass))
            try:
                self._session = await api.initiate_otp(self._phone)
            except TadiranAuthError as err:
                _LOGGER.warning("reauth initiate_otp failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                return await self.async_step_otp()

        return self.async_show_form(
            step_id="reauth_confirm",
            errors=errors,
            description_placeholders={"phone": self._phone},
        )
