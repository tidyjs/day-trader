# Classifier review: real inputs and outputs

Model `claude-haiku-5-5`, effort `low`. Generated from `data/scans/*.json` by `python -m src.review_catalyst`.
Inputs are exactly what the model saw (roundups with more than 3 tagged symbols removed first).


## 2026-11-09 (news up to 09:15 ET)

### BMR — Beamr Imaging Ltd. Ordinary Share

- status: `no_news`; attempts: 0; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.68
- **input, news used (0):**
  - (none)
- input, roundups dropped (1): "11 Information Technology Stocks Moving In Monday's Pre-Market Session" [11 tags]
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "", "promo_or_pump_flag": false, "quality": 0}`

### CLRB — Cellectar Biosciences, Inc. Common Stock

- status: `no_news`; attempts: 0; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.44
- **input, news used (0):**
  - (none)
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "", "promo_or_pump_flag": false, "quality": 0}`

### EZGO — EZGO Technologies Ltd. Ordinary Shares

- status: `ok`; attempts: 1; forced none by name check: True
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.2
- **input, news used (0):**
  - (none)
- input, filings (5 days): 6-K 2026-11-05 REPORT OF FOREIGN PRIVATE ISSUER
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "No news items for EZGO in the last 48 hours; only a generic 6-K foreign issuer report filed.", "promo_or_pump_flag": false, "quality": 0}`
- model's own output before the name check: `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "No news items for EZGO in the last 48 hours; only a generic 6-K foreign issuer report filed.", "promo_or_pump_flag": false, "quality": 0}`

### NCPL — Netcapital Inc. Common Stock

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 0.03
- **input, news used (2):**
  - [2026-11-09T14:03] [fiscal.ai] [tagged: NCPL] **Netcapital Inc. Receives Nasdaq Extension to Regain Compliance** — Netcapital Inc. announced it received a letter from Nasdaq granting an exception to regain compliance with Listing Rule 5250(c)(1) regarding periodic filing requirements.
  - [2026-11-09T12:30] [benzinga] [tagged: NCPL] **Netcapital Receives Nasdaq Extension Through Feb. 9, 2027, To Regain Compliance**
- input, filings (5 days): 8-K 2026-11-09 8-K 3.01,9.01
- **output:** `{"acquisition_target": false, "catalyst_type": "other", "dilution_language": false, "one_line_summary": "Netcapital received Nasdaq extension through Feb. 9, 2027 to regain compliance with periodic filing requirements.", "promo_or_pump_flag": false, "quality": 1}`

### WLDS — Wearable Devices Ltd. Ordinary Share

- status: `ok`; attempts: 1; forced none by name check: True
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.09
- **input, news used (0):**
  - (none)
- input, filings (5 days): 4 2026-11-09; 4 2026-11-09; 4 2026-11-09; 4 2026-11-09; 4 2026-11-09; 4 2026-11-09
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "No news items in the last 48 hours; only Form 4 insider filings listed for Wearable Devices.", "promo_or_pump_flag": false, "quality": 0}`
- model's own output before the name check: `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "No news items in the last 48 hours; only Form 4 insider filings listed for Wearable Devices.", "promo_or_pump_flag": false, "quality": 0}`

### WORX — SCWorx Corp. Common Stock

- status: `ok`; attempts: 1; forced none by name check: True
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.01
- **input, news used (0):**
  - (none)
- input, filings (5 days): SCHEDULE 13G 2026-11-04
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "No company-specific news in the last 48 hours; only a Schedule 13G filing appears.", "promo_or_pump_flag": false, "quality": 0}`
- model's own output before the name check: `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "No company-specific news in the last 48 hours; only a Schedule 13G filing appears.", "promo_or_pump_flag": false, "quality": 0}`

### YMAT — J-Star Holding Co., Ltd. Class A Ordinary Shares

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 0.01
- **input, news used (1):**
  - [2026-11-09T12:21] [benzinga] [tagged: YMAT] **J-Star Holding To Host Japanese Carbon Fiber And Advanced Composite Manufacturer For A Comprehensive Site Review**
- input, roundups dropped (2): "12 Consumer Discretionary Stocks Moving In Monday's Pre-Market Session" [12 tags]; "Why Greenfire Resources Shares Are Trading Higher By Over 25%; Here Are 20 Stocks Moving Premarket" [20 tags]
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "other", "dilution_language": false, "one_line_summary": "J-Star to host a Japanese carbon fiber manufacturer for a site review; no financial terms disclosed.", "promo_or_pump_flag": false, "quality": 1}`


## 2026-11-10 (news up to 09:15 ET)

### AMIX — Autonomix Medical, Inc. Common Stock

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 6.2
- **input, news used (1):**
  - [2026-11-09T20:59] [benzinga] [tagged: AMIX] **Autonomix Medical Will Be Issued U.S. Patent Number 12,793,841 Tomorrow Titled "MEDICAL DEVICES WITH CIRCUITRY FOR CAPTURING AND PROCESSING PHYSIOLOGICAL SIGNALS"**
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "other", "dilution_language": false, "one_line_summary": "Autonomix Medical to be issued U.S. Patent 12,793,841 covering physiological signal circuitry for medical devices.", "promo_or_pump_flag": false, "quality": 2}`

### HTOO — Fusion Fuel Green PLC Class A Ordinary Shares

- status: `no_news`; attempts: 0; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 1.09
- **input, news used (0):**
  - (none)
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "", "promo_or_pump_flag": false, "quality": 0}`

### KLTR — Kaltura, Inc. Common Stock

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 1.91
- **input, news used (5):**
  - [2026-11-10T14:03] [fiscal.ai] [tagged: KLTR] **Kaltura Announces Financial Results for Third Quarter 2026** — Kaltura, Inc. reported its third-quarter 2026 financial results, showing revenue growth and an increase in its full-year financial outlook.
  - [2026-11-09T22:41] [benzinga] [tagged: KLTR] **Kaltura Q3 2026 Earnings Call Transcript** — Kaltura (NASDAQ:KLTR) reported third-quarter financial results on Monday. The transcript from the company’s third-quarter earnings call has been provided below.This transcript is brought to you by Benzinga APIs. For
  - [2026-11-09T21:07] [benzinga] [tagged: KLTR] **Kaltura Raises FY2026 Sales Guidance from $183.000M-$185.000M to $185.000M-$185.700M vs $184.000M Est**
  - [2026-11-09T21:07] [benzinga] [tagged: KLTR] **Kaltura Sees Q4 Sales $46.200M-$46.900M vs $46.500M Est**
  - [2026-11-09T21:07] [benzinga] [tagged: KLTR] **Kaltura Q3 Adj. EPS $0.02 Beats $(0.01) Estimate, Sales $47.265M Beat $46.100M Estimate**
- input, roundups dropped (1): "12 Information Technology Stocks Moving In Tuesday's Pre-Market Session" [12 tags]
- input, filings (5 days): 10-Q 2026-11-09 10-Q; 8-K 2026-11-09 8-K 2.02,9.01
- **output:** `{"acquisition_target": false, "catalyst_type": "earnings", "dilution_language": false, "one_line_summary": "Kaltura reported Q3 2026 sales of $47.3M beating estimates, adj. EPS $0.02, and raised FY2026 guidance.", "promo_or_pump_flag": false, "quality": 5}`

### MNDO — MIND C.T.I. Ltd. Ordinary Shares

- status: `no_news`; attempts: 0; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 1.83
- **input, news used (0):**
  - (none)
- input, roundups dropped (1): "12 Information Technology Stocks Moving In Tuesday's Pre-Market Session" [12 tags]
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "", "promo_or_pump_flag": false, "quality": 0}`

### ONEN — ONE Nuclear Energy Inc. Common Stock

- status: `no_news`; attempts: 0; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.24
- **input, news used (0):**
  - (none)
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "", "promo_or_pump_flag": false, "quality": 0}`

### TTEC — TTEC Holdings, Inc. Common Stock

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 0.79
- **input, news used (3):**
  - [2026-11-10T14:03] [fiscal.ai] [tagged: TTEC] **TTEC Holdings, Inc. Reports Third Quarter 2026 Financial Results** — TTEC Holdings, Inc. announced its financial results for the third quarter of 2026, detailing performance metrics for its TTEC Digital and TTEC Engage business segments.
  - [2026-11-09T23:50] [benzinga] [tagged: TTEC] **TTEC Holdings Affirms FY2026 Adj EPS Guidance of $0.79-$0.99 vs $0.85 Est; Affirms FY2026 Sales Guidance of $1.940B-$1.990B vs $1.956B Est**
  - [2026-11-09T22:31] [benzinga] [tagged: TTEC] **TTEC Holdings Q3 EPS $(0.10), Sales $492.245M Beat $480.204M Estimate**
- input, roundups dropped (1): "12 Industrials Stocks Moving In Tuesday's Pre-Market Session" [12 tags]
- input, filings (5 days): 8-K 2026-11-10 FORM 8-K 2.02,9.01; 10-Q 2026-11-09 10-Q
- **output:** `{"acquisition_target": false, "catalyst_type": "earnings", "dilution_language": false, "one_line_summary": "TTEC reported Q3 2026 sales of $492.2M beating estimates and affirmed FY2026 guidance.", "promo_or_pump_flag": false, "quality": 4}`

### WFF — WF Holding Limited Ordinary Shares

- status: `no_news`; attempts: 0; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.06
- **input, news used (0):**
  - (none)
- input, roundups dropped (3): "12 Industrials Stocks Moving In Tuesday's Pre-Market Session" [12 tags]; "Why Sanmina Shares Are Trading Higher By Around 19%; Here Are 20 Stocks Moving Premarket" [20 tags]; "12 Industrials Stocks Moving In Monday's After-Market Session" [12 tags]
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "", "promo_or_pump_flag": false, "quality": 0}`

### YXT — YXT.COM GROUP HOLDING LIMITED American Depository Shares

- status: `no_news`; attempts: 0; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.41
- **input, news used (0):**
  - (none)
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "", "promo_or_pump_flag": false, "quality": 0}`

### ZNTL — Zentalis Pharmaceuticals, Inc. Common Stock

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 0.96
- **input, news used (3):**
  - [2026-11-10T14:03] [fiscal.ai] [tagged: ZNTL] **Wedbush Upgrades Zentalis Pharmaceuticals to Outperform** — Wedbush upgraded Zentalis Pharmaceuticals from Neutral to Outperform and increased its price target for the company's stock to $6 from $5.
  - [2026-11-10T14:03] [fiscal.ai] [tagged: ZNTL] **Zentalis Pharmaceuticals Reports Third Quarter 2026 Financial Results** — Zentalis Pharmaceuticals announced its financial results for the third quarter ended September 30, 2026, reporting a cash position of $228.9 million.
  - [2026-11-09T21:40] [benzinga] [tagged: ZNTL] **Zentalis Pharma Q3 EPS $(0.34) Beats $(0.53) Estimate**
- input, filings (5 days): 10-Q 2026-11-09 10-Q; 8-K 2026-11-09 8-K 2.02,7.01
- **output:** `{"acquisition_target": false, "catalyst_type": "earnings", "dilution_language": false, "one_line_summary": "Zentalis reported Q3 2026 results with EPS $(0.34) beating estimates and $228.9M cash; Wedbush upgraded to Outperform.", "promo_or_pump_flag": false, "quality": 4}`


## 2026-11-11 (news up to 09:15 ET)

### BDAI — Biddance AI Systems, Inc. Class A Ordinary Share

- status: `no_news`; attempts: 0; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.05
- **input, news used (0):**
  - (none)
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "", "promo_or_pump_flag": false, "quality": 0}`

### BRAI — Braiin Limited Common Stock

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.07
- **input, news used (1):**
  - [2026-11-10T22:01] [fiscal.ai] [tagged: BRAI] **Braiin Ltd. Named Presenting Partner of Defence Robotics & Counter-UAS Congress** — Braiin Ltd. has been announced as the presenting partner for the Defence Robotics & Counter-UAS Congress, held during the Global Drone 2026 event in Queensland, Australia.
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "promo", "dilution_language": false, "one_line_summary": "Braiin named presenting partner of a defence robotics and counter-UAS congress in Queensland; no financial terms disclosed.", "promo_or_pump_flag": true, "quality": 1}`

### CABR — Caring Brands, Inc. Common Stock

- status: `no_news`; attempts: 0; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 3.01
- **input, news used (0):**
  - (none)
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "", "promo_or_pump_flag": false, "quality": 0}`

### CANG — Cango Inc.

- status: `no_news`; attempts: 0; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.15
- **input, news used (0):**
  - (none)
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "", "promo_or_pump_flag": false, "quality": 0}`

### DLPN — Dolphin Entertainment, Inc. Common Stock

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 0.43
- **input, news used (5):**
  - [2026-11-11T14:04] [fiscal.ai] [tagged: DLPN] **Dolphin Entertainment Reports Record Revenue in Third Quarter 2026** — Dolphin Entertainment announced record third-quarter 2026 revenue of $16.0 million, reflecting an 8.3% year-over-year increase, alongside a return to profitability.
  - [2026-11-10T22:38] [benzinga] [tagged: DLPN] **UPDATE: Dolphin Entertainment Q3 Adj. EPS $0.08 Beats $(0.04) Estimate, Sales $16.021M Beat $15.200M Estimate**
  - [2026-11-10T22:04] [benzinga] [tagged: DLPN] **Dolphin Entertainment Q3 2026 Earnings Call Transcript** — Dolphin Entertainment (NASDAQ:DLPN) reported third-quarter financial results on Tuesday. The transcript from the company’s third-quarter earnings call has been provided below.This transcript is brought to you by
  - [2026-11-10T21:26] [benzinga] [tagged: DLPN] **Dolphin Entertainment Q3 Adj. EPS $0.08 Beats $(0.04) Estimate, Sales $16.021M Beat $15.200M Estimate**
  - [2026-11-10T14:04] [fiscal.ai] [tagged: DLPN] **Dolphin Entertainment Subsidiary 42West Leads Communications for Top Global Box Office Films** — Dolphin Entertainment announced that its subsidiary, 42West, served as the strategic North American communications lead for the top two theatrical releases at the global box office.
- input, filings (5 days): 10-Q 2026-11-10 QUARTERLY REPORT; 8-K 2026-11-10 FORM 8-K 2.02,9.01; 4 2026-11-09
- **output:** `{"acquisition_target": false, "catalyst_type": "earnings", "dilution_language": false, "one_line_summary": "Dolphin Entertainment reported record Q3 2026 revenue of $16.0M, up 8.3%, with adjusted EPS beating estimates.", "promo_or_pump_flag": false, "quality": 4}`

### DPU — Nexpu Ltd. Class A Ordinary Shares

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 0.21
- **input, news used (1):**
  - [2026-11-10T01:01] [fiscal.ai] [tagged: DPU] **Nexpu Subsidiary Plans Asia-Pacific Music Creation Challenge** — Nexpu Ltd. announced that its subsidiary, Top Kingwin Technology Inc., will host an Asia-Pacific-themed music creation challenge on its DPU Platform from November 8 to November 18, 2026.
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "other", "dilution_language": false, "one_line_summary": "Subsidiary Top Kingwin Technology to host Asia-Pacific music creation challenge on DPU Platform, November 8-18, 2026.", "promo_or_pump_flag": false, "quality": 1}`

### GEVO — Gevo, Inc. Common Stock

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 2.42
- **input, news used (4):**
  - [2026-11-11T11:50] [benzinga] [tagged: GEVO] **Why Is Gevo Stock Gaining Wednesday?** — Gevo stock surges after Q3 revenue jumps 94% to $82.95M and EPS beats estimates at $0.12. Read the full Q3 earnings breakdown.
  - [2026-11-10T22:32] [fiscal.ai] [tagged: GEVO] **Gevo, Inc. Reports Record Financial Results for Third Quarter 2026** — Gevo, Inc. announced record financial performance for the third quarter ended September 30, 2026, including $83 million in revenue and $23 million in net income.
  - [2026-11-10T22:13] [benzinga] [tagged: GEVO] **Gevo Q3 2026 Earnings Call Transcript** — Gevo (NASDAQ:GEVO) reported third-quarter financial results on Tuesday. The transcript from the company’s third-quarter earnings call has been provided below.This transcript is brought to you by Benzinga APIs. For
  - [2026-11-10T21:08] [benzinga] [tagged: GEVO] **Gevo Q3 Adj. EPS $0.12 Beats $0.03 Estimate, Sales $82.953M Beat $54.413M Estimate**
- input, roundups dropped (1): "12 Energy Stocks Moving In Tuesday's After-Market Session" [12 tags]
- input, filings (5 days): 10-Q 2026-11-10 10-Q; 8-K 2026-11-10 8-K 2.02,9.01; SCHEDULE 13G 2026-11-10
- **output:** `{"acquisition_target": false, "catalyst_type": "earnings", "dilution_language": false, "one_line_summary": "Gevo reported record Q3 2026 results: revenue up 94% to $83M, net income $23M, EPS $0.12 beat.", "promo_or_pump_flag": false, "quality": 4}`

### SCLX — Scilex Holding Company Common Stock

- status: `no_news`; attempts: 0; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.82
- **input, news used (0):**
  - (none)
- input, roundups dropped (1): "12 Health Care Stocks Moving In Wednesday's Pre-Market Session" [12 tags]
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "", "promo_or_pump_flag": false, "quality": 0}`

### SNOA — Sonoma Pharmaceuticals, Inc. Common Stock

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 2.35
- **input, news used (2):**
  - [2026-11-11T14:04] [fiscal.ai] [tagged: SNOA] **Sonoma Pharmaceuticals Reports Second Fiscal Quarter 2027 Financial Results** — Sonoma Pharmaceuticals announced its financial results for the second fiscal quarter ended September 30, 2026, achieving positive net income before income taxes for the first time in its history.
  - [2026-11-10T21:27] [benzinga] [tagged: SNOA] **Sonoma Pharmaceuticals Q2 EPS $(0.01) Up From $(0.32) YoY, Sales $7.174M Up From $5.604M YoY**
- input, roundups dropped (1): "12 Health Care Stocks Moving In Wednesday's Pre-Market Session" [12 tags]
- input, filings (5 days): 10-Q 2026-11-10 FORM 10-Q FOR SEP 2026
- **output:** `{"acquisition_target": false, "catalyst_type": "earnings", "dilution_language": false, "one_line_summary": "Sonoma reported Q2 FY2027 results: first-ever pre-tax net income, EPS $(0.01), sales $7.174M versus $5.604M.", "promo_or_pump_flag": false, "quality": 4}`

### YMAT — J-Star Holding Co., Ltd. Class A Ordinary Shares

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 0.06
- **input, news used (2):**
  - [2026-11-11T13:33] [benzinga] [tagged: YMAT] **J-Star Issues Update On U.S. Carbon Fiber Supply Chain Efforts; Chairman And CEO Converts $8.2M Debt To Equity**
  - [2026-11-11T01:02] [fiscal.ai] [tagged: YMAT] **J-Star Holding Announces U.S. Operational Progress and Upcoming Delegation Visit** — J-Star Holding Co., Ltd. is advancing its U.S. manufacturing initiative by hosting a delegation from a Japan-based global Tier 1 carbon fiber manufacturer for a site review of its planned Texas facility.
- input, roundups dropped (2): "10 Consumer Discretionary Stocks Moving In Wednesday's Pre-Market Session" [10 tags]; "Why Fossil Group Shares Are Trading Higher By Over 26%; Here Are 20 Stocks Moving Premarket" [20 tags]
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "other", "dilution_language": true, "one_line_summary": "J-Star updates U.S. carbon fiber supply chain efforts; chairman converts $8.2M debt to equity, plus delegation site visit.", "promo_or_pump_flag": false, "quality": 2}`


## 2026-11-12 (news up to 09:15 ET)

### CRMN — Skyline Builders Group Holding Limited Class A Ordinary Shares

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 0.85
- **input, news used (1):**
  - [2026-11-12T12:51] [benzinga] [tagged: CRMN, KAZR] **Skyline Builders Group To Change Its NASDAQ Ticker Symbol From 'KAZR' To 'CRMN', Effective November 12**
- input, filings (5 days): 6-K 2026-11-12 REPORT OF FOREIGN PRIVATE ISSUER
- **output:** `{"acquisition_target": false, "catalyst_type": "other", "dilution_language": false, "one_line_summary": "Skyline Builders changes NASDAQ ticker from KAZR to CRMN effective November 12; no operational catalyst.", "promo_or_pump_flag": false, "quality": 1}`

### GITS — Global Interactive Technologies, Inc. Common Stock

- status: `no_news`; attempts: 0; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.56
- **input, news used (0):**
  - (none)
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "", "promo_or_pump_flag": false, "quality": 0}`

### ICMB — Investcorp Credit Management BDC, Inc. Common Stock

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 53.8
- **input, news used (4):**
  - [2026-11-12T06:32] [benzinga] [tagged: BCIC, ICMB] **Investcorp Credit Management (ICMB) Stock Jumps Over 53% After Hours on BCIC Merger Deal** — Investcorp Credit Management shares surge 53.54% after hours as merger agreement with BCIC promises shareholders a substantial premium.
  - [2026-11-11T23:25] [benzinga] [tagged: ICMB] **Trading Halt: Halt status updated at 6:25:00 PM ET: Quotation Resumption: News and Resumption Times**
  - [2026-11-11T23:03] [benzinga] [tagged: BCIC, ICMB] **Investcorp Credit Management BDC  To Merge Into BCP Investment Subject To Approval By ICMB Stockholders**
  - [2026-11-11T22:55] [benzinga] [tagged: ICMB] **Trading Halt: Halted at 5:55:00 p.m. ET - Trading Halt: Halt News Pending**
- input, filings (5 days): 425 2026-11-12 425; 8-K 2026-11-12 8-K 1.01,7.01,9.01; 10-Q 2026-11-12 10-Q
- **output:** `{"acquisition_target": true, "catalyst_type": "merger", "dilution_language": false, "one_line_summary": "ICMB agreed to merge into BCP Investment, subject to ICMB stockholder approval; shares surged after hours.", "promo_or_pump_flag": false, "quality": 5}`

### MSC — Studio City International Holdings Limited American depositary shares, each representing four Class A ordinary shares

- status: `ok`; attempts: 1; forced none by name check: True
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.07
- **input, news used (1):**
  - [2026-11-11T14:04] [fiscal.ai] [tagged: MSC] **PFH Energy Solutions (BVI) Limited Files Early Warning Report Regarding Millennium Silver Corp.** — PFH Energy Solutions (BVI) Limited has filed an early warning report concerning its equity holdings in Millennium Silver Corp.
- input, filings (5 days): 4 2026-11-09 4; 4 2026-11-09 4
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "No news about Studio City International; the only item concerns Millennium Silver Corp, a different company.", "promo_or_pump_flag": false, "quality": 0}`
- model's own output before the name check: `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "No news about Studio City International; the only item concerns Millennium Silver Corp, a different company.", "promo_or_pump_flag": false, "quality": 0}`

### YXT — YXT.COM GROUP HOLDING LIMITED American Depository Shares

- status: `no_news`; attempts: 0; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.09
- **input, news used (0):**
  - (none)
- input, roundups dropped (1): "12 Information Technology Stocks Moving In Thursday's Pre-Market Session" [12 tags]
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "", "promo_or_pump_flag": false, "quality": 0}`


## 2026-11-13 (news up to 09:15 ET)

### BBCI — Bradbury Capital Inc. Ordinary Shares

- status: `ok`; attempts: 1; forced none by name check: True
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.19
- **input, news used (0):**
  - (none)
- input, filings (5 days): 3 2026-11-09 3; 4 2026-11-09 4; 6-K 2026-11-09 6-K
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "No company news in last 48 hours; only Form 3, Form 4 and 6-K filing titles listed.", "promo_or_pump_flag": false, "quality": 0}`
- model's own output before the name check: `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "No company news in last 48 hours; only Form 3, Form 4 and 6-K filing titles listed.", "promo_or_pump_flag": false, "quality": 0}`

### BIRD — Smartbird, Inc. Class A Common Stock

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 1.32
- **input, news used (6):**
  - [2026-11-13T14:06] [fiscal.ai] [tagged: BIRD] **Smartbird CEO Nadia Carlsten Issues Shareholder Letter Outlining Strategic Progress** — Smartbird CEO Nadia Carlsten released a letter to shareholders on November 13, 2026, detailing the company's recent progress in establishing technology partnerships and securing data center capacity.
  - [2026-11-13T13:01] [benzinga] [tagged: BIRD] **Smartbird CEO Says Several Prospective Customer Discussions Have Advanced To Detailed Technical And Commercial Planning**
  - [2026-11-13T11:57] [benzinga] [tagged: BIRD] **Smartbird Q3 EPS $(0.31) Beats $(1.32) Estimate**
  - [2026-11-12T14:04] [fiscal.ai] [tagged: BIRD] **Smartbird Secures Data Center Capacity for AI Infrastructure** — Smartbird, Inc. has entered into a multi-year colocation agreement with Expedient to secure over 3.7 megawatts of data center capacity.
  - [2026-11-12T13:03] [benzinga] [tagged: BIRD] **Smartbird Announces Multi-Year Colocation Agreement With Expedient For More Than 3.7 MW Of U.S. Data Center Capacity; Terms Not Disclosed**
  - [2026-11-12T09:02] [fiscal.ai] [tagged: BIRD] **Blackbird plc Receives Major Shareholder Notification** — A shareholder has increased their voting rights in Blackbird plc to 4.2997%.
- input, roundups dropped (1): "12 Consumer Discretionary Stocks Moving In Friday's Pre-Market Session" [12 tags]
- input, filings (5 days): 8-K 2026-11-13 FORM 8-K 8.01,9.01; 10-Q 2026-11-13 FORM 10-Q
- **output:** `{"acquisition_target": false, "catalyst_type": "contract", "dilution_language": false, "one_line_summary": "Smartbird signed multi-year colocation deal with Expedient for over 3.7 MW data center capacity; terms undisclosed.", "promo_or_pump_flag": false, "quality": 3}`

### BOF — BranchOut Food Inc. Common Stock

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 0.19
- **input, news used (1):**
  - [2026-11-12T14:04] [fiscal.ai] [tagged: BOF] **BranchOut Food Inc. to Participate in StoneX 15th Annual Discovery 1x1 Investor Conference** — BranchOut Food Inc. has confirmed its participation in the StoneX 15th Annual Discovery 1x1 Investor Conference, scheduled for December 10, 2026, in New York City.
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "other", "dilution_language": false, "one_line_summary": "BranchOut Food confirms participation in StoneX 15th Annual Discovery 1x1 Investor Conference on December 10, 2026.", "promo_or_pump_flag": false, "quality": 1}`

### CALC — CalciMedica, Inc. Common Stock

- status: `ok`; attempts: 1; forced none by name check: True
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.55
- **input, news used (0):**
  - (none)
- input, roundups dropped (1): "12 Health Care Stocks Moving In Friday's Pre-Market Session" [12 tags]
- input, filings (5 days): 10-Q 2026-11-10 10-Q; 8-K 2026-11-10 8-K 2.02,9.01
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "No news items in last 48 hours; only a 10-Q and an earnings-related 8-K filing listed.", "promo_or_pump_flag": false, "quality": 0}`
- model's own output before the name check: `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "No news items in last 48 hours; only a 10-Q and an earnings-related 8-K filing listed.", "promo_or_pump_flag": false, "quality": 0}`

### CDXS — Codexis, Inc. Common Stock

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 1.17
- **input, news used (3):**
  - [2026-11-13T14:05] [fiscal.ai] [tagged: CDXS] **Codexis Reports Third Quarter 2026 Financial Results** — Codexis announced its financial results for the third quarter ended September 30, 2026, reporting increased revenue and a narrowed net loss compared to the same period in 2025.
  - [2026-11-12T21:09] [benzinga] [tagged: CDXS] **Codexis Q3 EPS $(0.08) Beats $(0.10) Estimate, Sales $19.262M Beat $18.720M Estimate**
  - [2026-11-12T21:06] [benzinga] [tagged: CDXS] **Codexis Affirms FY2026 Sales Guidance of $72.000M-$76.000M vs $73.882M Est**
- input, roundups dropped (1): "12 Health Care Stocks Moving In Friday's Pre-Market Session" [12 tags]
- input, filings (5 days): 10-Q 2026-11-12 10-Q; 8-K 2026-11-12 8-K 2.02,9.01; 4 2026-11-10 FORM 4; 8-K 2026-11-10 8-K 1.01,1.02,2.03,3.02,9.01
- **output:** `{"acquisition_target": false, "catalyst_type": "earnings", "dilution_language": true, "one_line_summary": "Codexis reported Q3 2026 sales of $19.262M and EPS of $(0.08), beating estimates, and affirmed FY2026 sales guidance.", "promo_or_pump_flag": false, "quality": 4}`

### LFMD — LifeMD, Inc. Common Stock

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 2.38
- **input, news used (5):**
  - [2026-11-13T14:06] [fiscal.ai] [tagged: LFMD] **LifeMD Lowers Full-Year 2026 Revenue Guidance** — LifeMD updated its full-year 2026 revenue outlook, reducing the forecast to a range of $188 million to $191 million.
  - [2026-11-13T14:06] [fiscal.ai] [tagged: LFMD] **LifeMD, Inc. Reports Financial Results for the Third Quarter Ended September 30, 2026** — LifeMD reported its third-quarter 2026 financial results, highlighting a revenue of $44.6 million and an adjusted EBITDA loss of approximately $0.4 million.
  - [2026-11-12T21:12] [benzinga] [tagged: LFMD] **LifeMD Q3 EPS $(0.11) Beats $(0.14) Estimate, Sales $44.625M Miss $48.885M Estimate**
  - [2026-11-12T21:07] [benzinga] [tagged: LFMD] **LifeMD Lowers FY2026 Sales Guidance from $205.500M-$212.500M to $188.000M-$191.000M vs $207.582M Est**
  - [2026-11-12T21:07] [benzinga] [tagged: LFMD] **LifeMD Sees Q4 Sales $46.000M-$49.000M vs $61.318M Est**
- input, roundups dropped (1): "12 Health Care Stocks Moving In Friday's Pre-Market Session" [12 tags]
- input, filings (5 days): 10-Q 2026-11-12 10-Q; 8-K 2026-11-12 8-K 1.01,2.02,2.03,3.02,7.01,9.01; NT 10-Q 2026-11-09 NT 10-Q
- **output:** `{"acquisition_target": false, "catalyst_type": "earnings", "dilution_language": false, "one_line_summary": "LifeMD reported Q3 2026 results with sales miss and cut full-year 2026 revenue guidance to $188M-$191M.", "promo_or_pump_flag": false, "quality": 4}`

### MRLN — Merlin, Inc. Common Stock

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 7.64
- **input, news used (6):**
  - [2026-11-13T14:05] [fiscal.ai] [tagged: MRLN] **Merlin, Inc. Reports Third Quarter 2026 Financial Results** — Merlin, Inc. announced its financial and operating results for the third quarter ended September 30, 2026, while highlighting significant progress on key defense contracts.
  - [2026-11-13T05:23] [benzinga] [tagged: MRLN] **Merlin (MRLN) Stock Jumps Over 54% After Hours: What's Going On?** — Merlin shares surged 54.50% after hours as third-quarter earnings crushed analyst estimates, while revenue jumped ahead of expectations.
  - [2026-11-12T21:10] [benzinga] [tagged: MRLN] **Merlin Says New $8.9M USSOCOM Task Order Moves C-130J Autonomy Program Into Integration Phase**
  - [2026-11-12T21:10] [benzinga] [tagged: MRLN] **Merlin Q3 Cash & Short-Term Investments $161.6M Vs $183.9M At 30 June**
  - [2026-11-12T21:10] [benzinga] [tagged: MRLN] **Merlin Q3 Adj EBITDA Loss $(24.1)M Vs $(13.6)M YoY**
  - [2026-11-12T21:07] [benzinga] [tagged: MRLN] **Merlin Q3 EPS $0.37 Vs $(5.24) YoY, Rev $3.5M Vs $1.9M YoY**
- input, roundups dropped (1): "12 Industrials Stocks Moving In Friday's Pre-Market Session" [12 tags]
- input, filings (5 days): 424B3 2026-11-13 424B3; 424B3 2026-11-13 424B3; 8-K 2026-11-12 8-K 2.02,9.01; 10-Q 2026-11-12 10-Q; SCHEDULE 13G/A 2026-11-10
- **output:** `{"acquisition_target": false, "catalyst_type": "earnings", "dilution_language": true, "one_line_summary": "Merlin reported Q3 2026 results with EPS of $0.37 and revenue of $3.5M, plus a $8.9M USSOCOM task order.", "promo_or_pump_flag": false, "quality": 4}`

### SKYE — Skye Bioscience, Inc. Common Stock

- status: `ok`; attempts: 1; forced none by name check: True
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 1.45
- **input, news used (0):**
  - (none)
- input, filings (5 days): DEFA14A 2026-11-12 DEFA14A; 8-K 2026-11-12 8-K 8.01
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "No company-specific news in the last 48 hours; only routine SEC filings (DEFA14A, 8-K) listed.", "promo_or_pump_flag": false, "quality": 0}`
- model's own output before the name check: `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "No company-specific news in the last 48 hours; only routine SEC filings (DEFA14A, 8-K) listed.", "promo_or_pump_flag": false, "quality": 0}`

### SLSN — Solesence, Inc. Common Stock

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 71.31
- **input, news used (2):**
  - [2026-11-13T14:05] [fiscal.ai] [tagged: SLSN] **Solésence, Inc. Reports Third Quarter 2026 Financial Results** — Solésence, Inc. announced its financial results for the third quarter ended September 30, 2026, reporting a swing to net income and significant revenue growth compared to the prior year.
  - [2026-11-12T21:06] [benzinga] [tagged: SLSN] **Solesence Q3 EPS $0.05 Up From $(0.02) YoY, Sales $19.978M Up From $14.597M YoY**
- input, filings (5 days): 10-Q 2026-11-12 QUARTERLY REPORT; 8-K 2026-11-12 FORM 8-K 2.02,9.01; 10-Q/A 2026-11-10 AMENDMENT TO FORM 10-Q; 10-Q/A 2026-11-10 FORM 10-Q/A; 10-Q/A 2026-11-10 AMENDMENT QUARTERLY REPORT; 10-K/A 2026-11-10 AMENDMENT TO FORM 10-K; 10-K/A 2026-11-10 AMENDMENT TO FORM 10-K; SCHEDULE 13D/A 2026-11-09
- **output:** `{"acquisition_target": false, "catalyst_type": "earnings", "dilution_language": false, "one_line_summary": "Sol\u00e9sence reported Q3 2026 results: EPS $0.05 versus $(0.02) prior year, sales $19.98M up from $14.60M.", "promo_or_pump_flag": false, "quality": 4}`

### SPRU — Spruce Power Holding Corporation

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 0.5
- **input, news used (3):**
  - [2026-11-13T14:05] [fiscal.ai] [tagged: SPRU] **Spruce Power Reports Third Quarter 2026 Financial Results** — Spruce Power Holding Corporation announced its financial results for the third quarter ended September 30, 2026, reporting $8.5 million in operating income.
  - [2026-11-12T21:49] [benzinga] [tagged: SPRU] **Spruce Power Holding Q3 2026 Earnings Call Transcript** — Spruce Power Holding (NYSE:SPRU) reported third-quarter financial results on Thursday. The transcript from the company’s third-quarter earnings call has been provided below.This transcript is brought to you by Benzinga
  - [2026-11-12T21:13] [benzinga] [tagged: SPRU] **Spruce Power Holding Q3 EPS $0.28 Up From $(0.04) YoY, Sales $29.693M Down From $30.727M YoY**
- input, filings (5 days): 8-K 2026-11-12 8-K 2.02
- **output:** `{"acquisition_target": false, "catalyst_type": "earnings", "dilution_language": false, "one_line_summary": "Spruce Power reported Q3 2026 results with EPS of $0.28 and sales of $29.7M, down year over year.", "promo_or_pump_flag": false, "quality": 4}`

### STAK — STAK Inc. Class A Ordinary Shares

- status: `no_news`; attempts: 0; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **fail**; prior-day volume multiple: 0.24
- **input, news used (0):**
  - (none)
- input, roundups dropped (1): "Nasdaq Jumps Over 300 Points; Boyd Group Services Shares Plunge After Q3 Results" [7 tags]
- input, filings (5 days): (none)
- **output:** `{"acquisition_target": false, "catalyst_type": "none", "dilution_language": false, "one_line_summary": "", "promo_or_pump_flag": false, "quality": 0}`

### XBIO — Xenetic Biosciences, Inc. Common Stock

- status: `ok`; attempts: 1; forced none by name check: False
- rule `dq_promo_or_no_catalyst`: **pass**; prior-day volume multiple: 0.89
- **input, news used (1):**
  - [2026-11-13T14:06] [fiscal.ai] [tagged: XBIO] **Xenetic Biosciences Reports Third Quarter 2026 Financial Results and Provides Strategic Business Updates** — Xenetic Biosciences announced its financial results for the third quarter of 2026 and provided updates on its proposed share exchange transaction with Santersus AG.
- input, roundups dropped (1): "12 Health Care Stocks Moving In Thursday's Pre-Market Session" [12 tags]
- input, filings (5 days): DEFA14A 2026-11-13 DEFA14A; 8-K 2026-11-13 CURRENT REPORT 2.02,9.01; 10-Q 2026-11-12 FORM 10-Q FOR SEP 2026; SCHEDULE 13G/A 2026-11-12
- **output:** `{"acquisition_target": false, "catalyst_type": "earnings", "dilution_language": false, "one_line_summary": "Xenetic reported Q3 2026 financial results and updated on proposed share exchange with Santersus AG.", "promo_or_pump_flag": false, "quality": 3}`


## Tokens and cost per scan day

| day | candidates | model calls | input tokens | output tokens | est. cost |
|---|---|---|---|---|---|
| 2026-11-09 | 7 | 5 | 6,787 | 486 | $0.0009 |
| 2026-11-10 | 9 | 4 | 6,520 | 442 | $0.0009 |
| 2026-11-11 | 10 | 6 | 9,658 | 672 | $0.0013 |
| 2026-11-12 | 5 | 3 | 4,567 | 299 | $0.0006 |
| 2026-11-13 | 12 | 11 | 17,536 | 1,465 | $0.0025 |
| **mean** | 8.6 | 5.8 | 9,014 | 673 | $0.0012 |

Prices used: $0.1/M input, $0.5/M output (claude-haiku-5-5 list price, prompts under 100K tokens).
