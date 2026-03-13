"""AHU module — Indonesian Legal Entity Administration (company registry).

Source: ahu.go.id
Method: Playwright + CF Worker proxy (datacenter IP blocking risk)
Rate limit: Very conservative — aggressive bot detection

Usage:
    from modules.ahu import fetch, search

    result = await fetch("PT Contoh Indonesia")
    results = await search("CV Maju Bersama")
"""
