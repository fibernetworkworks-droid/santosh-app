"""v0.141 Hoola 3D Studio: Blender (official build) driven by Hoola, the way the Blender MCP servers drive it, but on the
server inside a locked box: every script is checked in code first (guard.py), runs in a separate Blender process with no
network, no secrets and its own folder (sandbox.py + runner.py), and all file reading / writing is done by Hoola's own
runner, never by the model's code."""
