# Latest messages

Newest first. Every message is also kept as its own file under `messages/YYYY/MM/`.

## Newest: [2026-11-16_0936_shortlist.md](2026/11/2026-11-16_0936_shortlist.md)

### Shortlist 2026-11-16: 0 Tier A, 2 Tier B, 1 Watch

- kind: `shortlist` (Morning shortlist)
- time: 2026-11-16 09:36 New York (2026-11-16T09:36:02.324615-05:00)

> Levels use data up to about 08:59 ET. Re-check the live premarket high at the open.
>
> Rules output only: names, rule results and warnings.

**Late start:** the workflow began after the 09:30 open; the scan still used data up to the normal cutoff.

Candidates (price and gap passed): 7 · Tier A 0 · Tier B 2 · Watch 1 · shown 3 of at most 5

## Tier B: Tier A rules without continuation and prior range

### 1. HIHO: Highway Holdings Limited · score 47.84

> **⚠️ REVERSE SPLIT POSSIBLY PENDING**: [6-K 2026-09-18 no effective date](https://www.sec.gov/Archives/edgar/data/1026785/000121390026101059/ea0305920-6k_highway.htm)

- **price** 1.03 · **gap** 31.2% vs prior close 0.785
- **premarket high** 1.19 full session · 1.17 in the 60 minutes to the cutoff
- **premarket** $41,669,273 traded · 126,889 trades
- **float** 2.9M (yahoo)
- **catalyst** other, quality 3/5 (2/3 runs agree): Highway Holdings declares special cash dividend of $0.43228 per share.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✗ · prior range ✗ · float ✓ · no offering ✓ · no pending split ✓ · catalyst ✓
- **warnings:**
  - EDGAR shares outstanding stale (as of 2026-03-31)

### 2. SLSN: Solesence, Inc. · score 45.82

- **price** 1.68 · **gap** 10.5% vs prior close 1.52
- **premarket high** 1.68 full session · 1.68 in the 60 minutes to the cutoff
- **premarket** $340,128 traded · 1,543 trades
- **float** 18.3M (yahoo)
- **catalyst** none, quality 0/5 (3/3 runs agree): No company-specific news in the last 48 hours; only a 10-Q and an earnings-related 8-K filing.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✓ · prior range ✗ · float ✓ · no offering ✓ · no pending split ✓ · catalyst ✓
- **warnings:**
  - 8-K 2026-10-02 item 3.01 (listing deficiency)
  - recent amended filings (possible restatement): 5 in 90 days (10-K/A 2026-11-10, 10-Q/A 2026-11-10)

## Watch: liquid and on T212, but in no tier

### 3. GP: GreenPower Motor Company Inc. Common Shares

> **WATCH: NO VERIFIABLE CATALYST** (and no prior-day volume surge)

- **price** 1.4383 · **gap** 24.0% vs prior close 1.16
- **premarket high** 2.77 full session · 1.57 in the 60 minutes to the cutoff
- **premarket** $40,457,298 traded · 154,271 trades
- **float** unknown (not checked)
- **catalyst** none, quality 0/5 (3/3 runs agree): No news items for GreenPower Motor; only a generic 6-K filing title from 2026-11-16 was available.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✓ · prior range ✓ · float – · no offering ✓ · no pending split ✓ · catalyst ✗
- **not tiered:** fails catalyst (no verifiable catalyst and no prior-day volume surge (0.8x))
- **warnings:**
  - EDGAR shares outstanding stale (as of 2026-03-31)

## Not shown (first failing rule)

- rule_t212: NCPL
- rule_pm_dollar_volume: RNAZ, COPR, BTOC

_halts feed: NYSE first seen 2026-11-16T09:36:02.551673-05:00; add NYSE to halts.confirmed_markets_

Detail: `data/scans/2026-11-16.json`, `data/candidates.csv`.


## Earlier

- [2026-11-16_0902_test.md](2026/11/2026-11-16_0902_test.md): TEST: notification check 2026-11-16 09:02 ET
- [2026-11-16_0241_test.md](2026/11/2026-11-16_0241_test.md): Test message 2026-11-16 02:41 ET
