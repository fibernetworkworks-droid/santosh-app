"""A GitHub Actions workflow for HER kernel repository: build the kernel (her defconfig + her fragment), optionally build her
out-of-tree module against it, boot it in QEMU with a tiny initramfs whose init prints a marker (and loads the module), and
keep the serial log as an artifact. Hoola writes the file; she adds it to her repository herself (nothing is pushed)."""
from __future__ import annotations

import re
from typing import Any

from .bootlog import MARKER

ARCH = {
    "x86_64": {"kernel_arch": "x86_64", "image": "arch/x86/boot/bzImage", "qemu": "qemu-system-x86_64", "pkg": "qemu-system-x86",
               "cross": "", "console": "ttyS0", "machine": "-machine q35 -cpu max", "busybox": ""},
    "arm64": {"kernel_arch": "arm64", "image": "arch/arm64/boot/Image", "qemu": "qemu-system-aarch64", "pkg": "qemu-system-arm",
              "cross": "aarch64-linux-gnu-", "console": "ttyAMA0", "machine": "-machine virt -cpu max", "busybox": ""},
    "riscv64": {"kernel_arch": "riscv", "image": "arch/riscv/boot/Image", "qemu": "qemu-system-riscv64", "pkg": "qemu-system-misc",
                "cross": "riscv64-linux-gnu-", "console": "ttyS0", "machine": "-machine virt -bios default", "busybox": ""},
}
# the test's init: a static C program (no busybox needed on any architecture) - mounts /proc and /dev, loads every module in
# /lib/modules (finit_module), prints the marker, powers off
INIT_C = r"""#include <dirent.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/syscall.h>
#include <unistd.h>

int main(void)
{
	DIR *d;
	struct dirent *e;
	char path[512];
	int fd;

	mount("proc", "/proc", "proc", 0, NULL);
	mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);
	d = opendir("/lib/modules");
	while (d && (e = readdir(d))) {
		if (!strstr(e->d_name, ".ko"))
			continue;
		snprintf(path, sizeof(path), "/lib/modules/%s", e->d_name);
		fd = open(path, O_RDONLY | O_CLOEXEC);
		if (fd < 0 || syscall(SYS_finit_module, fd, "", 0)) {
			printf("HOOLA_INSMOD_FAILED %s\n", e->d_name);
			fflush(stdout);
			reboot(RB_POWER_OFF);
		}
		printf("loaded %s\n", e->d_name);
		close(fd);
	}
	printf("@MARKER@\n");
	fflush(stdout);
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}"""
_SAFE = re.compile(r"^[A-Za-z0-9_./\-]*$")


def workflow(arch: str = "x86_64", defconfig: str = "defconfig", fragment: str = ".hoola/kernel.config", module_dir: str = "",
             branch: str = "main", timeout_s: int = 240, marker: str = MARKER, memory_mb: int = 1024) -> dict[str, Any]:
    if arch not in ARCH:
        raise ValueError("Architecture: " + " | ".join(ARCH))
    for label, v in (("defconfig", defconfig), ("fragment", fragment), ("module folder", module_dir), ("branch", branch)):
        if not _SAFE.match(str(v or "")) or ".." in str(v or ""):
            raise ValueError(f"The {label} may use only letters, digits and ./_- (no spaces or ..).")
    if not re.match(r"^[A-Z0-9_]{4,40}$", marker or ""):
        raise ValueError("The marker: 4 to 40 capital letters, digits or _.")
    timeout_s = max(60, min(1800, int(timeout_s or 240)))
    memory_mb = max(256, min(8192, int(memory_mb or 1024)))
    a = ARCH[arch]
    cross = a["cross"]
    cc_pkgs = {"arm64": "gcc-aarch64-linux-gnu", "riscv64": "gcc-riscv64-linux-gnu"}.get(arch, "")
    mk = f"make ARCH={a['kernel_arch']}" + (f" CROSS_COMPILE={cross}" if cross else "")
    mod = module_dir.strip("/")
    lines = f"""# SPDX-License-Identifier: GPL-2.0
# Made by the Hoola Kernel / OS Developer desk. Builds the kernel, {'builds ' + mod + ', ' if mod else ''}boots it in QEMU ({arch})
# and passes only when the console prints {marker}. Put it at .github/workflows/hoola-boot.yml in your kernel repository.
name: Hoola boot test ({arch})

on:
  push:
    branches: [{branch}]
  pull_request:
  workflow_dispatch:

jobs:
  boot:
    runs-on: ubuntu-24.04
    timeout-minutes: 120
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - name: Tools
        run: |
          sudo apt-get update
          sudo apt-get install -y build-essential bc bison flex libelf-dev libssl-dev cpio {a['pkg']} {cc_pkgs}

      - name: Configure
        run: |
          {mk} {defconfig}
          if [ -f "{fragment}" ]; then
            ARCH={a['kernel_arch']} ./scripts/kconfig/merge_config.sh -m .config "{fragment}"
            {mk} olddefconfig
          fi
          ./scripts/config --enable BLK_DEV_INITRD --enable DEVTMPFS --enable DEVTMPFS_MOUNT
          {mk} olddefconfig

      - name: Build the kernel
        run: {mk} -j"$(nproc)" {'Image' if arch != 'x86_64' else 'bzImage'}{' modules_prepare' if mod else ''}
"""
    if mod:
        lines += f"""
      - name: Build {mod}
        run: {mk} -j"$(nproc)" M="$PWD/{mod}" modules
"""
    lines += f"""
      - name: Make the test initramfs
        run: |
          mkdir -p initramfs/lib/modules initramfs/proc initramfs/dev
          cat > init.c <<'EOF'
""" + "\n".join("          " + x for x in INIT_C.replace("@MARKER@", marker).split("\n")) + f"""
          EOF
          {cross}gcc -static -O2 -o initramfs/init init.c
"""
    if mod:
        lines += f"          cp {mod}/*.ko initramfs/lib/modules/\n"
    lines += """          (cd initramfs && find . | cpio -o -H newc | gzip > ../initramfs.cpio.gz)
"""
    lines += f"""
      - name: Boot in QEMU
        run: |
          set +e
          timeout {timeout_s} {a['qemu']} {a['machine']} -m {memory_mb} -nographic -no-reboot \\
            -kernel {a['image']} -initrd initramfs.cpio.gz \\
            -append "console={a['console']} panic=-1 oops=panic" | tee serial.log
          grep -q "{marker}" serial.log || {{ echo "::error::The kernel did not reach {marker}"; exit 1; }}

      - name: Keep the serial log
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: serial-log-{arch}
          path: serial.log
"""
    return {"path": ".github/workflows/hoola-boot.yml", "yaml": lines, "arch": arch, "marker": marker,
            "steps": ["Tools", "Configure", "Build the kernel"] + ([f"Build {mod}"] if mod else []) + ["Make the test initramfs", "Boot in QEMU", "Keep the serial log"],
            "note": ("Hoola does not push this file: add it to your repository yourself. After a run, download the 'serial-log' "
                     "artifact and drop it on this page - it says how far the boot got and every error.")}
