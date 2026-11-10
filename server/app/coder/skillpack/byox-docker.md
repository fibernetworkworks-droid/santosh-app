---
name: byox-docker
description: Build a Linux container: namespaces, cgroups, pivot_root
when_to_use: own docker, container from scratch, namespaces, cgroups
---
GOAL: a container that runs a program in full PID/net/mnt isolation with memory limits.

PHASES
1. fork() + clone(CLONE_NEWPID | CLONE_NEWUTS): isolated PID namespace; hostname set.
2. chroot into an extracted busybox rootfs; mount /proc inside the container.
3. cgroups v2: cap memory at 128 MB, pids at 50; write to /sys/fs/cgroup/<name>/.
4. Network namespace + veth pair: container gets its own eth0 with an IP.
5. OCI image format: extract layers, overlay filesystem (overlayfs); run any image.

CORE CONCEPTS
- pivot_root swaps / and old_root atomically (safer than chroot alone).
- cgroups: echo $PID > cgroup.procs; write memory.max, pids.max.
- Overlay FS: lower (read-only layers) + upper (writes) + work + merged.

LANGUAGE: Go (syscall package) or C.

VERIFY: container PID 1 is the target process; free inside reports 128 MB max.
