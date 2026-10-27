"""Talks real MCP (streamable HTTP) to a local provider server, through the same client code used for Swiggy/Zomato."""
import socket
import threading
import time

import pytest
import uvicorn

from app.bazar.connectors.mcp_remote import McpHttpRemote, _find_items, _find_total

mcpserver = pytest.importorskip("mcp.server.mcpserver")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def provider_url():
    srv = mcpserver.MCPServer("fake-food-provider")
    seen_auth: list[str] = []

    @srv.tool()
    def get_cart() -> dict:
        """Current cart."""
        return {"items": [{"name": "Paneer Butter Masala", "quantity": 1}, {"name": "Butter Naan", "quantity": 4}], "to_pay": 389.0}

    @srv.tool()
    def place_order(payment: str = "upi") -> dict:
        """Place the order in the cart."""
        return {"order_id": "FAKE-1", "status": "PLACED", "payment": payment}

    app = srv.streamable_http_app()

    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}/mcp", seen_auth
    server.should_exit = True
    th.join(timeout=5)


def test_real_mcp_roundtrip(provider_url):
    url, _ = provider_url
    remote = McpHttpRemote(url, "user-token")
    names = [t["name"] for t in remote.list_tools()]
    assert {"get_cart", "place_order"} <= set(names)
    cart = remote.call_tool("get_cart", {})
    assert not cart["is_error"]
    assert _find_total(cart["data"]) == 38900
    assert _find_items(cart["data"])[1]["name"] == "Butter Naan × 4"
    placed = remote.call_tool("place_order", {"payment": "upi"})
    assert placed["data"]["order_id"] == "FAKE-1"
