# Changelog

## 0.2.7

- **Safety:** a control command that times out or gets a server error is no longer resent to the fallback API endpoint, which could deliver the same shock twice. Fallback now happens only when the server rejected the request outright.
- **Safety:** `openshock.stop_all` now sends the stop to every shocker even if some of them fail (e.g. one hub is offline). Previously the first failure ended the loop and the remaining shockers were never stopped. The service call still reports an error naming each shocker that could not be stopped.
- Authentication errors are reported immediately instead of first trying the fallback endpoints.
- Added `translations/en.json` so setup and options forms show proper labels and error messages.
- Changing the polling interval in the options now takes effect without restarting Home Assistant.
- Fixed **Reconfigure**: it now updates the existing entry (API URL and/or token) instead of aborting or creating a duplicate.
- `openshock.send_command` and `openshock.stop_all` now work with multiple OpenShock accounts; `stop_all` stops every account.
- The User-Agent now reports the installed integration version.
- Manifest and `hacs.json` updated for hassfest/HACS validation; minimum Home Assistant version is now correctly 2025.3.
- Added a GitHub Actions workflow running hassfest and HACS validation.

## 0.2.6

- Improved Home Assistant boot and restart time: the SignalR websocket now runs as a background task, and API requests time out after 15s instead of 300s. ([#27](https://github.com/greatmastix/Openshock-Homeassistant/pull/27))
