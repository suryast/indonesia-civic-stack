"""BPOM module — Indonesian Food & Drug Authority product registration lookup.

Source: cekbpom.pom.go.id
Method: httpx + BeautifulSoup (static HTML, no JS rendering)
Rate limit: ~10 req/min with exponential backoff

Usage:
    from modules.bpom import fetch, search

    result = await fetch("MD123456789")
    results = await search("mie goreng")
"""
