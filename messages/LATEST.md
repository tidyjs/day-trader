# Latest messages

Newest first. Every message is also kept as its own file under `messages/YYYY/MM/`.

## Newest: [2026-11-23_0941_shortlist.md](2026/11/2026-11-23_0941_shortlist.md)

### Shortlist 2026-11-23: 0 Tier A, 4 Tier B, 1 Watch

- kind: `shortlist` (Morning shortlist)
- time: 2026-11-23 09:41 New York (2026-11-23T09:41:16.759800-05:00)

> Levels use data up to about 08:59 ET. Re-check the live premarket high at the open.
>
> Rules output only: names, rule results and warnings.

**Late start:** the workflow began after the 09:30 open; the scan still used data up to the normal cutoff.

Candidates (price and gap passed): 26 · Tier A 0 · Tier B 4 · Watch 5 · shown 5 of at most 5

## Tier B: Tier A rules without continuation and prior range

### 1. DWTX: Dogwood Therapeutics, Inc. · score 66.67

- **price** 1.4 · **gap** 35.3% vs prior close 1.035
- **premarket high** 1.46 full session · 1.46 in the 60 minutes to the cutoff
- **premarket** $9,264,332 traded · 33,046 trades
- **float** 6.1M (yahoo)
- **catalyst** other, quality 3/5 (3/3 runs agree): Dogwood reports Phase 2b trial of Halneuron met primary endpoint for chemotherapy-induced neuropathic pain.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✓ · prior range ✗ · float ✓ · no offering ✓ · no pending split ✓ · catalyst ✓

### 2. MSS: Maison Solutions Inc. · score 54.7

- **price** 1.28 · **gap** 16.4% vs prior close 1.1
- **premarket high** 1.44 full session · 1.34 in the 60 minutes to the cutoff
- **premarket** $7,073,550 traded · 32,212 trades
- **float** 0.4M (yahoo)
- **catalyst** none, quality 0/5 (3/3 runs agree): No company-specific news in last 48 hours; only an 8-K filing dated 2026-11-23 with unspecified items.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✓ · prior range ✗ · float ✓ · no offering ✓ · no pending split ✓ · catalyst ✓
- **warnings:**
  - 8-K 2026-11-23 item 3.01 (listing deficiency)
  - 8-K 2026-09-29 item 3.01 (listing deficiency)
  - 8-K 2026-08-25 item 3.01 (listing deficiency)
  - EDGAR shares outstanding stale (as of 2024-08-06)
  - Yahoo vs EDGAR shares outstanding differ 2053% (0.8M vs 17.5M)

### 3. RCAT: Red Cat Holdings, Inc. · score 22.76

- **price** 1.98 · **gap** 10.3% vs prior close 1.795
- **premarket high** 1.98 full session · 1.98 in the 60 minutes to the cutoff
- **premarket** $560,564 traded · 1,059 trades
- **float** 140.1M (yahoo)
- **catalyst** contract, quality 3/5 (3/3 runs agree): Red Cat Holdings selected as one of five companies for a $150,000 Army innovation award.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✗ · prior range ✗ · float ✗ · no offering ✓ · no pending split ✓ · catalyst ✓
- **warnings:**
  - above 50M float (140.1M, yahoo)

### 4. CYPH: Cypherpunk Technologies Inc. · score 17.77

- **price** 1.6793 · **gap** 19.1% vs prior close 1.41
- **premarket high** 1.68 full session · 1.68 in the 60 minutes to the cutoff
- **premarket** $863,156 traded · 1,102 trades
- **float** 111.3M (yahoo)
- **catalyst** other, quality 1/5 (2/3 runs agree): Pomerantz announces investigation into Cypherpunk; Cantor Fitzgerald maintains Buy and raises price target to $5.00.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✗ · prior range ✗ · float ✗ · no offering ✓ · no pending split ✓ · catalyst ✓
- **warnings:**
  - above 50M float (111.3M, yahoo)

## Watch: liquid and on T212, but in no tier

### 5. BRAI: Braiin Limited

> **WATCH: NO VERIFIABLE CATALYST** (and no prior-day volume surge)

- **price** 1.79 · **gap** 20.9% vs prior close 1.48
- **premarket high** 1.84 full session · 1.84 in the 60 minutes to the cutoff
- **premarket** $2,251,560 traded · 5,688 trades
- **float** unknown (not checked)
- **catalyst** none, quality 0/5
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✗ · prior range ✗ · float – · no offering ✓ · no pending split ✓ · catalyst ✗
- **not tiered:** fails continuation, prior range, catalyst (no verifiable catalyst and no prior-day volume surge (0.3x))
- **warnings:**
  - EDGAR shares outstanding stale (as of 2026-06-30)

## Not shown (first failing rule)

- rule_t212: MEDS, NCRA, FOXX
- beyond the 5-name limit: KEEL, EOSE, TE, HIVE
- rule_pm_dollar_volume: TROX, GEMI, TAOX, RZAI, HURA, ENLV, ATPC, CNXU, HTT, LBGJ, MOBX, WKHS, AARD, SINT

_halts feed: NYSE first seen 2026-11-16T09:36:02.551673-05:00; add NYSE to halts.confirmed_markets_

Detail: `data/scans/2026-11-23.json`, `data/candidates.csv`.


## Earlier

- [2026-11-20_0934_shortlist.md](2026/11/2026-11-20_0934_shortlist.md): Shortlist 2026-11-20: 0 Tier A, 0 Tier B, 1 Watch
- [2026-11-19_0921_shortlist.md](2026/11/2026-11-19_0921_shortlist.md): Shortlist 2026-11-19: 0 Tier A, 1 Tier B, 0 Watch
- [2026-11-18_0939_shortlist.md](2026/11/2026-11-18_0939_shortlist.md): Shortlist 2026-11-18: 0 Tier A, 2 Tier B, 0 Watch
- [2026-11-17_0920_shortlist.md](2026/11/2026-11-17_0920_shortlist.md): Shortlist 2026-11-17: 1 Tier A, 1 Tier B, 0 Watch
- [2026-11-16_0936_shortlist.md](2026/11/2026-11-16_0936_shortlist.md): Shortlist 2026-11-16: 0 Tier A, 2 Tier B, 1 Watch
- [2026-11-16_0902_test.md](2026/11/2026-11-16_0902_test.md): TEST: notification check 2026-11-16 09:02 ET
- [2026-11-16_0241_test.md](2026/11/2026-11-16_0241_test.md): Test message 2026-11-16 02:41 ET
