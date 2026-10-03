"""Synthetic fixtures only: no confidential CRM records."""

import numpy as np
import pandas as pd
import pytest

from equinoxe import (
    DAYS_PER_YEAR, MIN_GROUP_PAIRS, consecutive_pairs, validate_identity, known_leases,
    forecast, evaluate, group_forecasts, latest_asking, available_external, weighted_median,
)


def lease_fixture():
    records = []
    for property_code, unit_handle, multiplier in [("synthetic_a", "fixture_one", 1), ("synthetic_b", "fixture_two", 2)]:
        for year in range(2019, 2026):
            rent = 1000 * multiplier * 1.04 ** (year - 2019)
            records.append({"sPropCode": property_code, "sUnitCode": "0203", "hUnit": unit_handle,
                "sSite": "same_site", "sState": "Quebec", "sBuilding": property_code,
                "sLeaseFrom": pd.Timestamp(year, 1, 1), "sSignDate": pd.Timestamp(year - 1, 12, 15),
                "sRent": rent, "sRentEffective": rent * 0.95, "sRenewal": int(year % 2 == 0)})
    return pd.DataFrame(records)


def test_identity_preserves_property_and_leading_zero():
    leases = lease_fixture()
    pairs, accounting, excluded = consecutive_pairs(leases)
    assert leases.sUnitCode.unique().tolist() == ["0203"]
    assert len(pairs) == 12
    assert pairs.groupby(["sPropCode", "sUnitCode"]).ngroups == 2
    assert accounting["first_leases"] == 2
    assert excluded.empty
    assert pairs.previous_sRent.min() == 1000
    assert pairs.loc[pairs.sPropCode.eq("synthetic_b"), "previous_sRent"].min() == 2000


def test_identity_disagreement_and_ambiguous_order_fail():
    leases = lease_fixture()
    inconsistent = leases.copy()
    inconsistent.loc[0, "hUnit"] = "different_handle"
    with pytest.raises(ValueError, match="multiple hUnit"):
        validate_identity(inconsistent)
    ambiguous = pd.concat([leases, leases.iloc[[0]].assign(sRent=999)], ignore_index=True)
    with pytest.raises(ValueError, match="Ambiguous"):
        consecutive_pairs(ambiguous)
    many_to_one = leases.copy()
    many_to_one["hUnit"] = "same_handle"
    with pytest.raises(ValueError, match="multiple apartment"):
        validate_identity(many_to_one)


def test_annualization_and_new_lease_type():
    leases = lease_fixture().iloc[:3].copy()
    pairs, unused_accounting, unused_excluded = consecutive_pairs(leases)
    first = pairs.iloc[0]
    expected = ((first.sRentEffective / first.previous_sRentEffective) ** (DAYS_PER_YEAR / 365) - 1) * 100
    assert first.sRentEffective_growth == pytest.approx(expected)
    assert first.sRenewal == 1
    assert len(pairs) == 2
    assert np.allclose(pairs.sRent_growth, pairs.sRentEffective_growth)


def test_exclusion_accounting_and_shared_price_eligibility():
    base = lease_fixture().iloc[[0]].copy()
    dates = pd.to_datetime(["2019-01-01", "2019-07-02", "2020-07-02", "2023-07-02", "2024-07-02"])
    rows = pd.concat([base] * len(dates), ignore_index=True)
    rows["sLeaseFrom"] = dates
    rows["sRent"] = [1000, 1010, 1020, 1030, 1040]
    rows["sRentEffective"] = [950, 960, 970, 980, 0]
    rows = pd.concat([rows, rows.iloc[[0]]], ignore_index=True)
    pairs, accounting, excluded = consecutive_pairs(rows)
    assert accounting == {"input_rows": 6, "exact_duplicates_removed": 1, "first_leases": 1,
        "short_intervals": 1, "long_intervals": 1, "invalid_prices_after_interval": 1, "eligible_pairs": 1}
    assert len(pairs) == 1
    assert len(excluded) == 3
    assert pairs.previous_sRent.iloc[0] == 1010


def test_strict_interval_boundaries():
    leases = lease_fixture().iloc[:2]
    gap = (leases.sLeaseFrom.iloc[1] - leases.sLeaseFrom.iloc[0]).days / DAYS_PER_YEAR
    assert consecutive_pairs(leases, min_gap=gap)[0].empty
    assert consecutive_pairs(leases, max_gap=gap)[0].empty


def test_forecast_cutoff_blocks_future_rows_and_late_signatures():
    leases = lease_fixture()
    result = forecast(leases, 2023)
    altered = leases.copy()
    altered.loc[altered.sLeaseFrom.dt.year.ge(2023), ["sRent", "sRentEffective"]] *= 20
    assert forecast(altered, 2023)["prediction_pct"] == result["prediction_pct"]
    signed_before_start_after = leases.iloc[[0]].assign(
        sPropCode="future_property", hUnit="future_unit", sLeaseFrom=pd.Timestamp("2023-01-01"),
        sSignDate=pd.Timestamp("2022-01-01"))
    late_signed = signed_before_start_after.assign(sPropCode="late_property", hUnit="late_unit",
        sLeaseFrom=pd.Timestamp("2022-01-01"), sSignDate=pd.Timestamp("2023-01-01"))
    extra = pd.concat([leases, signed_before_start_after, late_signed], ignore_index=True)
    assert len(known_leases(extra, "2022-12-31")) == len(known_leases(leases, "2022-12-31"))
    assert forecast(extra, 2023)["prediction_pct"] == result["prediction_pct"]


def test_asking_and_public_cutoffs_and_cardinality():
    asking = pd.DataFrame({"sPropCode": ["p", "p"], "sUnitCode": ["0203", "0203"],
        "sMonth": ["2022-12", "2023-01"], "sAskingRent": [1000, 9000]})
    latest = latest_asking(asking, "2022-12-31")
    assert len(latest) == 1
    assert latest.sAskingRent.iloc[0] == 1000
    assert latest.age_days.iloc[0] == 30
    with pytest.raises(ValueError, match="Ambiguous"):
        latest_asking(pd.concat([asking, asking.iloc[[0]]]), "2022-12-31")
    external = pd.DataFrame([
        {"source_id": "late_observation", "geography": "Quebec", "variable": "rent", "value": 4,
         "unit": "percent", "reference_end": "2022-12-31", "published_at": "2023-01-20"},
        {"source_id": "known_future_rule", "geography": "Ontario", "variable": "guideline", "value": 2,
         "unit": "percent", "reference_end": "2023-12-31", "published_at": "2022-06-01"},
    ])
    assert available_external(external, "2022-12-31").source_id.tolist() == ["known_future_rule"]
    invalid = external.copy()
    invalid.loc[0, "published_at"] = None
    with pytest.raises(ValueError, match="Missing external"):
        available_external(invalid, "2022-12-31")


def test_small_and_new_group_fallback():
    leases = lease_fixture()
    global_prediction = forecast(leases, 2026)["prediction_pct"]
    mixture = forecast(leases, 2026, method="segmented_distribution")
    assert all(group["fallback"] for group in mixture["groups"])
    assert mixture["prediction_pct"] == pytest.approx(global_prediction)
    groups = group_forecasts(leases, 2026, ["sBuilding"])
    assert groups.fallback.all()
    assert np.allclose(groups.prediction_pct, global_prediction)
    unseen = group_forecasts(leases, 2026, ["sBuilding"], requested_groups=[{"sBuilding": "unseen_fixture"}])
    unseen_row = unseen.loc[unseen.sBuilding.eq("unseen_fixture")].iloc[0]
    assert unseen_row.fallback
    assert unseen_row.recent_pairs == 0
    assert unseen_row.prediction_pct == pytest.approx(global_prediction)
    recent_only = leases.loc[leases.sLeaseFrom.dt.year.ge(2024)].assign(sState="Ontario",
        sPropCode=lambda frame: frame.sPropCode + "_new", hUnit=lambda frame: frame.hUnit + "_new")
    combined = pd.concat([leases, recent_only], ignore_index=True)
    new_group = forecast(combined, 2026, method="segmented_distribution")["groups"]
    assert all(group["fallback"] for group in new_group if group["province"] == "Ontario")


def test_supported_groups_and_weighted_distribution_median():
    base = lease_fixture().loc[lambda frame: frame.sPropCode.eq("synthetic_a")].copy()
    records = []
    for index in range(MIN_GROUP_PAIRS):
        records.append(base.assign(sUnitCode=f"fixture_{index:04d}", hUnit=f"handle_{index:04d}", sRenewal=1))
    leases = pd.concat(records, ignore_index=True)
    result = forecast(leases, 2026, method="segmented_distribution")
    assert not result["groups"][0]["fallback"]
    assert result["groups"][0]["supported_years"] == 3
    assert sum(group["weight"] for group in result["groups"]) == pytest.approx(1)
    expected_pairs = consecutive_pairs(known_leases(leases, "2025-12-31"))[0]
    selected = expected_pairs.loc[expected_pairs.year.between(2023, 2025)]
    assert result["prediction_pct"] == pytest.approx(selected.sRentEffective_growth.median())
    assert weighted_median([0, 1, 10, 100], [0.2, 0.2, 0.2, 0.4]) == 10
    assert weighted_median([1, 5], [1, 1]) == 3
    with pytest.raises(ValueError):
        weighted_median([1, 5], [0, 1])


def test_forecast_and_observed_target_consistency():
    leases = lease_fixture()
    detail = evaluate(leases, 2023)
    target = consecutive_pairs(known_leases(leases, "2023-12-31"))[0]
    expected = target.loc[target.year.eq(2023), "sRentEffective_growth"].median()
    assert detail["observed_pct"] == expected
    assert detail["observed_pairs"] == 2
    assert detail["prediction_pct"] == forecast(leases, 2023)["prediction_pct"]
    assert detail["prediction_pct"] == pytest.approx(np.mean(list(detail["annual_history"].values())))
    assert detail["error_pp"] == pytest.approx(detail["prediction_pct"] - expected)
    with pytest.raises(ValueError, match="No eligible"):
        forecast(leases.loc[leases.sLeaseFrom.dt.year.eq(2019)], 2020)
