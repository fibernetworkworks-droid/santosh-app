"""ROBOTICS DESK: the Robotics Software Engineer's own section, built like the finance desks - its own chat (kind 'robotics') with
the desk block + the robotics tool in view; an arm worked out from its DH table (Franka Panda's zero pose to the millimetre, inverse
kinematics, singularities, payload torques by hand); a URDF checked for what loaders and simulators reject; a ROS 2 graph and tf tree
read from the tools' own output (a remapping mismatch, a QoS that never connects, a split and a stale tf tree); a PID loop tuned
from a recorded step (the fitted model recovers the plant it came from; SIMC gains by the formula); moves planned as trapezoids and
S-curves (phase times by hand, the profile's area is the distance); the CI workflow is valid YAML; walked in a browser."""
from __future__ import annotations

import math
import os

import pytest
import yaml
from fastapi.testclient import TestClient

T = "default"

PANDA = """j1 revolute d=0.333 a=0 alpha=0 min=-166 max=166
j2 revolute d=0 a=0 alpha=-90 min=-101 max=101
j3 revolute d=0.316 a=0 alpha=90 min=-166 max=166
j4 revolute d=0 a=0.0825 alpha=90 min=-176 max=-4
j5 revolute d=0.384 a=-0.0825 alpha=-90 min=-166 max=166
j6 revolute d=0 a=0 alpha=90 min=-1 max=215
j7 revolute d=0 a=0.088 alpha=90 min=-166 max=166
flange d=0.107
"""
URDF = """<robot name="arm">
 <link name="base_link"/>
 <link name="link1"><inertial><mass value="1.2"/><inertia ixx="0.01" iyy="0.01" izz="0.03" ixy="0" ixz="0" iyz="0"/></inertial><visual><geometry><mesh filename="meshes/l1.stl"/></geometry></visual></link>
 <link name="link2"><visual><geometry><box size="1 1 1"/></geometry></visual><collision><geometry><box size="1 1 1"/></geometry></collision></link>
 <link name="tool"/>
 <link name="loose"/>
 <joint name="j1" type="revolute"><parent link="base_link"/><child link="link1"/><axis xyz="0 0 1"/><limit lower="-170" upper="170" effort="10" velocity="1"/></joint>
 <joint name="j2" type="revolute"><parent link="link1"/><child link="link2"/><axis xyz="0 0 0"/></joint>
 <joint name="j3" type="prismatic"><parent link="link2"/><child link="tool"/><limit lower="0" upper="0.1" effort="0" velocity="0.1"/></joint>
</robot>
"""
GOOD_URDF = """<robot name="good">
 <link name="base_link"/>
 <link name="link1"><inertial><mass value="1.2"/><inertia ixx="0.01" iyy="0.01" izz="0.005" ixy="0" ixz="0" iyz="0"/></inertial><collision><geometry><cylinder radius="0.05" length="0.3"/></geometry></collision></link>
 <joint name="j1" type="revolute"><parent link="base_link"/><child link="link1"/><axis xyz="0 0 1"/><limit lower="-2.9" upper="2.9" effort="40" velocity="2"/></joint>
</robot>
"""
GRAPH = '/camera_driver\n  Subscribers:\n    /parameter_events: rcl_interfaces/msg/ParameterEvent\n  Publishers:\n    /camera/image_raw: sensor_msgs/msg/Image\n    /scan: sensor_msgs/msg/LaserScan\n    /rosout: rcl_interfaces/msg/Log\n  Service Servers:\n    /camera_driver/describe_parameters: rcl_interfaces/srv/DescribeParameters\n  Service Clients:\n\n  Action Servers:\n\n  Action Clients:\n\n/detector\n  Subscribers:\n    /image_raw: sensor_msgs/msg/Image\n    /scan: sensor_msgs/msg/LaserScan\n  Publishers:\n    /detections: vision_msgs/msg/Detection2DArray\n  Service Servers:\n\n  Service Clients:\n    /set_mode: std_srvs/srv/SetBool\n  Action Servers:\n\n  Action Clients:\n    /navigate_to_pose: nav2_msgs/action/NavigateToPose\n$ ros2 topic info -v /scan\nType: sensor_msgs/msg/LaserScan\n\nPublisher count: 1\n\nNode name: camera_driver\nNode namespace: /\nTopic type: sensor_msgs/msg/LaserScan\nEndpoint type: PUBLISHER\nGID: 01.0f\nQoS profile:\n  Reliability: BEST_EFFORT\n  History (Depth): KEEP_LAST (5)\n  Durability: VOLATILE\n  Lifespan: Infinite\n  Deadline: Infinite\n  Liveliness: AUTOMATIC\n  Liveliness lease duration: Infinite\n\nSubscription count: 1\n\nNode name: detector\nNode namespace: /\nTopic type: sensor_msgs/msg/LaserScan\nEndpoint type: SUBSCRIPTION\nGID: 01.0f\nQoS profile:\n  Reliability: RELIABLE\n  History (Depth): KEEP_LAST (10)\n  Durability: VOLATILE\n  Lifespan: Infinite\n  Deadline: Infinite\n  Liveliness: AUTOMATIC\n  Liveliness lease duration: Infinite\n'
TF = "map:\n  parent: 'world'\n  broadcaster: 'static_tf'\n  rate: 10000.0\n  most_recent_transform: 0.0\nodom:\n  parent: 'map'\n  broadcaster: 'amcl'\n  rate: 20.1\n  most_recent_transform: 1700000010.2\nbase_link:\n  parent: 'odom'\n  broadcaster: 'ekf'\n  rate: 30.0\n  most_recent_transform: 1700000010.3\nlaser:\n  parent: 'base_link'\n  broadcaster: 'robot_state_publisher'\n  rate: 10000.0\n  most_recent_transform: 0.0\ncamera_link:\n  parent: 'base'\n  broadcaster: 'cam'\n  rate: 5.0\n  most_recent_transform: 1700000002.0\n"
MOVE = "x 0.5m vmax=1 amax=2\ny 0.2m vmax=1 amax=2 jerk=20\nj1 90deg vmax=180 amax=360 jerk=3600 inertia=0.5 torque=2\nz 0.1m vmax=0.5 amax=5 mass=10 force=80 vertical=1\n"


def step_csv(K=2.0, tau=10.0, theta=2.0, t0=5.0, n=800, dt=0.1):
    rows = ["time,speed,command"]
    for i in range(n):
        t = i * dt
        y = K * (1 - math.exp(-(t - t0 - theta) / tau)) if t > t0 + theta else 0.0
        rows.append(f"{t:.2f},{y:.5f},{1 if t >= t0 else 0}")
    return "\n".join(rows)


def closed_csv(z=0.2, wn=2.0):
    rows = ["t,y,sp"]
    w = wn * math.sqrt(1 - z * z)
    for i in range(600):
        t = i * 0.02
        tt = t - 1
        y = 0.0 if tt < 0 else 1 - math.exp(-z * wn * tt) * (math.cos(w * tt) + z / math.sqrt(1 - z * z) * math.sin(w * tt))
        rows.append(f"{t},{y},{1 if t >= 1 else 0}")
    return "\n".join(rows)


@pytest.fixture
def rbc(env):
    from app import robochat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "robotics_eng", trust="seekh")


# ---------------------------------------------------------------- the engine (pure code)
def test_arm_and_urdf():
    from app.rbdesk import arm as A, urdf as U
    z = A.analyse(PANDA, "0 0 0 0 0 0 0", mode="modified")
    assert z["pose"]["xyz"] == [0.088, 0.0, 0.926] and z["pose"]["rpy"][0] == 180.0          # Franka's published zero pose
    assert z["near_singular"] and z["rank"] == 5 and any(i["area"] == "Limits" and "j4" in i["text"] for i in z["issues"])
    r = A.analyse(PANDA, "0 -30 0 -120 0 90 45", "0.4 0.1 0.5 180 0 0", 2, "modified")
    assert r["ik"]["ok"] and r["ik"]["pos_err_mm"] < 0.1 and r["ik"]["ori_err_deg"] < 0.05 and not any(j["out"] for j in r["ik"]["q"])
    chk = A.analyse(PANDA, " ".join(str(j["value"]) for j in r["ik"]["q"]), mode="modified")           # the solution really lands there
    assert [round(v, 3) for v in chk["pose"]["xyz"]] == [0.4, 0.1, 0.5]
    two = A.analyse("l1 revolute a=1\nl2 revolute a=1", "0 90", "1.2 0.8 0")
    assert two["pose"]["xyz"] == [1.0, 1.0, 0.0] and two["ik"]["ok"]
    q1, q2 = (math.radians(j["value"]) for j in two["ik"]["q"])
    assert abs(math.cos(q1) + math.cos(q1 + q2) - 1.2) < 1e-3 and abs(math.sin(q1) + math.sin(q1 + q2) - 0.8) < 1e-3
    tq = A.analyse("base revolute d=0.4 alpha=90\nshoulder revolute a=0.5\nelbow revolute a=0.4", "0 0 0", "", 3)
    t = {x["name"]: x["value"] for x in tq["torque"]}
    assert t["shoulder"] == round(-3 * 9.80665 * 0.9, 3) and t["elbow"] == round(-3 * 9.80665 * 0.4, 3) and t["base"] == 0.0
    far = A.analyse("l1 revolute a=1\nl2 revolute a=1", "0 90", "3 0 0")
    assert far["ik"]["ok"] is False and any("farther than the arm reaches" in i["text"] for i in far["issues"])
    mm = A.analyse("l1 revolute a=1000\nl2 revolute a=1000", "0 90", length_unit="mm")
    assert mm["pose"]["xyz"] == [1.0, 1.0, 0.0]
    for bad in ("", "j1 revolute q=3", "j1 revolute min=10 max=5", "tool d=1\nj1 revolute"):
        with pytest.raises(A.ArmError):
            A.analyse(bad)
    with pytest.raises(A.ArmError):
        A.analyse(PANDA, "0 0 0")
    u = U.check(URDF)
    bad = [i["text"] for i in u["issues"] if i["sev"] == "bad"]
    assert any("triangle inequality" in t for t in bad) and any("look like degrees" in t for t in bad) and any("axis is zero" in t for t in bad)
    assert any("no <limit>" in t for t in bad) and any("effort must be above 0" in t for t in bad) and any("2 links have no parent" in t for t in bad)
    assert any("link2 moves on a joint but has no <inertial>" in t for t in bad)
    assert any("plain path" in i["text"] for i in u["issues"]) and [n["name"] for n in u["tree"] if n["depth"] == 3] == ["tool"]
    g = U.check(GOOD_URDF)
    assert g["counts"]["bad"] == 0 and g["counts"]["warn"] == 0 and g["mass"] == 1.2 and g["verdict"].endswith("loads as one tree")
    for bad in ("", "<robot><link name='a'/>", "<!DOCTYPE x [<!ENTITY a 'b'>]><robot/>", '<robot><xacro:macro name="x"/></robot>', "<model/>"):
        with pytest.raises(U.UrdfError):
            U.check(bad)


def test_graph_and_tf():
    from app.rbdesk import rosgraph as G
    r = G.analyse(GRAPH)
    bad = [i for i in r["issues"] if i["sev"] == "bad"]
    assert any("/image_raw" in i["text"] and "/camera/image_raw" in i["text"] for i in bad)
    assert any(i["area"] == "QoS" and "RELIABLE" in i["text"] and "BEST_EFFORT" in i["text"] for i in bad)
    assert any("service /set_mode" in i["text"] for i in r["issues"]) and any("action /navigate_to_pose" in i["text"] for i in r["issues"])
    assert [q for q in r["qos"] if not q["ok"]][0]["topic"] == "/scan" and len(r["nodes"]) == 2
    assert not any("describe_parameters" in s["name"] for s in r["services"])
    t = G.analyse(TF)
    assert t["tf_roots"] == ["base", "world"] and any("split into 2 trees" in i["text"] for i in t["issues"])
    assert any("camera_link stopped" in i["text"] for i in t["issues"]) and {x["child"] for x in t["tf"] if x["static"]} == {"map", "laser"}
    gv = 'digraph G {\n"map" -> "odom"[label=" Broadcaster: a\\nAverage rate: 10.2\\nMost recent transform: 1700.1\\n"];\n"odom" -> "base_link"[label="Broadcaster: b\\nAverage rate: 50\\nMost recent transform: 1700.1\\n"];\n}'
    v = G.analyse(gv)
    assert v["counts"]["bad"] == 0 and v["tf_roots"] == ["map"] and len(v["tf"]) == 2
    loop = G.analyse("a:\n  parent: 'b'\nb:\n  parent: 'a'\n")
    assert any("loop" in i["text"] for i in loop["issues"])
    dup = G.analyse("/n\n  Publishers:\n    /x: std_msgs/msg/Int32\n/n\n  Subscribers:\n    /x: std_msgs/msg/String\n")
    assert any("Two nodes are named /n" in i["text"] for i in dup["issues"]) and any(i["area"] == "Types" for i in dup["issues"])
    with pytest.raises(G.GraphError):
        G.analyse("hello")


def test_control_motion_ci():
    from app.rbdesk import ci as CI, control as C, motion as M
    r = C.analyse(step_csv())
    md = r["model"]
    assert abs(md["K"] - 2) < 0.02 and abs(md["tau"] - 10) < 0.1 and abs(md["theta"] - 2) < 0.1 and md["fit_pct"] < 1
    tn = {t["name"]: t for t in r["tunings"]}
    tight = tn["SIMC tight"]
    assert abs(tight["Kc"] - md["tau"] / (md["K"] * 2 * md["theta"])) < 1e-9 and abs(tight["Ti"] - min(md["tau"], 8 * md["theta"])) < 1e-9
    assert tight["stable"] and tight["overshoot"] < 10 and tn["SIMC smooth"]["overshoot"] < tight["overshoot"] and tn["Ziegler-Nichols (reaction curve)"]["overshoot"] > 30
    assert abs(tight["i"] - tight["p"] / tight["Ti"]) < 1e-12 and not r["closed"]
    y = C.analyse(step_csv(), kp=3, ki=1)
    assert y["yours"]["stable"] is False and any(i["area"] == "Your gains" for i in y["issues"])
    c = C.analyse(closed_csv())
    m = c["metrics"]
    assert c["closed"] and abs(m["overshoot"] - 100 * math.exp(-math.pi * 0.2 / math.sqrt(1 - 0.04))) < 1.5 and "model" not in c and c["model_note"]
    assert any(i["area"] == "Overshoot" for i in c["issues"])
    for bad in ("", "t,y\n1,2\n2,3", "t,y\n" + "\n".join(f"{i},1" for i in range(20)), "t,y\n" + "\n".join(f"{-i},{i}" for i in range(20))):
        with pytest.raises(C.ControlError):
            C.analyse(bad)
    p = M.plan(2, 1, 1, None)
    assert p["T"] == 3.0 and p["Ta"] == 1.0 and p["Tv"] == 1.0 and p["full"]
    tri = M.plan(1, 2, 1, None)
    assert abs(tri["T"] - 2.0) < 1e-6 and not tri["full"] and abs(tri["vp"] - 1.0) < 1e-6
    s = M.plan(2, 1, 1, 10)
    assert abs(s["T"] - 3.1) < 1e-9 and abs(s["Tj"] - 0.1) < 1e-9
    curve = M.profile(s, 2, 2000)
    area = sum((b[0] - a[0]) * (a[1] + b[1]) / 2 for a, b in zip(curve, curve[1:]))
    assert abs(area - 2) < 1e-3
    r = M.analyse(MOVE)
    ax = {a["name"]: a for a in r["axes"]}
    assert r["slowest"] == "j1" and abs(r["T"] - ax["j1"]["T"]) < 1e-12 and ax["x"]["scaled_v"] < 1
    assert all(abs(M.plan(a["d"], a["vp"], a["amax"], a["jerk"])["T"] - r["T"]) < 1e-6 for a in r["axes"])
    drive = [i for i in r["issues"] if i["area"] == "Drive" and i["sev"] == "bad"]
    assert {i["fn"] for i in drive} == {"j1", "z"} and abs(ax["z"]["need"]["value"] - 10 * (5 + 9.80665)) < 1e-6
    assert abs(ax["j1"]["need"]["value"] - 0.5 * math.radians(360)) < 1e-9
    for bad in ("", "x vmax=1 amax=1", "x 1m vmax=1", "x 1m vmax=0 amax=1", "x 1m vmax=1 amax=1 speed=4"):
        with pytest.raises(M.MotionError):
            M.analyse(bad)
    w = CI.workflow("jazzy", "my_robot my_robot_bringup", "my_robot_description/urdf/robot.urdf.xacro", "", "ros-jazzy-ros2-control")
    y = yaml.safe_load(w["yaml"])
    steps = y["jobs"]["build"]["steps"]
    assert y["permissions"] == {"contents": "read"} and y["jobs"]["build"]["runs-on"] == "ubuntu-24.04"
    assert steps[0]["uses"].startswith("ros-tooling/setup-ros@") and any(s.get("uses", "").startswith("ros-tooling/action-ros-ci@") for s in steps)
    assert "check_urdf" in w["yaml"] and CI.workflow("humble", "a_b")["runner"] == "ubuntu-22.04"
    for bad in (dict(packages=""), dict(packages="My-Pkg"), dict(distro="noetic", packages="a"), dict(packages="a", urdf="../x"), dict(packages="a", extra_deps="x; rm")):
        with pytest.raises(CI.CiError):
            CI.workflow(**bad)


def test_hire_chat_wiring_store_and_guards(rbc):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert rbc.summary(T)["hired"] is False and "Hire me from AI Employees" in rbc.greeting(T)
    with pytest.raises(PermissionError):
        rbc.do(T, "add", {"kind": "arm", "text": PANDA})
    _hire()
    d = rbc.summary(T)
    assert d["hired"] and "runs nothing on your robots" in d["foot"] and {n["go"] for n in d["desk"]["needs"]} >= {"arm", "settings"}
    chat = rbc.current(T)
    assert rbc.is_robotics(chat["id"]) and rbc.owns(T, chat["id"]) and "<robotics_desk>" in rbc.block(T)
    s_ = (root / "server/app/agent/santosh.py").read_text()
    assert "_rbc.is_robotics(conversation_id)" in s_ and "adm.admit_families(_rbc.FAMILIES)" in s_
    for f_ in ("callconv.py", "convs.py"):
        assert '"robotics"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/robotics")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "rbdesk.js" in r.text
    html = (root / "server/app/static/console/rbdesk.html").read_text()
    for x in ("chatkit.js", "rbdesk.css", "rbdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/robotics')" in (root / "server/app/static/console/v2.js").read_text()
    assert "robotics_eng: 'rbdesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["robotics_eng"]["live"] is True
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF["robotics_desk"] in rbc.FAMILIES and "robotics_desk" in HANDLERS
    a1 = rbc.do(T, "add", {"kind": "arm", "text": PANDA, "inputs": {"dh": "modified", "q": "0 -30 0 -120 0 90 45", "target": "0.4 0.1 0.5 180 0 0", "payload": 2}})
    assert a1["number"] == "A-0001" and a1["brief"]["ik"] is True and a1["brief"]["dof"] == 7 and a1["result"]["torque"]
    bad_arm = rbc.do(T, "add", {"kind": "arm", "text": "l1 revolute a=1\nl2 revolute a=1", "inputs": {"target": "3 0 0"}})
    assert bad_arm["brief"]["ik"] is False and bad_arm["brief"]["bad"]
    assert any(n["go"] == "arm/" + bad_arm["id"] and "not reached" in n["say"] for n in rbc.summary(T)["desk"]["needs"])
    u1 = rbc.do(T, "add", {"kind": "urdf", "text": URDF})
    assert u1["number"] == "U-0001" and u1["brief"]["bad"] and u1["result"]["link_rows"][1]["mass"] == 1.2
    import json
    json.dumps(u1)                                  # no NaN reaches the page
    g1 = rbc.do(T, "add", {"kind": "graph", "text": GRAPH + "\n" + TF})
    assert g1["number"] == "G-0001" and g1["brief"]["nodes"] == 2 and g1["brief"]["frames"] == 5
    c1 = rbc.do(T, "add", {"kind": "control", "text": step_csv()})
    assert c1["number"] == "C-0001" and c1["brief"]["model"] and c1["title"] == "Control: open loop, 0% overshoot"
    m1 = rbc.do(T, "add", {"kind": "motion", "text": MOVE})
    assert m1["number"] == "V-0001" and m1["brief"]["axes"] == 4 and m1["brief"]["bad"]
    m2 = rbc.do(T, "add", {"kind": "motion", "text": MOVE, "inputs": {"sync": "no"}})
    assert m2["result"]["sync"] is False and all(a["scaled_v"] is None for a in m2["result"]["axes"])
    assert rbc.do(T, "ci", {})["missing"] is True
    st = rbc.do(T, "settings", {"dh": "modified", "ros_distro": "humble", "packages": "my_robot", "urdf_path": "desc/robot.urdf", "payload_kg": 1.5})
    assert st["dh"] == "modified" and st["payload_kg"] == 1.5
    w = rbc.do(T, "ci", {})
    assert "ros-tooling/action-ros-ci" in w["yaml"] and yaml.safe_load(w["yaml"]) and w["runner"] == "ubuntu-22.04"
    rbc.forget(T)
    assert "DH tables modified" in rbc.block(T) and "ROS 2 humble" in rbc.block(T)
    a2 = rbc.do(T, "add", {"kind": "arm", "text": PANDA, "inputs": {"q": "0 0 0 -90 0 90 0"}})
    assert a2["result"]["mode"] == "modified" and a2["result"]["payload"] == 1.5
    mk = rbc.do(T, "mark", {"id": bad_arm["id"], "status": "fixed"})
    assert mk["status"] == "fixed" and not any(n["go"] == "arm/" + bad_arm["id"] for n in rbc.summary(T)["desk"]["needs"])
    import asyncio
    from app.agent import robotics_tools as RT
    from app.agent.tools import Ctx
    out = asyncio.run(RT.robotics_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="arm", text=PANDA, inputs={"q": "0 0 0 0 0 0 0"}))
    assert out["pose"]["xyz"] == [0.088, 0.0, 0.926] and out["near_singular"]
    out = asyncio.run(RT.robotics_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="control", text=step_csv()))
    assert out["tunings"][0]["name"] == "SIMC tight" and out["tunings"][0]["stable"]
    out = asyncio.run(RT.robotics_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="ci"))
    assert out["file"] == ".github/workflows/ros2-ci.yml"
    with pytest.raises(PermissionError):
        rbc.do(T, "settings", {"packages": "my password is hunter2"})
    assert rbc.do(T, "add", {"kind": "urdf", "text": GOOD_URDF.replace("<robot", "<!-- password = hunter2 --><robot")})["kind"] == "urdf"
    for bad in ({"dh": "weird"}, {"ros_distro": "noetic"}, {"packages": "Bad-Name"}, {"payload_kg": -1}, {"length_unit": "ft"}, {"sync": "maybe"}):
        with pytest.raises((rbc.RbDeskError, PermissionError)):
            rbc.do(T, "settings", bad)
    with pytest.raises(rbc.RbDeskError):
        rbc.do(T, "add", {"kind": "motion", "text": ""})
    with pytest.raises(rbc.RbDeskError):
        rbc.do(T, "nope", {})
    from app.employee import hire as H
    H.pause(T, "robotics_eng")
    assert rbc.do(T, "get", {"id": a1["id"]})["id"] == a1["id"] and rbc.do(T, "ci", {})["yaml"]
    with pytest.raises(PermissionError):
        rbc.do(T, "add", {"kind": "arm", "text": PANDA})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def rb_server(rbc, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    if not os.environ.get("HOOLA_CHROMIUM"):
        pytest.skip("set HOOLA_CHROMIUM for the browser walk")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    _hire()
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        _t.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        browser = pw.chromium.launch(executable_path=os.environ["HOOLA_CHROMIUM"])
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_desk_in_a_real_browser(rbc, rb_server):
    base, browser, key = rb_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    def put(pg, form, name, text):
        pg.eval_on_selector(f"form[data-form={form}] [name={name}]", "(el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles: true})); }", text)

    def submit(pg, form, text, sel):
        put(pg, form, "text", text)
        pg.click(f"form[data-form={form}] [type=submit]")
        pg.wait_for_selector(sel, timeout=60000)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append("console: " + m.text))
    pg.goto(base + "/console/robotics")
    pg.wait_for_selector(".rbk-path", timeout=20000)
    snap(pg, "rb-today-empty-1440")
    go(pg, "#/arm", "form[data-form=arm]")
    pg.select_option("form[data-form=arm] [name=dh]", "modified")
    put(pg, "arm", "q", "0 -30 0 -120 0 90 45")
    put(pg, "arm", "target", "0.4 0.1 0.5 180 0 0")
    put(pg, "arm", "payload", "2")
    submit(pg, "arm", PANDA, ".rbk-armv svg")
    assert pg.locator(".rbk-armv circle").count() == 18 and "Reaching the target" in pg.inner_text("#rbPage") and "Holding 2 kg" in pg.inner_text("#rbPage")
    snap(pg, "rb-arm-1440")
    go(pg, "#/model", "form[data-form=urdf]")
    submit(pg, "urdf", URDF, ".rbk-tree")
    assert "triangle inequality" in pg.inner_text("#rbPage") and pg.locator(".rbk-node").count() == 5
    snap(pg, "rb-model-1440")
    go(pg, "#/graph", "form[data-form=graph]")
    submit(pg, "graph", GRAPH + "\n" + TF, ".rbk-graph svg")
    assert pg.locator(".rbk-graph path.e").count() >= 4 and "never" in pg.inner_text("#rbPage") and "camera_link" in pg.inner_text(".rbk-tree >> nth=0")
    snap(pg, "rb-graph-1440")
    go(pg, "#/control", "form[data-form=control]")
    submit(pg, "control", step_csv(), ".rbk-chart svg")
    assert pg.locator(".rbk-chart polyline").count() == 4 and "SIMC tight" in pg.inner_text("#rbPage")
    snap(pg, "rb-control-1440")
    go(pg, "#/control", "form[data-form=control]")
    submit(pg, "control", closed_csv(), ".rbk-chart svg")
    assert "Offset" in pg.inner_text(".cs-hero")
    go(pg, "#/motion", "form[data-form=motion]")
    submit(pg, "motion", MOVE, ".rbk-chart svg")
    assert pg.locator(".rbk-chart polyline").count() == 4 and "set by j1" in pg.inner_text(".cs-hero")
    snap(pg, "rb-motion-1440")
    go(pg, "#/ci", "text=Set the ROS 2 version")
    go(pg, "#/settings", "form[data-form=settings]")
    pg.fill("form[data-form=settings] [name=packages]", "my_robot my_robot_bringup")
    pg.fill("form[data-form=settings] [name=urdf_path]", "my_robot_description/urdf/robot.urdf.xacro")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved')", timeout=20000)
    go(pg, "#/ci", "text=ros2-ci.yml")
    assert "action-ros-ci" in pg.inner_text("#rbPage")
    snap(pg, "rb-ci-1440")
    go(pg, "#/today", ".rbk-list")
    assert "7" in pg.inner_text(".cs-hero")
    snap(pg, "rb-today-1440")
    for route, sel in (("#/today", ".rbk-list"), ("#/arm", ".rbk-item"), ("#/model", ".rbk-item"), ("#/graph", ".rbk-item"), ("#/control", ".rbk-item"),
                       ("#/motion", ".rbk-item"), ("#/ci", "text=ros2-ci.yml"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('#rbPage *')].filter(e => !e.closest('pre,textarea,table,svg') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
    for route in ("#/arm", "#/model", "#/graph", "#/control", "#/motion"):
        go(pg, route, ".rbk-item")
        pg.locator(".rbk-item").first.click()
        pg.wait_for_selector(".rbk-head", timeout=20000)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        assert w[0] <= w[1] + 1, (route, w)
        snap(pg, "rb-" + route[2:] + "-390")
    assert not errs, errs
