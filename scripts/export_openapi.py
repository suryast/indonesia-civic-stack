#!/usr/bin/env python3
"""
Export the unified OpenAPI spec to docs/openapi.json.

Usage:
    python scripts/export_openapi.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

spec = app.openapi()
output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "openapi.json")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2, ensure_ascii=False)

print(f"OpenAPI spec written to {output_path}")
print(f"  Paths: {len(spec.get('paths', {}))}")
print(f"  Schemas: {len(spec.get('components', {}).get('schemas', {}))}")
