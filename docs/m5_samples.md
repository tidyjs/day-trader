# M5 sample messages (rendered 2026-11-16 from the saved scans)

Real output of `src/shortlist.py` for the five saved days, plus a sample failure, with the Watch rule pre-declared 2026-11-16 (SPEC 4.4c). These are historical runs, so they carry "historical run" warnings that a live scan won't. For review only, not committed messages.

---

<!-- 2026-11-09_0915_no_trade.md -->

# No names today (2026-11-09)

- kind: `no_trade` (No names today)
- time: 2026-11-09 09:15 New York (2026-11-09T09:15:00-05:00)

> Levels use data up to about 08:59 ET. Re-check the live premarket high at the open.
>
> Rules output only: names, rule results and warnings.

Candidates (price and gap passed): 7 · Tier A 0 · Tier B 0 · Watch 0 · shown 0 of at most 5

No name reached Tier A, Tier B or Watch today.

## Not shown (first failing rule)

- rule_t212: YMAT, NCPL
- rule_pm_dollar_volume: EZGO, WORX, CLRB, WLDS, BMR

## Scan warnings

- historical run: T212 list is from 2026-11-15 (later than scan day)
- historical run: universe is Alpaca's asset list from 2026-11-15 (no delisted names)

_halts feed: NYSE not seen yet (1 weekday(s) of fetches; markets so far: AMEX:3 NASDAQ:20)_

Detail: `data/scans/2026-11-09.json`, `data/candidates.csv`.

---

<!-- 2026-11-10_0915_shortlist.md -->

# Shortlist 2026-11-10: 0 Tier A, 4 Tier B, 1 Watch

- kind: `shortlist` (Morning shortlist)
- time: 2026-11-10 09:15 New York (2026-11-10T09:15:00-05:00)

> Levels use data up to about 08:59 ET. Re-check the live premarket high at the open.
>
> Rules output only: names, rule results and warnings.

Candidates (price and gap passed): 9 · Tier A 0 · Tier B 4 · Watch 2 · shown 5 of at most 5

## Tier B: Tier A rules without continuation and prior range

### 1. AMIX: Autonomix Medical, Inc. · score 49.4

> **⚠️ REVERSE SPLIT POSSIBLY PENDING**: [8-K 2026-11-03 no effective date](https://www.sec.gov/Archives/edgar/data/1617867/000143774926034696/amix20261029_8k.htm); [DEF 14A 2026-09-14 no effective date](https://www.sec.gov/Archives/edgar/data/1617867/000143774926030345/amix20260905_def14a.htm)

- **price** 1.89 · **gap** 11.2% vs prior close 1.7
- **premarket high** 2.3797 full session · 1.9 in the 60 minutes to the cutoff
- **premarket** $11,195,428 traded · 43,029 trades
- **float** 1.9M (yahoo)
- **catalyst** other, quality 2/5 (3/3 runs agree): Autonomix Medical to be issued U.S. patent 12,793,841 covering physiological signal circuitry for medical devices.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✓ · prior range ✗ · float ✓ · no offering ✓ · no pending split ✓ · catalyst ✓
- **warnings:**
  - halt status unknown (historical run: the feed only holds current halts)
  - Yahoo vs EDGAR shares outstanding differ 111% (2.0M vs 1.0M)
  - historical run: float is today's Yahoo value

### 2. KLTR: Kaltura, Inc. · score 41.97

- **price** 1.68 · **gap** 17.5% vs prior close 1.43
- **premarket high** 1.73 full session · 1.71 in the 60 minutes to the cutoff
- **premarket** $197,889 traded · 598 trades
- **float** 92.2M (yahoo)
- **catalyst** earnings, quality 5/5 (3/3 runs agree): Kaltura reported Q3 2026 sales of $47.3M beating estimates, adjusted EPS $0.02, and raised FY2026 guidance.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✗ · prior range ✗ · float ✗ · no offering ✓ · no pending split ✓ · catalyst ✓
- **warnings:**
  - halt status unknown (historical run: the feed only holds current halts)
  - spread unknown (no SIP quotes before cutoff)
  - above 50M float (92.2M, yahoo)
  - historical run: float is today's Yahoo value

### 3. TTEC: TTEC Holdings, Inc. · score 39.84

- **price** 1.65 · **gap** 18.3% vs prior close 1.395
- **premarket high** 1.7 full session · 1.7 in the 60 minutes to the cutoff
- **premarket** $550,334 traded · 2,167 trades
- **float** 20.4M (yahoo)
- **catalyst** earnings, quality 4/5 (3/3 runs agree): TTEC reported Q3 2026 sales of $492.2M beating estimates and affirmed FY2026 guidance.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✗ · prior range ✓ · float ✓ · no offering ✓ · no pending split ✓ · catalyst ✓
- **warnings:**
  - halt status unknown (historical run: the feed only holds current halts)
  - historical run: float is today's Yahoo value

### 4. ZNTL: Zentalis Pharmaceuticals, Inc. · score 27.46

- **price** 1.9562 · **gap** 12.4% vs prior close 1.74
- **premarket high** 1.9738 full session · 1.9738 in the 60 minutes to the cutoff
- **premarket** $157,886 traded · 118 trades
- **float** 78.4M (yahoo)
- **catalyst** earnings, quality 4/5 (3/3 runs agree): Zentalis reported Q3 2026 results with EPS of $(0.34) beating estimates and $228.9M cash; Wedbush upgraded to Outperform.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✗ · prior range ✗ · float ✗ · no offering ✓ · no pending split ✓ · catalyst ✓
- **warnings:**
  - halt status unknown (historical run: the feed only holds current halts)
  - spread unknown (no SIP quotes before cutoff)
  - above 50M float (78.4M, yahoo)
  - historical run: float is today's Yahoo value

## Watch: liquid and on T212, but in no tier

### 5. MNDO: MIND C.T.I. Ltd.

> **WATCH: NO VERIFIABLE CATALYST** (and no prior-day volume surge)

- **price** 1.2599 · **gap** 44.8% vs prior close 0.87
- **premarket high** 1.28 full session · 1.28 in the 60 minutes to the cutoff
- **premarket** $10,454,275 traded · 20,871 trades
- **float** unknown (not checked)
- **catalyst** none, quality 0/5
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✗ · prior range ✗ · float – · no offering ✓ · no pending split ✓ · catalyst ✗
- **not tiered:** fails continuation, prior range, catalyst (no verifiable catalyst and no prior-day volume surge (1.8x))
- **warnings:**
  - halt status unknown (historical run: the feed only holds current halts)
  - EDGAR shares outstanding stale (as of 2025-12-31)

## Not shown (first failing rule)

- beyond the 5-name limit: WFF
- rule_pm_dollar_volume: ONEN, YXT, HTOO

## Scan warnings

- historical run: T212 list is from 2026-11-15 (later than scan day)
- historical run: universe is Alpaca's asset list from 2026-11-15 (no delisted names)

_halts feed: NYSE not seen yet (1 weekday(s) of fetches; markets so far: AMEX:3 NASDAQ:20)_

Detail: `data/scans/2026-11-10.json`, `data/candidates.csv`.

---

<!-- 2026-11-11_0915_shortlist.md -->

# Shortlist 2026-11-11: 0 Tier A, 1 Tier B, 2 Watch

- kind: `shortlist` (Morning shortlist)
- time: 2026-11-11 09:15 New York (2026-11-11T09:15:00-05:00)

> Levels use data up to about 08:59 ET. Re-check the live premarket high at the open.
>
> Rules output only: names, rule results and warnings.

Candidates (price and gap passed): 10 · Tier A 0 · Tier B 1 · Watch 2 · shown 3 of at most 5

## Tier B: Tier A rules without continuation and prior range

### 1. GEVO: Gevo, Inc. · score 45.5

- **price** 1.66 · **gap** 19.4% vs prior close 1.39
- **premarket high** 1.68 full session · 1.67 in the 60 minutes to the cutoff
- **premarket** $848,231 traded · 2,129 trades
- **float** 228.3M (yahoo)
- **catalyst** earnings, quality 5/5 (3/3 runs agree): Gevo reports record Q3 2026 results: revenue about $83M, net income $23M, EPS $0.12 beating estimates.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✗ · prior range ✗ · float ✗ · no offering ✓ · no pending split ✓ · catalyst ✓
- **warnings:**
  - halt status unknown (historical run: the feed only holds current halts)
  - above 50M float (228.3M, yahoo)
  - historical run: float is today's Yahoo value

## Watch: liquid and on T212, but in no tier

### 2. BRAI: Braiin Limited

> **WATCH: PROMO / PUMP FLAGGED** by at least 2 of 3 classifier runs

- **price** 1.97 · **gap** 10.7% vs prior close 1.78
- **premarket high** 2 full session · 2 in the 60 minutes to the cutoff
- **premarket** $270,216 traded · 804 trades
- **float** unknown (not checked)
- **catalyst** promo, quality 1/5 (3/3 runs agree): Braiin named presenting partner of a defence robotics and counter-UAS congress in Queensland; no financial terms disclosed.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✗ · prior range ✗ · float – · no offering ✓ · no pending split ✓ · catalyst ✗
- **not tiered:** fails continuation, prior range, catalyst (classifier: promo/pump (3/3 runs) (Braiin named presenting partner of a defence robotics and counter-UAS congress i))
- **warnings:**
  - halt status unknown (historical run: the feed only holds current halts)
  - EDGAR shares outstanding missing

### 3. CANG: Cango Inc.

> **WATCH: NO VERIFIABLE CATALYST** (and no prior-day volume surge)

- **price** 1.31 · **gap** 14.9% vs prior close 1.14
- **premarket high** 1.34 full session · 1.33 in the 60 minutes to the cutoff
- **premarket** $241,745 traded · 526 trades
- **float** unknown (not checked)
- **catalyst** none, quality 0/5
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✗ · prior range ✗ · float – · no offering ✓ · no pending split ✓ · catalyst ✗
- **not tiered:** fails continuation, prior range, catalyst (no verifiable catalyst and no prior-day volume surge (0.1x))
- **warnings:**
  - halt status unknown (NYSE: feed coverage not confirmed)
  - EDGAR shares outstanding missing

## Not shown (first failing rule)

- rule_t212: YMAT, BDAI, CABR
- rule_pm_dollar_volume: SNOA, DLPN, DPU, SCLX

## Scan warnings

- historical run: T212 list is from 2026-11-15 (later than scan day)
- historical run: universe is Alpaca's asset list from 2026-11-15 (no delisted names)

_halts feed: NYSE not seen yet (1 weekday(s) of fetches; markets so far: AMEX:3 NASDAQ:20)_

Detail: `data/scans/2026-11-11.json`, `data/candidates.csv`.

---

<!-- 2026-11-12_0915_shortlist.md -->

# Shortlist 2026-11-12: 1 Tier A, 1 Tier B, 0 Watch

- kind: `shortlist` (Morning shortlist)
- time: 2026-11-12 09:15 New York (2026-11-12T09:15:00-05:00)

> Levels use data up to about 08:59 ET. Re-check the live premarket high at the open.
>
> Rules output only: names, rule results and warnings.

Candidates (price and gap passed): 5 · Tier A 1 · Tier B 1 · Watch 0 · shown 2 of at most 5

## Tier A: passed every rule

### 1. ICMB: Investcorp Credit Management BDC, Inc. · score 95.67

> **⚠️ MERGER TARGET: price likely pinned to deal terms**

- **price** 1.04 · **gap** 68.3% vs prior close 0.6181
- **premarket high** 1.16 full session · 1.1 in the 60 minutes to the cutoff
- **premarket** $31,516,830 traded · 106,380 trades
- **float** 14.4M (edgar shares outstanding (ceiling))
- **catalyst** merger, quality 5/5 (3/3 runs agree): ICMB agreed to merge into BCP Investment, subject to ICMB stockholder approval; shares jumped after hours.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✓ · prior range ✓ · float ✓ · no offering ✓ · no pending split ✓ · catalyst ✓
- **warnings:**
  - halt status unknown (historical run: the feed only holds current halts)
  - float missing (Yahoo)
  - historical run: float is today's Yahoo value

## Tier B: Tier A rules without continuation and prior range

### 2. CRMN: Skyline Builders Group Holding Limited · score 48.35

- **price** 1.71 · **gap** 47.4% vs prior close 1.16
- **premarket high** 10.84 full session · 2.9 in the 60 minutes to the cutoff
- **premarket** $110,337,601 traded · 340,776 trades
- **float** 0.3M (yahoo)
- **catalyst** other, quality 1/5 (3/3 runs agree): Skyline Builders announces Nasdaq ticker change from KAZR to CRMN effective November 12, 2026.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✗ · prior range ✗ · float ✓ · no offering ✓ · no pending split ✓ · catalyst ✓
- **warnings:**
  - halt status unknown (historical run: the feed only holds current halts)
  - EDGAR shares outstanding missing
  - historical run: float is today's Yahoo value

## Not shown (first failing rule)

- rule_pm_dollar_volume: GITS, YXT, MSC

## Scan warnings

- historical run: T212 list is from 2026-11-15 (later than scan day)
- historical run: universe is Alpaca's asset list from 2026-11-15 (no delisted names)

_halts feed: NYSE not seen yet (1 weekday(s) of fetches; markets so far: AMEX:3 NASDAQ:20)_

Detail: `data/scans/2026-11-12.json`, `data/candidates.csv`.

---

<!-- 2026-11-13_0915_shortlist.md -->

# Shortlist 2026-11-13: 1 Tier A, 1 Tier B, 1 Watch

- kind: `shortlist` (Morning shortlist)
- time: 2026-11-13 09:15 New York (2026-11-13T09:15:00-05:00)

> Levels use data up to about 08:59 ET. Re-check the live premarket high at the open.
>
> Rules output only: names, rule results and warnings.

Candidates (price and gap passed): 12 · Tier A 1 · Tier B 1 · Watch 1 · shown 3 of at most 5

## Tier A: passed every rule

### 1. SLSN: Solesence, Inc. · score 75.41

- **price** 1.15 · **gap** 26.5% vs prior close 0.909
- **premarket high** 1.35 full session · 1.2 in the 60 minutes to the cutoff
- **premarket** $533,045 traded · 2,461 trades
- **float** 18.3M (yahoo)
- **catalyst** earnings, quality 4/5 (3/3 runs agree): Solésence reported Q3 2026 results with EPS of $0.05 and sales of $19.98M, up from $14.6M.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✓ · prior range ✓ · float ✓ · no offering ✓ · no pending split ✓ · catalyst ✓
- **warnings:**
  - halt status unknown (historical run: the feed only holds current halts)
  - 8-K 2026-10-02 item 3.01 (listing deficiency)
  - recent amended filings (possible restatement): 5 in 90 days (10-K/A 2026-11-10, 10-Q/A 2026-11-10)
  - historical run: float is today's Yahoo value

## Tier B: Tier A rules without continuation and prior range

### 2. MRLN: Merlin, Inc. · score 61.09

- **price** 1.2802 · **gap** 32.8% vs prior close 0.9644
- **premarket high** 1.53 full session · 1.3784 in the 60 minutes to the cutoff
- **premarket** $15,408,096 traded · 48,540 trades
- **float** 46.4M (yahoo)
- **catalyst** earnings, quality 4/5 (3/3 runs agree): Merlin reports Q3 2026 results with EPS beat and $8.9M USSOCOM C-130J task order; 424B3 filings present.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✓ · prior range ✗ · float ✓ · no offering ✓ · no pending split ✓ · catalyst ✓
- **warnings:**
  - halt status unknown (historical run: the feed only holds current halts)
  - resale registration, supply overhang: 424B3 2026-11-13 supplement to resale registration (424B3 2026-05-13), supply overhang
  - possible offering: 424B3 2026-11-13 supplement to a primary offering prospectus (424B3 2026-04-21), no new offering terms
  - historical run: float is today's Yahoo value

## Watch: liquid and on T212, but in no tier

### 3. STAK: STAK Inc.

> **WATCH: NO VERIFIABLE CATALYST** (and no prior-day volume surge)

- **price** 1.75 · **gap** 15.5% vs prior close 1.515
- **premarket high** 2.1 full session · 2.1 in the 60 minutes to the cutoff
- **premarket** $8,237,208 traded · 32,984 trades
- **float** unknown (not checked)
- **catalyst** none, quality 0/5
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✓ · prior range ✗ · float – · no offering ✓ · no pending split ✓ · catalyst ✗
- **not tiered:** fails prior range, catalyst (no verifiable catalyst and no prior-day volume surge (0.2x))
- **warnings:**
  - halt status unknown (historical run: the feed only holds current halts)
  - EDGAR shares outstanding stale (as of 2026-06-30)

## Not shown (first failing rule)

- rule_pm_dollar_volume: BBCI, LFMD, BIRD, CDXS, BOF, XBIO, SKYE, SPRU, CALC

## Scan warnings

- historical run: T212 list is from 2026-11-15 (later than scan day)
- historical run: universe is Alpaca's asset list from 2026-11-15 (no delisted names)

_halts feed: NYSE not seen yet (1 weekday(s) of fetches; markets so far: AMEX:3 NASDAQ:20)_

Detail: `data/scans/2026-11-13.json`, `data/candidates.csv`.

---

<!-- 2026-11-17_0916_scanner_failed.md -->

# Scanner failed 2026-11-17

- kind: `scanner_failed` (Scanner failed)
- time: 2026-11-17 09:16 New York (2026-11-17T09:16:00-05:00)

> **No shortlist today.** The morning scan failed.
>
> Do not use an earlier shortlist: its data is from another day.

What to check: the failed run in the repo's **Actions** tab, and `data/` for a partial scan.

<details><summary>Error details</summary>

ConnectionError: HTTPSConnectionPool(host='data.alpaca.markets'): Max retries exceeded (sample)

</details>
