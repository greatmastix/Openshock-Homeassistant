# OpenShock Home Assistant Integration

This custom integration provides:

- Automatic polling of shocker status/telemetry.
- Per-shocker action buttons (Shock, Vibrate, Sound, Stop).
- Per-shocker default intensity and duration controls.
- Services for full command control (`openshock.send_command`, `openshock.stop_all`).

## Setup

1. Copy `custom_components/openshock` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add integration: **Settings → Devices & Services → Add Integration → OpenShock**.
4. Provide API URL and API key.

## Notes

Because OpenShock deployments may expose different endpoint variants, this integration includes endpoint/payload fallbacks for command and list APIs.
