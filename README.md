# Tadiran AC — Home Assistant integration

Unofficial Home Assistant integration for [Tadiran](https://www.tadiran-ac.co.il/) air conditioners that are paired with the **My Tadiran** mobile app. Talks to the Tadiran cloud API directly (no Tuya cloud roundtrip).

Each AC is exposed as a `climate` entity supporting:

- power on/off
- HVAC modes: cool / heat / dry / fan only / auto
- target temperature (16–30°C)
- current temperature
- fan speed: low / medium / high / auto

Swing controls are not exposed — the API has `swing_ud` / `swing_lr` fields but they're phantoms on Tadiran AC models without physical louver motors, and the My Tadiran app hides them too.

## Requirements

- Home Assistant 2024.10 or newer
- An active My Tadiran account (the phone number registered with the app)

## Install (HACS)

1. In Home Assistant, open **HACS → ⋮ → Custom repositories**.
2. Add `https://github.com/rluvaton/ha-my-tadiran` as repository type **Integration**.
3. Find **Tadiran AC** in the HACS integration list and install it.
4. Restart Home Assistant.

## Install (manual)

1. Copy `custom_components/tadiran/` from this repo into your HA `config/custom_components/` directory.
2. Restart Home Assistant.

## Setup

1. **Settings → Devices & Services → Add Integration → Tadiran AC**.
2. Enter the phone number registered with your My Tadiran account (with country code, e.g. `+972XXXXXXXXX`).
3. You'll get an SMS code from Tadiran/AWS Cognito. Enter it in the second screen.

After setup, the integration keeps itself authenticated via the Cognito refresh token — you won't need to re-enter an SMS code unless the refresh token is revoked (in which case HA will prompt you to re-authenticate).

## How auth works

- Tadiran's app authenticates against AWS Cognito (User Pool `eu-west-1_WG1VW4YTe`) using the `CUSTOM_AUTH` flow with phone-number-as-username and SMS OTP.
- The config flow performs this OTP exchange once and stores the resulting `refresh_token` in your config entry.
- Each polling cycle, the integration exchanges the refresh token for a fresh `id_token` via `REFRESH_TOKEN_AUTH` (no SMS needed).

## Limitations

- **Only tested on a Tadiran Ducted Inverter AC.** Other Tadiran model families (mini-split, cassette, portable, etc.) may use different mode strings, expose different shadow fields, or have hardware features this integration doesn't surface (e.g. swing). If you have a different model and it doesn't work, please open an issue with the output of `GET /tadiran-mobile-app/api/v1/devices/` and `GET /mobile-app/api/v1/devices/{id}/shadow/` so we can extend support.
- SMS OTP is the only initial auth path. If Cognito revokes your refresh token, you'll need to re-enter an SMS code.
- Tested only against Israeli (`tenant-...`) accounts so far; EU tenants should work but are unverified.
- LAN/local control is not implemented — the integration is cloud-only.
- Target temperature is hidden in AUTO (heat/cool) mode — Tadiran ACs don't accept temp changes in that mode (the My Tadiran app hides the control there too).

## Known quirks

**The My Tadiran app may show old values for a while after changes from HA.** The Tadiran cloud shadow has two fields per property: `desired` (what was requested) and `reported` (what the device has acknowledged). Our integration updates `desired` and the device acts on it within seconds — you'll often hear the AC engine adjust immediately. But `reported` lags by anywhere from a few seconds to several minutes as it waits for the device's heartbeat to sync state back to the cloud. The mobile app appears to prefer `reported`, so it may keep showing the old value for a while. **Trust HA and the AC itself, not the app, when there's a mismatch.**

**Cloud command propagation can take up to ~90 seconds.** When you change something in HA, the integration optimistically shows the new value immediately and masks the lagging cloud state for up to three poll cycles (~90s). If after that the cloud still doesn't reflect the change, HA snaps to the cloud's value — usually a sign the command was actually rejected, in which case you'll have seen a notification banner.

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

This project is not affiliated with Tadiran or with Tuya. Use at your own risk.
