"""Local data validation and transparent rental-growth calculations."""

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

UNIT_KEY = ["sPropCode", "sUnitCode"]
MIN_GAP_YEARS = 0.5
MAX_GAP_YEARS = 2.5
DAYS_PER_YEAR = 365.25
HISTORY_YEARS = 3
MIN_GROUP_PAIRS = 30
MIN_GROUP_YEARS = 2
METHODS = ("previous_year", "recent_mean", "segmented_distribution")
PRICE_COLUMNS = ["sRent", "sRentEffective"]
TABLE_FILES = {
    "listings": "equinoxe_listings.csv",
    "leases": "equinoxe_lease_history.csv",
    "concessions": "equinoxe_concessions.csv",
    "asking": "equinoxe_asking_history.csv",
}
DATE_COLUMNS = {
    "listings": ["sAsOf", "sAvailable"],
    "leases": ["sLeaseFrom", "sLeaseTo", "sSignDate", "sAvailable"],
    "concessions": ["sDateFrom", "sDateTo"],
    "asking": [],
}


def data_directory():
    value = os.environ.get("JADCO_DATA_DIR")
    if not value:
        raise ValueError("Set JADCO_DATA_DIR to the external source-package directory.")
    directory = Path(value).expanduser().resolve()
    if not directory.is_dir():
        raise ValueError("JADCO_DATA_DIR must be an existing directory.")
    return directory


def verify_manifest(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    records = []
    for entry in manifest["files"]:
        path = directory / entry["path"]
        content = path.read_bytes()
        records.append({
            "file": entry["path"],
            "size_ok": len(content) == entry["bytes"],
            "sha256_ok": hashlib.sha256(content).hexdigest() == entry["sha256"],
        })
    result = pd.DataFrame(records)
    if not result[["size_ok", "sha256_ok"]].all().all():
        raise ValueError("Source integrity check failed.")
    return result


def load_tables(directory):
    tables = {}
    for name, filename in TABLE_FILES.items():
        raw = pd.read_csv(Path(directory) / filename, dtype="string", keep_default_na=False)
        table = pd.read_csv(
            Path(directory) / filename,
            dtype={column: "string" for column in raw if column.startswith("h") or column in UNIT_KEY},
        )
        for column in DATE_COLUMNS[name]:
            parsed = pd.to_datetime(raw[column], errors="coerce")
            if parsed.isna().any():
                raise ValueError(f"Invalid or missing date: {name}.{column}")
            table[column] = parsed
        if name == "asking":
            table["date"] = pd.to_datetime(raw["sMonth"] + "-01", errors="raise")
        if name == "leases":
            table["year"] = table["sLeaseFrom"].dt.year
        tables[name] = table
    return tables


def validate_identity(table):
    if table[UNIT_KEY + ["hUnit"]].isna().any().any():
        raise ValueError("Missing apartment identity.")
    if table.groupby(UNIT_KEY, observed=True)["hUnit"].nunique().gt(1).any():
        raise ValueError("Apartment key maps to multiple hUnit identifiers.")
    if table.groupby("hUnit", observed=True)[UNIT_KEY].nunique().gt(1).any().any():
        raise ValueError("hUnit maps to multiple apartment keys.")


def audit_tables(tables, directory):
    summaries = []
    columns = []
    checks = []
    listings = tables["listings"]
    validate_identity(listings)
    if listings.duplicated(UNIT_KEY).any() or listings["hUnit"].duplicated().any():
        raise ValueError("Listings must contain exactly one row per apartment.")
    for name, table in tables.items():
        raw = pd.read_csv(Path(directory) / TABLE_FILES[name], dtype="string", keep_default_na=False)
        empty = raw.apply(lambda values: values.str.strip().eq("").sum()).sum()
        placeholders = raw.apply(
            lambda values: values.str.strip().str.lower().isin(
                ["null", "none", "na", "n/a", "nan", "unknown", "-", "?", "9999", "-999"]
            ).sum()
        ).sum()
        summaries.append({
            "table": name, "rows": len(raw), "columns": len(raw.columns),
            "missing_cells": int(table.isna().sum().sum()), "empty_cells": int(empty),
            "placeholder_cells": int(placeholders), "exact_duplicates": int(raw.duplicated().sum()),
        })
        for column in raw:
            columns.append({"table": name, "column": column, "dtype": str(table[column].dtype),
                            "missing": int(table[column].isna().sum())})
        validate_identity(table)
        keys = table[UNIT_KEY + ["hUnit"]].drop_duplicates()
        linked = keys.merge(listings[UNIT_KEY + ["hUnit"]], on=UNIT_KEY, how="left",
                            validate="one_to_one", suffixes=("", "_listing"), indicator=True)
        checks.append({"table": name, "check": "unmatched_unit_keys",
                       "count": int(linked["_merge"].ne("both").sum())})
        checks.append({"table": name, "check": "hUnit_key_disagreement",
                       "count": int(linked["hUnit"].ne(linked["hUnit_listing"]).sum())})
        for column in ["hProperty", "hBuilding", "sBuilding", "sState", "sCity", "sBeds", "sSqft", "sFloor"]:
            unstable = table.groupby(UNIT_KEY, observed=True)[column].nunique().gt(1).sum()
            matched = table.merge(listings[UNIT_KEY + [column]], on=UNIT_KEY, how="left",
                                 validate="many_to_one", suffixes=("", "_listing"))
            checks.append({"table": name, "check": f"unstable_{column}", "count": int(unstable)})
            checks.append({"table": name, "check": f"listing_disagreement_{column}",
                           "count": int(matched[column].ne(matched[column + "_listing"]).sum())})
        for column in DATE_COLUMNS[name]:
            checks.append({"table": name, "check": f"invalid_{column}",
                           "count": int(table[column].isna().sum())})
    leases = tables["leases"]
    business_keys = {
        "listings": UNIT_KEY,
        "leases": UNIT_KEY + ["sLeaseFrom"],
        "concessions": UNIT_KEY + ["sChargeCode", "sDateFrom", "sDateTo"],
        "asking": UNIT_KEY + ["sMonth"],
    }
    for name, key in business_keys.items():
        checks.append({"table": name, "check": "business_key_duplicate_rows",
                       "count": int(tables[name].duplicated(key, keep=False).sum())})
    lease_checks = {
        "end_before_start": leases["sLeaseTo"].lt(leases["sLeaseFrom"]),
        "sign_after_start": leases["sSignDate"].gt(leases["sLeaseFrom"]),
        "nonpositive_contractual": leases["sRent"].le(0),
        "nonpositive_effective": leases["sRentEffective"].le(0),
        "effective_above_contractual": leases["sRentEffective"].gt(leases["sRent"]),
        "starts_after_2025": leases["sLeaseFrom"].gt(pd.Timestamp("2025-12-31")),
        "signatures_after_2025": leases["sSignDate"].gt(pd.Timestamp("2025-12-31")),
        "ends_after_2025": leases["sLeaseTo"].gt(pd.Timestamp("2025-12-31")),
        "term_sequence_duplicate_rows": leases.duplicated(UNIT_KEY + ["sTermSeq"], keep=False),
    }
    for name, values in lease_checks.items():
        checks.append({"table": "leases", "check": name, "count": int(values.sum())})
    concessions = tables["concessions"]
    checks.extend([
        {"table": "concessions", "check": "end_before_start",
         "count": int(concessions["sDateTo"].lt(concessions["sDateFrom"]).sum())},
        {"table": "concessions", "check": "nonnegative_amount",
         "count": int(concessions["sAmount"].ge(0).sum())},
        {"table": "asking", "check": "nonpositive_asking_rent",
         "count": int(tables["asking"]["sAskingRent"].le(0).sum())},
    ])
    return pd.DataFrame(summaries), pd.DataFrame(columns), pd.DataFrame(checks)


def consecutive_pairs(leases, min_gap=MIN_GAP_YEARS, max_gap=MAX_GAP_YEARS):
    validate_identity(leases)
    if leases["sLeaseFrom"].isna().any():
        raise ValueError("Missing lease start prevents reliable ordering.")
    if not leases["sRenewal"].isin([0, 1]).all():
        raise ValueError("Unknown renewal flag.")
    ordered = leases.drop_duplicates().sort_values(UNIT_KEY + ["sLeaseFrom"]).copy()
    if ordered.duplicated(UNIT_KEY + ["sLeaseFrom"]).any():
        raise ValueError("Ambiguous same-apartment lease start; resolve before pairing.")
    grouped = ordered.groupby(UNIT_KEY, observed=True)
    ordered["previous_date"] = grouped["sLeaseFrom"].shift()
    for column in PRICE_COLUMNS:
        ordered["previous_" + column] = grouped[column].shift()
    ordered["gap_years"] = (ordered["sLeaseFrom"] - ordered["previous_date"]).dt.days / DAYS_PER_YEAR
    has_previous = ordered["previous_date"].notna()
    interval_ok = ordered["gap_years"].gt(min_gap) & ordered["gap_years"].lt(max_gap)
    positive = ordered[PRICE_COLUMNS + ["previous_" + column for column in PRICE_COLUMNS]].gt(0).all(axis=1)
    positive &= ordered[PRICE_COLUMNS + ["previous_" + column for column in PRICE_COLUMNS]].notna().all(axis=1)
    eligible = has_previous & interval_ok & positive
    accounting = {
        "input_rows": len(leases), "exact_duplicates_removed": len(leases) - len(ordered),
        "first_leases": int((~has_previous).sum()),
        "short_intervals": int((has_previous & ordered["gap_years"].le(min_gap)).sum()),
        "long_intervals": int((has_previous & ordered["gap_years"].ge(max_gap)).sum()),
        "invalid_prices_after_interval": int((has_previous & interval_ok & ~positive).sum()),
        "eligible_pairs": int(eligible.sum()),
    }
    assert accounting["input_rows"] == sum(accounting[key] for key in accounting if key != "input_rows")
    pairs = ordered.loc[eligible].copy()
    pairs["year"] = pairs["sLeaseFrom"].dt.year
    for column in PRICE_COLUMNS:
        pairs[column + "_growth"] = (
            (pairs[column] / pairs["previous_" + column]) ** (1 / pairs["gap_years"]) - 1
        ) * 100
    return pairs, accounting, ordered.loc[has_previous & ~eligible].copy()


def known_leases(leases, cutoff):
    cutoff = pd.Timestamp(cutoff)
    return leases.loc[leases["sLeaseFrom"].le(cutoff) & leases["sSignDate"].le(cutoff)].copy()


def available_external(external, cutoff):
    if external is None:
        return pd.DataFrame()
    required = ["source_id", "geography", "variable", "value", "unit", "reference_end", "published_at"]
    if not set(required).issubset(external):
        raise ValueError("External signals require explicit reference and publication dates.")
    selected = external.copy()
    for column in ["reference_end", "published_at"]:
        selected[column] = pd.to_datetime(selected[column], errors="raise")
        if selected[column].isna().any():
            raise ValueError("Missing external availability date.")
    if not np.isfinite(pd.to_numeric(selected["value"], errors="raise")).all():
        raise ValueError("Invalid external value.")
    return selected.loc[selected["published_at"].le(pd.Timestamp(cutoff))].copy()


def latest_asking(asking, cutoff):
    if asking is None:
        return pd.DataFrame()
    dated = asking.copy()
    dated["date"] = pd.to_datetime(dated["sMonth"] + "-01", errors="raise")
    if dated.duplicated(UNIT_KEY + ["date"]).any():
        raise ValueError("Ambiguous asking observation for apartment and month.")
    selected = dated.loc[dated["date"].le(pd.Timestamp(cutoff))]
    latest = selected.sort_values("date").drop_duplicates(UNIT_KEY, keep="last").copy()
    latest["age_days"] = (pd.Timestamp(cutoff) - latest["date"]).dt.days
    return latest


def weighted_median(values, weights):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if len(values) == 0 or not np.isfinite(values).all() or not np.isfinite(weights).all() or (weights <= 0).any():
        raise ValueError("Weighted median requires finite values and positive weights.")
    order = np.argsort(values, kind="stable")
    sorted_values = values[order]
    cumulative = np.cumsum(weights[order])
    midpoint = cumulative[-1] / 2
    position = np.searchsorted(cumulative, midpoint)
    if np.isclose(cumulative[position], midpoint, rtol=1e-12, atol=1e-12) and position + 1 < len(values):
        return float((sorted_values[position] + sorted_values[position + 1]) / 2)
    return float(sorted_values[position])


def forecast(leases, target_year, method="recent_mean", price_col="sRentEffective", asking=None, external=None):
    if method not in METHODS or price_col not in PRICE_COLUMNS:
        raise ValueError("Unknown forecast method or price variable.")
    cutoff = pd.Timestamp(target_year - 1, 12, 31)
    history = known_leases(leases, cutoff)
    pairs, accounting, unused_excluded = consecutive_pairs(history)
    growth_col = price_col + "_growth"
    annual = pairs.groupby("year")[growth_col].median()
    recent = annual.reindex(range(target_year - HISTORY_YEARS, target_year)).dropna()
    if recent.empty:
        raise ValueError("No eligible recent history available before cutoff.")
    baseline = float(recent.mean())
    groups = []
    if method == "previous_year":
        if target_year - 1 not in annual:
            raise ValueError("Previous-year baseline has no previous-year observations.")
        prediction = float(annual.loc[target_year - 1])
    elif method == "recent_mean":
        prediction = baseline
    else:
        current = pairs.loc[pairs["year"].eq(target_year - 1)]
        if current.empty:
            raise ValueError("No previous-year pairs for composition weights.")
        recent_pairs = pairs.loc[pairs["year"].between(target_year - HISTORY_YEARS, target_year - 1)]
        values = []
        weights = []
        group_columns = ["sState", "sRenewal"]
        for key, current_group in current.groupby(group_columns, observed=True):
            pool = recent_pairs.loc[recent_pairs["sState"].eq(key[0]) & recent_pairs["sRenewal"].eq(key[1])]
            counts = pool.groupby("year").size()
            valid_years = counts.loc[counts.ge(MIN_GROUP_PAIRS)].index
            supported = len(valid_years) >= MIN_GROUP_YEARS
            group_weight = len(current_group) / len(current)
            if supported:
                for year in valid_years:
                    year_pool = pool.loc[pool["year"].eq(year), growth_col]
                    values.extend(year_pool.tolist())
                    weights.extend([group_weight / len(valid_years) / len(year_pool)] * len(year_pool))
            else:
                values.append(baseline)
                weights.append(group_weight)
            groups.append({"province": key[0], "renewal": int(key[1]), "weight": group_weight,
                           "supported_years": len(valid_years), "fallback": not supported})
        prediction = weighted_median(values, weights)
    signals = available_external(external, cutoff)
    asking_snapshot = latest_asking(asking, cutoff)
    return {
        "target_year": target_year, "cutoff": cutoff.date().isoformat(), "method": method,
        "price_col": price_col, "prediction_pct": prediction, "training_leases": len(history),
        "training_pairs": len(pairs), "annual_history": recent.to_dict(), "exclusion_accounting": accounting,
        "groups": groups, "available_external_rows": len(signals),
        "asking_units_at_cutoff": len(asking_snapshot),
        "asking_median_age_days": float(asking_snapshot["age_days"].median()) if len(asking_snapshot) else None,
    }


def evaluate(leases, target_year, method="recent_mean", price_col="sRentEffective", asking=None, external=None):
    result = forecast(leases, target_year, method, price_col, asking, external)
    observed_leases = known_leases(leases, pd.Timestamp(target_year, 12, 31))
    observed_pairs, unused_accounting, unused_excluded = consecutive_pairs(observed_leases)
    target = observed_pairs.loc[observed_pairs["year"].eq(target_year)]
    if target.empty:
        raise ValueError("No observed target-year pairs.")
    observed = float(target[price_col + "_growth"].median())
    result.update({"observed_pct": observed, "error_pp": result["prediction_pct"] - observed,
                   "absolute_error_pp": abs(result["prediction_pct"] - observed),
                   "observed_pairs": len(target), "observed_units": target.groupby(UNIT_KEY).ngroups})
    return result


def group_forecasts(leases, target_year, group_columns, price_col="sRentEffective", requested_groups=None):
    cutoff = pd.Timestamp(target_year - 1, 12, 31)
    history = known_leases(leases, cutoff)
    pairs, unused_accounting, unused_excluded = consecutive_pairs(history)
    recent_pairs = pairs.loc[pairs["year"].between(target_year - HISTORY_YEARS, target_year - 1)]
    baseline = forecast(leases, target_year, price_col=price_col)["prediction_pct"]
    records = []
    group_keys = history[group_columns].drop_duplicates()
    if requested_groups is not None:
        requested = pd.DataFrame(requested_groups)
        if not set(group_columns).issubset(requested):
            raise ValueError("Requested groups must provide all grouping columns.")
        group_keys = pd.concat([group_keys, requested[group_columns]], ignore_index=True).drop_duplicates()
    for key in group_keys.itertuples(index=False, name=None):
        mask = pd.Series(True, index=recent_pairs.index)
        for column, value in zip(group_columns, key):
            mask &= recent_pairs[column].eq(value)
        pool = recent_pairs.loc[mask]
        counts = pool.groupby("year").size()
        supported_years = counts.loc[counts.ge(MIN_GROUP_PAIRS)].index
        medians = pool.groupby("year")[price_col + "_growth"].median().reindex(supported_years)
        supported = len(supported_years) >= MIN_GROUP_YEARS
        records.append(dict(zip(group_columns, key), prediction_pct=float(medians.mean()) if supported else baseline,
                            recent_pairs=len(pool), supported_years=len(supported_years), fallback=not supported))
    return pd.DataFrame(records)
