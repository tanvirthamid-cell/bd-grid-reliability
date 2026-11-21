# First analysis results: fleet reliability, Bangladesh grid, Oct 2019 – Dec 2024

Scripts: `code/20_sample.py` (sample), `21_heat.py`, `22_age_owner.py`, `23_durations.py`, `24_robust.py`. Raw estimates are in `out/analysis/*.json`.

**Sample.** Large thermal units: 38 combined-cycle (CCGT), 24 gas-turbine, 19 steam; 120k unit-days. 95 reciprocating-engine plants are analysed separately through lost output, because one row covers many engines. The sample ends at Dec 2024, before the Jan 2025 reporting change.

**Methods.** Linear probability models with outcomes per 1,000 unit-days. Standard errors are clustered by unit (robustness: by plant site, and two-way by unit and date).

**Outcomes.**
- **Trip:** a generator trip in the grid operator's (NLDC) narrative.
- **Forced onset:** a forced outage starts on a day the unit ran the previous day.
- **Forced state:** the unit is in a forced outage, among days it is running or forced (a daily forced-outage rate).
- **Non-fuel unavailability:** the unit is off for a reason other than fuel, finance, reserve or contract.

---

## 1. Private units are more available, trip less, and return to service faster
Comparison: same technology and calendar month (technology × year-month fixed effects), controlling for age and size. The comparison group is public units (BPDB, EGCB, APSCL, NWPGCL, RPCL…).

| Outcome | Mean | Private − public | Robustness |
|---|---|---|---|
| Forced state (per 1,000 days) | 117 | **−62 (28), p = .03** | site-clustered p = .04; no age control −84 (31) |
| Non-fuel unavailability (pp) | 21.7 | **−11.7 (4.5)** | zero output for a non-fuel reason, any label: −15.3 (4.8), p = .002 |
| Trips recorded by the grid operator (per 1,000 days) | 11.9 | **−7.3 (3.4)** | site-clustered p = .03 |
| Return-to-service hazard after an outage (Cox) | — | **HR 1.36, p = .01** | also controls technology, outage class, year, age, size |

Private units spend about half as many days in forced outage, trip about 60% less often, and come back from outages about a third faster.

**Main threat: self-reporting.** Private plants are paid for availability, so they have reasons to label outages favourably. Two checks don't depend on the plant's own wording, and both show the same gap:
- trips, which the grid operator writes down;
- days with zero output for any non-fuel reason, whatever the label.

**What this can't separate:** ownership from vintage and technology type within a class. Private CCGTs are newer designs, and private engine plants make up most of the IPP fleet. It also can't separate ownership from fuel priority, since private gas plants may get gas first.

## 2. Heavy rain raises trips, through electrical and grid faults; heat does not
Model: within unit (unit + year-month fixed effects), among units that ran the previous day.

- **Rain:** +0.09 trips per 1,000 unit-days per mm (s.e. 0.03, p ≈ .005–.02 in every specification). On days above 30 mm, the trip rate by cause, compared with dry days (per 1,000):

| Cause | Dry days (<1 mm) | Days >30 mm | Ratio |
|---|---|---|---|
| Electrical | 1.2 | 3.1 | 2.6× |
| Grid | 0.42 | 1.03 | 2.5× |
| Boiler | 0.65 | 1.03 | 1.6× |
| Turbine | 0.65 | 0.62 | flat |
| Fuel supply | 2.4 | 2.1 | flat |

  The rise is in electrical and grid causes, not mechanical ones, which fits lightning, insulation moisture and transmission faults.
- **Heat: no detectable effect.**
  - Large thermal units: +0.44 trips per 1,000 per °C of Tmax (0.33).
  - CCGTs: +0.80 per °C (0.50).
  - Forced onsets: −0.3 (0.5).
  - This holds with lagged and 3-day Tmax, unit × month-of-year fixed effects, dropping load-shedding days, and two-way clustering.
  - Engine plants: lost output from engine faults doesn't change with Tmax either (−0.04 pp per °C, s.e. 0.05).
  - **Power is limited:** for CCGTs above 36 °C, the 95% interval runs from −3 to +16 trips per 1,000 (mean 16). A large heat effect can't be ruled out.
  - **Temperature measure:** NASA POWER cell temperature, which is 1.4 °C cooler than the Dhaka report temperature.
- **System demand:** each 1 GW above the month's mean goes with 0.6–0.9 *fewer* events per 1,000 (p < .05). That is probably operational (maintenance deferred and units held steady on peak days) rather than physical. It needs care before it's interpreted.

## 3. Age: suggestive only
- Within technology and month, units aged 20+ show +92 (43) forced days per 1,000 compared with 5–9-year-old units (pooled), and steam units +156 (35).
- New units (0–4 years) show more non-fuel unavailability (+13 pp, s.e. 7, p ≈ .05). That fits commissioning and teething problems, an early "bathtub-curve" pattern.
- **Not robust.** With documented commissioning years only (no first-appearance or conflicting years), no age bin is significant. Earlier, two misdated old units moved the 20+ rate from 25% to 8%. Treat this as descriptive.
- Repair is slower for old units (Cox HR 0.74, p = .05), steam units (0.65, p = .03) and larger units (0.76 per log MW).

## 4. Durations and trip anatomy (descriptive)
- Forced outages: median 2 days, mean 45. Unspecified maintenance: median 5, mean 33. The tails are long.
- Time from trip to resync where both times are given: CCGT median 2.8 h (n = 196), steam 3.5 h (34), gas turbine 1.4 h (21), engines 0.9 h (36).
- Stated trip causes for CCGTs (excluding unstated and other): control 41, turbine 50, boiler/HRSG 35, cooling 17, plus electrical and fuel supply.

## Assessment for a Q2/Q3 paper
- **Strongest contributions:**
  - The fleet-wide, unit-level reliability dataset itself, with validation against official totals.
  - The ownership/availability gap, robust to self-reporting checks.
  - The rain → electrical/grid trip result, which has a clear mechanism.
- **Heat:** a well-powered null for daily outages, but too wide to rule out a sizeable trip effect.
- **Weak points:**
  - Age, given the commissioning-year uncertainty.
  - The ownership comparison may reflect vintage and technology mix.
  - The temperature measure is coarse.
- **Suggested framing:** "Operational reliability of a gas-constrained thermal fleet: evidence from 5 years of unit-level dispatch reports in Bangladesh." Target journals: *Energy Reports*, *Energy for Sustainable Development*, *Results in Engineering*, *Int. J. of System Assurance Engineering and Management*.

## Not yet done
- Hand validation of the remark labels and trip links.
- Figures.
- A lightning dataset to test the rain mechanism directly.
- Heterogeneity by gas-turbine model.
- Dropping the Jan 2025+ period was a design choice; a 2025–26 replication would be a useful out-of-sample check.
