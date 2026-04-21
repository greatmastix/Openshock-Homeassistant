# OpenShock for Home Assistant

Simple custom integration to control OpenShock shockers from Home Assistant.

## What it adds

- **One device per shocker** (hubs are only used for discovery)
- Command buttons: **Shock**, **Vibrate**, **Sound**, **Stop**
- Device automation action: **Shock**, **Beep**, **Vibrate** with duration/intensity inputs
- Per-shocker defaults: **Intensity** and **Duration**
- Services:
  - `openshock.send_command`
  - `openshock.stop_all`

## Install

1. Copy `custom_components/openshock` into your Home Assistant `custom_components` folder.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → OpenShock**.
4. Enter your OpenShock API base URL and API token.

## Disclosure

This project/integration scaffold was created with assistance from AI and then iterated based on real-device user feedback.
