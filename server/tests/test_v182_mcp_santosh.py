"""v0.182: the read-only Santosh MCP server.

Guards:
- token issue/verify/revoke work and the subject equals the tenant string
- the server builds with exactly the 7 read-only tools
- notebook_list returns [] for a fresh tenant (proves tenant_id flows through)
"""
import asyncio
import hashlib


def _hash(tok: str) -> str:
    return hashlib.sha256(tok.encode()).hexdigest()


def test_token_issue_verify_and_revoke(env):
    from app.bazar.db import McpSantoshToken, session_factory
    from app.mcp_santosh import DbTokenVerifier, issue_token

    with session_factory() as s:
        tok = issue_token(s, "test-tenant-1", "My Claude")
        s.commit()

    assert tok.startswith("snt_santosh_")
    assert len(tok) > 20

    at = asyncio.run(DbTokenVerifier().verify_token(tok))
    assert at is not None
    assert at.subject == "test-tenant-1"
    assert "notebook:read" in at.scopes
    assert "drive:read" in at.scopes

    with session_factory() as s:
        row = s.query(McpSantoshToken).filter_by(token_hash=_hash(tok)).one()
        row.revoked = True
        s.commit()

    at2 = asyncio.run(DbTokenVerifier().verify_token(tok))
    assert at2 is None, "revoked token must not verify"


def test_wrong_token_rejected(env):
    from app.mcp_santosh import DbTokenVerifier
    at = asyncio.run(DbTokenVerifier().verify_token("snt_santosh_notreal"))
    assert at is None


def test_server_builds_with_7_readonly_tools(env):
    from app.mcp_santosh import build_server
    srv = build_server(user_resolver=lambda: "test-tenant")
    tools = srv._tool_manager.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "notebook_list", "notebook_open", "notebook_ask",
        "drive_find", "drive_list_folder", "drive_read_file", "drive_storage",
    }, names


def test_notebook_list_empty_for_fresh_tenant(env):
    """Proves tenant_id passed to Ctx flows straight into the notebook service without a lookup."""
    from app.agent.notebook_tools import NOTEBOOK_HANDLERS
    from app.agent.tools import Ctx
    ctx = Ctx(tenant_id="fresh-tenant-no-notebooks", conversation_id="", actor="mcp:notebook_list")
    result = asyncio.run(NOTEBOOK_HANDLERS["notebook_list"](ctx))
    assert "notebooks" in result
    assert result["notebooks"] == []
