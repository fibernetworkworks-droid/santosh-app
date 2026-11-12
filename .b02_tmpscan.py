"""List pytest temp dirs of DEAD sessions (lock pid not alive); with --rm remove only those."""
import os, sys, shutil, time, subprocess
root = "/tmp/pytest-of-root"
rm = "--rm" in sys.argv
dead_bytes = live = dead = 0
for name in sorted(os.listdir(root)):
    d = os.path.join(root, name)
    if not os.path.isdir(d) or os.path.islink(d) or not name.startswith("pytest-"):
        continue
    lock = os.path.join(d, ".lock")
    pid = None
    try:
        pid = int(open(lock).read().strip())
    except Exception:
        pid = None
    alive = False
    if pid:
        try:
            os.kill(pid, 0); alive = True
        except ProcessLookupError:
            alive = False
        except PermissionError:
            alive = True
    age = time.time() - os.path.getmtime(d)
    if alive or (pid is None and age < 3600):
        live += 1
        print("LIVE", name, pid, int(age))
        continue
    try:
        sz = int(subprocess.run(["du", "-sm", d], capture_output=True, text=True).stdout.split()[0])
    except Exception:
        sz = -1
    dead += 1; dead_bytes += max(sz, 0)
    print("DEAD", name, pid, int(age), f"{sz}MB", "removed" if rm else "")
    if rm:
        shutil.rmtree(d, ignore_errors=True)
print("live", live, "dead", dead, "dead MB", dead_bytes)
