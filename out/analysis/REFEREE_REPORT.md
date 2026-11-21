# Independent referee report on paper/paper.tex (19 Nov 2026)

**Recommendation: major revision.** Realistic now: Q2–Q3 (Energy Reports, Results in Engineering, IJSAEM, Heliyon) after revision. Not a reliability-focused Q1 journal such as RESS as it stands.

The reviewer's report was checked by hand. Confirmed: RPCL 210 MW CCPP coded private; United Payra coded steam/coal, though it is mostly HFO engines; Haripur GT forced on 1,745 of 1,870 days and Tongi on 1,317 of 1,869; top 5 units = 65% of forced days; 8 undated units inflate the unit counts in Table 2.

## Fix list (priority order)
1. **Coding errors.** RPCL → public; United Payra → engine/oil (or drop); SIPP/Doreen/Regent → private; BIFPCL → public JV. Rerun everything. (Reviewer's rerun: private gap −68.2 forced, −7.3 trips (p=.047), −11.9 non-fuel.)
2. **State machine.**
   - Split spells when the cause changes.
   - Treat mothballed or long-idle units (e.g. >180 days off with no running) as inactive, not forced. This fixes the gas-turbine FOR of 0.24.
   - Drop the tautological "98% follow a running day" statistic.
   - Stop double-counting trip-initiated forced onsets in the combined event outcome.
3. **IEEE 762 metrics.** EAF, EFOR (including reduced output), FOF, POF, MTBF/MTTR by technology; Weibull/lognormal fits; NHPP or Laplace trend test; benchmark against NERC GADS.
4. **Label-free ownership check.** Use any zero-output day (private −20.6 pp, s.e. 5.7). The current version excludes fuel labels, which is exactly where the bias would sit. Add a wild cluster bootstrap (about 12 private clusters). Describe the hazard ratio correctly ("36% higher return hazard", not "36% faster"). State the coal-steam vs old gas-steam confound.
5. **Trip linking.** Add a similarity threshold; keep sponsor names for matching (Summit Bibiyana-II vs Bibiyana-III); drop non-trip lines ("synchronized for the first time"); remove 34 duplicates; hand-audit a sample.
6. **Heat.** Report the low within-cell variance of Tmax (SD 1.6 °C) and event counts; address the significant negative forced-onset bins; control for multiple comparisons; consider ERA5-Land.
7. **Rain.** The electrical/grid mechanism rests on 15 + 5 events. Use a cause-specific Poisson model with confidence intervals and soften the claim; lightning data would test it properly.
8. **Minor.**
   - Align trips and system data to `p1_data_date` (16 days misaligned).
   - Fix the Table 1 and Table 2 unit counts, and generate Table 1 from a script.
   - Fix the duplicate rows from the merge in Figure 2.
   - Describe the energy check as internal consistency, not external validation.
   - Run the fuel check on 2019–24 where possible.
   - Drop the "bathtub" claim: it falls to +10.7 (p=.12) once test days are excluded.
9. **Hand validation** of remark labels and trip links, with precision and recall reported. This is still the single biggest credibility gap.

---
# Round 2 (second independent referee) and fixes
The second referee found: the wild bootstrap did not re-partial its draws; the 180-day inactive rule reclassified long fault outages; Bhairob was coded as a CCGT; pooled Weibull β<1 can be a mixture artefact; EFOR is two-thirds derates; some numbers were hard-coded; and the paper said "all of recent construction" and "entirely through electrical".

**Fixed:**
- WCR bootstrap: each draw is re-partialled; 4,999 draws.
- Inactive class only for spells over 180 days with no fault remark; sensitivity at 90/180/365 days and with no inactive class (Table 2).
- Bhairob is now an engine.
- Unlinked trips are de-duplicated.
- Per-unit Weibull fits and a unit-cluster bootstrap. The paper now says intervals are close to exponential within units and that heterogeneity drives the pooled shape.
- EFOR derate sensitivity: none, ≥10% shortfalls, load-shedding days.
- A caveat on labelling drift in the trend tests.
- The quoted numbers that were still typed by hand are now macros.
- Wording corrected.

**Consequences:**
- Ownership is now **suggestive**. The forced-state gap is −81/1000 (wild p=.02), but the CCGT-only gap is p=.08, trips p=.15, and the label-free measure p=.06.
- CCGT EFOR is 0.13. Gas-turbine EFOR is 0.34, with 75% of its forced days coming from 3 units.

**Still open:** independent hand validation of remarks and trip links, with precision and recall; ERA5; a GADS benchmark; the fuel check covers 2025–26 only.
