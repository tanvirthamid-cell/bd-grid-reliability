# Operational Reliability of a Gas-Constrained Thermal Fleet: Evidence from Unit-Level Dispatch Reports in Bangladesh

Code, derived data and paper source for the study. The paper is `paper/paper.pdf`; results are in `out/analysis/RESULTS.md`.

## Data and licence
- **Source reports:** public BPDB/NLDC daily generation reports (<https://misc.bpdb.gov.bd>). The raw PDFs (~1.8 GB) are **not redistributed** here. Re-download them with `code/01_index.py` then `code/02_download.py` (into `data/raw/`).
- **Weather:** NASA POWER daily data (<https://power.larc.nasa.gov>), fetched by `code/15_weather.py`.
- **Commissioning years:** BPDB Annual Report 2022-23 and the WRI Global Power Plant Database v1.3 (CC BY 4.0); see `data/ext/cod_manual.csv`.
- **Code** (`code/`): MIT licence (see `LICENSE`).
- **Derived data** (`data/`, `out/`): CC BY 4.0.
- **Large tables are gzipped:** `data/panel_full.csv.gz`, `data/panel.csv.gz`, `data/units_classified.csv.gz`, `data/units.csv.gz`. Run `gunzip -k data/*.csv.gz` before running the scripts.

## Rebuild
Run from the repo root. First download and parse: `01_index.py` → `02_download.py` → `03_parse.py` → `04_classify.py` → `06_shutdown_lists.py` → `07_trips.py` → `12_commissioning.py` → `15_weather.py`. Then the analysis:
08 → 13 → 14 → 10 → 16 → 20 → 25 → 26 → 23 → 05/09 → 30 → 31 → `tectonic -X compile paper/paper.tex` (all scripts are in `code/`).

The research notes below are the original working log.

---

# Bangladesh grid data: is there a Q2/Q3 engineering paper here? (vetting note, 19 Nov 2026)

## Data checked

**BPDB daily generation archive** (`https://misc.bpdb.gov.bd/daily-generation-archive`)
- Public, no login, plain HTTP. The listing has 694 pages; files actually download from about Jan 2020 to today (pages past ~250 list no files).
- Each day has three PDFs, the NLDC (PGCB) "System Summary Report":
  - **Page 1:** day and evening peak demand and generation, unserved energy, Dhaka max temperature, gas supplied (MMCFD), production cost per kWh, generation by zone × fuel (MkWh), cost by fuel, a list of planned and forced shutdowns with capacity, and grid events (outage/restoration times and causes).
  - **Page 2: unit-level table**, about 130 rows a day: plant/unit, owner (PDB, EGCB, APSCL, IPP, rental, import), unit configuration, installed and "present" capacity, evening-peak MW, day energy (kWh), and a free-text remark ("Gas shortage", "Fuel shortage", "Under maintenance", "Machine problem", "Contract expired", "FGMO", "Overhauling" …).
  - **Page 3:** load by grid substation at the evening peak, by zone.
- Text extracts cleanly with `pdftotext -layout`. The format was already similar in Jan 2020. Expect column drift and plant renames across years.
- That gives roughly 2,500 days × ~130 units, about 300k unit-days, each with a reason for being down.

**Existing compiled datasets (competition):**
- Data in Brief 2025, DOI 10.1016/j.dib.2025.112014: daily national/zonal demand, generation, load shedding and Dhaka temperature, 2019–2024. A Mendeley extension runs to Aug 2026.
- UCI dataset 1175: PGCB hourly generation and demand, with a forecasting paper (Islam, Turja & Habib, 2025).
- A Chattogram zone demand and weather dataset on Mendeley.
- All of these are **aggregate demand series used for forecasting**. None of them uses the unit-level page 2.

**Weather:** ERA5 and NASA POWER give daily temperature and humidity at each plant's coordinates. They're free, but ERA5 needs a free CDS account in the user's name.

## Candidate papers

| # | Question | Verdict |
|---|---|---|
| A | Heat → demand / load shedding | **Drop.** Two data papers and forecasting work already cover it. |
| B | Ambient-temperature derating of gas turbines from fleet data (the most "mechanical") | **Drop as designed.** "Present capacity" is static (Haripur 412 MW reads 412 in both January and May), so derating can't be read off it. Peak MW is driven by dispatch and gas supply. |
| C | **Fleet reliability: forced-outage rates, time to failure and time to repair by technology (GT, ST, CCPP, gas engine, HFO engine), age and owner, 2020–26** | **Best fit for Q2/Q3 engineering.** The closest published work is single-plant RAM studies in Nigeria and Indonesia using plant logs. A fleet-wide unit-day panel with reasons for each outage is larger and new. |
| D | Fuel vs machine: how much lost capacity came from gas/fuel shortage vs technical failure, around the July 2022 halt to spot-LNG purchases | **Strong add-on, or a separate energy-policy paper.** The event date is sharp, gas units can be compared with coal, hydro and import units, and the papers found so far are journalism only. |

## Recommended design (C, with D as a section)
1. Scrape all page-2 (and page-1) PDFs, parse them to unit-day rows, and build a unit crosswalk across renames.
2. Classify the remarks into four states: running / fuel-constrained / planned maintenance / forced (machine) outage, plus "reserve/contract expired". Validate by hand on a random sample of about 500.
3. Calculate availability, forced outage rate, equivalent availability factor, and MTBF/MTTR spells. Fit Weibull/lognormal to times between failures, check for a trend (NHPP/Laplace), and run hazard models with technology, age, owner, ambient temperature and humidity at the plant, and load.
4. Decompose unavailable MW by cause over time, with an event-study of gas units vs non-gas units around July 2022.

Possible journals: *Energy Reports*, *Results in Engineering*, *Energy for Sustainable Development*, *Int. J. of System Assurance Engineering and Management*, *Journal of Quality in Maintenance Engineering* (all Q1–Q3 depending on year). For D alone: *Energy Strategy Reviews*, *Utilities Policy*.

## Risks
- **The data is a daily evening-peak snapshot**, not event logs. Outage durations are measured in days, so short trips inside a day are missed. Hourly time-to-failure can't be estimated, so it has to be framed as daily-resolution.
- **"Zero output" doesn't always mean failure.** It can be reserve shutdown, merit-order dispatch or an expired contract. How the remarks are classified drives everything, so the hand-validation step matters.
- **The remarks reflect the operator's own reporting.** Plants may label technical problems as "gas shortage", or the reverse. Treat that as a limitation and possibly test it (for example, "gas shortage" at plants on the same pipeline while others nearby run).
- **Format drift across 2020–2026** and gaps in the archive need checking. Not done yet.
- **No ME co-author.** Reliability methods are standard, but reviewers will expect correct IEEE 762 metric definitions.
- **Unit and plant names are public infrastructure, not people,** so there's no name-linking issue.

## Not checked yet
Full date coverage and missing days; the 2020–2022 page layouts; whether page 1's forced-shutdown list is complete; ERA5 account access.

---

# Scrape-and-test results (19 Nov 2026)

## Pipeline (run from `bd_grid/`; Python = `../bd_tariff_paper/.venv/bin/python -I`)
| Script | Output |
|---|---|
| `code/01_index.py` | `data/index.csv`: 6,936 listing rows. Real files exist only from **Oct 2019**; 2007–2019 rows point to a "no PDF found" placeholder. |
| `code/02_download.py` | `data/raw/p1`, `data/raw/p2`: **2,578 days × 2 PDFs, no failures** (1.9 GB, curl, 4 threads). |
| `code/03_parse.py` (+ `parse_lib.py`) | `data/units.csv`: **413,294 unit-day rows**. `data/day_check.csv` compares each day against the printed totals. `data/system.csv` holds the page-1 fields. |
| `code/04_classify.py` | `data/units_classified.csv`: cause labels from the remarks. |
| `code/05_checks.py` | `out/daily.csv`, `out/checks.json` (consistency tests). |
| `code/06_shutdown_lists.py` | `data/shutdown_lists.csv` (page-1 planned/forced lists), `data/trip_events.csv`. |
| — | `out/validation_sample.csv`: 520 rows, 40 per label, with blank columns for hand checking. |

The data date is the date **printed** on the page, normally the file date minus one day. 2,500+ days match that pattern; a few odd printed dates fall back to file date minus one.

## Parsing accuracy
- Summed unit energy matches the printed "National Grid Total" within 0.5% on **2,562 of 2,575 days (99.5%)**. Capacity matches on 2,554. The 13 misses (all 2025–26) each drop 2–6 rows that wrap onto two lines. Fixable.
- The median day has 159 units (range 130–181). One day parses to 0 rows; to check.
- Page-1 fields are parsed for both layouts: energy, evening-peak demand and generation, gas supplied, and available max generation. Load-shed MW is recorded through 2024; from 2025 the report gives unserved energy instead. Max temperature appears only from 2025.

## Classification
- 1,055 distinct remarks fall into 12 rule-based classes. **Unclassified: 0.2% of offline MW-days.**
- Offline capacity, 2019–26 (MW-days): planned/maintenance 28%, gas shortage 27%, reserve/low demand 14%, **no remark 11%**, other fuel 8%, machine fault 4%, test 2%, finance/payment 1.5%, contract 1.4%, grid 0.9%.
- Running but below capacity (capacity minus peak): no remark 26%, other fuel 16%, gas 14%, reserve 11%, **machine/engine fault 10%**, FGMO/AGC mode 7%, maintenance 6%, grid 4%.

## Consistency tests (do the remarks mean what they say?)
- **Gas-shortage MW vs daily gas supply:** r = −0.39 within calendar month (−0.64 in levels). Machine-fault MW vs gas supply: r = −0.02. Other-fuel MW: −0.01. Each cause moves with its own driver and not with the others, so the labels look real rather than boilerplate.
- **Reserve/low-demand MW:** 2,080 MW on days with no load shedding, 198 MW on days with 1–500 MW of shedding, **40 MW on days with more than 500 MW shed**. Operators don't call a unit "reserve" while customers are being cut off.
- The page-1 "forced shutdown" list (~8 units/day, 2019–mid 2024) is **not a mechanical-failure label**. 55% of gas-shortage units also appear on it, so it can't separate planned maintenance from forced repairs. Its planned column is empty before 2024, and the mid-2024 layout pulls event-table rows into it. Limited use.

## Problems found
1. **Reporting change in January 2025.** The share of offline MW with no remark jumped from 4–13% (2024 months) to 33–41% (early 2025): units idled for gas now show "-". Filling blanks from the same unit's surrounding outage run recovers about 60% of the 2025 blank MW-days. **Main sample should be Oct 2019 – Dec 2024 (5.25 years)**, with 2025–26 used for robustness only.
2. **"Under maint." doesn't say whether the maintenance is planned or a forced repair.** That is the main obstacle for a reliability paper. The likely fix is outage length and onset: an abrupt start after running at full output looks forced; a long run starting in the dry season looks planned. Or report "maintenance outages" without splitting them.
3. **The July 2022 LNG event is weaker than hoped.** Monthly gas-shortage MW went 2,167 (Jun) → 2,422 (Jul) → 3,675 (Nov 2022), while gas to power fell from ~1,060 to 838 MMCFD by November. The decline was gradual, not a sharp break, so design D would be a descriptive decomposition rather than an event study.

## New asset: generator trip events
Page-1 narratives contain **13,445 trip lines, ~1,760 of them generator trips** (2019–26), each with a clock time and often a stated cause ("drum level control valve", "boiler MFT", "main cooling water", "DP high") and a resynchronisation time. This is an hourly-resolution forced-outage record: the cleanest mechanical-failure measure here and the best ME hook. Entries often run onto a second line that isn't joined yet.

## Verdict
- The data holds up. It is national, unit-level, 5+ years, with internal consistency checks that pass.
- The strongest engineering paper combines: (a) unit-day availability by cause (fuel vs machine vs maintenance vs dispatch) by technology and owner, 2019–24; (b) generator trip events (rates, causes, time to resync, and whether trips cluster in hot months or under heavy load) by technology and unit size.
- Remaining work before modelling: join wrapped lines (unit table and trip narratives); hand-check `out/validation_sample.csv`; build a unit crosswalk (renames, splits) with technology, fuel, commissioning year and coordinates; decide the planned/forced rule for "Under maint.".

---

# Clean-and-build results (19 Nov 2026)

## New and changed scripts
| Script | What it does |
|---|---|
| `parse_lib.py` (updated) | Handles rows where the energy figure is pushed onto the next line or glued to the remark. **All 2,575 checkable days now match the printed totals (energy and capacity, within 0.5%).** One day (2025-07-05) is genuinely missing: BPDB uploaded the substation sheet in place of page 2. |
| `07_trips.py` | `data/gen_trips.csv`: **1,618 generator trips** (2019–26). It joins continuation lines and removes duplicate event-table lines. 1,599 have a trip time, 400 a resync time, and 784 a stated cause. Causes are coded as fuel supply 203, electrical 133, turbine 77, boiler 67, grid 67, control 54, cooling 27, other 156, unstated 834. |
| `08_crosswalk.py` | `data/unit_xwalk.csv`, `data/units_master.csv`, `data/panel.csv` (**409k unit-days, 237 units**). Spelling variants are merged by name similarity plus matching unit configuration. Leftover rows are mapped to a unit with the same configuration within ±7 days. Six renames are merged by hand (`MANUAL`). Each unit gets technology (name/configuration rules), fuel (remark history plus a list of known coal plants), owner (public / public JV / private / import), maximum capacity, and first/last date. |
| `09_fuel_check.py` | `out/fuel_check.json`. **Inferred fuels match the official zone-by-fuel generation table within 2% for every fuel** (gas 0.994, coal 1.003, oil 0.982, others 1.000) over 650 days in 2025–26. Unassigned fuel is 0.3% of energy. |
| `10_spells.py` | `data/spells.csv` (9,530 runs of consecutive offline days, with cause, maintenance class, trip-initiated flag and censoring flags) and `data/trips_linked.csv` (1,543 of 1,618 trips linked to a unit, matched by location, MW size and north/south). |
| `11_preview.py` | `out/preview_by_tech.csv`: a first reliability table, Oct 2019 – Dec 2024. |

## Planned vs forced rule (for maintenance outages)
- **Planned:** the remark mentions an overhaul, HGPI, inspection, schedule, annual, AOH, renovation, BMRE or development.
- **Forced:** the remark names a fault, or a generator trip for that unit is logged on the first day of the outage or the day before.
- **Maintenance, unspecified:** anything else, essentially a bare "Under maint.".

By capacity × days, maintenance outages split forced 40%, unspecified 50%, planned 11%. The groups behave as expected:
- Forced outages last a median of 2 days, and the unit ran the day before in 710 of 733 cases.
- Planned outages last a median of 12 days, and the unit ran the day before in 34 of 37.
- Unspecified outages last a median of 4 days, and the unit ran the day before in 545 of 657, so they look mostly like short repairs.

Planned outages are rare by count because a long overhaul is one long outage.

## Preview: Oct 2019 – Dec 2024, thermal units (share of unit-days)
| Technology | Units | Unit-years | Running | Fuel/finance off | Forced | Maint. unspec. | Reserve | Forced-outage rate (daily) | Trips per unit-year | Capacity factor |
|---|---|---|---|---|---|---|---|---|---|---|
| CCGT | 45 | 158 | 72% | 8.5% | 5.3% | 9.2% | 1.4% | 0.069 | 5.2 | 0.54 |
| Gas turbine | 24 | 112 | 45% | 15% | 14% | 5.3% | 15% | 0.239 | 0.7 | 0.15 |
| Steam | 22 | 60 | 46% | 26% | 2.0% | 24% | 0.9% | 0.043 | 2.7 | 0.42 |
| Reciprocating engine | 97 | 379 | 83% | 4.6% | 0.9% | 0.2% | 8.5% | 0.010 | 0.4 | 0.33 |

**Read with care:**
- An engine plant is one row covering 10–30 engines, so single-engine failures show up as reduced output ("Engine problem"), not as the unit going off. Engine reliability has to be measured from reduced output, not from off days.
- Trip rates depend on which plants the narratives mention; large units are mentioned more.
- The gas-turbine forced-outage rate may include gas-related shutdowns that were labelled as faults.

## Still open
1. **Hand-check** `out/validation_sample.csv` (remark labels) and a sample of `data/trips_linked.csv`. Known wrong link: "Summit Meghnaghat 305 MW GT" → `meghnaghat100mwiel`.
2. **Commissioning year** (age) isn't in this data. "Entered in sample" is flagged only for units that started after Nov 2019. It needs BPDB annual-report plant lists, typed in by hand.
3. **Plant coordinates** for weather data (ERA5 needs a free account in your name; NASA POWER doesn't).
4. **Engine plants:** build a reduced-output-based outage measure.
5. **Trip narratives:** 834 trips have no stated cause. Joining the cause text from the next day's report might recover some.

---

# Ages and weather (19 Nov 2026)

## Scripts
| Script | What it does |
|---|---|
| `12_commissioning.py` | Parses BPDB Annual Report 2022-23, "Year Wise Commissioning Status" (2010 – Jun 2023): 143 dated rows → `data/ext/commissioning_bpdb.csv`. Source PDF: bpdb.gov.bd annual-report page (object-storage link in `data/ext/ar_page.html`). The old bpdb.portal.gov.bd site is offline. |
| `data/ext/cod_manual.csv` | **Hand-made unit → commissioning-year table.** Automatic name matching was too error-prone: the annual report gives per-unit MW and uses different names. Sources: `bpdb_ar` (107 thermal units), `wri_gppd` (7; WRI Global Power Plant Database v1.3, CC BY 4.0), **`recall_unverified` (22 older units, mostly pre-2010 PDB/APSCL sets such as Ghorasal 1–5, Ashuganj 3–5, Raozan, Haripur, Meghnaghat MPL; years from my own recall — check before publishing)**. |
| `13_ages.py` | Applies the table. Units first seen after Nov 2019 get their first appearance (23). The rest are `unknown` (28 thermal, mostly small REB/SIPP engine plants). `08_crosswalk.py` now also merges 12 renames from the Dec 2024 layout change (225 units). |
| `data/ext/town_coords.csv`, `14_locate.py` | Town-level coordinates (hand table, ~0.05°) → 197 of 225 units located. Unlocated: 5 small or ambiguous thermal rows. |
| `15_weather.py` | NASA POWER daily T2M, T2M_MAX, RH2M and precipitation for 81 points, Oct 2019 – 16 Nov 2026 (no account needed) → `data/weather_daily.csv`. |
| `16_merge.py` | **`data/panel_full.csv`**: unit-day panel plus state (running / forced / …), trip flag, commissioning year, age, town, weather. Checks go to `out/age_weather_checks.json`. |

## Checks
- Coverage of thermal unit-days, 2019–24: weather 99.9%, age 82.6%.
- **NASA POWER vs the report's printed Dhaka maximum temperature** (662 days, 2025–26): r = 0.82. NASA POWER runs 1.4 °C cooler on average; it's a 0.5° grid-cell average, not a city station. Fine for within-unit variation, but not as an absolute plant-intake temperature.

## First descriptive patterns (raw, not adjusted for technology or season)
- **Age:** the daily forced-outage rate rises from 2.3% (0–5 years) and 2.7% (5–10) to 10% (10–20) and **25% (20+ years)**. This is strongly confounded: the old units are mostly steam and gas-turbine sets, so it needs within-technology comparisons.
- **Heat:** among units that ran the previous day, there's no clear raw gradient. Forced-outage starts run 2.8, 2.2, 1.9, 2.0 and 2.1 per 1,000 unit-days and trips 5.5, 5.3, 4.9, 5.7 and 5.8 across Tmax bins <27, 27–30, 30–33, 33–36 and ≥36 °C. Trips rise slightly on hot days. Cool-season days carry more forced outages, likely because maintenance and gas problems are seasonal. A heat effect, if any, needs unit and month fixed effects.

## Still open
- Verify the 22 `recall_unverified` years (BPDB older annual reports or plant websites).
- 28 thermal units with unknown age (small engine plants).
- Engine plants: build a reduced-output-based outage measure.
- Hand-check the remark labels and trip links (`out/validation_sample.csv`, `data/trips_linked.csv`).

## Commissioning-year verification (19 Nov 2026)
I checked all 22 `recall_unverified` years against web sources (Summit, ADB, APSCL via energytransitionbd.org, GEM wiki, L&T, Daily Star, Dhaka Tribune, UNB, Wikipedia). The notes column of `data/ext/cod_manual.csv` names the source for each.
- **Confirmed (17):** Ashuganj 3 (1986) and 5 (1988); Baghabari 71 MW (1991) and 100 MW (2001); Barapukuria 1–2 (2006); Bibiyana-II (2015); Bibiyana-III (2018 open cycle); Raozan 1 (1993) and 2 (1997); Haripur HPL (2001); Meghnaghat MPL (2002); Summit Meghnaghat (2015); Tongi (2005).
- **Corrected:**
  - Ghorasal 1&2: 1974 → **1967** (units are 1967 and 1976; the combined row uses the older).
  - Ghorasal repowered unit 4: 2022 → **2018**. Its gas turbine started in simple cycle in Oct 2018; the original steam unit dates from 1989.
- **Set to unknown (3):**
  - Siddhirganj 210 MW steam: my 2004 isn't supported; sources say 2012 or 2015.
  - Haripur GT: no source.
  - The second Siddhirganj 210 MW row.
- **Still flagged:**
  - Ghorasal 5: 1994, though GEM lists a 1999 unit and unit numbering differs between sources.
  - Fenchuganj phase 1: 1995 (GEM) vs 1994 (Wikipedia).
  - Ashuganj 4: 1987, within the documented 1986–89 window.
- **Effect:** the raw forced-outage rate for units aged 20+ fell from 25% to **8.3%**. The earlier figure leaned heavily on Siddhirganj 210 and the misdated Ghorasal 4. The age pattern is now 2.3% / 2.7% / 10.0% / 8.3% for 0–5 / 5–10 / 10–20 / 20+ years, so it isn't monotonic, and it's sensitive to a few large units.

---

# Analysis (19 Nov 2026)
See `out/analysis/RESULTS.md` (scripts 20-24). Headline: private units are more available and recover faster, robust to self-reporting checks; heavy rain raises electrical/grid trips; no detectable heat effect; age effects not robust.

## Paper draft (19 Nov 2026)
`paper/paper.tex` + `paper/refs.bib` (references checked against Crossref), figures from `code/30_figures.py`, compiled with `tectonic -X compile paper.tex` -> `paper/paper.pdf` (10 pages). Numbers are typed in from `out/analysis/*.json` (no placeholder system yet).

## Revision after referee report (19 Nov 2026)
Fixes are in `out/analysis/REFEREE_REPORT.md`; v1 draft is kept as `paper/paper_v1.tex`.
- **Ownership coding** (`08_crosswalk.py`): ownership follows the company. RPCL → public; small sponsor-named SIPPs → private; Barisal 307 → private (documented override). United Payra is no longer matched as coal.
- **Spells** (`10_spells.py`): a change of cause group starts a new spell; spells over 180 days are `inactive`. Trip linking now:
  - requires a similarity of at least 0.55;
  - matches sponsor names, unit numbers and Roman numerals;
  - drops first-synchronisation lines and duplicates.
- **Dates:** trips and system series are aligned on the printed page-1 date.
- **New scripts:**
  - `25_ieee.py`: EFOR, EAF, MTBF/MTTR, Weibull, Crow-AMSAA, Laplace.
  - `26_main.py`: ownership with a manual wild cluster restricted bootstrap and label-free measures; Poisson weather models with Holm adjustment; cause-specific rain.
  - `31_numbers.py`: every number in the paper as a macro in `paper/numbers.tex`, plus `paper/tab_ieee.tex`.
- **Trip-link audit:** `out/trip_link_audit_sample.csv` (author check, 95/100 correct before the rule fixes).
- **Rebuild order:** 08 → 13 → 14 → 10 → 16 → 20 → 25 → 26 → 23 → 05/09 → 30 → 31 → `tectonic -X compile paper/paper.tex`.
