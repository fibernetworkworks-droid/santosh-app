"""A GitHub Actions workflow for a ROS 2 repository: on every pull request it installs ROS 2 on the runner (ros-tooling/setup-ros),
builds her packages with colcon and runs their tests (ros-tooling/action-ros-ci), and - if she names her robot description - expands
the xacro and runs the official URDF parser (check_urdf) on it. The file is text she adds to her repository herself; nothing is pushed."""
from __future__ import annotations

import re
from typing import Any


class CiError(ValueError):
    pass


DISTROS = {"humble": "ubuntu-22.04", "jazzy": "ubuntu-24.04", "kilted": "ubuntu-24.04", "rolling": "ubuntu-24.04"}


def workflow(distro: str = "jazzy", packages: str = "", urdf: str = "", runner: str = "", extra_deps: str = "") -> dict[str, Any]:
    if distro not in DISTROS:
        raise CiError("ROS 2 version: " + ", ".join(DISTROS) + ".")
    pk = [p for p in re.split(r"[\s,]+", str(packages or "").strip()) if p]
    if not pk:
        raise CiError("Packages: the ROS 2 packages to build and test, separated by spaces.")
    for p in pk:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,99}", p):
            raise CiError(f"Package '{p}': ROS 2 package names are lower case letters, digits and underscores, starting with a letter.")
    u = str(urdf or "").strip()
    if u and (not re.fullmatch(r"[\w./\-]{1,200}", u) or ".." in u or u.startswith("/")):
        raise CiError("Robot description: a path inside the repository such as my_robot_description/urdf/robot.urdf.xacro.")
    r = str(runner or "").strip() or DISTROS[distro]
    if not re.fullmatch(r"[\w.\-]{1,40}", r):
        raise CiError("Runner: a runner label such as ubuntu-24.04.")
    deps = [d for d in re.split(r"[\s,]+", str(extra_deps or "").strip()) if d]
    for d in deps:
        if not re.fullmatch(r"[a-z0-9][a-z0-9.+\-]{0,80}", d):
            raise CiError(f"Extra package '{d}': an apt package name.")
    check = ""
    if u:
        check = f"""      - name: Get the repository for the description check
        uses: actions/checkout@v4
        with:
          path: desc
      - name: Check the robot description
        shell: bash
        run: |
          set -eo pipefail
          sudo apt-get install -y liburdfdom-tools ros-{distro}-xacro
          source /opt/ros/{distro}/setup.bash
          S=$(ls -d */install/setup.bash 2>/dev/null | head -1 || true)
          if [ -n "$S" ]; then source "$S"; fi
          F="desc/{u}"
          if [[ "$F" == *.xacro ]]; then xacro "$F" > /tmp/robot.urdf; else cp "$F" /tmp/robot.urdf; fi
          check_urdf /tmp/robot.urdf
"""
    extra = f"      - name: Extra packages\n        run: sudo apt-get update && sudo apt-get install -y {' '.join(deps)}\n" if deps else ""
    yaml = f"""name: ROS 2 build and test
# Made by Hoola's Robotics desk. Builds and tests {', '.join(pk)} on ROS 2 {distro.title()}{' and checks the robot description' if u else ''}.
on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
jobs:
  build:
    runs-on: {r}
    timeout-minutes: 60
    steps:
      - name: Install ROS 2 {distro.title()}
        uses: ros-tooling/setup-ros@v0.7
        with:
          required-ros-distributions: {distro}
{extra}      - name: Build and test
        uses: ros-tooling/action-ros-ci@v0.4
        with:
          target-ros2-distro: {distro}
          package-name: {' '.join(pk)}
{check}"""
    return {"file": ".github/workflows/ros2-ci.yml", "yaml": yaml, "runner": r,
            "note": ("Put it at .github/workflows/ros2-ci.yml. The build resolves each package's dependencies with rosdep from its package.xml, "
                     "so declare every dependency there. Check the action versions (ros-tooling/setup-ros, ros-tooling/action-ros-ci) against "
                     "their pages before you rely on it - Hoola has not run this workflow on GitHub.")}
