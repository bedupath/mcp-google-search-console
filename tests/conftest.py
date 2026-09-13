import socket
from collections.abc import Callable

import httpx
import pytest

from mcp_google_search_console.client import GSCClient
from mcp_google_search_console.config import Settings


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not use live network connections")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


class FakeAuth:
    def __init__(self):
        self.calls = 0

    async def get_token(self):
        self.calls += 1
        return "synthetic-test-token"


@pytest.fixture
async def client_factory():
    transports = []

    def factory(handler: Callable, settings: Settings | None = None):
        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        transports.append(http)
        auth = FakeAuth()
        delays = []

        async def sleep(delay):
            delays.append(delay)

        client = GSCClient(settings or Settings(), auth=auth, http_client=http, sleep=sleep)
        return client, auth, delays

    yield factory
    for http in transports:
        await http.aclose()
