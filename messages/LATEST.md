# Latest messages

Newest first. Every message is also kept as its own file under `messages/YYYY/MM/`.

## Newest: [2026-11-18_0939_shortlist.md](2026/11/2026-11-18_0939_shortlist.md)

### Shortlist 2026-11-18: 0 Tier A, 2 Tier B, 0 Watch

- kind: `shortlist` (Morning shortlist)
- time: 2026-11-18 09:39 New York (2026-11-18T09:39:55.511016-05:00)

> Levels use data up to about 08:59 ET. Re-check the live premarket high at the open.
>
> Rules output only: names, rule results and warnings.

**Late start:** the workflow began after the 09:30 open; the scan still used data up to the normal cutoff.

Candidates (price and gap passed): 6 · Tier A 0 · Tier B 2 · Watch 0 · shown 2 of at most 5

## Tier B: Tier A rules without continuation and prior range

### 1. HIHO: Highway Holdings Limited · score 51.07

- **price** 1.68 · **gap** 36.6% vs prior close 1.23
- **premarket high** 1.97 full session · 1.97 in the 60 minutes to the cutoff
- **premarket** $32,380,726 traded · 101,201 trades
- **float** 2.9M (yahoo)
- **catalyst** other, quality 3/5 (3/3 runs agree): Highway Holdings declared a US$0.43228 per share special cash dividend via its Special Committee.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✓ · prior range ✗ · float ✓ · no offering ✓ · no pending split ✓ · catalyst ✓
- **warnings:**
  - EDGAR shares outstanding stale (as of 2026-03-31)

### 2. GMM: Global Mofy AI Limited · score 35.49

- **price** 1.63 · **gap** 17.3% vs prior close 1.39
- **premarket high** 2.11 full session · 1.73 in the 60 minutes to the cutoff
- **premarket** $27,301,449 traded · 93,205 trades
- **float** 0.6M (yahoo)
- **catalyst** other, quality 2/5 (3/3 runs agree): Global Mofy AI announced an indirect investment in Anthropic via an investment fund made in September 2026.
- **rules** price ✓ · gap ✓ · T212 ✓ · $ vol ✓ · trades ✓ · continuation ✓ · prior range ✗ · float ✓ · no offering ✓ · no pending split ✓ · catalyst ✓
- **warnings:**
  - EDGAR shares outstanding stale (as of 2023-09-30)
  - Yahoo vs EDGAR shares outstanding differ 111% (54.6M vs 25.9M)

## Not shown (first failing rule)

- rule_pm_dollar_volume: FEAM, DETX, CNTN
- rule_t212: CAPS

_halts feed: NYSE first seen 2026-11-16T09:36:02.551673-05:00; add NYSE to halts.confirmed_markets_

Detail: `data/scans/2026-11-18.json`, `data/candidates.csv`.


## Earlier

- [2026-11-17_0920_shortlist.md](2026/11/2026-11-17_0920_shortlist.md): Shortlist 2026-11-17: 1 Tier A, 1 Tier B, 0 Watch
- [2026-11-16_0936_shortlist.md](2026/11/2026-11-16_0936_shortlist.md): Shortlist 2026-11-16: 0 Tier A, 2 Tier B, 1 Watch
- [2026-11-16_0902_test.md](2026/11/2026-11-16_0902_test.md): TEST: notification check 2026-11-16 09:02 ET
- [2026-11-16_0241_test.md](2026/11/2026-11-16_0241_test.md): Test message 2026-11-16 02:41 ET
