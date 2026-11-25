"""v0.999.194 APPS WIRING: an app she connected through Composio actually reaches the brain - it is named in the
system prompt, naming it opens composio_apps / bazar_run, tool_search finds it, the PC picker prefers it, the call
knows it - and the 'Add key' path points at the real Connectors page."""
import asyncio

from tests.test_v0276_composio import _link, cz  # noqa: F401  (fixture)


def _key(cz, tenant="default"):
    return cz["svc"].composio_key(tenant, "zendesk", {"generic_api_key": "k-123", "subdomain": "acme"})


def test_her_apps_read_by_tenant_not_hashed_id(cz):
    _link(cz)
    _key(cz)
    apps = dict(cz["cmp"].her_apps("default"))
    assert apps == {"slack": "Slack", "zendesk": "Zendesk"}
    assert cz["cmp"].her_apps("other") == []                    # another tenant never sees her apps


def test_named_apps_matches_her_words():
    from app.bazar import composio as c
    apps = [("perplexityai", "Perplexity AI"), ("slack", "Slack"), ("zoho_books", "Zoho Books")]
    names = lambda t: [k for k, _ in c.named_apps(t, apps)]   # noqa: E731
    assert names("Use Perplexity to find the latest GST changes") == ["perplexityai"]
    assert names("ask perplexity ai about CRMs") == ["perplexityai"]
    assert names("slack pe message bhejo") == ["slack"]
    assert names("send the invoice from zoho books") == ["zoho_books"]
    assert names("what is the weather") == []
    assert names("slackline yoga") == []                        # whole words only


def test_prompt_line_tells_the_brain(cz):
    _link(cz)
    line = cz["cmp"].prompt_line("default")
    assert "Slack (toolkit slack)" in line and "bazar_run pack_id=cmp-<toolkit>" in line
    assert "rather than your own web search" in line
    assert cz["cmp"].prompt_line("other") == ""


def test_pick_prefers_her_connected_app(cz):
    _link(cz)
    from app.agent import pick
    way = pick._connected_way("post the update on slack", "default")
    assert "cmp-slack" in way and "Slack" in way
    assert "cmp-slack" not in pick._connected_way("post the update on slack", "other")


def test_tool_search_finds_her_app(cz):
    _link(cz)
    from app.agent import admit
    from app.agent.tools import Ctx
    from app.config import get_settings
    ctx = Ctx(tenant_id="default", conversation_id=cz["conv"]["default"])
    st = get_settings()
    old = st.chat_core_tools
    st.chat_core_tools = True                                   # the live start: only the ~22 core tools in view
    try:
        ctx.admit = admit.AdmitSet(st)
        assert "bazar" not in ctx.admit.families
        out = asyncio.run(admit.tool_search(ctx, need="slack"))
    finally:
        st.chat_core_tools = old
    assert "composio_apps" in out["admitted"] and "bazar_run" in out["admitted"]
    out2 = asyncio.run(admit.tool_search(Ctx(tenant_id="other", conversation_id="x"), need="slack"))
    assert "bazar_run" not in str(out2)                         # not hers: nothing opens


def test_add_key_path_points_at_connectors(cz):
    from app.agent.bazar_tools import BAZAR_TOOLS
    desc = [t for t in BAZAR_TOOLS if t["name"] == "composio_apps"][0]["description"]
    assert "Connectors > the app > Add key" in desc and "MCP servers > Apps" not in desc
    out = cz["svc"].composio_connect("default", "zendesk", cz["conv"]["default"])
    assert out["status"] == "needs_key" and "open Connectors" in out["say"]


def test_wiring_hooks_in_place():
    import inspect
    from app import voice
    from app.agent import santosh
    src = inspect.getsource(santosh)
    assert "_cmp.prompt_line(tenant_id, _her_apps)" in src and '"bazar": "her app "' in src
    assert "connected apps line for the call" in inspect.getsource(voice)
