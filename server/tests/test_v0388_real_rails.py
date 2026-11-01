"""v0.388 SACH BOLO - the write rails made real, from the vendors' own documentation.

Every test here pins a defect that primary-source research found in v0.358-v0.375, and each one would have
failed silently against a real customer system. The point of each is named in its docstring.
"""
from __future__ import annotations

import json
import zipfile

import pytest

from app.enterprise import dialect, rules as R, sfmeta


# ---------------------------------------------------------------- the dialect table
def test_dialect_is_a_table_not_an_if_chain():
    """Each system's write rules are DATA. A new system is a row, which is how the SUMS lesson went."""
    assert dialect.of("sap")["csrf"] == "sap"
    assert dialect.of("windchill")["csrf"] == "ptc"
    assert dialect.of("salesforce")["csrf"] is None
    assert dialect.of("sap")["etag"] == "required"
    assert dialect.of("windchill")["reserve"]          # Windchill needs a check-out, nobody else does
    assert not dialect.of("sap")["reserve"]
    assert dialect.of("never-heard-of-it") == dialect.DEFAULT


class FakeRes:
    def __init__(self, code=200, body=None, headers=None, text=""):
        self.status_code, self._b, self.headers, self.text = code, body, headers or {}, text

    def json(self):
        if self._b is None:
            raise ValueError("no json")
        return self._b


class FakeClient:
    """Records every request so a test can assert on the HEADERS, which is where all of these bugs lived."""

    def __init__(self, script):
        self.script, self.seen = script, []

    def request(self, method, url, json=None, params=None, headers=None):
        self.seen.append({"method": method, "url": url, "body": json, "params": params,
                          "headers": dict(headers or {})})
        r = self.script(method, url, headers or {}, json)
        return r if r is not None else FakeRes(200, {"ok": True})

    def close(self):
        pass


class Ep:
    def __init__(self, system="sap", env="test"):
        self.system, self.env = system, env
        self.base_url = "https://erp.example.com/sap/opu/odata/sap/SRV"
        self.auth_enc, self.auth_kind, self.header_name = "", "bearer", ""


def mk(system="sap", script=None, env="test"):
    c = dialect.Call.__new__(dialect.Call)
    c.ep = Ep(system, env)
    c.system = system
    c.d = dialect.of(system)
    c._token = None
    c._idem_support = "unknown"
    c._c = FakeClient(script or (lambda *a: FakeRes(200, {"ok": True})))
    return c


# ---------------------------------------------------------------- SAP: CSRF + If-Match
def test_sap_write_sends_csrf_token_fetched_in_the_same_session():
    """SAP: no X-CSRF-Token on a modifying request -> 403. The token is bound to the SECURITY SESSION, so it
    must be fetched and used on one client. Before v0.388 we sent neither, on a fresh client each call."""
    def script(method, url, headers, body):
        if headers.get("X-CSRF-Token") == "Fetch":
            return FakeRes(200, {}, {"x-csrf-token": "TOK-123"})
        return FakeRes(201, {"id": 1})
    c = mk("sap", script)
    code, _data, _n = c.create("Orders", {"a": 1})
    assert code == 201
    writes = [r for r in c._c.seen if r["method"] == "POST"]
    assert writes and writes[0]["headers"]["X-CSRF-Token"] == "TOK-123"
    assert writes[0]["headers"]["Content-Type"] == "application/json"   # was missing entirely


def test_sap_refuses_to_write_when_no_csrf_token_is_issued():
    """Fails CLOSED. A write SAP would 403 is never sent at all."""
    c = mk("sap", lambda *a: FakeRes(200, {}, {}))
    with pytest.raises(dialect.DialectError) as e:
        c.create("Orders", {"a": 1})
    assert "CSRF" in str(e.value)


def test_a_403_refetches_the_token_and_retries_once():
    """A failed response carries no valid token, so one retry with a fresh token is the documented cure."""
    state = {"n": 0, "tok": 0}

    def script(method, url, headers, body):
        if headers.get("X-CSRF-Token") == "Fetch":
            state["tok"] += 1
            return FakeRes(200, {}, {"x-csrf-token": f"T{state['tok']}"})
        state["n"] += 1
        return FakeRes(403, {"error": "csrf"}) if state["n"] == 1 else FakeRes(201, {"id": 7})
    c = mk("sap", script)
    code, _d, _n = c.create("Orders", {"a": 1})
    assert code == 201 and state["tok"] == 2          # fetched twice: once, then again after the 403


def test_sap_patch_reads_the_etag_and_sends_if_match():
    """v4 SAP APIs: "the If-Match header must be set for all Update operations". The ETag comes from a GET of
    THAT entity - v2 in the header, v4 in @odata.etag."""
    def script(method, url, headers, body):
        if headers.get("X-CSRF-Token") == "Fetch":
            return FakeRes(200, {}, {"x-csrf-token": "T"})
        if method == "GET":
            return FakeRes(200, {"@odata.etag": 'W/"tag-9"'}, {})
        return FakeRes(204, None, {})
    c = mk("sap", script)
    code, _d, note = c.update("Orders('5')", {"qty": 2})
    assert code == 204 and note.get("if_match")
    patch = [r for r in c._c.seen if r["method"] == "PATCH"][0]
    assert patch["headers"]["If-Match"] == 'W/"tag-9"'


def test_sap_patch_refuses_rather_than_writing_without_an_etag():
    """Where the vendor demands If-Match, a row we cannot read is SKIPPED, not written blind (SAP would 428)."""
    def script(method, url, headers, body):
        if headers.get("X-CSRF-Token") == "Fetch":
            return FakeRes(200, {}, {"x-csrf-token": "T"})
        if method == "GET":
            return FakeRes(404, {"error": "gone"}, {})
        raise AssertionError("must never reach the PATCH")
    with pytest.raises(dialect.DialectError):
        mk("sap", script).update("Orders('5')", {"qty": 2})


def test_a_412_is_marked_never_retry():
    """412 = somebody changed the row between our read and our write. The row we planned against is not the
    row that is there, so a blind retry would overwrite their change."""
    def script(method, url, headers, body):
        if headers.get("X-CSRF-Token") == "Fetch":
            return FakeRes(200, {}, {"x-csrf-token": "T"})
        if method == "GET":
            return FakeRes(200, {"@odata.etag": "e1"}, {})
        return FakeRes(412, {"error": "stale"}, {})
    _code, _d, note = mk("sap", script).update("Orders('5')", {"q": 1})
    assert note.get("dobara_na_bhejo") is True


def test_sap_idempotent_create_sends_a_stable_32_char_request_id():
    """SAP's documented idempotent create: RequestID + RepeatabilityCreation, answered by
    RepeatabilityResult: accepted = "the server state reflects a single execution". The id must be the SAME
    on a retry or it is not idempotent at all."""
    def script(method, url, headers, body):
        if headers.get("X-CSRF-Token") == "Fetch":
            return FakeRes(200, {}, {"x-csrf-token": "T"})
        return FakeRes(201, {"id": 1}, {"repeatabilityresult": "accepted"})
    c = mk("sap", script)
    _code, _d, note = c.create("Orders", {"a": 1}, idem_key="a" * 32)
    post = [r for r in c._c.seen if r["method"] == "POST"][0]
    assert len(post["headers"]["RequestID"]) == 32
    assert post["headers"]["RequestID"] == dialect._guid32("a" * 32)   # stable, not random
    assert post["headers"]["RepeatabilityCreation"]
    assert note["repeatability"] == "accepted"
    assert c.support()["idempotent_create"] == "accepted"


def test_idempotency_unsupported_is_recorded_not_assumed():
    """The SPRO job is opt-in per customer system; SAP answers 412 when it is off. We record that, so the
    engine knows this endpoint gives no protection instead of believing it does."""
    def script(method, url, headers, body):
        if headers.get("X-CSRF-Token") == "Fetch":
            return FakeRes(200, {}, {"x-csrf-token": "T"})
        return FakeRes(412, {"error": "repeatability not enabled"}, {})
    c = mk("sap", script)
    c.create("Orders", {"a": 1}, idem_key="b" * 32)
    assert c.support()["idempotent_create"] == "unsupported"


def test_salesforce_gets_no_csrf_and_no_etag():
    """A table, not a habit: Salesforce REST needs neither, and we must not invent headers for it."""
    c = mk("salesforce", lambda *a: FakeRes(201, {"id": "x"}))
    c.create("sobjects/Account", {"Name": "A"})
    post = [r for r in c._c.seen if r["method"] == "POST"][0]
    assert "X-CSRF-Token" not in post["headers"] and "If-Match" not in post["headers"]


# ---------------------------------------------------------------- Windchill: nonce + the reservation
def test_windchill_reads_the_nonce_name_from_the_server():
    """PTC returns NonceKey + NonceValue; the header NAME is whatever NonceKey says, so we never hard-code
    it."""
    def script(method, url, headers, body):
        if url.endswith("PTC/GetCSRFToken()"):
            return FakeRes(200, {"NonceKey": "CSRF_NONCE", "NonceValue": "N-7"})
        return FakeRes(201, {"ok": 1})
    c = mk("windchill", script)
    c.create("ChangeRequests", {"Name": "CR"})
    post = [r for r in c._c.seen if r["method"] == "POST" and "GetCSRFToken" not in r["url"]][0]
    assert post["headers"]["CSRF_NONCE"] == "N-7"


def test_windchill_patch_reserves_first_and_always_releases():
    """The dangerous one. A reservation taken and not given back locks HER object against her own engineers,
    so the release must happen even when the PATCH fails."""
    calls = []

    def script(method, url, headers, body):
        if url.endswith("PTC/GetCSRFToken()"):
            return FakeRes(200, {"NonceKey": "CSRF_NONCE", "NonceValue": "N"})
        calls.append(url.rsplit("/", 1)[-1])
        if url.endswith(".Reserve"):
            return FakeRes(200, {"ok": 1})
        if url.endswith(".UndoReservation"):
            return FakeRes(200, {"ok": 1})
        return FakeRes(500, {"error": "boom"})
    c = mk("windchill", script)
    item = "ChangeRequests('OR:wt.change2.WTChangeRequest2:1')"
    try:
        with c.writing(item):
            c.update(item, {"Name": "x"})
    except Exception:                       # the PATCH fails on purpose; the release must still happen
        pass
    assert "PTC.ChangeMgmt.Reserve" in calls
    assert "PTC.ChangeMgmt.UndoReservation" in calls      # released despite the failing PATCH


def test_windchill_never_patches_when_the_reserve_fails():
    """No check-out, no write: Windchill would refuse it anyway, and trying leaves state half-moved."""
    def script(method, url, headers, body):
        if url.endswith("PTC/GetCSRFToken()"):
            return FakeRes(200, {"NonceKey": "CSRF_NONCE", "NonceValue": "N"})
        if url.endswith(".Reserve"):
            return FakeRes(409, {"error": "already checked out by someone else"})
        if method == "PATCH":
            raise AssertionError("must never PATCH an unreserved object")
        return FakeRes(200, {})
    c = mk("windchill", script)
    item = "ChangeRequests('OR:1')"
    with pytest.raises(dialect.DialectError):
        with c.writing(item):
            c.update(item, {"Name": "x"})


def test_windchill_read_asks_for_a_real_page_size():
    """Windchill pages at 25 rows by default, so our 2,000 cap was never what truncated a read."""
    c = mk("windchill", lambda *a: FakeRes(200, {"value": []}))
    c.get("Parts", page=500)
    assert c._c.seen[0]["headers"]["Prefer"] == "odata.maxpagesize=500"
    c2 = mk("sap", lambda *a: FakeRes(200, {"value": []}))
    c2.get("Orders", page=500)
    assert "Prefer" not in c2._c.seen[0]["headers"]       # not a header to sprinkle everywhere


def test_page_size_is_capped_at_the_servers_own_ceiling():
    c = mk("windchill", lambda *a: FakeRes(200, {}))
    c.get("Parts", page=99999)
    assert c._c.seen[0]["headers"]["Prefer"] == f"odata.maxpagesize={dialect.MAX_PAGE}"


# ---------------------------------------------------------------- Salesforce Metadata deploy
def test_package_xml_groups_by_type_and_pins_the_version():
    xml = sfmeta.package_xml([{"type": "ApexClass", "name": "Foo"},
                              {"type": "ApexClass", "name": "Bar"},
                              {"type": "Flow", "name": "My_Flow"}])
    assert "<name>ApexClass</name>" in xml and "<name>Flow</name>" in xml
    assert xml.count("<types>") == 2                       # grouped, not one block per component
    assert f"<version>{sfmeta.PIN}</version>" in xml
    assert xml.index("<members>Bar</members>") < xml.index("<members>Foo</members>")   # stable order


def test_zip_puts_each_type_in_its_documented_folder():
    data = sfmeta.build_zip([{"type": "ApexClass", "name": "Foo", "body": "public class Foo {}"},
                             {"type": "Flow", "name": "F", "body": "<Flow/>"},
                             {"type": "PermissionSet", "name": "P", "body": "<PermissionSet/>"}])
    with zipfile.ZipFile(__import__("io").BytesIO(data)) as z:
        names = set(z.namelist())
    assert "package.xml" in names
    assert "classes/Foo.cls" in names and "classes/Foo.cls-meta.xml" in names
    assert "flows/F.flow" in names and "permissionsets/P.permissionset" in names


def test_a_field_level_change_is_refused_with_the_reason():
    """CustomField lives INSIDE objects/<Obj>.object and Metadata REST has no retrieve to merge against, so
    building a partial object file would risk the rest of her object. Refusing is the honest answer."""
    with pytest.raises(sfmeta.MetaError) as e:
        sfmeta.build_zip([{"type": "CustomField", "name": "Acc.X__c", "body": "<x/>"}])
    assert "CustomObject" in str(e.value)


def test_production_options_are_salesforces_rules_not_ours():
    """rollbackOnError "must be set to true if you're deploying to a production org"; allowMissingFiles
    "Don't set this argument for deployment to production orgs"; purgeOnDelete does not work there."""
    o = sfmeta.deploy_options("production", [{"type": "ApexClass", "name": "A"}])
    assert o["rollbackOnError"] is True
    assert o["allowMissingFiles"] is False
    assert "purgeOnDelete" not in o
    assert o["testLevel"] == "RunLocalTests"               # Salesforce's own production default with Apex


def test_a_config_only_package_sets_no_test_level():
    """"If your package doesn't contain Apex components, no tests are run by default" - and setting a level
    would override that "regardless of the types of components that are present"."""
    o = sfmeta.deploy_options("production", [{"type": "Flow", "name": "F"}])
    assert "testLevel" not in o


def test_no_test_run_is_refused_in_production():
    with pytest.raises(sfmeta.MetaError):
        sfmeta.deploy_options("production", [{"type": "ApexClass", "name": "A"}], test_level="NoTestRun")


def test_validate_is_check_only_and_deploy_is_not():
    assert sfmeta.deploy_options("test", [{"type": "Flow", "name": "F"}])["checkOnly"] is False
    # validate() flips exactly that one flag - the dry run and the real run are the same package
    import inspect
    src = inspect.getsource(sfmeta.validate)
    assert 'opts["checkOnly"] = True' in src


def test_an_unknown_metadata_type_is_refused():
    with pytest.raises(sfmeta.MetaError):
        sfmeta.package_xml([{"type": "SomethingInvented", "name": "X"}])


# ---------------------------------------------------------------- the honesty fixes
def test_the_caps_name_the_real_gate():
    """v0.358's cap text named the WRONG gate twice. The RBI Master Direction defines an FIU as an entity
    "registered with and regulated by any financial sector regulator" - not a licence, and not something an
    audit buys. The Rs 2 crore and the biennial CISA audit belong to the AA licence, a different thing."""
    bank = R.ROLES["bank_int"]["cap"]
    assert "FIU" in bank and "regulator" in bank.lower()
    assert "2 crore" not in bank and "licence aur" not in bank
    assert "Sahamati ka empanelled audit" not in bank      # it is a conformance certification, not an audit


def test_the_health_cap_does_not_assert_what_we_could_not_verify():
    """The ABDM/NHA documents could not be read from a primary source, and the vendor sources contradict each
    other on CERT-In vs STQC. So the cap says the requirement is unverified instead of stating it as fact."""
    cap = R.ROLES["health_int"]["cap"]
    assert "NAHI hai" in cap or "nahi" in cap
    assert "jaancha" in cap
    assert "CERT-In empanelled security audit pehle paas karna padta hai" not in cap


def test_teamcenter_stays_read_only_for_the_right_reason():
    """The old reason was FALSE: Siemens documents an official external read+write route (Teamcenter Services
    SOA, with Item/ItemRevision, BOM and ChangeManagement operations). We stay read-only because we do not
    speak SOA and its REST surface is generated per installation - not because Siemens forbids it."""
    assert R.SYSTEMS["teamcenter"]["how"] == "read_only"
    note = R.SYSTEMS["teamcenter"]["note"]
    assert "SOA" in note
    rule = " ".join(R.ROLES["plm"]["rules"])
    assert "SOA" in rule
    assert "jaanche bina" not in rule                      # the old, false reason is gone


def test_every_role_and_desk_survived():
    assert len(R.ROLES) == 10
    assert sum(len(v) for v in R.JOBS.values()) == 90
    assert set(R.CAPPED) == {"health_int", "bank_int", "regtech"}


# ---------------------------------------------------------------- Composio: the slug and the two call bugs
def test_toolkit_of_handles_a_toolkit_whose_own_slug_has_an_underscore():
    """The defect: 525 of Composio's 1,694 toolkit slugs contain an underscore, so `slug.split("_")[0]` named
    a toolkit that does not exist and the call died with "<app> juda nahi hai" even when her account WAS
    connected. Longest known prefix wins instead."""
    from app.bazar import composio as cmp
    known = {"zoho": 1, "zoho_books": 1, "salesforce": 1, "salesforce_service_cloud": 1, "netsuite": 1}
    cmp.TOOL_CACHE.clear()
    orig = cmp.toolkits
    cmp.toolkits = lambda: known                                     # type: ignore[assignment]
    try:
        assert cmp.toolkit_of("ZOHO_BOOKS_CREATE_INVOICE") == "zoho_books"
        assert cmp.toolkit_of("ZOHO_GET_RECORDS") == "zoho"
        assert cmp.toolkit_of("SALESFORCE_SERVICE_CLOUD_CREATE_CASE") == "salesforce_service_cloud"
        assert cmp.toolkit_of("NETSUITE_CREATE_INVOICE") == "netsuite"
        assert cmp.toolkit_of("ZOHO_BOOKS_CREATE_INVOICE").split("_")[0] == "zoho"   # the OLD answer, wrong
    finally:
        cmp.toolkits = orig                                          # type: ignore[assignment]


def test_a_read_on_such_a_toolkit_is_no_longer_misread_as_a_write():
    """Knock-on of the same bug: with a truncated toolkit the head could not be stripped, so the first word
    was never a read verb and every read became an approval card."""
    from app.bazar import composio as cmp
    orig = cmp.toolkits
    cmp.toolkits = lambda: {"zoho_books": 1, "zoho": 1}              # type: ignore[assignment]
    try:
        assert cmp.is_read("ZOHO_BOOKS_LIST_INVOICES") is True
        assert cmp.is_read("ZOHO_BOOKS_CREATE_INVOICE") is False
        assert cmp.is_read("ZOHO_BOOKS_LIST_INVOICES", "zoho") is False   # the old, wrong toolkit
    finally:
        cmp.toolkits = orig                                          # type: ignore[assignment]


def test_the_execute_body_no_longer_sends_the_rejected_version_string():
    """Composio documents the literal "latest" as the one form REJECTED for direct execution; omitting the
    field selects latest. We used to send it, so every ERP write could fail on a version error."""
    import inspect
    from app.bazar import composio as cmp
    src = inspect.getsource(cmp.Client.execute)
    assert '"version": "latest"' not in src
    assert '"user_id": user_id' in src


def test_an_unclear_composio_answer_is_never_counted_as_success():
    """It used to default to TRUE when the field was missing, so a changed response shape would report a
    FAILED write as done - and the row's idempotency key would then mark it complete for ever."""
    from app.enterprise import run as RUN
    assert 'out.get("successful", out.get("success", True))' not in open(
        "app/enterprise/run.py").read()
    assert hasattr(RUN, "Ambiguous")


def test_a_timeout_is_parked_not_retried():
    """Composio does not retry a non-idempotent write and says an ambiguous timeout must be resolved by
    reading the provider's state. A retry could post the same record twice, so the row waits for her."""
    from app.enterprise import run as RUN
    assert RUN._looks_timeout(Exception("Read timed out"))
    assert RUN._looks_timeout(TimeoutError("boom"))
    assert not RUN._looks_timeout(ValueError("bad field"))
    # and an ambiguous row is excluded from the retry set by construction
    src = open("app/enterprise/run.py").read()
    assert 'EntRunRow.status.in_(("todo", "failed"))' in src
    assert '"ambiguous"' in src


def test_salesforce_tooling_is_refused_in_production_before_her_tap():
    """Salesforce itself: "CRUD operations on the following Tooling API objects in an active org generate the
    error Save or update not supported in active organizations". So this was NEVER going to work in her live
    org - and saying so at plan time, not after her tap, is the whole fix."""
    from app.enterprise import run as RUN
    with pytest.raises(RUN.RunError) as e:
        RUN._guard_target("salesforce", "tooling", "production", "CustomField", "odata")
    assert "Metadata" in str(e.value)
    # a sandbox is fine for the same object
    RUN._guard_target("salesforce", "tooling", "test", "CustomField", "odata")


def test_the_types_with_no_tooling_write_path_are_refused_in_every_org():
    from app.enterprise import run as RUN
    for t in ("CustomObject", "Profile", "PermissionSet", "Layout"):
        for env in ("test", "production"):
            with pytest.raises(RUN.RunError):
                RUN._guard_target("salesforce", "tooling", env, t, "odata")


def test_records_are_untouched_by_the_config_guard():
    """The data API is a different surface with different risk - that split is v0.367's point and it stands."""
    from app.enterprise import run as RUN
    RUN._guard_target("salesforce", "data", "production", "Account", "odata")
    RUN._guard_target("sap", "data", "production", "A_SalesOrder", "odata")


def test_cannot_check_a_slug_is_not_the_same_as_the_slug_being_wrong():
    """A bug found in self-review before shipping: with Composio unconfigured, `tool_exists` returned False,
    so the plan guard would have refused EVERY composio-rail run with "no such tool" - blaming her slug for
    our own missing key. Unknown must stay unknown."""
    from app.bazar import composio as cmp
    from app.enterprise import run as RUN
    assert cmp.configured() is False
    assert cmp.tool_exists("NETSUITE_CREATE_INVOICE") is None      # cannot ask
    assert cmp.tool_exists("no spaces allowed!") is False          # definitely not a slug
    RUN._guard_target("netsuite", "data", "test", "NETSUITE_CREATE_INVOICE", "composio")   # must not raise
