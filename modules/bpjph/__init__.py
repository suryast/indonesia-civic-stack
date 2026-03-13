"""BPJPH module — Indonesian Halal Product Guarantee Agency certification lookup.

Source: sertifikasi.halal.go.id
Method: Playwright + Camoufox (JS-rendered, form submission)
Rate limit: Conservative — portal is fragile

Usage:
    from modules.bpjph import fetch, search

    result = await fetch("BPJPH-12345")
    results = await search("PT Indofood")
"""
