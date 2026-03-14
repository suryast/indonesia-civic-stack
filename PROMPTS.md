# Example Prompts for AI Agents

Copy-paste these prompts into Claude Code, Claude Desktop, ChatGPT, or any MCP-compatible agent with civic-stack tools connected.

---

## 🔍 Single Portal Queries

### Food & Drug (BPOM)
```
Check if BPOM registration number MD 867031247085 is still active.
Show me the product name, manufacturer, and expiry date.
```

```
Search BPOM for all registered paracetamol products.
Show results in a table with registration number, product name, and status.
```

### Halal Certification (BPJPH)
```
Is "Indomie Goreng" halal certified? Search the BPJPH database and show the certificate details.
```

```
Cross-reference "Wardah" across both BPJPH (halal) and BPOM (cosmetics) databases.
Show a side-by-side comparison.
```

### Company Registry (AHU)
```
Look up "PT Telkom Indonesia" in the AHU company registry.
Who are the directors and what's the company status?
```

### Financial Licenses (OJK)
```
Is "Bank Syariah Indonesia" licensed by OJK? Also check the waspada (warning) list.
```

```
Search OJK for all licensed fintech companies. How many are there?
```

### Earthquakes & Weather (BMKG)
```
What was the latest earthquake in Indonesia? Show magnitude, location, depth, and time.
```

```
Get the weather forecast for Bali from BMKG.
```

---

## 🔗 Multi-Portal Cross-Reference

### Company Due Diligence
```
I need to verify a company called "PT Maju Bersama". Run a full due diligence check:
1. AHU — is it registered? Who are the directors?
2. OJK — does it have a financial license? Is it on the waspada list?
3. BPOM — does it have any registered products?
4. OSS — what's its NIB (business identity number)?

Present findings in a single summary table with ✅/❌ for each check.
```

### Product Safety Audit
```
Audit the product "Tolak Angin" across all relevant databases:
- BPOM registration status
- BPJPH halal certification
- Manufacturer company status in AHU

Flag any mismatches or expired registrations.
```

---

## 📊 Interactive Diagrams (Claude Artifacts)

### Architecture Visualization
```
Using the civic-stack MCP tools, create an interactive diagram showing:
- All 11 government portals and their data types
- Which ones are currently accessible vs degraded
- The data flow from portal → scraper → SDK → your app

Use a Mermaid diagram in an artifact.
```

### Data Relationship Map
```
Query AHU for "PT Indofood" and BPOM for products by "Indofood".
Then create an interactive diagram showing:
- The company entity (from AHU)
- All its registered products (from BPOM)  
- Halal certification status for each product (from BPJPH)

Render as a tree diagram in an artifact.
```

### Earthquake Dashboard
```
Get the last 15 significant earthquakes from BMKG.
Create an interactive artifact showing:
- A timeline of earthquakes by date
- Magnitude distribution (bar chart)
- A table with all details

Use React in a Claude artifact with charts.
```

### Election Data Explorer
```
Search KPU for candidates in "Jakarta".
Create an interactive artifact with:
- A filterable table of candidates
- Party distribution pie chart
- Search/filter by name or party

Build it as a React component in a Claude artifact.
```

---

## 🏗️ Build Something

### Compliance Dashboard
```
I want to build a compliance dashboard. Using civic-stack tools:
1. Search OJK for all licensed banks
2. For each bank, check AHU company status
3. Cross-reference with the OJK waspada list

Create a React artifact showing a dashboard with:
- Total licensed banks
- Active vs inactive breakdown
- Any companies on the waspada list highlighted in red
```

### Natural Disaster Monitor
```
Using BMKG tools, build a real-time earthquake monitor artifact:
1. Get the latest earthquake
2. Get earthquake history (last 15)
3. Create a dashboard showing:
   - Latest earthquake with large magnitude display
   - History table sorted by magnitude
   - Alert banner if latest earthquake is M5.0+
   
Auto-refresh concept with a "Check Again" button.
```

### Halal Product Scanner
```
Build a halal product checker artifact:
1. Input field for product name or barcode
2. On submit, search BPJPH for halal cert AND BPOM for registration
3. Show combined results:
   - ✅ Halal + BPOM registered = SAFE
   - ⚠️ Halal but no BPOM = CHECK MANUALLY
   - ❌ Not found = UNKNOWN
   
Build as an interactive React artifact.
```

---

## 🤖 Agent Workflows

### Daily Monitoring
```
Set up a daily check:
1. Get latest earthquake from BMKG — alert if M5.0+
2. Check BPOM for any recalled products (search "ditarik")
3. Check OJK waspada list for newly added entities

Summarize findings in a brief daily report.
```

### Investigative Research
```
I'm researching government procurement in Jakarta.
1. Search LPSE for tenders containing "jalan" (road construction)
2. For each winning vendor, look up their company in AHU
3. Cross-reference vendor directors with LHKPN wealth declarations

Flag any potential conflicts of interest.
```

---

## 💡 Tips

- **Start simple**: Try a single-portal query first to see the response format
- **Chain queries**: Use results from one portal as input for another
- **Ask for artifacts**: Claude can build interactive dashboards from civic-stack data
- **Request tables**: Structured data works best in table format
- **Specify format**: "Show as table", "Create a chart", "Build an interactive artifact"
- **Multi-source**: The real power is cross-referencing across portals — always combine at least 2 sources
