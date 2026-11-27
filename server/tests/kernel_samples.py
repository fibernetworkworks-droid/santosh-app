"""Kernel crash / boot logs, a patch and a .config shaped like the real thing, for the Kernel / OS Developer desk's tests."""

NULL_X86 = """[  123.456789] BUG: kernel NULL pointer dereference, address: 0000000000000018
[  123.456801] #PF: supervisor read access in kernel mode
[  123.456805] #PF: error_code(0x0000) - not-present page
[  123.456810] PGD 0 P4D 0
[  123.456815] Oops: 0000 [#1] PREEMPT SMP PTI
[  123.456820] CPU: 2 PID: 4321 Comm: insmod Tainted: G           OE      6.8.0-rc3 #1
[  123.456825] Hardware name: QEMU Standard PC (Q35 + ICH9, 2009), BIOS 1.16.3-debian-1.16.3-2 04/01/2014
[  123.456830] RIP: 0010:my_sensor_read_temp+0x1c/0x60 [my_sensor]
[  123.456835] Code: 00 00 55 48 89 e5 41 54 53 48 8b 47 08 <48> 8b 58 18
[  123.456840] RSP: 0018:ffffb3c1c0a0fc28 EFLAGS: 00010246
[  123.456845] RAX: 0000000000000000 RBX: ffff9e2a41e1c000 RCX: 0000000000000000
[  123.456850] Call Trace:
[  123.456852]  <TASK>
[  123.456855]  ? __die+0x24/0x70
[  123.456860]  ? page_fault_oops+0x15b/0x460
[  123.456865]  my_sensor_read_temp+0x1c/0x60 [my_sensor]
[  123.456870]  my_sensor_probe+0x9a/0x140 [my_sensor]
[  123.456875]  i2c_device_probe+0x10f/0x320
[  123.456880]  really_probe+0x1c5/0x3e0
[  123.456885]  __driver_probe_device+0x81/0x170
[  123.456890]  driver_probe_device+0x23/0xb0
[  123.456895]  </TASK>
[  123.456900] Modules linked in: my_sensor(OE) i2c_dev virtio_net net_failover
[  123.456905] CR2: 0000000000000018
[  123.456910] ---[ end trace 0000000000000000 ]---
"""

KASAN = """[   42.100000] ==================================================================
[   42.100010] BUG: KASAN: slab-use-after-free in ring_pop+0x48/0x90 [ringbuf]
[   42.100020] Read of size 8 at addr ffff888012345678 by task kworker/1:2/88
[   42.100030] CPU: 1 PID: 88 Comm: kworker/1:2 Not tainted 6.9.0 #3
[   42.100040] Call Trace:
[   42.100045]  <TASK>
[   42.100050]  dump_stack_lvl+0x48/0x70
[   42.100055]  print_report+0xd2/0x660
[   42.100060]  kasan_report+0xd5/0x110
[   42.100065]  ring_pop+0x48/0x90 [ringbuf]
[   42.100070]  ring_worker+0x31/0x80 [ringbuf]
[   42.100075]  process_one_work+0x1d0/0x3e0
[   42.100080]  </TASK>
[   42.100085]
[   42.100090] Allocated by task 77:
[   42.100095]  kasan_save_stack+0x22/0x50
[   42.100100]  ring_push+0x5a/0x120 [ringbuf]
[   42.100105]  ring_ioctl+0x88/0x100 [ringbuf]
[   42.100110]
[   42.100115] Freed by task 77:
[   42.100120]  kasan_save_stack+0x22/0x50
[   42.100125]  kfree+0xa6/0x2a0
[   42.100130]  ring_clear+0x3e/0x70 [ringbuf]
[   42.100135]
[   42.100140] The buggy address belongs to the object at ffff888012345600
[   42.100145]  which belongs to the cache kmalloc-192 of size 192
"""

ARM64_GPF = """[   10.000000] Unable to handle kernel paging request at virtual address dead000000000108
[   10.000100] Internal error: Oops: 96000044 [#1] PREEMPT SMP
[   10.000200] CPU: 0 PID: 1 Comm: init Tainted: G        W          6.6.30 #1
[   10.000300] Hardware name: linux,dummy-virt (DT)
[   10.000400] pc : list_del_entry+0x10/0x40
[   10.000500] lr : mydev_remove+0x30/0x60 [mydev]
[   10.000600] Call trace:
[   10.000700]  list_del_entry+0x10/0x40
[   10.000800]  mydev_remove+0x30/0x60 [mydev]
[   10.000900]  platform_remove+0x2c/0x60
"""

HUNG = """[  610.000000] INFO: task kworker/u8:3:211 blocked for more than 122 seconds.
[  610.000100]       Not tainted 6.10.0 #1
[  610.000200] "echo 0 > /proc/sys/kernel/hung_task_timeout_secs" disables this message.
[  610.000300] task:kworker/u8:3    state:D stack:0     pid:211   tgid:211   ppid:2      flags:0x00004000
[  610.000400] Call Trace:
[  610.000500]  <TASK>
[  610.000600]  __schedule+0x3c1/0x1110
[  610.000700]  schedule+0x27/0xf0
[  610.000800]  schedule_preempt_disabled+0x15/0x30
[  610.000900]  __mutex_lock.constprop.0+0x3a9/0x6f0
[  610.001000]  mydev_work+0x2a/0x90 [mydev]
[  610.001100]  </TASK>
"""

BOOT_OK = """[    0.000000] Linux version 6.8.0 (builder@ci) (gcc 13.2.0) #1 SMP PREEMPT_DYNAMIC
[    0.000000] Command line: console=ttyS0 panic=-1 oops=panic
[    0.012000] Memory: 980000K/1048000K available
[    0.120000] smp: Brought up 1 node, 2 CPUs
[    0.300000] pci 0000:00:01.0: [8086:7000] type 00 class 0x060100
[    0.500000] Serial: 8250/16550 driver, 4 ports, IRQ sharing enabled
[    0.700000] my_sensor 1-0048: probe failed with error -121
[    0.710000] Direct firmware load for regulatory.db failed with error -2
[    0.900000] Trying to unpack rootfs image as initramfs...
[    1.100000] Freeing unused kernel image (initmem) memory: 3000K
[    1.120000] Run /init as init process
loaded my_sensor.ko
HOOLA_BOOT_OK
"""

BOOT_FAIL = """[    0.000000] Linux version 6.8.0 #1 SMP
[    0.000000] Command line: console=ttyS0 root=/dev/vda1
[    0.012000] Memory: 980000K/1048000K available
[    1.500000] VFS: Cannot open root device "vda1" or unknown-block(0,0): error -6
[    1.500100] Please append a correct "root=" boot option
[    1.500200] Kernel panic - not syncing: VFS: Unable to mount root fs on unknown-block(0,0)
"""

PATCH_BAD = """From 1234567890abcdef1234567890abcdef12345678 Mon Sep 17 00:00:00 2001
From: Asha Rao <asha@example.com>
Date: Mon, 1 Dec 2026 10:00:00 +0530
Subject: [PATCH] Fixed the null pointer in my sensor driver.

Fixes: abc123 (my_sensor: add driver)
Reported-by: Ravi Kumar <ravi@example.com>
---
 drivers/hwmon/my_sensor.c | 6 +++++-
 1 file changed, 5 insertions(+), 1 deletion(-)

diff --git a/drivers/hwmon/my_sensor.c b/drivers/hwmon/my_sensor.c
index 1111111..2222222 100644
--- a/drivers/hwmon/my_sensor.c
+++ b/drivers/hwmon/my_sensor.c
@@ -10,7 +10,11 @@ static int my_sensor_read_temp(struct my_sensor *s)
 {
-	int v = s->client->addr;
+	int v;
+        if(s->client == NULL)
+		return -ENODEV;
+	v = s->client->addr;@TRAIL@
+	printk("my_sensor: read %d\\n", v);
 	return v;
 }
"""

PATCH_BAD = PATCH_BAD.replace("@TRAIL@", "   ")

PATCH_GOOD = """From 1234567890abcdef1234567890abcdef12345678 Mon Sep 17 00:00:00 2001
From: Asha Rao <asha@example.com>
Date: Mon, 1 Dec 2026 10:00:00 +0530
Subject: [PATCH v2] hwmon: my_sensor: check the client before reading

my_sensor_read_temp() follows s->client without checking it. When the
probe fails half way the client is NULL and reading the temperature
crashes the kernel.

Return -ENODEV when there is no client.

Fixes: 0123456789ab ("hwmon: my_sensor: add driver")
Reported-by: Ravi Kumar <ravi@example.com>
Closes: https://lore.kernel.org/all/20261201.example@example.com/
Signed-off-by: Asha Rao <asha@example.com>
---
 drivers/hwmon/my_sensor.c | 5 ++++-
 1 file changed, 4 insertions(+), 1 deletion(-)

diff --git a/drivers/hwmon/my_sensor.c b/drivers/hwmon/my_sensor.c
index 1111111..2222222 100644
--- a/drivers/hwmon/my_sensor.c
+++ b/drivers/hwmon/my_sensor.c
@@ -10,7 +10,10 @@ static int my_sensor_read_temp(struct my_sensor *s)
 {
-	int v = s->client->addr;
+	int v;
+
+	if (!s->client)
+		return -ENODEV;
+	v = s->client->addr;
 	return v;
 }
"""

CONFIG = """#
# Automatically generated file; DO NOT EDIT.
# Linux/x86 6.8.0 Kernel Configuration
#
CONFIG_X86_64=y
CONFIG_PRINTK=y
CONFIG_TTY=y
CONFIG_SERIAL_8250=y
CONFIG_SERIAL_8250_CONSOLE=y
CONFIG_BLK_DEV_INITRD=y
CONFIG_RD_GZIP=y
CONFIG_DEVTMPFS=y
# CONFIG_DEVTMPFS_MOUNT is not set
CONFIG_BINFMT_ELF=y
CONFIG_BINFMT_SCRIPT=y
CONFIG_PROC_FS=y
CONFIG_SYSFS=y
CONFIG_VIRTIO_PCI=y
CONFIG_VIRTIO_BLK=m
CONFIG_VIRTIO_NET=y
CONFIG_PCI=y
CONFIG_STACKPROTECTOR_STRONG=y
CONFIG_STRICT_KERNEL_RWX=y
CONFIG_RANDOMIZE_BASE=y
CONFIG_DEVMEM=y
CONFIG_KALLSYMS=y
"""
