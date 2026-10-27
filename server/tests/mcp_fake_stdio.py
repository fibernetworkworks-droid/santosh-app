"""A tiny stdio MCP server for runner tests (plain JSON-RPC lines, no SDK). Needs WEATHER_KEY, like real servers that
read an API key from their environment; asks the client for roots once to prove server->client requests are answered."""
import json
import os
import sys

NEED = sys.argv[1] if len(sys.argv) > 1 else "WEATHER_KEY"
if not os.environ.get(NEED):
    print(f"Error: {NEED} environment variable is required", file=sys.stderr, flush=True)
    sys.exit(1)

TOOLS = [{"name": "get_forecast", "description": "Weather for a city",
          "inputSchema": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
          "annotations": {"readOnlyHint": True}},
         {"name": "delete_city", "description": "Delete a saved city",
          "inputSchema": {"type": "object", "properties": {"city": {"type": "string"}}}}]
inits = 0


def send(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


for line in sys.stdin:
    try:
        m = json.loads(line)
    except ValueError:
        continue
    mid, method = m.get("id"), m.get("method")
    if method is None:
        continue
    if method == "initialize":
        inits += 1
        send({"jsonrpc": "2.0", "id": mid, "result": {"protocolVersion": m["params"]["protocolVersion"],
                                                       "capabilities": {"tools": {}},
                                                       "serverInfo": {"name": "fake-weather", "version": "1.0"}}})
        send({"jsonrpc": "2.0", "id": "srv-1", "method": "roots/list"})
    elif method == "tools/list":
        send({"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}})
    elif method == "tools/call":
        p = m.get("params") or {}
        city = (p.get("arguments") or {}).get("city", "?")
        text = f"{city}: 31C sunny (inits {inits})" if p.get("name") == "get_forecast" else f"deleted {city}"
        send({"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": text}], "isError": False}})
    elif method == "ping":
        send({"jsonrpc": "2.0", "id": mid, "result": {}})
    elif mid is not None:
        send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "no such method"}})
