# Module: `kpu`

**Source portal:** sirekap-obj-data.kpu.go.id + infopemilu.kpu.go.id
**Scrape method:** REST API wrapper (clean JSON endpoints, no scraping)
**Phase:** 3
**License:** MIT
**Status:** ACTIVE

---

## Source

| Field | Value |
|---|---|
| Portal URL | `https://sirekap-obj-data.kpu.go.id/pemilu` (SIREKAP) + `https://infopemilu.kpu.go.id` (Infopemilu) |
| Operator | Komisi Pemilihan Umum (KPU RI) |
| Data type | 2024 Pemilu results, candidate profiles, campaign finance (SILON) |
| Auth required | None — public open data APIs |
| Last verified | 2026-03-13 |

---

## Rate Limits & Block Behaviour

| Parameter | Value |
|---|---|
| Safe request rate | ~2 req/s (generous API limits) |
| Block trigger | Unknown — no blocking observed |
| Block type | TBD |
| Mitigation | Built-in token-bucket rate limiter (2 req/s) |
| IP rotation needed | Not required |

---

## Normalized Schema (`result` object)

### Candidate profile

```python
{
    "candidate_id": str,          # KPU candidate ID or nomor urut
    "name": str,                  # Full candidate name
    "party": str | None,          # Party name or abbreviation
    "party_no": int | None,       # Party number
    "election_type": str | None,  # "presiden" | "dpr" | "dpd" | "dprd_prov" | "dprd_kab"
    "region": str | None,         # Dapil (electoral district)
    "position": str | None,       # Jabatan / position
    "gender": str | None,         # "L" | "P"
    "photo_url": str | None,      # Candidate photo URL
    "vote_count": int | None,     # Total votes received (if available)
    "elected": bool | None,       # True if candidate won
}
```

### Election results (SIREKAP)

```python
{
    "region_code": str,                # Province/regency code ("0" for national)
    "election_type": str,              # "ppwp" | "pdpr" | "dpd" | "pdprd_prov" | "pdprd_kab"
    "total_votes": int | None,         # Total valid votes counted
    "results_by_party": dict,          # Party code → vote count mapping
    "tps_reported": int | None,        # Number of TPS reported
    "tps_total": int | None,           # Total TPS in region
    "last_updated": str | None,        # ISO 8601 timestamp
}
```

### Campaign finance (SILON)

```python
{
    "candidate_id": str,               # KPU candidate ID
    "candidate_name": str,             # Candidate name
    "initial_balance_idr": float | None,  # Saldo awal in IDR
    "total_income_idr": float | None,     # Total penerimaan in IDR
    "total_expenditure_idr": float | None, # Total pengeluaran in IDR
    "reporting_period": str | None,    # Periode laporan
    "report_status": str | None,       # Status laporan
}
```

---

## MCP Tools

| Tool | Signature | Description |
|---|---|---|
| `get_candidate` | `(name_or_id: str) -> dict` | Get candidate profile by name or ID |
| `search_kpu_candidates` | `(name: str, election_type: str?, party: str?) -> list[dict]` | Search candidates with filters |
| `get_election_results_kpu` | `(region_code: str, election_type: str) -> dict` | Get SIREKAP real-time results |
| `get_campaign_finance_kpu` | `(candidate_id: str) -> dict` | Get SILON campaign finance report |

### claude mcp add

```bash
claude mcp add kpu -- python -m modules.kpu.server
```

---

## FastAPI Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/kpu/candidate/{candidate_id}` | Get candidate profile |
| `GET` | `/kpu/search?q=name&election_type=...&party=...` | Search candidates |
| `GET` | `/kpu/results/{region_code}?election_type=...` | Get SIREKAP election results |
| `GET` | `/kpu/finance/{candidate_id}` | Get SILON campaign finance |

---

## Example Response (Candidate)

```json
{
  "result": {
    "candidate_id": "1",
    "name": "PRABOWO SUBIANTO - GIBRAN RAKABUMING RAKA",
    "party": "GERINDRA",
    "party_no": 2,
    "election_type": "presiden",
    "region": "Nasional",
    "position": "Presiden & Wakil Presiden",
    "gender": "L",
    "photo_url": "https://infopemilu.kpu.go.id/...",
    "vote_count": 96214691,
    "elected": true
  },
  "found": true,
  "status": "ACTIVE",
  "confidence": 1.0,
  "source_url": "https://infopemilu.kpu.go.id/Pemilu/caleg/list",
  "fetched_at": "2026-03-13T10:00:00Z",
  "last_updated": null,
  "module": "kpu",
  "raw": null
}
```

---

## Known Issues & Quirks

- SIREKAP data is real-time during elections but becomes static after final tallies are certified
- Campaign finance (SILON) data availability varies by candidate and reporting compliance
- Region code "0" returns national aggregates
- Election type codes in SIREKAP differ from Infopemilu: "ppwp" (presiden), "pdpr" (DPR), etc.
- No personal data — all data is voluntarily published by candidates or generated from public vote tallies

---

## VCR Fixtures

| Cassette | Scenario |
|---|---|
| TBD | Candidate profile found |
| TBD | Candidate not found |
| TBD | SIREKAP results for DKI Jakarta DPR |
| TBD | Campaign finance report |

---

## Legal Basis

This module queries KPU's official public APIs for 2024 Pemilu data published for
transparency and voter information purposes. No authentication is required. Data is
fetched on demand and not persisted. No personal data beyond what candidates voluntarily
publish (names, photos, party affiliation) is accessed. All data is public record.
