# Milestone 0: verification results

Run 2026-11-15 (Sunday) against the 5 sessions 2026-11-09 to 2026-11-13. Scanner code has **not** been started. It waits on your review of test 6 (the gate).

Raw output for every run is in `docs/m0_raw/`.

## Summary

| # | Test | Result |
|---|---|---|
| 6 | **T212 overlap (gate)** | **80%** of liquid $1-$2 gappers are on T212 (12 of 15). The gate passes, but volume is thin: about **2.4 T212-tradable liquid gappers a day**, before any continuation, float or dilution filter |
| 1 | IEX for premarket gap % | **Fails the spec's assumption.** 0% of sub-$2 names had any IEX print before 08:00 ET. Only 2-3% had one by 09:15 |
| 2 | Delayed SIP bars | Works. Full premarket from 04:00 ET. Data less than 15 min old is refused (403), as documented |
| 3 | Alpaca news | Works on free keys. Rate limit header `200`/min, matching the documented limit. No 429s |
| 4 | EDGAR | Works, but the User-Agent must contain an email. `424B*` also catches debt deals. Share counts are missing for 2 of 12 gappers and stale for foreign filers |
| 5 | Yahoo float | Present for 11 of 12 gappers. Some values disagree with EDGAR by large amounts |
| 7 | Haiku classifier | 20 of 20 valid JSON, no retries. It credits roundup articles about **other** companies to the gapper |

---

## Test 6: T212 overlap (the gate)

Method (`m0/t6_t212_overlap.py`):
- **Universe:** Alpaca active, tradable, US-listed common stock (heuristic).
- **Gapper:** price $1.00-$2.00 at 09:15 ET (last SIP 1-min close) and at least +10% vs the prior SIP daily close.
- **"Liquid":** premarket SIP dollar volume of $100k or more (spec 4.1).
- **T212 list:** pulled from the T212 API once, 6,885 US stocks, saved to `data/t212_instruments.json` (git-ignored).

| | Rows | On T212 | % |
|---|---|---|---|
| All $1-$2 gappers of +10% or more | 38 | 33 | 86.8 |
| …with $100k or more premarket dollar volume | 15 | 12 | **80.0** |

| Date | Liquid gappers | On T212 |
|---|---|---|
| 11-09 | 2 | 0 |
| 11-10 | 5 | 5 |
| 11-11 | 3 | 2 |
| 11-12 | 1 | 1 |
| 11-13 | 4 | 4 |

Liquid gappers:

| Date | Symbol | 09:15 px | Gap % | PM $ vol | PM trades | On T212 |
|---|---|---|---|---|---|---|
| 11-09 | NCPL | 1.52 | 20.6 | 2.44M | 5,874 | no |
| 11-09 | YMAT | 1.23 | 17.1 | 17.2M | 74,630 | no |
| 11-10 | MNDO | 1.26 | 44.8 | 10.7M | 21,096 | yes |
| 11-10 | TTEC | 1.68 | 20.4 | 726k | 2,887 | yes |
| 11-10 | KLTR | 1.66 | 16.1 | 206k | 626 | yes |
| 11-10 | WFF | 1.25 | 15.7 | 8.98M | 34,190 | yes |
| 11-10 | AMIX | 1.87 | 10.0 | 11.3M | 43,565 | yes |
| 11-11 | YMAT | 1.43 | 43.0 | 24.2M | 90,488 | no |
| 11-11 | GEVO | 1.70 | 22.3 | 1.10M | 2,642 | yes |
| 11-11 | CANG | 1.32 | 15.6 | 243k | 530 | yes |
| 11-12 | CRMN | 1.71 | 47.3 | 111M | 343,620 | yes |
| 11-13 | MRLN | 1.26 | 30.5 | 15.9M | 49,848 | yes |
| 11-13 | SLSN | 1.10 | 20.9 | 630k | 2,750 | yes |
| 11-13 | BBCI | 1.37 | 19.1 | 135k | 456 | yes |
| 11-13 | STAK | 1.77 | 16.8 | 8.36M | 33,663 | yes |

**Bug found and fixed while testing:** T212's `ticker` field keeps a company's *old* symbol after a rename. For example, CRMN is stored as `SKBL_US_EQ` and MRLN as `BACQ_US_EQ`. The current symbol is in `shortName`. Matching on `ticker` gave 53% overlap; matching on `shortName` gives 80%. The real scanner must match on `shortName` (or ISIN). The remaining misses (YMAT, NCPL, and the illiquid ANPA, CABR) are not in T212's list under any name.

**What this means for the plan, for your review:**
- The overlap is not tiny, so by the spec the gate passes.
- But volume is small: **15 liquid gappers in 5 days, 12 of them tradable on T212**, and that's *before* the continuation, prior-close-in-top-25%, float and dilution filters. Realistically the shortlist will often hold 0-1 names, and section 11's target of **30 simulated trades in 2 weeks is unlikely**. Expect 4-8 weeks of logging unless the rules are loosened.
- Only 5 sessions were checked. A longer look-back (for example 20 sessions) would give a steadier rate and costs only a few minutes of API calls.
- Two notable names were caught only after their tickers changed (CRMN from KAZR on 11-12). Any symbol-keyed history (prior closes, the 3-session continuation check) has to handle renames.

## Test 1: IEX for premarket gap % (historical mode)

`t1_iex_snapshots.py --historical` for 2026-11-13 and 2026-11-10, over about 700 names with a prior close of $0.80-$2.40:

| Day | Names | Any IEX print by 04:30 | by 08:00 | by 09:15 |
|---|---|---|---|---|
| 11-13 | 709 | 0 (0%) | 0 (0%) | 14 (2.0%) |
| 11-10 | 707 | 0 (0%) | 0 (0%) | 22 (3.1%) |

And from test 2, for the actual gappers, IEX share volume as a percentage of SIP share volume from 04:00 to 09:30 ET was a **median of 0.0%** and at most 2.6%. CRMN traded 22.3M SIP shares premarket, of which 1,709 were on IEX.

**Conclusion: section 5's "use IEX for gap %" does not hold for sub-$2 names.** IEX has no prints before 08:00 and almost none by 09:15. An IEX snapshot at 09:15 will usually show the prior close or one tiny print.

**Proposed change:** compute gap % **and** volume from delayed SIP 1-min bars. At a 09:15 ET scan, delayed SIP covers up to about 09:00 ET, so the gap is "as of 09:00", with no look-ahead. Use the IEX snapshot only as an extra "last seen" field, never as a filter. If you want the gap closer to the open, move the email to about 09:20-09:25 ET (data as of 09:05-09:10).

Still to do: the **live** snapshot runs at about 04:00, 08:00 and 09:15 ET on a trading day (11:00, 15:00 and 16:15 Johannesburg time). Given the historical result, these will most likely confirm it, and they're optional.

## Test 2: delayed SIP bars

`t2_sip_bars.py --day 2026-11-13`, using 30 gapper symbols:

- 1-min SIP bars returned on free keys. 18 of 30 names had a bar before 05:00 ET, and the main names start at 04:00.
- Bars by hour (ET): 04: 269, 05: 212, 06: 194, 07: 298, 08: 276, 09: 194.
- `end=now`: **403** `subscription does not permit querying recent SIP data`. `end=now-16min`: 200. This matches the documented 15-minute delay.
- Rate limit header: `x-ratelimit-limit: 200`.

## Test 3: Alpaca news

- 200 OK on free keys, about 1 s per call. Fields: `headline, summary, content, symbols, source, created_at, url, …`.
- A burst of 40 calls: limit header `200`, matching the documented 200/min. Remaining went from 198 to 195 (the window refills continuously), with no 429s.
- Alpaca sends `X-Ratelimit-*`, not `X-RateLimit-*`. This only matters for case-sensitive code. Found and fixed in the M0 helpers.
- Coverage note: many sub-$2 gappers' only "news" is Benzinga roundup lists ("12 Industrials Stocks Moving…"). See test 7.

## Test 4: SEC EDGAR

Mechanics run on AAPL/SNDL/PLUG/GNS/SIRI, then on 12 real gappers (7-day filings look-back).

| Ticker | EDGAR shares out | As of | Filings, 7 d | Offering forms | 8-K items |
|---|---|---|---|---|---|
| CRMN | none | | 2 | | |
| YMAT | 13.95M | 2026-04-30 | 0 | | |
| MRLN | 101.1M | 2026-08-11 | 5 | 424B3 | 2.02 |
| AMIX | 2.05M | 2026-11-06 | 1 | | |
| MNDO | 20.37M | 2025-12-31 | 2 | | |
| WFF | 5.04M | 2025-12-31 | 0 | | |
| STAK | 19.21M | 2026-06-30 | 0 | | |
| NCPL | 7.85M | 2026-03-19 | 1 | | 3.01 |
| GEVO | 247.4M | 2026-11-06 | 3 | | 2.02 |
| TTEC | 49.38M | 2026-10-30 | 2 | | 2.02 |
| SLSN | 70.65M | 2026-11-12 | 8 | | 2.02 |
| CANG | none | | 0 | | |

Findings:
- **4a. The User-Agent must contain an email.** Without one: 403. With one: 200. `SEC_USER_AGENT` in `.env` is set.
- **4b. `424B*` is too broad.** AAPL had a `424B2` (a notes offering), and MRLN's `424B3` is usually a resale prospectus. **Proposed:** in M2, disqualify on `424B*` / S-1 / S-3 / F-1 / F-3 only when the text names common stock, warrants, pre-funded warrants, units or an ATM. Add 8-K item **3.02** (unregistered equity sale) as a disqualifier signal.
- **4c. Share counts are missing or stale.** CRMN (a recent listing) and CANG (an ADR) have no `dei` shares outstanding. Foreign filers (MNDO, WFF, SNDL, GNS) only update at year end, so their counts are 10+ months old. **Proposed:** add "EDGAR shares outstanding missing or older than 120 days" to the "float stale" warning.
- **4d. Proposed new warning:** 8-K item **3.01** (listing-standards deficiency, NCPL). It often comes before a reverse split, which section 4.2 disqualifies.

## Test 5: Yahoo `floatShares` vs EDGAR

Twelve gappers, one request per 1.5 s, no errors or throttling.

| Ticker | Yahoo float | Yahoo shares out | EDGAR shares out | Float % of EDGAR | Note |
|---|---|---|---|---|---|
| CRMN | 0.33M | 15.9M | none | | Float looks implausibly low |
| YMAT | 1.49M | 3.30M | 13.95M | 10.7 | Yahoo and EDGAR shares outstanding differ by 4x |
| MRLN | 46.4M | 102.4M | 101.1M | 45.9 | Within 15% of the 50M cap |
| AMIX | 1.93M | 2.05M | 2.05M | 94.6 | |
| MNDO | 15.4M | 19.5M | 20.4M | 75.5 | |
| WFF | 0.55M | 2.51M | 5.04M | 10.8 | Shares outstanding differ by 2x |
| STAK | 10.0M | 10.0M | 19.2M | 52.1 | Shares outstanding differ by 2x |
| NCPL | 4.39M | 8.02M | 7.85M | 55.9 | |
| GEVO | 228.3M | 247.4M | 247.4M | 92.3 | Over the 50M cap |
| TTEC | 20.4M | 49.4M | 49.4M | 41.4 | |
| SLSN | 18.3M | 70.6M | 70.6M | 25.9 | |
| CANG | none | 39.3M | none | | Float missing |

- Yahoo float present for **11 of 12**.
- When EDGAR is recent, Yahoo's shares outstanding matches it exactly. Where they differ by 2-4x (YMAT, WFF, STAK), the most likely cause is a reverse split or an issuance since the last EDGAR filing. That's the kind of name the spec most wants flagged.
- **Proposed:** add a "float uncertain" warning when Yahoo and EDGAR shares outstanding differ by more than 25%. Spec 4.1 already avoids a hard fail near the cap (MRLN).

## Test 7: Haiku classifier (`claude-haiku-5-5`)

Twenty headlines from the 48 h before each gapper's 09:15 ET, classified one at a time with structured JSON output and code-side validation.

- 20 of 20 valid on the first try, 0 retries, 0 "classifier unavailable". 16.5k input + 1.9k output tokens in total, a fraction of a cent.
- **Correct labels:** earnings for GEVO and MRLN (quality 4). CRMN's ticker change: other, quality 1. NCPL's Nasdaq extension: other, quality 1-2. Roundup lists with no company news: none, 0. YMAT's CEO converting debt to equity: `dilution_language = true`. AMIX patent: other, 2.
- **Wrong labels (a real defect):** roundup articles are tagged with every ticker they list, so the classifier credits **another company's** catalyst to the gapper:
  - YMAT: "merger, 3" from an article about Greenfire Resources being acquired
  - WFF: "earnings, 4" from Sanmina's results
  - YMAT: "earnings, 2" from Fossil's results

  Over a full day this would lift catalyst-quality scores for names with no news of their own.
- **Proposed for M3:**
  - Classify **per ticker**, not per headline. Pass the company name with all of that ticker's items, and tell the model that a catalyst counts only if it's about that company.
  - Drop items whose `symbols` list has more than 3 tickers before they reach the model.
  - Add a deterministic check: no headline mentions the company name means `catalyst_type` "none".

## Proposed spec changes (for your approval)

1. **Section 5 / 4.1:** use delayed SIP for gap % as well as volume; IEX for display only (test 1).
2. **Section 4.2:** offering disqualifier needs equity wording or 8-K item 3.02, not just a `424B*` form (4b).
3. **Section 4.3:** new warnings for 8-K 3.01 deficiency (4d), EDGAR shares outstanding missing or older than 120 days (4c), and Yahoo vs EDGAR shares outstanding differing by more than 25% (test 5).
4. **Section 6:** classifier works per ticker with the company name, and filters roundup articles (test 7).
5. **Section 11:** expect fewer than 30 simulated trades in 2 weeks at current rules (test 6). Consider a longer phase 1 or replaying past sessions to build sample size faster.
6. **T212 matching:** use `shortName` or ISIN, never the internal `ticker` (test 6).

## Housekeeping

- The T212 key is a **live-account** key: demo returns 401, live returns 200 with key + secret. `.env` now has `T212_BASE_URL=https://live.trading212.com`. The script only ever calls the read-only instruments endpoint, and only when `data/t212_instruments.json` is missing.
- Python 3.9 (system) with `anthropic` 0.125, `yfinance` 1.2.0. The urllib3/LibreSSL warning is harmless.

## How to re-run

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd m0
../.venv/bin/python t6_t212_overlap.py --days 5   # writes gappers.json, used by the rest
../.venv/bin/python t2_sip_bars.py --day 2026-11-13
../.venv/bin/python t3_news.py
../.venv/bin/python t1_iex_snapshots.py --historical 2026-11-13
../.venv/bin/python t4_edgar.py --days 7
../.venv/bin/python t5_yahoo_float.py
../.venv/bin/python t7_classifier.py --n 20
```
