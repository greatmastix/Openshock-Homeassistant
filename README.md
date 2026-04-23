# OpenShock for Home Assistant

Simple custom integration to control OpenShock shockers from Home Assistant.

## What it adds

- **One device per shocker** (hubs are only used for discovery)
- Command buttons: **Shock**, **Vibrate**, **Sound**, **Stop**
- Per-shocker defaults: **Intensity** and **Duration**
- Services:
  - `openshock.send_command`
  - `openshock.stop_all`
- Optional telemetry sensors (**only** if API provides them): Status, Battery, RSSI

## Install

1. Copy `custom_components/openshock` into your Home Assistant `custom_components` folder.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → OpenShock**.
4. Enter your OpenShock API base URL and API token.


## Dashboard custom card (device-targeted)

A lightweight Lovelace custom card is bundled with the integration.
It calls `openshock.send_command` with `device_id` so you can target the **shocker device directly** (no shocker ID lookup needed in your dashboard YAML).

The integration serves and registers the card JavaScript automatically at startup.
You can add it from the dashboard UI with a visual editor (including an OpenShock device selector), or with YAML as:

```yaml
type: custom:openshock-shocker-card
title: Desk Shocker
device_id: 1234567890abcdef1234567890abcdef
intensity: 50
duration_ms: 1000
```

> Tip: In Home Assistant, you can find the `device_id` in **Developer Tools → Actions**, by selecting `openshock.send_command` and choosing your device from the device selector.

## Quick troubleshoot

- Use an **API token** (not your account password).
- If setup fails, verify your API base URL is correct.
- API auth follows OpenShock token headers (`OpenShockToken` / `Open-Shock-Token`) and uses the V2 control endpoint first.
- Sound actions use OpenShock `Sound` control type (`beep` is accepted as alias).

## Disclosure

This project/integration scaffold was created with assistance from AI and then iterated based on real-device user feedback.
