"""The server owner's older Google Drive route: the service account, limited to the shared folder."""
import asyncio

import httpx
import pytest

import app.drive.models  # noqa: F401
from app.agent import drive_tools as dt
from app.agent.tools import Ctx, ToolError
from app.drive.client import FOLDER, GDOC
from tests.test_drive import FakeDrive
from tests.test_life import conv_ctx


@pytest.fixture
def sa(env, monkeypatch):
    monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "SHARED1")
    from app.config import get_settings
    get_settings.cache_clear()
    from app import gdrive
    from app.drive import accounts as da
    from app.mailbox import accounts as ma
    monkeypatch.setattr(gdrive, "configured", lambda tenant_id=None: tenant_id in (None, "default"))
    monkeypatch.setattr(da, "_service_token", lambda force: "at")
    monkeypatch.setattr(da, "_service_email", lambda: "santosh@proj.iam.gserviceaccount.com")
    fake = FakeDrive()
    fake.add("SHARED1", "Santosh shared", FOLDER)
    fake.add("in1", "Proposal FNW", GDOC, parents=["SHARED1"], content=b"Proposal body text")
    fake.add("out1", "Proposal private", GDOC, parents=["root"], content=b"secret")
    ma.set_http(httpx.Client(transport=httpx.MockTransport(fake)))
    yield fake
    ma.set_http(None)


def test_owner_service_account_sees_only_the_shared_folder(sa):
    ctx = conv_ctx()
    out = asyncio.run(dt.DRIVE_HANDLERS["drive_find"](ctx, query="Proposal"))
    names = [f["name"] for f in out["files"]]
    assert names == ["Proposal FNW"]
    text = asyncio.run(dt.DRIVE_HANDLERS["drive_read_file"](ctx, file="Proposal FNW"))
    assert "Proposal body text" in text["text"]


def test_service_account_is_owner_only(sa):
    with pytest.raises(ToolError, match="Profile > Google Drive"):
        asyncio.run(dt.DRIVE_HANDLERS["drive_find"](Ctx("usr_other", "c"), query="x"))
