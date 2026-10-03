# Équinoxe rental-growth forecast — CodeML 2026

The evaluated deliverable is [`notebooks/equinoxe_analysis.ipynb`](notebooks/equinoxe_analysis.ipynb), a French notebook derived from the supplied starter. It audits all four tables, explains changing lease composition, compares consecutive leases of the same apartment, analyzes concessions and lease types, integrates dated public context, and completes `estimate_2026()` and `backtest()`.

**Target:** unweighted median annualized effective-rent growth across eligible consecutive same-apartment lease transitions starting in the forecast year. It is a price-growth statistic for comparable transitions in the supplied extract, not exact portfolio revenue growth. Contractual growth uses the same eligible pairs.

The authoritative teammate handoff is [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md). Public-source definitions, URLs, publication dates, limitations and AI disclosure are in [`docs/REFERENCES.md`](docs/REFERENCES.md); the French jury outline is [`docs/presentation_outline.md`](docs/presentation_outline.md).

## Confidential data

Keep the original package outside this repository, unchanged. Set `JADCO_DATA_DIR` to that directory. It must contain `consignes.pdf`, `presentation-jadco.pdf`, `starter.ipynb`, `manifest.json` and all four `equinoxe_*.csv` files. Execution verifies every manifest size and SHA-256. CSV apartment/property codes and Yardi handles are loaded as strings; leading zeros survive.

Do not commit CRM rows, source PDFs/notebook, row-level exports, local caches or failed/executed notebook copies. `.gitignore` excludes these and local configuration. Only reviewed aggregates may be shared. Ignore rules do not remove already tracked files: inspect `git ls-files` before pushing. At project start, only the original `main.py` was tracked; it remains unchanged.

## Windows PowerShell setup

Run from the repository root. Python **3.13** was used for verification; the lock file records the installed dependencies (Windows-specific packages included). Python 3.11–3.13 should be compatible, but other versions/platforms have not been executed here.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
$env:JADCO_DATA_DIR = 'D:\your\actual\path\to\Jadco\instructions'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\execute_notebook.py
```

Replace the example path with the actual verified source-package path; do not assume the D: example exists. `requirements.txt` pins primary libraries and is an alternative installation input on other platforms; `requirements-lock.txt` pins the complete tested environment. Neither installation includes data. Windows sandboxed agents may need permission to create Python temporary files or Jupyter's secure kernel connection file; normal local PowerShell does not have that sandbox restriction.

`scripts/execute_notebook.py` starts a fresh kernel using the active Python executable, runs all cells in order, reviews textual outputs for CRM addresses/links and private table headers, and rechecks source integrity. It writes only ignored files under `private_outputs/`: executed notebook, aggregate chart PNGs and runtime state. Failures are logged there without publishing private traceback content. The automated scan is an additional safeguard, not a universal privacy guarantee; chart sources and notebook outputs must still be reviewed.

To attach the reviewed aggregate tables/charts to the evaluated notebook:

```powershell
.\.venv\Scripts\python.exe scripts\execute_notebook.py --share-aggregates
```

To work interactively, use the virtual-environment kernel explicitly:

```powershell
.\.venv\Scripts\python.exe -m ipykernel install --prefix .venv --name equinoxe --display-name 'Équinoxe (.venv)'
.\.venv\Scripts\python.exe -m jupyterlab notebooks\equinoxe_analysis.ipynb
```

Select **Équinoxe (.venv)** in JupyterLab and use **Restart Kernel and Run All Cells**. Launch from this PowerShell session so the kernel inherits `JADCO_DATA_DIR`. A copied `.env.example` → `.env` is ignored but **not automatically loaded**: set the variable in the shell or your own local launcher. Never commit an actual machine path.

## Notebook maintenance

The notebook contains the key pairing, forecasting and evaluation code. `equinoxe.py` supplies local loading, verification and the same algorithms for synthetic tests. When changing shared algorithms, edit the module and synchronize the notebook with the small builder:

```powershell
.\.venv\Scripts\python.exe scripts\build_notebook.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\execute_notebook.py --share-aggregates
```

**The builder recreates the derivative and clears outputs.** Preserve deliberate notebook edits before invoking it, or put them in `scripts/build_notebook.py`. The original starter is only read, never changed. Do not replace the existing `main.py` with the forecasting project.

## Methods and validation

`UNIT_KEY = ["sPropCode", "sUnitCode"]`, validated against `hUnit`; never site plus unit. Consecutive lease starts determine the predecessor. Eligibility is the starter's strict `0.5 < gap_years < 2.5`; both measures' prices must be positive. Growth is `((current / previous) ** (1 / gap_years) - 1) * 100`, using 365.25 days/year. Pair construction precedes splitting by the new lease's `sRenewal`.

Training includes only leases starting **and signed** on/before the December 31 cutoff. Pre-signed future-start leases are conservatively excluded. Backtests predict 2023/2024/2025 using cutoffs 2022/2023/2024; the observed target keeps earlier predecessor leases. Public information is publication-filtered. Current listing prices and future composition weights never enter models. Asking histories are sparse and used only for cutoff/staleness diagnostics.

Three methods are compared: previous-year median, mean of the previous three annual global medians, and one province/type distribution-mixture candidate. The central method is the transparent recent mean; the candidate's small development-backtest gain does not justify extra assumptions. Group diagnostics require at least 30 pairs/year in two recent years; small/new groups explicitly fall back to the global recent mean. These group forecasts do not combine into the global median.

Public aggregates are versioned in `docs/public_signals.json`, so execution is offline after package installation. CMHC/SCHL, provincial rent CPI and regulatory information inform interpretation and scenarios. They are **not externally fitted predictors**; historical external panels and building-specific legal applicability remain incomplete. No legally permissible rent increase is inferred from these extracts. The model is a recalculated statistical rule with no fitted parameters to serialize.

The three validation years inform method comparison: these are **development backtests**, not an independent holdout. Errors are percentage points, not classification accuracy. Scenarios are historical-regime assumptions, not confidence intervals.

## Verified results

The 2026 central forecast is **2.46% effective** and **4.24% contractual**. Effective type diagnostics are **2.17% renewals** and **3.39% turnovers**. The selected method's 2023–2025 development MAE is **1.364 percentage points**. These are price-growth predictions for the defined transitions, not portfolio revenue growth. Historical-regime scenarios are 1.77% / 2.46% / 3.58%, not a confidence interval.

The final 32-cell notebook (16 code cells) executes in a fresh kernel, all ten synthetic tests pass, source integrity is rechecked, and 55 output objects / six aggregate charts are reviewed. The evaluated notebook includes only those aggregate outputs. Detailed checks, assumptions and remaining input limitations are in the handoff and presentation. Review `git status`, share candidates and notebook outputs before your own commit/push; no commit, push, publication or deployment is performed by this project.
