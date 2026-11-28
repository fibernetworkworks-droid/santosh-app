"""EMBEDDED DESK: the Embedded Systems Engineer's own section, built like the finance desks - its own chat (kind 'embedded') with
the desk block + the embedded tool in view; a linker map read into regions, objects, symbols and library pulls, and compared with an
older build; firmware checked for interrupt safety and unprotected shared data; RTOS task sets checked by response-time analysis
(the textbook case to the microsecond); battery life from the device's states; exact clock dividers; the CI workflow is valid YAML
and its size check really fails a pull request that grows too much; walked in a browser."""
from __future__ import annotations

import os
import subprocess
import sys

import pytest
import yaml
from fastapi.testclient import TestClient

T = "default"

MAP = """Archive member included to satisfy reference by file (symbol)

/usr/lib/arm-none-eabi/newlib/thumb/v7e-m/libc_nano.a(lib_a-printf.o)
                              build/main.o (printf)

Memory Configuration

Name             Origin             Length             Attributes
FLASH            0x0000000008000000 0x0000000000010000 xr
RAM              0x0000000020000000 0x0000000000005000 xrw
*default*        0x0000000000000000 0xffffffffffffffff

Linker script and memory map

.isr_vector     0x0000000008000000      0x188
 *(.isr_vector)
 .isr_vector    0x0000000008000000      0x188 build/startup.o
                0x0000000008000000                g_pfnVectors

.text           0x0000000008000188     0xe000
 *(.text)
 .text          0x0000000008000188       0x40 build/startup.o
                0x0000000008000188                Reset_Handler
 .text.main     0x00000000080001c8      0x200 build/main.o
                0x00000000080001c8                main
 .text.SysTick_Handler
                0x00000000080003c8       0x40 build/main.o
                0x00000000080003c8                SysTick_Handler
 .text          0x0000000008000408     0x2000 /usr/lib/arm-none-eabi/newlib/thumb/v7e-m/libc_nano.a(lib_a-printf.o)
                0x0000000008000408                printf
                0x0000000008000800                _vfprintf_r
 .text          0x0000000008002408      0x600 /usr/lib/gcc/arm-none-eabi/13/thumb/libgcc.a(_arm_muldf3.o)
                0x0000000008002408                __aeabi_dmul
 *fill*         0x0000000008002a08      0x300 
 .text.big      0x0000000008002d08     0xb478 build/drivers.o
                0x0000000008002d08                Driver_Table

.rodata         0x000000000800e188      0x100
 .rodata        0x000000000800e188      0x100 build/main.o

.data           0x0000000020000000       0x40 load address 0x000000000800e288
 .data          0x0000000020000000       0x40 build/main.o
                0x0000000020000000                g_config

.bss            0x0000000020000040     0x2400
 .bss.rx_buf    0x0000000020000040     0x2000 build/uart.o
                0x0000000020000040                rx_buf
 .bss           0x0000000020002040      0x400 build/main.o
                0x0000000020002040                counter

._user_heap_stack
                0x0000000020002440      0x600
                0x0000000020002a40                . = (. + 0x400)

.debug_info     0x0000000000000000    0x12345
 .debug_info    0x0000000000000000    0x12345 build/main.o
"""
FW = """#include "stm32f4xx_hal.h"
#include "FreeRTOS.h"
#define BUF_LEN 1024

uint32_t tick_count;
volatile uint8_t rx_ready = 0;
uint64_t uptime_us;
static QueueHandle_t q;

static int fact(int n) { return n <= 1 ? 1 : n * fact(n - 1); }

void USART2_IRQHandler(void)
{
    char *p = malloc(16);
    tick_count++;
    rx_ready = 1;
    uptime_us += 10;
    printf("rx\n");
    xQueueSend(q, &p, 0);
    HAL_Delay(5);
}

void HAL_GPIO_EXTI_Callback(uint16_t pin)
{
    float v = 1.5;
    log_event(pin);
}

void log_event(uint16_t pin) { char line[32]; sprintf(line, "%u", pin); }

int main(void)
{
    uint8_t buf[BUF_LEN];
    float k = 2.5;
    HAL_Init();
    while (!(USART2->SR & USART_SR_TXE));
    *(uint32_t *)0x40020014 = 1;
    for (;;) {
        tick_count++;
        if (tick_count > 100) { printf("%f\n", k); }
        uint64_t t = uptime_us;
        __disable_irq();
        tick_count += 2;
        __enable_irq();
    }
}
"""
SIZEA = """build/app.elf  :
section              size        addr
.isr_vector           392   134217728
.text               50000   134218120
.rodata               256   134268120
.data                  64   536870912
.bss                 9216   536870976
._user_heap_stack    1536   536880192
.ARM.attributes        48           0
.comment              110           0
Total               61622
"""
TASKS = "uart_rx isr period=100us wcet=10us\ncontrol period=1ms wcet=250us prio=5\ncomms period=10ms wcet=2ms prio=4 block=100us\nlogger period=100ms wcet=12ms prio=2\n"
BAD_TASKS = "control period=1ms wcet=300us prio=3\nlog period=10ms wcet=4ms prio=5\ncomms 5ms 1ms prio=4\n"
POWER = "sleep 2.5uA\nmeasure 4.5mA 120ms every 60s\nradio tx 45mA 30ms every 10min\nled 5mA 50ms 24 times a day\n"
CLOCKS = "uart 72MHz 115200\nuart 16MHz 115200\ntimer 84MHz 1kHz 16bit\npwm 72MHz 20kHz\nsystick 72MHz 1ms\nspi 48MHz 10MHz\nadc 12bit 3.3V\n"


@pytest.fixture
def emc(env):
    from app import embeddedchat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "embedded_eng", trust="seekh")


# ---------------------------------------------------------------- the engine (pure code)
def test_memory_and_firmware():
    from app.emdesk import firmware as F, memory as M
    r = M.analyse(MAP)
    regs = {x["name"]: x for x in r["regions"]}
    assert r["format"] == "map" and regs["FLASH"]["used"] == 392 + 0xE000 + 0x100 + 0x40 and regs["RAM"]["used"] == 0x40 + 0x2400 + 0x600
    assert regs["FLASH"]["pct"] == 88.6 and regs["RAM"]["pct"] == 52.8
    assert r["objects"][0]["name"] == "drivers.o" and any(o["name"] == "libc_nano.a(lib_a-printf.o)" and o["lib"] for o in r["objects"])
    syms = {s["name"]: s for s in r["symbols"]}
    assert syms["Driver_Table"]["size"] == 0xB478 and syms["rx_buf"]["size"] == 0x2000 and syms["rx_buf"]["where"] == "RAM"
    assert {l["what"] for l in r["libraries"]} >= {"The printf family", "soft double maths"}
    assert next(x for x in r["sections"] if x["name"] == ".data")["where"] == "RAM (copy in FLASH)"
    assert any("alignment padding" in i["text"] for i in r["issues"]) and any("heap and stack" in i["text"] for i in r["issues"])
    s = M.analyse(SIZEA, "64K", "20K", MAP)
    assert s["format"] == "size -A" and s["flash"] == 392 + 50000 + 256 + 64 and s["ram"] == 64 + 9216 + 1536
    assert s["growth"]["flash"] == s["flash"] - r["flash"] and s["growth"]["sections"][0]["name"] == ".text"
    full = M.analyse(SIZEA, "32K", "8K")
    assert any(i["sev"] == "bad" and "over full" in i["text"] for i in full["issues"])
    b = M.analyse("   text    data     bss     dec     hex filename\n  50392      64    9216   59672    e918 build/app.elf\n", "64K", "20K")
    assert b["flash"] == 50456 and b["ram"] == 9280
    assert M.analyse("08000188 00000040 T Reset_Handler\n20000040 00002000 B rx_buf\n")["ram"] == 8192
    for bad in ("", "hello world"):
        with pytest.raises(M.MemError):
            M.analyse(bad)
    with pytest.raises(M.MemError):
        M.analyse(SIZEA, "lots")
    f = F.check(FW)
    assert (f["lang"], f["rtos"], f["platform"]) == ("C", "FreeRTOS", "STM32 HAL")
    assert [x["name"] for x in f["isrs"]] == ["USART2_IRQHandler", "HAL_GPIO_EXTI_Callback", "log_event"] and f["isrs"][2]["why"].startswith("called from")
    rules = {(i["rule"], i["fn"]) for i in f["issues"]}
    for want in [("Memory in an interrupt", "USART2_IRQHandler"), ("RTOS call without FromISR", "USART2_IRQHandler"), ("Waiting in an interrupt", "USART2_IRQHandler"),
                 ("Register access without volatile", "main"), ("Recursion", "fact"), ("Printing in an interrupt", "log_event"), ("Busy wait with no timeout", "main"),
                 ("Read-modify-write not protected", "main"), ("Big array on the stack", "main"), ("Floating point in an interrupt", "HAL_GPIO_EXTI_Callback"),
                 ("Never sleeps", "main"), ("No watchdog", "main"), ("printf with %f", "main"), ("sprintf without a size", "log_event")]:
        assert want in rules, want
    shared = {s["name"]: s for s in f["shared"]}
    assert shared["tick_count"]["volatile"] is False and shared["tick_count"]["unprotected"] == ["main"] and "rx_ready" not in shared or shared["rx_ready"]["volatile"]
    nv = [i for i in f["issues"] if i["rule"] == "Shared without volatile"]
    assert {i["line"] for i in nv} == {5, 7} and any(i["rule"] == "Wide value shared with an interrupt" for i in f["issues"])
    ok = F.check("volatile int f; static volatile int c;\nvoid TIM2_IRQHandler(void){ f=1; c++; }\nint main(void){ __disable_irq(); c++; __enable_irq(); while(1){ __WFI(); HAL_IWDG_Refresh(&h); } }")
    assert ok["counts"]["bad"] == 0 and ok["counts"]["warn"] == 0
    avr = F.check("#include <avr/interrupt.h>\nvolatile uint8_t t;\nISR(TIMER1_COMPA_vect) { t++; _delay_ms(5); }\nint main(void){ for(;;){} }")
    assert avr["isrs"][0]["name"] == "ISR(TIMER1_COMPA_vect)" and any(i["rule"] == "Waiting in an interrupt" for i in avr["issues"])
    ard = F.check("int n;\nvoid onPulse(){ n++; Serial.println(n); }\nvoid setup(){ attachInterrupt(digitalPinToInterrupt(2), onPulse, RISING); }\nvoid loop(){ if (n > 3) n = 0; }")
    assert ard["lang"] == "Arduino" and ard["isrs"][0]["why"] == "registered as an interrupt handler" and any(i["rule"] == "Shared without volatile" for i in ard["issues"])
    with pytest.raises(F.FirmwareError):
        F.check("just words")


def test_timing_power_clocks_ci(tmp_path):
    from app.emdesk import ci as CI, clocks as K, power as P, timing as TM
    r = TM.analyse("t1 7 3\nt2 12 3\nt3 20 5")          # the textbook set (Buttazzo): responses 3, 6, 20 ms
    assert [t["R"] for t in r["tasks"]] == [3000.0, 6000.0, 20000.0] and r["ok"] and r["growth"] == 0 and r["U"] == 92.86
    r = TM.analyse(TASKS, switch_us=2)
    assert r["ok"] and [t["name"] for t in r["tasks"]] == ["uart_rx", "control", "comms", "logger"] and r["growth"] > 0 and r["timeline"] and not r["misses"]
    assert r["tasks"][2]["R"] > r["tasks"][2]["C"] + r["tasks"][2]["B"]
    b = TM.analyse(BAD_TASKS, switch_us=2)
    assert not b["ok"] and b["misses"] and {t["name"] for t in b["tasks"] if not t["ok"]} == {"control", "comms"}
    assert b["deadline_order"]["order"] == ["control", "comms", "log"] and b["deadline_order"]["ok"] is True
    assert any(i["sev"] == "warn" and "everything would meet its deadline" in i["text"] for i in b["issues"])
    z = TM.analyse("a period=10 wcet=2 prio=1\nb period=20 wcet=5 prio=2", prio_order="lower")
    assert [t["name"] for t in z["tasks"]] == ["a", "b"]
    for bad in ("", "x period=1ms", "5 10ms 2ms", "a 1ms 2ms"):
        with pytest.raises(TM.TimingError):
            TM.analyse(bad)
    p = P.analyse(POWER, 230, target="2 years")
    assert round(p["avg_mA"] * 1000, 2) == 13.81 and p["rows"][0]["name"] == "measure" and p["rows"][0]["pct"] == 65.1
    assert p["life"] == "17.6 months" and any("short of the 2.0 years target" in i["text"] for i in p["issues"])
    assert p["whatif"][0]["change"].startswith("measure") and p["whatif"][0]["life"] > p["life_h"]
    assert any("coin cell" in i["text"] for i in p["issues"])
    for bad in ("", "radio 45mA 30ms", "x 5mA every 10s", "a 1mA 2s every 1s"):
        with pytest.raises(P.PowerError):
            P.analyse(bad)
    k = K.analyse(CLOCKS)
    res = {x["title"]: x for x in k["results"]}
    u = res["UART 115200 baud from 72 MHz"]["rows"]
    assert u[0]["setting"].startswith("BRR = 0x271") and abs(u[0]["error"]) < 1e-9
    a = res["UART 115200 baud from 16 MHz"]["rows"]
    assert a[1]["setting"] == "UBRR = 8" and round(a[1]["error"], 2) == -3.55 and a[1]["state"] == "bad"
    t1 = res["Timer 1 kHz from 84 MHz (16-bit)"]
    assert t1["exact"] and t1["rows"][0]["way"] == "PSC = 1, ARR = 41999"
    assert res["PWM 20 kHz from 72 MHz"]["rows"][0]["setting"] == "ARR = 3599" and res["SysTick 1 ms from 72 MHz"]["rows"][0]["setting"] == "LOAD = 71999"
    assert res["SPI at most 10 MHz from 48 MHz"]["rows"][0]["way"] == "/ 8" and "0.8057 mV" in res["ADC 12-bit at 3.3 V"]["rows"][0]["setting"]
    with pytest.raises(K.ClockError):
        K.analyse("blink 1Hz")
    w = CI.workflow("make -j4", "build/fw.elf", "arm", "64K", "20K", 512, "make test")
    y = yaml.safe_load(w["yaml"])
    names = [s.get("name") for s in y["jobs"]["size"]["steps"]]
    assert y["permissions"] == {"contents": "read"} and names[:5] == ["Head", "Base", "Toolchain", "Host tests", "Build both"]
    for bad in (dict(build_cmd=""), dict(build_cmd="make ${{ secrets.X }}"), dict(build_cmd="make", elf="../x.elf"), dict(build_cmd="make", toolchain="pic"),
                dict(build_cmd="make", flash="", ram="", max_growth="")):
        with pytest.raises(CI.CiError):
            CI.workflow(**{"flash": "64K", **bad})
    code = w["compare"].replace("\n          ", "\n").strip()
    (tmp_path / "base.txt").write_text(SIZEA)
    (tmp_path / "head.txt").write_text(SIZEA.replace(".text               50000", ".text               50400"))
    run = lambda: subprocess.run([sys.executable, "-I", "-c", code, str(tmp_path / "base.txt"), str(tmp_path / "head.txt")], capture_output=True, text=True,   # noqa: E731
                                 env={"PATH": os.environ.get("PATH", ""), "GITHUB_STEP_SUMMARY": str(tmp_path / "s.md")})
    assert run().returncode == 0
    (tmp_path / "head.txt").write_text(SIZEA.replace(".text               50000", ".text               60000"))
    out = run()
    assert out.returncode == 1 and "flash grew +10,000 bytes" in out.stdout and "| .text | +10,000 |" in (tmp_path / "s.md").read_text()


def test_hire_chat_wiring_store_and_guards(emc):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert emc.summary(T)["hired"] is False and "Hire me from AI Employees" in emc.greeting(T)
    with pytest.raises(PermissionError):
        emc.do(T, "add", {"kind": "memory", "text": MAP})
    _hire()
    d = emc.summary(T)
    assert d["hired"] and "runs nothing on your boards" in d["foot"] and {n["go"] for n in d["desk"]["needs"]} >= {"memory", "settings"}
    chat = emc.current(T)
    assert emc.is_embedded(chat["id"]) and emc.owns(T, chat["id"]) and "<embedded_desk>" in emc.block(T)
    s_ = (root / "server/app/agent/santosh.py").read_text()
    assert "_emc.is_embedded(conversation_id)" in s_ and "adm.admit_families(_emc.FAMILIES)" in s_
    for f_ in ("callconv.py", "convs.py"):
        assert '"embedded"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/embedded")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "emdesk.js" in r.text
    html = (root / "server/app/static/console/emdesk.html").read_text()
    for x in ("chatkit.js", "emdesk.css", "emdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/embedded')" in (root / "server/app/static/console/v2.js").read_text()
    assert "embedded_eng: 'emdesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["embedded_eng"]["live"] is True
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF["embedded_desk"] in emc.FAMILIES and "embedded_desk" in HANDLERS
    m1 = emc.do(T, "add", {"kind": "memory", "text": MAP})
    assert m1["number"] == "M-0001" and m1["title"] == "Memory: FLASH 88.6%, RAM 52.8%" and m1["brief"]["regions"][0]["pct"] == 88.6
    m2 = emc.do(T, "add", {"kind": "memory", "text": SIZEA, "inputs": {"flash": "64K", "ram": "20K", "before": "M-0001"}})
    assert m2["brief"]["grew"] < 0 and m2["result"]["growth"]["before"]["flash"] == m1["result"]["flash"]
    fw = emc.do(T, "add", {"kind": "firmware", "text": FW})
    assert fw["number"] == "F-0001" and fw["brief"]["isrs"] == 3 and fw["brief"]["bad"]
    assert any(n["go"] == "code/" + fw["id"] for n in emc.summary(T)["desk"]["needs"])
    tm = emc.do(T, "add", {"kind": "timing", "text": BAD_TASKS, "inputs": {"switch_us": 2}})
    assert tm["number"] == "T-0001" and tm["brief"]["miss"] == 2 and tm["brief"]["bad"]
    good = emc.do(T, "add", {"kind": "timing", "text": TASKS, "inputs": {"switch_us": 2}})
    assert good["brief"]["ok"] and emc.summary(T)["desk"]["timing"]["ok"] is True
    pw = emc.do(T, "add", {"kind": "power", "text": POWER, "inputs": {"capacity": 230, "target": "2 years"}})
    assert pw["title"] == "Battery: 13.8 µA average, 17.6 months" and pw["brief"]["life_h"] < pw["brief"]["target_h"]
    ck = emc.do(T, "add", {"kind": "clocks", "text": CLOCKS})
    assert ck["number"] == "K-0001" and ck["brief"]["sums"] == 7
    assert emc.do(T, "ci", {})["missing"] is True
    st = emc.do(T, "settings", {"build_cmd": "make -j4", "flash": "256K", "ram": "64K", "clock": "72MHz", "toolchain": "arm", "max_growth": "1024", "battery_mah": 230,
                               "prio_order": "lower"})
    assert st["flash"] == "256K" and st["prio_order"] == "lower"
    w = emc.do(T, "ci", {})
    assert "arm-none-eabi-size" in w["yaml"] and yaml.safe_load(w["yaml"])
    emc.forget(T)
    assert "flash 256K" in emc.block(T) and "smaller number is more urgent" in emc.block(T)
    k2 = emc.do(T, "add", {"kind": "clocks", "text": "uart 115200"})
    assert "72 MHz" in k2["result"]["results"][0]["title"]
    mk = emc.do(T, "mark", {"id": fw["id"], "status": "fixed"})
    assert mk["status"] == "fixed" and not any(n["go"] == "code/" + fw["id"] for n in emc.summary(T)["desk"]["needs"])
    import asyncio
    from app.agent import embedded_tools as ET
    from app.agent.tools import Ctx
    out = asyncio.run(ET.embedded_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="memory", text=MAP))
    assert out["regions"][0]["pct"] == 88.6 and out["symbols"][0]["name"] == "Driver_Table"
    out = asyncio.run(ET.embedded_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="timing", text=TASKS, inputs={"prio_order": "higher"}))
    assert out["ok"] and out["tasks"][0]["name"] == "uart_rx"
    out = asyncio.run(ET.embedded_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="ci"))
    assert out["file"] == ".github/workflows/firmware-size.yml"
    with pytest.raises(PermissionError):
        emc.do(T, "settings", {"build_cmd": "my password is hunter2"})
    assert emc.do(T, "add", {"kind": "firmware", "text": FW.replace("HAL_Init();", "HAL_Init(); /* password = hunter2 */")})["kind"] == "firmware"
    for bad in ({"flash": "lots"}, {"clock": "fast"}, {"prio_order": "sideways"}, {"toolchain": "pic"}, {"usable_pct": 0}, {"target_life": "soon"}, {"elf": "../../etc/x"}):
        with pytest.raises((emc.EmDeskError, PermissionError)):
            emc.do(T, "settings", bad)
    with pytest.raises(emc.EmDeskError):
        emc.do(T, "add", {"kind": "timing", "text": ""})
    with pytest.raises(emc.EmDeskError):
        emc.do(T, "nope", {})
    from app.employee import hire as H
    H.pause(T, "embedded_eng")
    assert emc.do(T, "get", {"id": m1["id"]})["id"] == m1["id"] and emc.do(T, "ci", {})["yaml"]
    with pytest.raises(PermissionError):
        emc.do(T, "add", {"kind": "memory", "text": MAP})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def em_server(emc, monkeypatch):
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


def test_desk_in_a_real_browser(emc, em_server):
    base, browser, key = em_server
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
    pg.goto(base + "/console/embedded")
    pg.wait_for_selector(".emk-path", timeout=20000)
    snap(pg, "em-today-empty-1440")
    go(pg, "#/memory", "form[data-form=memory]")
    submit(pg, "memory", MAP, ".emk-regs")
    assert "88.6%" in pg.inner_text(".emk-regs") and "Driver_Table" in pg.inner_text("#emPage") and "printf" in pg.inner_text("#emPage")
    snap(pg, "em-memory-1440")
    go(pg, "#/memory", "form[data-form=memory]")
    put(pg, "memory", "flash", "64K")
    put(pg, "memory", "ram", "20K")
    pg.select_option("form[data-form=memory] [name=before]", index=1)
    submit(pg, "memory", SIZEA, "text=Since the older build")
    snap(pg, "em-memory-grew-1440")
    go(pg, "#/code", "form[data-form=firmware]")
    submit(pg, "firmware", FW, ".emk-isrs")
    assert "USART2_IRQHandler" in pg.inner_text(".emk-isrs") and "tick_count" in pg.inner_text("#emPage")
    pg.click("details.emk-raw summary")
    pg.wait_for_selector(".emk-src div.m.bad")
    snap(pg, "em-code-1440")
    go(pg, "#/timing", "form[data-form=timing]")
    submit(pg, "timing", TASKS, ".emk-gantt svg")
    assert pg.locator(".emk-gantt rect.k").count() > 10 and "All met" in pg.inner_text(".cs-hero")
    snap(pg, "em-timing-1440")
    go(pg, "#/timing", "form[data-form=timing]")
    put(pg, "timing", "switch_us", "2")
    submit(pg, "timing", BAD_TASKS, ".emk-gantt svg")
    assert pg.locator(".emk-gantt circle.miss").count() > 0 and pg.locator("table.emk-tt tr.bad").count() == 2
    snap(pg, "em-timing-bad-1440")
    go(pg, "#/power", "form[data-form=power]")
    put(pg, "power", "capacity", "230")
    put(pg, "power", "target", "2 years")
    submit(pg, "power", POWER, ".iv-donut")
    assert "17.6 months" in pg.inner_text(".cs-hero") and "measure half as often" in pg.inner_text("#emPage")
    snap(pg, "em-power-1440")
    go(pg, "#/clocks", "form[data-form=clocks]")
    submit(pg, "clocks", CLOCKS, "text=BRR = 0x271")
    assert "UBRR = 8" in pg.inner_text("#emPage") and "PSC = 1, ARR = 41999" in pg.inner_text("#emPage")
    snap(pg, "em-clocks-1440")
    go(pg, "#/ci", "text=Set the build command")
    go(pg, "#/settings", "form[data-form=settings]")
    pg.fill("form[data-form=settings] [name=build_cmd]", "make -j4")
    pg.fill("form[data-form=settings] [name=flash]", "256K")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved')", timeout=20000)
    go(pg, "#/ci", "text=firmware-size.yml")
    assert "arm-none-eabi-size" in pg.inner_text("#emPage")
    snap(pg, "em-ci-1440")
    go(pg, "#/today", ".emk-list")
    assert "can miss" in pg.inner_text(".cs-hero") or "All met" in pg.inner_text(".cs-hero")
    snap(pg, "em-today-1440")
    for route, sel in (("#/today", ".emk-list"), ("#/memory", ".emk-item"), ("#/code", ".emk-item"), ("#/timing", ".emk-item"), ("#/power", ".emk-item"),
                       ("#/clocks", ".emk-item"), ("#/ci", "text=firmware-size.yml"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('#emPage *')].filter(e => !e.closest('pre,textarea,table,svg,.emk-gantt,.emk-src') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
    for route in ("#/memory", "#/timing", "#/power", "#/code"):
        go(pg, route, ".emk-item")
        pg.locator(".emk-item").first.click()
        pg.wait_for_selector(".emk-head", timeout=20000)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        assert w[0] <= w[1] + 1, (route, w)
        snap(pg, "em-" + route[2:] + "-390")
    assert not errs, errs
