"""A GitHub Actions workflow that keeps firmware inside its chip: on every pull request it builds the firmware for the pull request's
base and its head with the cross compiler, reads both images with `size -A`, and fails when flash or RAM goes over her budget or
grows more than she allows - with the per-section change written to the run's summary. Host-side unit tests can run first. The file
is text she adds to her repository herself; nothing is pushed."""
from __future__ import annotations

import re
from typing import Any

from .memory import MemError, _parse_kb


class CiError(ValueError):
    pass


TOOLCHAINS = {
    "arm": ("sudo apt-get update && sudo apt-get install -y gcc-arm-none-eabi binutils-arm-none-eabi libnewlib-arm-none-eabi", "arm-none-eabi-size"),
    "riscv": ("sudo apt-get update && sudo apt-get install -y gcc-riscv64-unknown-elf binutils-riscv64-unknown-elf picolibc-riscv64-unknown-elf", "riscv64-unknown-elf-size"),
    "avr": ("sudo apt-get update && sudo apt-get install -y gcc-avr binutils-avr avr-libc", "avr-size"),
    "esp32": ("", "xtensa-esp32-elf-size"),
    "host": ("", "size"),
    "none": ("", "size"),
}


def _cmd(v: str, what: str, need: bool) -> str:
    v = str(v or "").strip()
    if not v:
        if need:
            raise CiError(f"{what}: the command that builds the firmware (for example: make, cmake --build build, pio run).")
        return ""
    if "\n" in v or "\r" in v or len(v) > 400:
        raise CiError(f"{what}: one line, up to 400 characters.")
    if "${{" in v:
        raise CiError(f"{what}: no ${{{{ }}}} expressions - they would run inside the workflow.")
    return v


COMPARE = r'''import os, re, subprocess, sys
SIZE, FLASH_MAX, RAM_MAX, GROW = @SIZE@, @FLASH@, @RAM@, @GROW@
FLASH = (".isr_vector", ".vectors", ".text", ".rodata", ".ARM.extab", ".ARM.exidx", ".preinit_array", ".init_array", ".fini_array", ".init", ".fini",
         ".eh_frame", ".srodata", ".progmem", ".flash", ".vector_table")
RAM = (".bss", ".sbss", ".noinit", "._user_heap_stack", ".heap", ".stack", ".tbss", ".ram", ".dma", ".ccmram", ".tdata")
SKIP = (".debug", ".comment", ".ARM.attributes", ".stab", ".note", ".riscv.attributes", ".gnu.attributes")
def read(path):
    out = subprocess.run(SIZE + ["-A", path], capture_output=True, text=True) if not path.endswith(".txt") else None
    text = out.stdout if out else open(path).read()
    if out and out.returncode:
        print(out.stderr)
        sys.exit("::error::size could not read " + path)
    secs = {}
    for ln in text.splitlines():
        m = re.match(r"^(\.[\w.$@-]+)\s+(\d+)", ln.strip())
        if m:
            secs[m.group(1)] = secs.get(m.group(1), 0) + int(m.group(2))
    fl = ram = 0
    for n, s in secs.items():
        if n.startswith(SKIP):
            continue
        if n.startswith(".data") or n.startswith(".sdata"):
            fl += s
            ram += s
        elif n.startswith(RAM):
            ram += s
        elif n.startswith(FLASH):
            fl += s
    return fl, ram, secs
fb, rb, sb = read(sys.argv[1])
fh, rh, sh = read(sys.argv[2])
fail = []
if FLASH_MAX and fh > FLASH_MAX:
    fail.append(f"flash {fh:,} bytes is over the budget of {FLASH_MAX:,}")
if RAM_MAX and rh > RAM_MAX:
    fail.append(f"RAM {rh:,} bytes is over the budget of {RAM_MAX:,}")
if GROW is not None and fh - fb > GROW:
    fail.append(f"flash grew {fh - fb:+,} bytes (allowed {GROW:+,})")
if GROW is not None and rh - rb > GROW:
    fail.append(f"RAM grew {rh - rb:+,} bytes (allowed {GROW:+,})")
pct = lambda a, b: f" ({100 * a / b:.1f}%)" if b else ""
lines = ["| | base | head | change |", "|---|---|---|---|",
         f"| flash | {fb:,} | {fh:,}{pct(fh, FLASH_MAX)} | {fh - fb:+,} |", f"| RAM | {rb:,} | {rh:,}{pct(rh, RAM_MAX)} | {rh - rb:+,} |"]
ch = sorted(((n, sh.get(n, 0) - sb.get(n, 0)) for n in set(sb) | set(sh) if not n.startswith(SKIP) and sh.get(n, 0) != sb.get(n, 0)), key=lambda x: -abs(x[1]))
if ch:
    lines += ["", "| section | change |", "|---|---|"] + [f"| {n} | {d:+,} |" for n, d in ch[:15]]
verdict = f"flash {fh:,} bytes ({fh - fb:+,}), RAM {rh:,} bytes ({rh - rb:+,})"
with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as s:
    s.write("## Firmware size\n\n" + verdict + "\n\n" + "\n".join(lines) + "\n")
print(verdict)
for f in fail:
    print("::error::" + f)
sys.exit(1 if fail else 0)
'''


def workflow(build_cmd: str = "", elf: str = "build/firmware.elf", toolchain: str = "arm", flash: Any = "", ram: Any = "", max_growth: Any = "",
             test_cmd: str = "", runner: str = "ubuntu-24.04") -> dict[str, Any]:
    build = _cmd(build_cmd, "Build", True)
    test = _cmd(test_cmd, "Host tests", False)
    elf = str(elf or "").strip()
    if not re.fullmatch(r"[\w./\-]{1,160}", elf) or ".." in elf or elf.startswith("/"):
        raise CiError("Firmware image: a path inside the repository such as build/firmware.elf.")
    if toolchain not in TOOLCHAINS:
        raise CiError("Toolchain: " + ", ".join(TOOLCHAINS) + ".")
    if not re.fullmatch(r"[\w.\-]{1,40}", str(runner or "")):
        raise CiError("Runner: a runner label such as ubuntu-24.04.")
    try:
        fmax, rmax = _parse_kb(flash), _parse_kb(ram)
    except MemError as e:
        raise CiError(str(e))
    grow = None
    if str(max_growth or "").strip() != "":
        try:
            grow = int(float(max_growth))
        except (TypeError, ValueError):
            raise CiError("Allowed growth: a number of bytes (0 = no growth at all).")
        if grow < 0:
            raise CiError("Allowed growth: 0 or more bytes.")
    if not fmax and not rmax and grow is None:
        raise CiError("Set a flash or RAM budget, or the growth allowed, so the check has something to hold.")
    install, size_tool = TOOLCHAINS[toolchain]
    py = (COMPARE.replace("@SIZE@", repr([size_tool])).replace("@FLASH@", repr(fmax)).replace("@RAM@", repr(rmax)).replace("@GROW@", repr(grow)))
    py = "\n".join(("          " + ln) if ln else "" for ln in py.splitlines())
    setup = f"      - name: Toolchain\n        run: {install}\n" if install else ""
    if toolchain == "esp32":
        setup = "      - name: Toolchain (ESP-IDF)\n        uses: espressif/esp-idf-ci-action@v1\n        with:\n          command: idf.py --version\n"
    tests = f"      - name: Host tests\n        working-directory: head\n        run: {test}\n" if test else ""
    yaml = f"""name: Firmware size
# Made by Hoola's Embedded desk. Builds the firmware for the pull request's base and head and fails when flash or RAM
# goes over the budget{' or grows more than ' + format(grow, ',') + ' bytes' if grow is not None else ''}.
on:
  pull_request:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  size:
    runs-on: {runner}
    timeout-minutes: 30
    steps:
      - name: Head
        uses: actions/checkout@v4
        with:
          path: head
          submodules: recursive
      - name: Base
        uses: actions/checkout@v4
        with:
          path: base
          submodules: recursive
          ref: ${{{{ github.event.pull_request.base.sha || github.sha }}}}
{setup}{tests}      - name: Build both
        run: |
          set -euo pipefail
          (cd head && {build})
          (cd base && {build}) || echo "::warning::the base did not build - comparing against an empty image"
          test -f "head/{elf}" || {{ echo "::error::the build did not write head/{elf}"; exit 1; }}
          test -f "base/{elf}" || printf '.text 0 0\\n' > base-empty.txt
      - name: Compare
        run: |
          B="base/{elf}"; test -f "$B" || B=base-empty.txt
          python3 - "$B" "head/{elf}" <<'PY'
{py}
          PY
      - name: Keep the image
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: firmware
          path: head/{elf}
          retention-days: 14
"""
    return {"file": ".github/workflows/firmware-size.yml", "yaml": yaml, "compare": py, "size_tool": size_tool,
            "note": ("Put it at .github/workflows/firmware-size.yml. The build command runs in each checkout and must write " + elf + ". "
                     + ("It installs the toolchain from Ubuntu's packages - if your project pins a compiler version, install that one instead. " if install else "")
                     + "Leave room under the budget for a bootloader, an update slot and the stack; the check counts what the linker placed, not the stack the code reaches.")}
