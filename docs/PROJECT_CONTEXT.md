# Project context and teammate handoff

## Objective and status
Estimate Collection Équinoxe's 2026 rental growth using information available by 2025-12-31. Main evaluated deliverable: a French Jupyter notebook derived from the supplied starter. Status: phases A–J and final handoff completed, clean-kernel verified, with reviewed aggregate outputs saved in the evaluated notebook. No implementation blocker. Public integration is contextual; complete historical external panels and building-specific legal applicability remain disclosed limitations.

## Verified facts
- The current workspace is the existing Git repository, on branch `main`, with a clean initial working tree.
- Only `main.py` is tracked; it prints `Hello, World!` and will be preserved.
- The source package was found in the sibling `instructions` directory, two levels above the repository. It contains the two PDFs, starter notebook, manifest, and four CSVs requested.
- This execution environment mounts C: only. The supplied D: assumption does not describe this mounted workspace. Machine-specific paths are intentionally omitted from tracked documentation.
- No applicable `AGENTS.md` was found in the workspace's ancestor directories or source-package root.
- Python 3.13 is present; pandas, NumPy, Matplotlib, pypdf, nbformat, nbclient, and pytest are initially absent.
- No private data is tracked, so untracking or Git-history changes are unnecessary.

## Target and analytical decisions
Selected target, after reading the official sources: the **unweighted median annualized effective-rent growth across eligible consecutive lease transitions starting in the target calendar year**, with contractual growth on the exact same pairs as a comparison. Each transition receives one vote; an apartment may appear more than once. This represents observed comparable transitions in the extract, not exact portfolio revenue growth or a fixed basket of all apartments.

Price: supplied `sRentEffective`; annual assignment: new lease `sLeaseFrom`; identity: `sPropCode` + string `sUnitCode`, verified equivalent to `hUnit`; predecessor: immediately preceding lease start, constructed before splitting types; strict eligibility: `0.5 < days_between_starts / 365.25 < 2.5`, both current and previous prices positive for both measures. Annualization: `((current / previous) ** (1 / gap_years) - 1) * 100`. New lease `sRenewal` classifies the transition. No outlier trimming or concession reconstruction is imposed.

Forecast training requires both start and signature on/before the December 31 cutoff; pre-signed future-start leases are excluded conservatively. Observed targets retain prior-year predecessor leases. The tested segmentation candidate predicts the same global median using past distributions and prior-year province/type shares; it does not redefine the target as an average of group medians. The selected central method is the recent mean, as explained below.

## Source interpretation and audit findings
- Read all five written-instruction pages, all eight presentation pages, all 24 starter Markdown/code cells, manifest, and every CSV locally.
- Official PDFs require Python/Jupyter, public information, 2023–2025 backtests, AI references, and no CRM records in deliverables. The derived notebook will replace private previews with aggregates.
- Slides say 4,303 leases; written instructions and independently counted CSV say 4,302. Use the actual file, preserving this discrepancy.
- All seven supplied manifest entries match byte size and SHA-256.
- Basic audit reproduces dimensions, zero missing/empty/placeholder cells and zero exact row duplicates. Placeholder checks use a documented candidate-token list, not proof that no semantic placeholders exist.
- Identifiers are preserved as strings. All tables' apartment keys and `hUnit` agree with the unique listing reference; no unmatched keys. Common property/building/geography/bedroom/area/floor fields are stable within tables and match listings.
- Leases have no duplicate apartment/start or apartment/term-sequence keys, reversed dates, late signatures, nonpositive prices, or effective prices above contractual. Both flags contain only 0 and 1.
- 963 contractual end dates exceed 2025; these are contract terms, not observations of 2026 growth. Listing `sAsOf` spans January–December 2025, not a uniform December snapshot.
- Concessions have 72 rows involved in repeated apartment/charge-code/start/end keys, despite no identical whole rows. These are not automatically deleted and no row-level concession merge is performed.
- Pairing reproduces 3,179 pairs from 890 apartments; 1,061 first leases plus 62 short intervals are excluded. All excluded intervals are 182 days (0.4983 years), with 46 renewals and 16 turnovers. They are not proven duplicate leases; strict starter eligibility excludes plausible six-month transitions. Sensitivity analysis will disclose this.
- Reproduced effective medians: 2021 3.5434%, 2022 4.5864%, 2023 2.0194%, 2024 1.7716%, 2025 3.5752%. Contractual medians: 4.4566%, 5.3962%, 2.2881%, 3.3890%, 7.0446% respectively.
- 2025 renewals: 473 pairs, effective 2.9083%, contractual 6.4085%; turnovers: 307, effective 5.7407%, contractual 8.9808%.

## Files and reproduction
- `.gitignore`: excludes CRM files, private outputs, virtual environments, local configuration, caches, and executed notebook copies.
- `.env.example`: demonstrates configurable `JADCO_DATA_DIR`; it contains no real machine path.
- `docs/PROJECT_CONTEXT.md`: authoritative, continuously updated team handoff.
- `main.py`: original work, unchanged.
- `notebooks/equinoxe_analysis.ipynb`: main French evaluated deliverable, 32 cells, required entry points and visible algorithms.
- `equinoxe.py`: local data loading/audit and shared tested analytical algorithms.
- `scripts/build_notebook.py`: derives the notebook from the external starter and shared algorithms; clears outputs.
- `scripts/execute_notebook.py`: clean-kernel execution, privacy scan, local chart export and optional aggregate sharing.
- `tests/test_equinoxe.py`, `pytest.ini`: ten synthetic tests and focused collection without caches.
- `requirements.txt`, `requirements-lock.txt`: pinned primary libraries and complete tested Windows environment.
- `README.md`: setup, execution, kernel selection and maintenance commands.
- `docs/REFERENCES.md`, `docs/public_signals.json`: sourced public context and AI-use disclosure.
- `docs/presentation_outline.md`: French jury narrative with verified results.

Set `JADCO_DATA_DIR` to the external source-package directory. Follow README setup, then run `.venv\Scripts\python.exe -m pytest -q` and `.venv\Scripts\python.exe scripts\execute_notebook.py`. The latter writes an ignored executed notebook and six aggregate PNGs under `private_outputs/`; `--share-aggregates` transfers reviewed outputs to the main notebook. `.env` is not auto-loaded. Never copy original CRM files into tracked paths.

## Checks and limitations
Executed: initial filesystem/Git/instruction checks; all source reading; manifest verification; comprehensive audit; historical aggregate reproduction; development backtests; ten synthetic tests; clean-kernel execution of all 32 cells (16 executable); text review of 55 outputs; visual review of all six aggregate charts and their source. All pass. Composition legends were moved below bars and the final chart re-reviewed. Final Git/share-candidate inspection, Python compilation, notebook schema validation, address/link/machine-path scans and source integrity recheck pass. See the log for transient Windows setup/kernel issues and resolutions.

## Public context and model-selection status
Verified dated public aggregates are stored in `docs/public_signals.json`, with definitions, publication/retrieval dates, units, geography and comparability limits in `docs/REFERENCES.md`. Sources cover CMHC Montreal/Ottawa, Quebec/Ontario rent CPI, November national rent CPI, TAL and Ontario rules. Historical external numerical panels are not fitted. The external interface filters on publication date, including future-reference guidelines announced before a cutoff.

Important verified timing: 2023 CMHC results were released 2024-01-31; December 2025 CPI was released 2026-01-19. Neither was available at its year-end. Ontario's 2026 conditional 2.1% guideline was announced 2025-06-30. Quebec's method reform was announced 2025-12-17, but the January 2026 numerical calculation is excluded. Actual first-occupation/readiness dates and section F/max-rent terms are unavailable: no provincial ceiling is imposed on this extract's effective-growth statistics.

Selected central method: three-year arithmetic mean of annual global effective-growth medians. Previous-year and one province/type distribution-mixture candidate were tested. The candidate's small improvement over three development years is insufficient evidence to justify added thresholds and composition assumptions. Public easing supports a cautious central scenario rather than extrapolating 2025's acceleration, but no arbitrary numerical adjustment is applied.

## Verified results and interpretation
Central 2026 **2.4553717283% effective**, **4.2405792125% contractual**. Type diagnostics: renewals 2.1678%, turnovers 3.3908% effective. These separate subgroup medians' forecasts do not aggregate into the global median. Historical-regime scenarios: low 1.7716%, central 2.4554%, high 3.5752%; these are assumptions, not a confidence interval.

| Year | Prediction % | Observed % | Signed error pp | Absolute error pp | Observed pairs / units |
|---|---:|---:|---:|---:|---:|
| 2023 | 3.7164 | 2.0194 | +1.6970 | 1.6970 | 416 / 416 |
| 2024 | 3.3831 | 1.7716 | +1.6115 | 1.6115 | 698 / 678 |
| 2025 | 2.7925 | 3.5752 | -0.7827 | 0.7827 | 780 / 779 |

Development MAE: selected recent mean **1.36375 pp**; previous year **1.53950 pp**; segmented candidate **1.28869 pp**, a 0.07506 pp gain. Selection and reporting share these years; no independent test-set claim. The selected forecast is the mean of annual medians, not itself an observed pooled median; it predicts the future target median under stable recent-regime assumptions.

Composition analysis reproduces naive 2023 growth 10.8497%. Per-lease effective discount median reaches 10.3051% in 2025. Asking diagnostics show a median age of 305 days at final cutoff, despite observations existing for all 1,061 units. Lowering the interval threshold to 0.49 descriptively gives a three-year reference of 2.5339%, a +0.0785 pp sensitivity; main eligibility remains strict.

Building diagnostics use the same recent-year median-mean idea with explicit minimum support: Daniel-Johnson 2.6866%, Le Carlyle 2.6165%, Levesque 2.6072%, Saint-Elzear 2.4059%, The Met 2.6405%; Westpark 2.4554% is a global fallback, not a supported building-specific estimate. Small or explicitly requested unseen groups return the global baseline. No subgroups have independent validation.

No trained-model serialization is required: no fitted parameters, only a deterministic statistical rule recalculated from source. No dashboard was added; effort prioritizes the evaluated notebook.

## Next steps
1. Teammates: reproduce using README and review the notebook's target, method selection and assumptions.
2. Verify actual first-occupation/readiness dates, section F/maximum-rent provisions and concession semantics if authoritative documents are available; currently disclosed uncertainties.
3. Rehearse the French presentation, preserving price-growth versus revenue-growth distinctions.
4. Review the 16 safe share candidates and notebook outputs before your own commit/push. All project additions remain untracked for your review. No assistant commit, staging, push or deployment.
5. Evaluate the frozen method when 2026 observations arrive; future external features require historical publication vintages and new validation.

## Chronological work log (most recent first)
### 2026-10-03 — Final verification and teammate handoff complete
- Changed: saved reviewed aggregate outputs in the evaluated notebook; finalized this authoritative context and exact teammate next steps.
- Why: deliver a concrete, reproducible notebook and communication materials ready for human review before GitHub submission.
- Evidence: final fresh-kernel run executes all 16 code cells; 55 outputs and six images pass privacy review. All ten synthetic tests pass in 0.60 seconds; `pip check` reports no broken requirements. Forecasts and development errors match the results above.
- Checked: notebook schema and Python compilation; all 16 tracked/untracked nonignored share candidates inspected/scanned for private addresses/links and actual machine paths; no CSV/PDF/private exports among them. `main.py` byte-identical to HEAD; seven manifest entries still match both size and hash; ignore rules verified for environment, local configuration, private notebook and CRM paths. README's optional interactive kernel-install command also succeeds in the ignored virtual environment after approved access to Windows temporary files. No commit or push.
- Limitations: automated scans are not universal privacy guarantees; manual output/chart-source review supplements them. Full historical external numerical panels, authoritative legal applicability and concession cash reconciliation remain explicitly incomplete analytical inputs, not claimed accomplishments.
- Next teammate: use README to reproduce, review assumptions and the French presentation, then stage/commit/push yourself after confidentiality review.

### 2026-10-03 — Visual/privacy review and review-ready results
- Changed: visually reviewed six aggregate charts; moved composition legends below bars; completed reproducible README and result-supported French presentation.
- Why: ensure readable, safe outputs for the evaluated notebook and jury.
- Evidence: charts show annual/group aggregates, labelled units and type counts, with no row-level points, handles or addresses. Numeric outputs match the result tables and outline.
- Checked: clean kernel succeeds with 55 outputs, six PNGs and source integrity rechecked; privacy text scan passes. Public inputs are clearly contextual, not a fitted integration claim.
- Next teammate: finish final execution after legend changes and Git/privacy inspection, then reproduce and review before pushing.

### 2026-10-03 — Clean-kernel results and final communication
- Changed: completed the French notebook's 32 cells, README, dependency lock, French presentation outline, group fallback for explicitly unseen groups and the local privacy-aware execution workflow.
- Why: make the concrete forecast reproducible and reviewable, with the exact target beside it and honest validation/public-data limits.
- Evidence: clean-kernel execution succeeds; 55 outputs pass textual address/link/private-table scans; six chart outputs are built only from aggregates. Numbers in the results section and outline match local calculations.
- Checked: all ten synthetic tests pass after the unseen-group addition; `pip check` passes. The first full run exposed a pandas Index comparison typo in chart annotation, corrected to an explicit comparison. Sandbox kernel security requires approved execution; unrelated pytest cache directories are ignored and test collection now targets `tests/`.
- Next teammate: finish visual review and final Git/content/privacy checks, then use README commands and review the presentation. The assistant will not commit or push.

### 2026-10-03 — French notebook and synthetic behavior checks
- Changed: built a 32-cell French notebook from the verified starter, expanded composition/concession/type/asking analyses, exposed pairing/forecast/evaluation functions directly, added ten synthetic tests and a local execution/privacy-review script.
- Why: make the evaluated notebook readable and central while sharing the exact tested algorithms; prevent future-information leakage and accidental row-level output sharing.
- Evidence: all ten tests pass, covering property identity/leading zeros, ambiguity, annualization, strict bounds, exclusion accounting, both-price eligibility, cutoff invariance, dated external/asking availability, group fallback, mixture medians and observed aggregation.
- Checked: `pytest -q` completed (10 passed; Windows sandbox cache warnings). Notebook generation/format validation succeeded. Initial kernel startup was blocked while Jupyter tried to create its default user-profile IPython directory; local runtime configuration is being added before retry.
- Status: numerical exploratory results are reproducible, but clean-kernel completion/privacy review remain pending; do not claim the notebook is execution-verified yet.
- Next teammate: run the clean-kernel executor, investigate any cell failure locally, then update result summaries/presentation from verified aggregates.

### 2026-10-03 — Public-source verification and reproducible dependency setup
- Changed: added dated public aggregates, detailed source/AI references, pinned primary dependencies and a complete installed dependency lock.
- Why: distinguish publication dates from reference periods and avoid treating provincial regulatory headlines as unconditional predictions.
- Evidence: official CMHC, Statistics Canada, TAL, Quebec government and Ontario ministry releases; see `docs/REFERENCES.md` for exact URLs and limitations. PromoPay independently reproduces 1,494 entries (1,318 one-month / 176 two-month), median -$1,356.60; asking history spans October 2016–December 2025, mean 3.635 observations/unit, maximum 12. Identity collision count reproduces 248.
- Checked: local aggregate queries; successful dependency installation and `pip check` (no broken requirements). Direct Ontario general-page opening failed; the dated official ministry release verifies the relevant guideline/exemptions. Other requested public sources were accessible.
- Decision: external evidence informs explanations/scenarios and is publication-filtered; no fabricated historical external coefficient or hard legal cap. Keep incomplete historical panels and building-specific legal applicability explicit.
- Next teammate: build the French derived notebook, synthetic behavioral tests, privacy-aware executor and README; validate all cells in order before finalizing results.

### 2026-10-03 — Official requirements, target, and Phase A/D checks
- Changed: implemented `equinoxe.py` for configurable local loading, integrity/audit, identity validation, consecutive pairing, and shared temporal forecasting primitives; settled the target above before selecting a method.
- Why: correct apartment identity and explicit exclusion accounting are prerequisites to interpretable growth; forecasting and validation must share cutoff logic.
- Evidence: full source reading and independently reproduced audit/pair/year/type counts match historical verification targets. A complete accounting reconciles all 4,302 leases.
- Checked: locally executed all loaders/audits and pair construction; inspected inferred/parsed types and aggregate failures. No original files changed. Primary dependencies are pinned; environment installation completed sufficiently to execute the audit.
- Decision: retain supplied effective rent without claiming cash collection; retain strict starter intervals but disclose six-month sensitivity. Sources' opening-date and legal-cap shorthand will be qualified.
- Next teammate: implement composition/concession/asking charts, dated public-source registry, synthetic checks, then select from only three predeclared methods using development backtests.

### 2026-10-03 — Starter reading and integrity verification
- Changed: added pinned primary dependencies; read all 24 starter cells and all CSV headers/rows locally with standard-library readers.
- Why: establish provenance before modeling and preserve identifiers instead of trusting inferred CSV types.
- Evidence: all seven manifest entries match byte size and SHA-256. Dimensions reproduce 1,061×29 listings, 4,302×35 leases, 3,560×18 concessions, 3,857×14 asking rows. Starter explicitly warns about PromoPay and the extract's inability to measure occupancy.
- Checked: independent CSV iteration and SHA-256 computation. Originals untouched. Initial environment setup hit Windows temporary-file sandbox permissions; approved environment creation succeeded and dependency installation is in progress.
- Assumptions/issues: starter's effective-rent-as-cash wording is not independently supported; first observed lease is not proof of opening date; these will be qualified in the derived notebook. PDF reading remains pending installed pypdf.
- Next teammate: finish local PDF reading and comprehensive audit; settle the target before forecasting.

### 2026-10-03 — Initial inspection and confidentiality setup
- Changed: added ignore rules, environment-variable example, and this handoff; preserved existing code.
- Why: protect confidential source files before any outputs are generated and establish a reviewable teammate record.
- Evidence: Git tracks only `main.py`; the complete source package exists outside the repository; no ancestor instructions apply.
- Checked: filesystem and Git inspection commands above. No data was uploaded, committed, or pushed.
- Next teammate: read official sources, verify hashes, then audit the data before choosing a forecast.
