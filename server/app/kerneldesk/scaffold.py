"""Out-of-tree driver starters, written by code from fixed templates (no model): a plain module with a parameter, a misc
character device (/dev/<name>), a platform driver matched from the device tree, an I2C client driver. Each comes with its
Makefile, a Kconfig entry for when it moves into the tree, a device tree snippet where it needs one and a README. They pass
this desk's own patch style checks; they are NOT compiled here (no kernel headers on this server) - her CI builds them."""
from __future__ import annotations

import io
import re
import zipfile
from typing import Any

KINDS = {"hello": "A plain module with a parameter", "misc": "A character device at /dev/<name> (read, write, ioctl)",
         "platform": "A platform driver matched from the device tree (probe / remove, a register map)",
         "i2c": "An I2C device driver (probe, read a register)"}


def clean_name(name: str) -> str:
    n = re.sub(r"[^a-z0-9_]", "_", str(name or "").lower()).strip("_")
    n = re.sub(r"_+", "_", n)[:24].strip("_")
    if not n or n[0].isdigit():
        raise ValueError("A driver name: letters, digits and _ (starting with a letter), like my_sensor.")
    return n


def _vendor(v: str) -> str:
    v = re.sub(r"[^a-z0-9-]", "", str(v or "").lower())[:24]
    return v or "acme"


HELLO = r'''// SPDX-License-Identifier: GPL-2.0
/*
 * {name}: {what}
 */
#include <linux/init.h>
#include <linux/module.h>
#include <linux/moduleparam.h>

static int count = 1;
module_param(count, int, 0444);
MODULE_PARM_DESC(count, "How many times to say hello");

static int __init {name}_init(void)
{
	int i;

	for (i = 0; i < count; i++)
		pr_info("{name}: hello %d\n", i);
	return 0;
}

static void __exit {name}_exit(void)
{
	pr_info("{name}: goodbye\n");
}

module_init({name}_init);
module_exit({name}_exit);

MODULE_DESCRIPTION("{what}");
MODULE_AUTHOR("{author}");
MODULE_LICENSE("GPL");
'''

MISC = r'''// SPDX-License-Identifier: GPL-2.0
/*
 * {name}: {what}
 *
 * A character device at /dev/{name}: write up to {size} bytes and read them back;
 * an ioctl clears the buffer.
 */
#include <linux/fs.h>
#include <linux/miscdevice.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/uaccess.h>

#define {upper}_SIZE {size}
#define {upper}_IOC_CLEAR _IO('h', 1)

static DEFINE_MUTEX({name}_lock);
static char {name}_buf[{upper}_SIZE];
static size_t {name}_len;

static ssize_t {name}_read(struct file *file, char __user *ubuf, size_t count,
			  loff_t *ppos)
{
	ssize_t ret;

	mutex_lock(&{name}_lock);
	ret = simple_read_from_buffer(ubuf, count, ppos, {name}_buf, {name}_len);
	mutex_unlock(&{name}_lock);
	return ret;
}

static ssize_t {name}_write(struct file *file, const char __user *ubuf,
			   size_t count, loff_t *ppos)
{
	ssize_t ret;

	mutex_lock(&{name}_lock);
	ret = simple_write_to_buffer({name}_buf, sizeof({name}_buf), ppos, ubuf, count);
	if (ret > 0)
		{name}_len = max_t(size_t, {name}_len, *ppos);
	mutex_unlock(&{name}_lock);
	return ret;
}

static long {name}_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
	if (cmd != {upper}_IOC_CLEAR)
		return -ENOTTY;
	mutex_lock(&{name}_lock);
	memset({name}_buf, 0, sizeof({name}_buf));
	{name}_len = 0;
	mutex_unlock(&{name}_lock);
	return 0;
}

static const struct file_operations {name}_fops = {{
	.owner		= THIS_MODULE,
	.read		= {name}_read,
	.write		= {name}_write,
	.unlocked_ioctl	= {name}_ioctl,
	.llseek		= default_llseek,
}};

static struct miscdevice {name}_dev = {{
	.minor	= MISC_DYNAMIC_MINOR,
	.name	= "{name}",
	.fops	= &{name}_fops,
	.mode	= 0600,
}};

module_misc_device({name}_dev);

MODULE_DESCRIPTION("{what}");
MODULE_AUTHOR("{author}");
MODULE_LICENSE("GPL");
'''

PLATFORM = r'''// SPDX-License-Identifier: GPL-2.0
/*
 * {name}: {what}
 */
#include <linux/io.h>
#include <linux/mod_devicetable.h>
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/regmap.h>

#define {upper}_REG_ID		0x00
#define {upper}_REG_CTRL	0x04

struct {name}_priv {{
	struct device *dev;
	struct regmap *map;
}};

static const struct regmap_config {name}_regmap = {{
	.reg_bits	= 32,
	.val_bits	= 32,
	.reg_stride	= 4,
	.max_register	= {upper}_REG_CTRL,
}};

static int {name}_probe(struct platform_device *pdev)
{
	struct {name}_priv *priv;
	void __iomem *base;
	unsigned int id;
	int ret;

	priv = devm_kzalloc(&pdev->dev, sizeof(*priv), GFP_KERNEL);
	if (!priv)
		return -ENOMEM;
	priv->dev = &pdev->dev;

	base = devm_platform_ioremap_resource(pdev, 0);
	if (IS_ERR(base))
		return PTR_ERR(base);

	priv->map = devm_regmap_init_mmio(&pdev->dev, base, &{name}_regmap);
	if (IS_ERR(priv->map))
		return dev_err_probe(&pdev->dev, PTR_ERR(priv->map), "no register map\n");

	ret = regmap_read(priv->map, {upper}_REG_ID, &id);
	if (ret)
		return dev_err_probe(&pdev->dev, ret, "cannot read the ID register\n");

	platform_set_drvdata(pdev, priv);
	dev_info(&pdev->dev, "found, ID 0x%08x\n", id);
	return 0;
}

static void {name}_remove(struct platform_device *pdev)
{
	dev_info(&pdev->dev, "removed\n");
}

static const struct of_device_id {name}_of_match[] = {{
	{{ .compatible = "{vendor},{dtname}" }},
	{{ }}
}};
MODULE_DEVICE_TABLE(of, {name}_of_match);

static struct platform_driver {name}_driver = {{
	.probe	= {name}_probe,
	.remove	= {name}_remove,
	.driver	= {{
		.name		= "{name}",
		.of_match_table	= {name}_of_match,
	}},
}};
module_platform_driver({name}_driver);

MODULE_DESCRIPTION("{what}");
MODULE_AUTHOR("{author}");
MODULE_LICENSE("GPL");
'''

I2C = r'''// SPDX-License-Identifier: GPL-2.0
/*
 * {name}: {what}
 */
#include <linux/i2c.h>
#include <linux/mod_devicetable.h>
#include <linux/module.h>

#define {upper}_REG_ID	0x00

static int {name}_probe(struct i2c_client *client)
{
	int id;

	id = i2c_smbus_read_byte_data(client, {upper}_REG_ID);
	if (id < 0)
		return dev_err_probe(&client->dev, id, "no answer at 0x%02x\n", client->addr);

	dev_info(&client->dev, "found at 0x%02x, ID 0x%02x\n", client->addr, id);
	return 0;
}

static const struct of_device_id {name}_of_match[] = {{
	{{ .compatible = "{vendor},{dtname}" }},
	{{ }}
}};
MODULE_DEVICE_TABLE(of, {name}_of_match);

static const struct i2c_device_id {name}_id[] = {{
	{{ "{dtname}" }},
	{{ }}
}};
MODULE_DEVICE_TABLE(i2c, {name}_id);

static struct i2c_driver {name}_driver = {{
	.driver = {{
		.name		= "{name}",
		.of_match_table	= {name}_of_match,
	}},
	.probe		= {name}_probe,
	.id_table	= {name}_id,
}};
module_i2c_driver({name}_driver);

MODULE_DESCRIPTION("{what}");
MODULE_AUTHOR("{author}");
MODULE_LICENSE("GPL");
'''

TEMPLATES = {"hello": HELLO, "misc": MISC, "platform": PLATFORM, "i2c": I2C}


def make(kind: str, name: str, what: str = "", author: str = "", vendor: str = "", size: int = 4096) -> dict[str, str]:
    if kind not in TEMPLATES:
        raise ValueError("Kind: " + " | ".join(KINDS))
    n = clean_name(name)
    what = re.sub(r"[\"\\\n\r]", " ", str(what or KINDS[kind])).strip()[:120] or KINDS[kind]
    author = re.sub(r"[\"\\\n\r]", " ", str(author or "Your Name <you@example.com>")).strip()[:120]
    v = _vendor(vendor)
    dtname = n.replace("_", "-")
    try:
        size = max(16, min(65536, int(size)))
    except (TypeError, ValueError):
        size = 4096
    keys = {"name": n, "upper": n.upper(), "what": what, "author": author, "vendor": v, "dtname": dtname, "size": str(size)}
    c = re.sub(r"\{(" + "|".join(keys) + r")\}", lambda m: keys[m.group(1)], TEMPLATES[kind]).replace("{{", "{").replace("}}", "}")
    files = {f"{n}.c": c,
             "Makefile": (f"# SPDX-License-Identifier: GPL-2.0\nobj-m += {n}.o\n\nKDIR ?= /lib/modules/$(shell uname -r)/build\n\n"
                          f"all:\n\t$(MAKE) -C $(KDIR) M=$(CURDIR) modules\n\nclean:\n\t$(MAKE) -C $(KDIR) M=$(CURDIR) clean\n"),
             "Kconfig": (f"# SPDX-License-Identifier: GPL-2.0\nconfig {n.upper()}\n\ttristate \"{what[:60]}\"\n"
                         + ("\tdepends on I2C\n\tdepends on OF\n" if kind == "i2c" else "\tdepends on OF\n\tselect REGMAP_MMIO\n" if kind == "platform" else "")
                         + f"\thelp\n\t  {what}.\n\n\t  To build it as a module, choose M here: the module will be called {n}.\n")}
    if kind in ("platform", "i2c"):
        node = (f"\t{dtname}@1000 {{\n\t\tcompatible = \"{v},{dtname}\";\n\t\treg = <0x1000 0x100>;\n\t}};\n" if kind == "platform" else
                f"&i2c1 {{\n\t{dtname}@48 {{\n\t\tcompatible = \"{v},{dtname}\";\n\t\treg = <0x48>;\n\t}};\n}};\n")
        files[f"{dtname}.dtsi"] = "// SPDX-License-Identifier: GPL-2.0\n/* Put this node in your board's .dts (and a binding in Documentation/devicetree/bindings/) */\n" + node
    files["README.md"] = (f"# {n}\n\n{what}\n\nBuild against your running kernel:\n\n    make\n    sudo insmod {n}.ko\n    dmesg | tail\n"
                          f"    sudo rmmod {n}\n\nBuild against a kernel tree: `make KDIR=/path/to/linux`.\n\n"
                          + (f"Try it: `echo hello > /dev/{n}; cat /dev/{n}`.\n\n" if kind == "misc" else "")
                          + ("The compatible string is `" + v + "," + dtname + "` - use your company's vendor prefix "
                             "(Documentation/devicetree/bindings/vendor-prefixes.yaml) before you send it upstream.\n\n" if kind in ("platform", "i2c") else "")
                          + "Made from a Hoola template. Not compiled on Hoola's server: build it in your CI (the Boot & CI page writes the workflow).\n")
    return files


def as_patch(files: dict[str, str]) -> str:
    """The .c file as an added file in a diff, so the desk's patch checks can read it."""
    out = []
    for fn, body in files.items():
        if not fn.endswith((".c", "Kconfig", "Makefile")):
            continue
        ls = body.rstrip("\n").split("\n")
        out.append(f"diff --git a/{fn} b/{fn}\nnew file mode 100644\n--- /dev/null\n+++ b/{fn}\n@@ -0,0 +1,{len(ls)} @@\n" + "\n".join("+" + x for x in ls))
    return "\n".join(out) + "\n"


def zip_of(files: dict[str, str], folder: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for fn, body in files.items():
            info = zipfile.ZipInfo(f"{folder}/{fn}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, body.encode())
    return buf.getvalue()


def summary(kind: str) -> dict[str, Any]:
    return {"kind": kind, "say": KINDS.get(kind, "")}
