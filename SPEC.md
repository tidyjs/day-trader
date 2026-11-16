# Sub-$2 Gapper Shortlist Tool: Build Spec

Starting brief for Claude Code. Read the whole file before writing code.

## 1. Purpose

A scheduled tool that emails a ranked shortlist (maximum 5) of US stocks priced $1-$2 that are gapping up as continuation runners, with trigger, stop, share count and targets for each. A human places all trades manually on Trading 212 (T212). The tool never places orders.

After each US close it replays every shortlisted name through the same rules on minute bars and logs the simulated result, so we can measure whether the shortlist has a real edge before any money is risked.

**Honest framing:** the pipeline can be made reliable. The picks cannot be guaranteed. Whether they beat random is exactly what the log measures.

## 2. Non-goals

- No broker integration, no order placement, no live trading code.
- No LLM involvement in picking names, setting levels or sizing. The LLM only classifies catalysts, and that classification is one input to a deterministic score.
- No paid data in phase 1.

## 3. Trader parameters (config, not hard-coded)

All numbers below live in `config.yaml` and are assumptions to be tested, not known-good values.

| Parameter | Value |
|---|---|
| Account | $50, USD, T212, cash, no leverage, no options, fractional shares allowed |
| Style | Day trade only, no overnight, no after-hours |
| Price range | $1.00-$2.00 |
| Risk per trade | 5% of equity |
| Daily loss cap | 10% of equity, or 2 consecutive losses, whichever comes first |
| Max open positions | 1 |
| Max names on shortlist | 5 |
| Trader time zone | Africa/Johannesburg (no DST). All scheduling logic uses America/New_York. |

## 4. Setup rules

### 4.1 Universe filters (all must pass)

- US-listed common stock, last price $1.00-$2.00, present on the T212 tradable list (matched on T212 `shortName`, never the internal `ticker`, which keeps old symbols after renames).
- Premarket gap of at least +10% vs prior close. Price and gap come from **delayed SIP** 1-min bars, so at a 09:15 ET scan they are as of about 09:00 ET. IEX is display-only (M0 test 1: no IEX prints for sub-$2 names before 08:00 ET).
- Continuation: in at least one of the last 3 sessions the stock closed up 20% or more, or traded at 3x or more its average volume.
- Prior session closed in the top 25% of its range.
- Premarket dollar volume of at least $100k, measured on delayed SIP bars.
- Approximate float under 50M shares. Log as approximate. Never hard-fail on a margin under 15%.

### 4.2 Disqualifiers (any one removes the name)

- Offering, ATM program, shelf takedown or prospectus filing in the last 5 days, when the evidence is clear: an EDGAR 424B*, S-1, S-3, F-1 or F-3 (or amendment) whose text names common stock, warrants, pre-funded warrants, units or an ATM; an 8-K with offering language; or an 8-K item 3.02 (unregistered sale of equity). A filing type alone is not enough (M0: `424B2` also covers debt notes). Ambiguous cases become the "possible offering" warning in 4.3, never a silent pass. The match must be wording about the company's **own** issuance ("we are offering", a securities purchase / underwriting / ATM agreement, pricing or closing of its offering), not a generic mention of listed common stock (M3: MRLN was wrongly disqualified on "Our shares of Common Stock are listed on Nasdaq"). A prospectus supplement that only attaches a periodic report is judged by the registration it supplements.
- Reverse split announced or pending.
- Classifier flags promo or pump-style news, or there is no verifiable catalyst and no prior-day volume surge.

### 4.3 Warnings (name stays on the list with a visible tag)

- Halted at scan time (show halt time). Source: Nasdaq Trader halts feed, saved in each scan. Feed failure, a historical run, or a listing market whose feed coverage is not confirmed (NYSE, ARCA, BATS until seen in the feed) gives "halt status unknown", never a clean pass.
- Estimated spread over 3% (show the number).
- Float figure missing or stale, including EDGAR shares outstanding that is missing or older than 120 days (common for foreign filers).
- Yahoo and EDGAR shares outstanding differ by more than 25% (often a reverse split or new issuance since the last filing).
- 8-K item 3.01 (listing-standards deficiency) in the last 90 days. Often comes before a reverse split.
- Possible offering: an offering-type filing in the last 5 days that does not clearly meet the 4.2 disqualifier test.
- Resale registration, supply overhang: selling holders may sell registered shares and the company receives no proceeds. A warning, not a disqualifier.
- Classifier reports dilution language in recent news but no filing was found.
- T212 list older than 1 day (show its age).
- Merger target: "merger target: price likely pinned to deal terms" when the classifier's catalyst is a merger and the company is the one being acquired (`acquisition_target`). Warning only. **Pre-declared 2026-11-16**, before any forward scan; judge its effect only on scans from that date on.

### 4.4a Candidate log (every name, every rule)

Every name that passes the basic price and gap filters is logged, whether or not it reaches the email, with a pass/fail flag for each rule in 4.1-4.3 and the value it was tested on. Only names that pass every 4.1 rule and no 4.2 disqualifier go in the email. The log grows the sample much faster than the shortlist, and later shows which filters actually add value. With a sample this small, **do not tune filters off a few trades**: any threshold change waits for the phase 1 review and is judged on the full log.

### 4.4 Ranking

Fixed, documented scoring formula over: gap size, prior-day volume multiple, catalyst quality, float. Weights live in config. The LLM output is one numeric input. Ties are broken by higher premarket dollar volume.

### 4.5 Entry, stop, exit (manual on T212)

- No premarket buying. Entries from the open until 12:30 ET.
- **Trigger:** price breaks above the higher of the opening 5-minute high and the premarket high. Limit orders only. Skip if price is already more than 3% above the trigger.
- **Stop:** under the opening-range low or the most recent higher low, placed as a real stop order immediately after fill. Skip the trade if the stop is more than 12% below entry.
- **Size:** `shares = (equity * 0.05) / (entry - stop)`, capped so position value never exceeds equity.
- **Exit:** sell half at 1.5R and move the stop to breakeven. Trail the rest under higher 5-minute lows.
- **Time stop:** if price has not reached +0.5R within 30 minutes of entry, exit. (Assumption, tune later.)
- **Flat by 15:30 ET.**

## 5. Architecture

```
repo/
  config.yaml            thresholds, weights, times
  src/
    data/alpaca.py       assets, snapshots, bars (iex + sip), news
    data/edgar.py        ticker->CIK, shares outstanding, filings
    data/yahoo.py        floatShares (approximate, on-demand)
    data/t212.py         load tradable list from export/CSV
    scan.py              universe + filters + flags
    catalyst.py          Haiku classifier (JSON only)
    rank.py              score, levels, sizing
    email_out.py         morning shortlist, no-trade, failure alert
    replay.py            post-close simulation
    run.py               entrypoint, ET-time gating
  data/
    scans/YYYY-MM-DD.json     raw inputs and outputs of each scan
    candidates.csv            every candidate with per-rule pass/fail (4.4a)
    t212/YYYY-MM-DD.json      daily T212 instrument snapshot used by the scan
    trades_sim.csv            every simulated trade
    trades_actual.csv         trades the human reports
  tests/
  .github/workflows/scan.yml
```

### Data sources (free tier, verify each in Milestone 0)

- **Alpaca Market Data (free):** active tradable assets, snapshots on `feed=iex` (display only), delayed SIP bars on `feed=sip` (end time at least 15 minutes ago; newer returns 403), news endpoint. Rate limit 200 requests/min (confirmed in M0).
- **SEC EDGAR:** `company_tickers.json` for CIK mapping, company facts for shares outstanding, submissions for recent filings. Custom User-Agent header required and it **must contain an email address** (M0: 403 without one), max 10 requests/second.
- **T212:** instrument list from the read-only `/api/v0/equity/metadata/instruments` endpoint (key + secret, basic auth), refreshed once a day before the scan and saved by date. If the refresh fails, use the latest saved list and add the "T212 list is N days old" warning. Each scan records which list it used. `EntityPublicFloat` is a dollar value that can be 6-12 months stale. It is not a float figure. Use shares outstanding as a coarse ceiling only.
- **Yahoo `floatShares`:** on-demand for the morning gappers only, treated as approximate. Unofficial, so no tight loops.
- **Anthropic API:** `claude-haiku-5-5` for catalyst classification.

### Known data caveats

- IEX is a small share of total volume and may print little or nothing before about 8:00 ET. Do not build live volume filters on IEX. Use IEX for gap %, and delayed SIP for volume.
- A single tiny IEX print can fake a gap. Require minimum dollar volume and trade count, not just `v >= 1`.
- `tradable=true` on Alpaca does not mean tradable on T212.

## 6. Catalyst classifier contract

Input: the company name, plus all headlines and summaries for that ticker from the last 48 hours and recent filing titles, classified **per company, in one call**, not per headline. A catalyst counts only if it is about that company. Before the call, drop news items tagged with more than 3 symbols ("stocks moving premarket" roundups). After the call, a deterministic check: if no remaining item mentions the company name or ticker, `catalyst_type` is forced to "none". (M0 test 7: roundup articles gave gappers other companies' catalysts.)
Output: strict JSON, no prose.

```json
{
  "catalyst_type": "earnings|contract|fda|merger|offering|promo|other|none",
  "quality": 0,
  "promo_or_pump_flag": false,
  "dilution_language": false,
  "acquisition_target": false,
  "one_line_summary": ""
}
```

`quality` is 0-5. Validate the JSON, retry once, and on failure mark the name "classifier unavailable" (a warning, not a pass).

M3 must include a fixed test set of headlines where the named company differs from the gapper (for example a roundup about another company's merger tagged with the gapper's ticker). The expected label is "none" with quality 0.

## 7. Replay engine (the measurement)

For each shortlisted name, after the close:

1. Pull minute SIP bars for the day.
2. Simulate the trigger, stop, partial, trail, time stop and 15:30 ET flat exactly as in 4.5.
3. Apply 1% slippage on each side (config).
4. If a stop and a target are both hit inside one bar, assume the stop hit first.
5. Log R multiple, P&L, entry/exit times and which rule ended the trade.

Run three modes: (a) every shortlisted name independently, to build sample size fast; (b) the one-position, daily-cap sequence, to show what a human would actually have been able to take; (c) every logged candidate from 4.4a, tagged with its rule flags, so filters can be compared later. Mode (c) is analysis only, not the verdict on the strict rules.

**Historical replay caveat.** Replaying past sessions before the forward log exists is a rough sanity check only, and it is biased in our favour: the Alpaca asset list only contains stocks that exist today (many sub-$2 runners are later delisted), and float and the T212 list are today's values, not what they were then. The forward log is the verdict.

**No look-ahead:** the morning scan may only use data available at scan time. Save its raw inputs so any day is reproducible.

## 8. Email

- **Morning shortlist** at 09:15 ET. One block per name: ticker, price, gap %, prior-day move, approximate float, catalyst summary, tags (warnings), trigger, stop, share count, 1.5R target. The email states the data cutoff time (delayed SIP, about 09:00 ET) and says: "Levels use data up to about 09:00 ET. Re-check the live premarket high at the open before using the trigger."
- **No trade today:** explicit email when nothing passes.
- **Scanner failed:** separate alert. Silence must never be ambiguous.
- **Post-close recap:** what each name did and the simulated result.

**Delivery (changed 2026-11-16 at the user's request): files in the repo, not email.** Every message is a Markdown file under `messages/YYYY/MM/YYYY-MM-DD_HHMM_<kind>.md`, committed back by the workflow; `messages/LATEST.md` shows the newest in full and links the 30 before it. GitHub does not notify on commits to your own repo, so a failure also fails the workflow run, which GitHub does notify. "Email" in this section means one of these message files.

## 9. Scheduling

GitHub Actions on a private repo. Cron is UTC only, so schedule two entries (one for each side of US DST) and have `run.py` check New York time and exit silently if it is the wrong one. Commit data files back to the repo. Secrets live in GitHub secrets, never in the repo.

## 10. Milestones and acceptance criteria

**M0: Verification (no scanner code yet).** Write small scripts that test each of the following and record the results in `docs/m0_results.md`:
1. Alpaca IEX snapshots for sub-$2 names at 4:00, 8:00 and 9:15 ET: real prints or stale prior close?
2. Alpaca delayed SIP bars: free access, premarket coverage from 4:00 ET.
3. Alpaca news: works on free keys, rate limit.
4. EDGAR: CIK mapping, shares outstanding, recent filings, User-Agent accepted.
5. Yahoo `floatShares` for 10 gappers vs EDGAR shares outstanding.
6. **T212 overlap:** over a week of Alpaca-detected $1-$2 gappers, what fraction exist on T212?
7. Haiku classifier on ~20 real headlines, labels eyeballed.

**Gate:** if test 6 shows tiny overlap, stop and report to the user. Do not continue to M1.

**M0 status:** done 2026-11-15, gate passed (80% T212 overlap). Results in `docs/m0_results.md`; changes from it are folded into this spec.

**M1 Scanner.** Universe, prior close, gap %, T212 filter, and the candidate log for those rules. Acceptance: reproducible on a saved day, no look-ahead.
**M2 Filters and flags.** All of 4.1-4.3 with unit tests using fixture data. Yahoo (and SIP quotes) only for names that pass every cheaper rule; a pass/fail column per rule in `candidates.csv`. Status: built 2026-11-15 (`docs/m2.md`); halt warning waits on approval of a halt-data source.
**M3 Classifier.** Contract in section 6, with validation and retry. Status: built 2026-11-15 (`docs/m3.md`); test set 14/14 including 5 wrong-company cases.
**M4 Ranking and levels.** Deterministic, unit-tested, including sizing edge cases (stop too wide, position cap).
**M5 Email.** All four email types, tested with a dry-run mode.
**M6 Replay.** Both modes, unit-tested with synthetic bars including the stop-and-target-in-one-bar case.
**M7 Scheduling.** DST-safe gating, failure alert verified by forcing an error. Status: `src/run.py` and `.github/workflows/scan.yml` built 2026-11-16 (`docs/m7.md`); gating tested on both sides of DST; forced-error alert verified with the `record` sender. Email delivery waits on M5 (provider choice); the workflow is not pushed until the repo is confirmed private.

## 11. Phase 1 review (after at least 30 simulated trades; expect 4-8 weeks)

M0 found about 2.4 T212-tradable liquid gappers a day before the continuation, float and dilution filters, so the strict shortlist will often hold 0-1 names. Plan for 4-8 weeks of forward logging.

Report: trade count, win rate, average win vs. average loss in R, expectancy after slippage, max drawdown, share of total profit from the top two trades, T212 overlap rate, warning-flagged vs. clean performance, and per-rule results from the candidate log (4.4a). If 30 trades are not reached, extend rather than conclude.

Go live with the $50 only if expectancy is positive and does not hinge on one or two outliers.

## 12. Working agreements for Claude Code

- Do not skip M0 or the gate.
- Keep the LLM out of selection, levels and sizing.
- Never add paid services or new data vendors without asking.
- Prefer small, tested modules. Every threshold comes from `config.yaml`.
- Flag any place where a documented API limit differs from what the test call returns.
- If a rule here conflicts with reality (for example the free data cannot support it), say so and propose a change. Do not silently work around it.

## 13. Open items for the user

- Private GitHub repo URL.
- Alpaca data API keys, Anthropic API key.
- Email address and provider choice (Gmail app password or Resend).
- T212 tradable ticker list (export or read-only API key).
