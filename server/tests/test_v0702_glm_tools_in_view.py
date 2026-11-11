"""v0.702 GLM SIRF DIKHTE AUZAAR (her G8 run, 8 Nov: every GLM step was ~70k tokens in, slow, timing out).

Claude's tool search sends ~650 tools with only ~60 in view (the rest defer_loading: true). GLM has no such switch, so
the door used to send every deferred tool in FULL. Now GLM gets what Claude sees: the tools in view + the ones
tool_search loaded in this conversation; tool_reference blocks become text naming the loaded tool.
"""
from app import glmdoor


def _tool(name, deferred=False):
    t = {"name": name, "description": name, "input_schema": {"type": "object", "properties": {}}}
    if deferred:
        t["defer_loading"] = True
    return t


def _names(body):
    return sorted(f["function"]["name"] for f in body.get("tools", []))


def test_deferred_tools_stay_out(monkeypatch):
    kw = {"model": "claude-haiku-5-5", "max_tokens": 500,
          "messages": [{"role": "user", "content": "hi"}],
          "tools": [_tool("email_draft"), _tool("tool_search")] + [_tool(f"desk_{i}", True) for i in range(600)]}
    _url, _h, body, _label = glmdoor.build(kw)
    assert _names(body) == ["email_draft", "tool_search"]
    assert all("defer_loading" not in str(f) for f in body["tools"])


def test_tool_search_result_loads_the_tool_for_glm():
    msgs = [{"role": "user", "content": "gst ka hisaab"},
            {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "tool_search",
                                               "input": {"query": "gst"}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1",
                                          "content": [{"type": "tool_reference", "tool_name": "desk_7"}]}]}]
    kw = {"model": "claude-haiku-5-5", "max_tokens": 500, "messages": msgs,
          "tools": [_tool("tool_search"), _tool("desk_7", True), _tool("desk_8", True)]}
    _url, _h, body, _label = glmdoor.build(kw)
    assert _names(body) == ["desk_7", "tool_search"]
    tool_msg = next(m for m in body["messages"] if m["role"] == "tool")
    assert "desk_7" in tool_msg["content"]


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.819.0"
