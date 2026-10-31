# OpenShock for Home Assistant

Simple custom integration to control OpenShock shockers from Home Assistant.

[![Open your Home Assistant instance and add this repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=greatmastix&repository=Openshock-Homeassistant&category=integration)

## What it adds

- **One device per shocker** (hubs are only used for discovery)
- Command buttons: **Shock**, **Vibrate**, **Sound**, **Stop**
- Device automation action: **Shock**, **Beep**, **Vibrate** with duration/intensity inputs
- Per-shocker defaults: **Intensity** and **Duration**
- Live device online/offline status via the OpenShock SignalR hub
- Services:
  - `openshock.send_command` (accepts either `device_id` or `shocker_id`)
  - `openshock.stop_all` (stops every shocker on every configured account)

## Requirements

- Home Assistant **2025.3** or newer

## Install

1. Install via HACS using the button above, or copy `custom_components/openshock` into your Home Assistant `custom_components` folder.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → OpenShock**.
4. Enter your OpenShock API base URL and API token.

## Configuration

- **Polling interval:** open the integration's **Configure** menu. Changes apply immediately (the integration reloads).
- **API URL or token:** use **Reconfigure** from the integration's menu. Leave the token empty to keep the current one.

## Example Home Assistant Dashboard

Below is an example Lovelace dashboard using Mushroom cards to control an OpenShock device.

> **Important:** Replace the example entity IDs below with the actual entity IDs created in your Home Assistant instance.

```yaml
type: grid
cards:
  - type: custom:mushroom-title-card
    title: Shock Collar

  - type: heading
    heading: Actions
    icon: mdi:lightning-bolt

  - type: grid
    columns: 3
    square: false
    cards:
      - type: custom:mushroom-template-card
        primary: Shock
        icon: mdi:lightning-bolt
        icon_color: red
        layout: vertical
        tap_action:
          action: call-service
          service: button.press
          target:
            entity_id: button.YOUR_DEVICE_SHOCK

      - type: custom:mushroom-template-card
        primary: Vibrate
        icon: mdi:vibrate
        icon_color: amber
        layout: vertical
        tap_action:
          action: call-service
          service: button.press
          target:
            entity_id: button.YOUR_DEVICE_VIBRATE

      - type: custom:mushroom-template-card
        primary: Sound
        icon: mdi:volume-high
        icon_color: blue
        layout: vertical
        tap_action:
          action: call-service
          service: button.press
          target:
            entity_id: button.YOUR_DEVICE_SOUND

  - type: heading
    heading: Settings
    icon: mdi:tune

  - type: grid
    columns: 2
    square: false
    cards:
      - type: custom:mushroom-number-card
        entity: number.YOUR_DEVICE_INTENSITY
        name: Intensity
        icon: mdi:signal
        display_mode: buttons

      - type: custom:mushroom-number-card
        entity: number.YOUR_DEVICE_DURATION
        name: Duration
        icon: mdi:timer-outline
        display_mode: buttons
```

### Dashboard notes

- Replace:
  - `button.YOUR_DEVICE_SHOCK`
  - `button.YOUR_DEVICE_VIBRATE`
  - `button.YOUR_DEVICE_SOUND`
  - `number.YOUR_DEVICE_INTENSITY`
  - `number.YOUR_DEVICE_DURATION`
- This example uses [Mushroom Cards](https://github.com/piitaya/lovelace-mushroom).
- You can also add a **Stop** button if you expose one in your dashboard.

## Quick troubleshoot

- Use an **API token** (not your account password).
- If setup fails, verify your API base URL is correct.
- API auth follows OpenShock token headers (`OpenShockToken` / `Open-Shock-Token`) and uses the V2 control endpoint first.
- Sound actions use OpenShock `Sound` control type (`beep` is accepted as alias).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Disclosure

This project/integration scaffold was created with assistance from AI and then iterated based on real-device user feedback.
