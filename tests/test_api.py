"""Tests for the OpenShock API client.

api.py is loaded straight from its file so these tests only need aiohttp and
pytest, not Home Assistant (importing the package would run its __init__).

Run with: python -m pytest tests
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from typing import Any

import pytest

_API_PATH = Path(__file__).parents[1] / "custom_components" / "openshock" / "api.py"
_spec = importlib.util.spec_from_file_location("openshock_api", _API_PATH)
api = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(api)

SHOCKER_A = "11111111-1111-1111-1111-111111111111"
SHOCKER_B = "22222222-2222-2222-2222-222222222222"
SHOCKER_C = "33333333-3333-3333-3333-333333333333"

OWN_SHOCKERS = [
    {
        "id": "hub-1",
        "name": "Hub 1",
        "shockers": [
            {"id": SHOCKER_A, "name": "Collar"},
            {"id": SHOCKER_B, "name": "Leg"},
        ],
    },
    {"id": "hub-2", "name": "Hub 2", "shockers": [{"id": SHOCKER_C, "name": "Arm"}]},
]


def _client(errors: dict[str, Exception]) -> tuple[Any, list[tuple[str, str, Any]]]:
    """Return a client whose _request is mocked, and the list of calls it records.

    `errors` maps a shocker id to the error a control request for it raises.
    """
    client = api.OpenShockApiClient(session=None, base_url="https://api.example", api_key="token")
    calls: list[tuple[str, str, Any]] = []

    async def fake_request(method: str, path: str, *, json_body: Any = None) -> Any:
        calls.append((method, path, json_body))
        if method == "GET":
            return {"data": OWN_SHOCKERS}
        controls = json_body["shocks"] if isinstance(json_body, dict) else json_body
        for control in controls:
            if (error := errors.get(control["id"])) is not None:
                raise error
        return {"message": ""}

    client._request = fake_request
    return client, calls


def _stopped_ids(calls: list[tuple[str, str, Any]]) -> list[str]:
    ids = []
    for method, _path, body in calls:
        if method != "POST":
            continue
        controls = body["shocks"] if isinstance(body, dict) else body
        for control in controls:
            assert control["type"] == "Stop"
            ids.append(control["id"])
    return ids


def test_stop_all_stops_every_shocker() -> None:
    client, calls = _client({})

    asyncio.run(client.stop_all())

    assert sorted(_stopped_ids(calls)) == [SHOCKER_A, SHOCKER_B, SHOCKER_C]


@pytest.mark.parametrize(
    "error",
    [
        api.OpenShockApiError("Request failed for /2/shockers/control: TimeoutError()"),
        api.OpenShockApiError("HTTP 503 for /2/shockers/control: hub offline", status=503),
    ],
    ids=["timeout", "server-error"],
)
def test_stop_all_continues_after_a_failure(error: Exception) -> None:
    # The first shocker fails; the other two must still be stopped.
    client, calls = _client({SHOCKER_A: error})

    with pytest.raises(api.OpenShockApiError) as excinfo:
        asyncio.run(client.stop_all())

    assert sorted(_stopped_ids(calls)) == [SHOCKER_A, SHOCKER_B, SHOCKER_C]
    # An ambiguous failure is still never resent to the fallback endpoint.
    assert [path for method, path, _ in calls if method == "POST"].count("/1/shockers/control") == 0

    message = str(excinfo.value)
    assert "1 of 3" in message
    assert f"Collar ({SHOCKER_A})" in message
    assert str(error) in message
    assert SHOCKER_B not in message
    assert SHOCKER_C not in message


def test_stop_all_names_every_failed_shocker() -> None:
    client, calls = _client(
        {
            SHOCKER_A: api.OpenShockApiError("HTTP 503 for /2/shockers/control: down", status=503),
            SHOCKER_C: api.OpenShockApiError("Request failed for /2/shockers/control: TimeoutError()"),
        }
    )

    with pytest.raises(api.OpenShockApiError) as excinfo:
        asyncio.run(client.stop_all())

    assert sorted(_stopped_ids(calls)) == [SHOCKER_A, SHOCKER_B, SHOCKER_C]
    message = str(excinfo.value)
    assert "2 of 3" in message
    assert f"Collar ({SHOCKER_A})" in message
    assert f"Arm ({SHOCKER_C})" in message
    assert SHOCKER_B not in message


def test_stop_all_sends_other_stops_before_reraising_unexpected_errors() -> None:
    client, calls = _client({SHOCKER_A: RuntimeError("bug")})

    with pytest.raises(RuntimeError, match="bug"):
        asyncio.run(client.stop_all())

    assert sorted(_stopped_ids(calls)) == [SHOCKER_A, SHOCKER_B, SHOCKER_C]
