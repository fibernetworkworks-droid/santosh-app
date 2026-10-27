"""vedit - precise, verifiable video editing for AI agents and people."""
from .core import ENGINE_VERSION as __version__, RenderError, TimelineError, VeditError, load_timeline, probe, render, verify
from . import ops

__all__ = ["render", "load_timeline", "probe", "verify", "ops", "VeditError", "TimelineError", "RenderError", "__version__"]
