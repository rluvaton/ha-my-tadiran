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

- SMS OTP is the only initial auth path. If Cognito revokes your refresh token, you'll need to re-enter an SMS code.
- Tested only against Israeli (`tenant-...`) accounts so far; EU tenants should work but are unverified.
- LAN/local control is not implemented — the integration is cloud-only.

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

This project is not affiliated with Tadiran or with Tuya. Use at your own risk.
