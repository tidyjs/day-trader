# Latest messages

Newest first. Every message is also kept as its own file under `messages/YYYY/MM/`.

## Newest: [2026-11-24_0930_shortlist.md](2026/11/2026-11-24_0930_shortlist.md)

### Shortlist 2026-11-24: 0 Tier A, 0 Tier B, 1 Watch

- kind: `shortlist` (Morning shortlist)
- time: 2026-11-24 09:30 New York (2026-11-24T09:30:23.307392-05:00)

> Levels use data up to about 08:59 ET. Re-check the live premarket high at the open.
>
> Rules output only: names, rule results and warnings.

**Late start:** the workflow began after the 09:30 open; the scan still used data up to the normal cutoff.

Candidates (price and gap passed): 6 · Tier A 0 · Tier B 0 · Watch 1 · shown 1 of at most 5

## Watch: liquid and on T212, but in no tier

### 1. MSS: Maison Solutions Inc.

> **WATCH: NO VERIFIABLE CATALYST** (and no prior-day volume surge)

- **price** 1.38 · **gap** 15.0% vs prior close 1.2
- **premarket high** 1.56 full session · 1.4 in the 60 minutes to the cutoff
- **premarket** $2,773,161 traded · 11,468 trades
- **float** unknown (not checked)
- **catalyst** none, quality 0/5 (3/3 runs agree): No company-specific news in last 48 hours; only an 8-K filing titled current report on 2026-11-23.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✓ · prior range ✗ · float – · no offering ✓ · no pending split ✓ · catalyst ✗
- **not tiered:** fails prior range, catalyst (no verifiable catalyst and no prior-day volume surge (2.1x))
- **warnings:**
  - 8-K 2026-11-23 item 3.01 (listing deficiency)
  - 8-K 2026-09-29 item 3.01 (listing deficiency)
  - EDGAR shares outstanding stale (as of 2024-08-06)

## Not shown (first failing rule)

- excluded from Watch: offering disqualifier: YFOR, APUS
- rule_t212: HTLM, FOXX
- rule_pm_dollar_volume: HTCR

_halts feed: NYSE first seen 2026-11-16T09:36:02.551673-05:00; add NYSE to halts.confirmed_markets_

Detail: `data/scans/2026-11-24.json`, `data/candidates.csv`.


## Earlier

- [2026-11-23_0941_shortlist.md](2026/11/2026-11-23_0941_shortlist.md): Shortlist 2026-11-23: 0 Tier A, 4 Tier B, 1 Watch
- [2026-11-20_0934_shortlist.md](2026/11/2026-11-20_0934_shortlist.md): Shortlist 2026-11-20: 0 Tier A, 0 Tier B, 1 Watch
- [2026-11-19_0921_shortlist.md](2026/11/2026-11-19_0921_shortlist.md): Shortlist 2026-11-19: 0 Tier A, 1 Tier B, 0 Watch
- [2026-11-18_0939_shortlist.md](2026/11/2026-11-18_0939_shortlist.md): Shortlist 2026-11-18: 0 Tier A, 2 Tier B, 0 Watch
- [2026-11-17_0920_shortlist.md](2026/11/2026-11-17_0920_shortlist.md): Shortlist 2026-11-17: 1 Tier A, 1 Tier B, 0 Watch
- [2026-11-16_0936_shortlist.md](2026/11/2026-11-16_0936_shortlist.md): Shortlist 2026-11-16: 0 Tier A, 2 Tier B, 1 Watch
- [2026-11-16_0902_test.md](2026/11/2026-11-16_0902_test.md): TEST: notification check 2026-11-16 09:02 ET
- [2026-11-16_0241_test.md](2026/11/2026-11-16_0241_test.md): Test message 2026-11-16 02:41 ET
