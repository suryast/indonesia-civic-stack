"""
indonesia-civic-stack — Python SDK for Indonesian government data portals.

Usage:
    from civic_stack import bpom, bmkg, ojk

    results = await bpom.search("paracetamol")
    earthquake = await bmkg.get_latest_earthquake()
"""

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from types import ModuleType

try:
    __version__ = version("indonesia-civic-stack")
except PackageNotFoundError:
    # Uninstalled source checkouts have no authoritative distribution version.
    __version__ = "0+unknown"

__all__ = [
    "__version__",
    "ahu",
    "bmkg",
    "bpjph",
    "bpom",
    "bps",
    "djpb",
    "jdih",
    "kpu",
    "ksei",
    "lhkpn",
    "lpse",
    "ojk",
    "oss_nib",
    "simbg",
]


def __getattr__(name: str) -> ModuleType:
    """Load only the requested SDK module, keeping browser extras optional."""
    if name not in __all__ or name == "__version__":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module
