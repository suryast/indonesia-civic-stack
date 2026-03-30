"""
indonesia-civic-stack — Python SDK for Indonesian government data portals.

Usage:
    from civic_stack import bpom, bmkg, ojk

    results = await bpom.search("paracetamol")
    earthquake = await bmkg.get_latest_earthquake()
"""

__version__ = "0.1.0"

# Lazy imports — modules are only loaded when accessed
from civic_stack import (  # noqa: F401
    ahu,
    bmkg,
    bpjph,
    bpom,
    bps,
    djpb,
    jdih,
    kpu,
    ksei,
    lhkpn,
    lpse,
    ojk,
    oss_nib,
    simbg,
)

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
