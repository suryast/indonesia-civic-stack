# HalalKah → civic-stack Migration Guide

This guide walks through replacing the bespoke halalkah.id scraper with
`indonesia-civic-stack` modules. The application logic and response shape
are unchanged — only the data layer is swapped.

---

## Before (bespoke scraper)

```python
# The old halalkah.id scraper — duplicated logic, no tests, bit-rots quickly
import httpx
from bs4 import BeautifulSoup

async def check_halal_status(product_name: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://sertifikasi.halal.go.id/...",
            params={"q": product_name},
        )
    soup = BeautifulSoup(resp.text, "html.parser")
    # ... 60 lines of fragile HTML parsing ...
    return {
        "is_halal": ...,
        "cert_no": ...,
        "expiry": ...,
    }
```

Problems:
- No tests → breaks silently when the portal changes
- No rate limiting → risk of IP block
- Bespoke result shape → tight coupling to halalkah.id frontend
- No BPOM cross-reference → missed mismatch cases

---

## After (civic-stack)

```python
from examples.halalkah.halal_check import HalalKahChecker

checker = HalalKahChecker(proxy_url=os.environ.get("CIVIC_PROXY_URL"))

result = await checker.verify_product("mie goreng spesial")
# result.is_halal          → True
# result.halal_status      → "CERTIFIED"
# result.bpom_status       → "ACTIVE"
# result.has_mismatch      → False
# result.cert_no           → "ID00110019882120240001"
# result.company           → "PT INDOFOOD SUKSES MAKMUR TBK"
```

Benefits:
- Tested against VCR fixtures — breaks loudly if portal changes
- Built-in rate limiting (token bucket, per module)
- Camoufox fingerprint randomization on Playwright sessions
- BPOM cross-reference built in — flags lapsed certs automatically
- Weekly scheduled CI alerts the team when a portal degrades

---

## Step-by-step Migration

### 1. Install

```bash
pip install indonesia-civic-stack
# or add to requirements.txt / pyproject.toml
```

### 2. Set environment variable

```bash
# .env
CIVIC_PROXY_URL=https://your-cloudflare-worker.workers.dev
```

### 3. Replace the data layer call

Find every place halalkah.id calls the old scraper and replace with:

```python
# Old
result = await old_halal_scraper.check(product_name)

# New
from examples.halalkah.halal_check import HalalKahChecker
checker = HalalKahChecker(proxy_url=settings.CIVIC_PROXY_URL)
result = await checker.verify_product(product_name)
```

The `HalalVerificationResult` dataclass has the same fields as the old scraper
result dict — access them as `result.is_halal`, `result.cert_no`, etc.

### 4. Update the mismatch handling UI (optional but recommended)

The new checker exposes `result.has_mismatch` and `result.mismatch_detail`.
Use these to show the user when a product has a BPOM registration but a
lapsed halal cert (or vice versa) — a case the old scraper missed entirely.

```python
if result.has_mismatch:
    show_warning(f"⚠️ {result.mismatch_detail}")
```

### 5. Run the smoke test

```bash
python examples/halalkah/smoke_test.py --live
```

All cases must pass before deploying to production.

---

## Verify it works end-to-end

```bash
# Start the API server
uvicorn app:app --reload

# Test the cross-reference endpoint
curl "http://localhost:8000/bpjph/cross-ref?product_name=mie+goreng+spesial"

# Expected response
{
  "product_name": "mie goreng spesial",
  "bpjph": {"found": true, "status": "ACTIVE", ...},
  "bpom": {"found": true, "status": "ACTIVE", ...},
  "mismatch": false,
  "mismatch_detail": null
}
```

---

## Rollback

If you need to roll back, the old scraper code is still in the
`feat/bespoke-scraper` branch. civic-stack is additive — you can
run both in parallel during a canary rollout by feature-flagging the
`CIVIC_STACK_ENABLED` environment variable.
