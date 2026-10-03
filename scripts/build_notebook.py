"""Build a clean, aggregate-only derivative of the original starter notebook."""

import hashlib
import inspect
import sys
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import equinoxe


def build():
    source = equinoxe.data_directory() / "starter.ipynb"
    original = nbformat.read(source, as_version=4)
    notebook = nbformat.v4.new_notebook()
    notebook.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.13"},
        "provenance": {"derived_from": "starter.ipynb", "source_cells": len(original.cells),
                       "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                       "adaptation": "Starter sections 1–7 expanded; raw previews replaced by aggregates."},
    }

    def markdown(content):
        notebook.cells.append(nbformat.v4.new_markdown_cell(content.strip()))

    def code(content):
        notebook.cells.append(nbformat.v4.new_code_cell(content.strip()))

    markdown("""
# Hausse de loyer Équinoxe — prévision 2026

**Question : quelle croissance du loyer effectif peut-on prévoir pour les transitions de bail en 2026 ?**

Ce notebook est dérivé des 24 cellules du `starter.ipynb` fourni : chargement, conventions Yardi,
effet de composition, appariement, concessions, renouvellements et prévision. Les fonctions non
implémentées sont complétées et les vérifications temporelles sont ajoutées. Les données sources
restent intactes et hors du dépôt. Aucun aperçu de ligne CRM n'est affiché.

La démarche : vérifier → définir → comparer → prévoir → tester → expliquer. Les calculs sont
reproduits depuis les quatre CSV locaux. Les petits helpers de lecture/vérification se trouvent dans
`equinoxe.py`; l'appariement et la prévision sont également visibles ici, sans modèle complexe caché.
Le document de passation anglais est `docs/PROJECT_CONTEXT.md`.

**Portée :** extrait de six immeubles, et non portefeuille complet. On ne peut pas en déduire
l'occupation, l'inoccupation, l'absorption ni le rôle total de loyers. Une date de fin en 2026 est une
condition contractuelle connue, pas un loyer 2026 observé. La présentation indique 4 303 baux;
les consignes écrites et le CSV en contiennent 4 302. On utilise le fichier vérifié.
""")
    markdown("""
## 1. Chargement local et intégrité — phases A et B

Installer les dépendances et définir `JADCO_DATA_DIR` selon le README. Aucun chemin absolu de
l'ordinateur n'est enregistré ici. Tous les fichiers du manifeste sont vérifiés par taille et SHA-256.
Les identifiants `h*`, `sPropCode` et `sUnitCode` sont lus comme chaînes; les zéros initiaux sont conservés.
Les prix, surfaces et indicateurs sont numériques; `s` ne signifie pas automatiquement « chaîne ».
Les dates sont converties avec contrôle des échecs. Une erreur d'intégrité arrête l'exécution.
""")
    code("""
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import Markdown, display

ROOT = Path.cwd().resolve()
if not (ROOT / "equinoxe.py").exists():
    ROOT = ROOT.parent
if not (ROOT / "equinoxe.py").exists():
    raise RuntimeError("Exécuter depuis la racine du dépôt ou notebooks/.")
sys.path.insert(0, str(ROOT))
from equinoxe import (
    UNIT_KEY, MIN_GAP_YEARS, MAX_GAP_YEARS, DAYS_PER_YEAR, HISTORY_YEARS,
    MIN_GROUP_PAIRS, MIN_GROUP_YEARS, METHODS, PRICE_COLUMNS,
    data_directory, verify_manifest, load_tables, audit_tables,
    validate_identity, known_leases, available_external, latest_asking, weighted_median,
)

pd.set_option("display.max_rows", 150)
pd.set_option("display.precision", 3)
COLORS = {"contractual": "#1976a3", "effective": "#d26a23", "naive": "#7655a6"}
plt.rcParams.update({"figure.figsize": (10, 4.8), "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 11, "axes.grid": True,
                     "grid.alpha": 0.2, "figure.dpi": 120})
DATA_DIR = data_directory()
display(verify_manifest(DATA_DIR))
tables = load_tables(DATA_DIR)
listings, leases, concessions, asking = (tables[name] for name in ["listings", "leases", "concessions", "asking"])
audit_summary, column_types, audit_checks = audit_tables(tables, DATA_DIR)
display(audit_summary)
display(column_types)
display(audit_checks)
""")
    markdown("""
### Dictionnaire et interprétation des données

| Colonnes | Signification et usage |
|---|---|
| `hUnit`, `hProperty`, `hBuilding` | Handles Yardi : identifiants opaques, pas des grandeurs. |
| `sPropCode` + `sUnitCode` | Identité d'appartement pour trier/apparier; bijection avec `hUnit` vérifiée. |
| `sLink` | Identifiant/lien représentatif de l'unité; unicité vérifiée, contenu non publié. |
| `sSite`, `sBuilding`, `sCity`, `sState` | Étiquettes de regroupement; un site peut contenir plusieurs propriétés. |
| `sBeds`, `sBaths`, `sSqft`, `sFloor` | Chambres, salles de bain, surface en pi², étage; stabilité contrôlée. |
| `sRent` | Loyer mensuel contractuel du bail; dans listings, prix d'une observation de l'offre. |
| `sRentEffective` | Loyer mensuel effectif fourni, après avantages selon la source; pas une collecte de cash vérifiée. |
| `sLeaseFrom`, `sLeaseTo`, `sSignDate` | Début contractuel, fin contractuelle, date de signature. Le début attribue l'année de transition. |
| `sTermMonths`, `sTermSeq` | Durée et séquence stockées, contrôlées sans les utiliser comme clé globale de bail. |
| `sRenewal` | 1 : renouvellement; 0 : relocation, selon le nouveau bail. |
| `sConcession` | Indicateur 0/1 fourni; distinct du nombre de lignes de concessions. |
| `sChargeCode`, `sChargeDesc`, `sAmount`, `sMonths` | Type, description, montant signé et durée renseignée d'un avantage. Le sens total/mensuel n'est pas uniforme. |
| `sDateFrom`, `sDateTo` | Période renseignée de concession; peut dépasser 2025. Pas d'identifiant explicite du bail. |
| `sMonth`, `sAskingRent` | Mois et prix affiché observé; série irrégulière, distincte des loyers signés. |
| `sAsOf`, `sAvailable` | Date du relevé et disponibilité renseignée, sans preuve d'occupation réelle. |

Les contrôles de placeholders recherchent vide, null, none, na, n/a, nan, unknown, -, ?, 9999 et -999.
Ils ne prouvent pas l'absence de codes particuliers inconnus. Les collisions d'une clé de concession
ne sont pas des duplicatas de bail : plusieurs avantages peuvent avoir le même code et la même période.
On les conserve, sans jointure multiplicative ni reconstruction arbitraire du loyer effectif.
""")
    code("""
identity_summary = pd.Series({
    "listing_hUnit_distinct": listings.hUnit.nunique(),
    "listing_property_unit_distinct": listings.drop_duplicates(UNIT_KEY).shape[0],
    "unsafe_site_unit_collision_rows": int(listings.duplicated(["sSite", "sUnitCode"], keep=False).sum()),
    "maximum_links_per_unit": int(leases.groupby(UNIT_KEY).sLink.nunique().max()),
    "maximum_units_per_link": int(leases.groupby("sLink").hUnit.nunique().max()),
    "leading_zero_unit_codes": int(listings.sUnitCode.str.startswith("0").sum()),
    "listing_asof_min": listings.sAsOf.min().date().isoformat(),
    "listing_asof_max": listings.sAsOf.max().date().isoformat(),
})
display(identity_summary.to_frame("value"))
display(listings.groupby(["sState", "sCity", "sBuilding"]).size().rename("apartments").to_frame())
display(leases[["sRenewal", "sConcession"]].apply(pd.Series.value_counts).fillna(0).astype(int))
additional_stability = []
for column in ["sBaths", "sUnitType", "sUnitSubtype", "sLink"]:
    linked = leases.merge(listings[UNIT_KEY + [column]], on=UNIT_KEY, how="left",
                          validate="many_to_one", suffixes=("", "_listing"))
    additional_stability.append({"column": column,
        "unstable_units": int(leases.groupby(UNIT_KEY)[column].nunique().gt(1).sum()),
        "listing_disagreement_rows": int(linked[column].ne(linked[column + "_listing"]).sum())})
display(pd.DataFrame(additional_stability))
display(leases[["sLeaseFrom", "sLeaseTo", "sSignDate", "sTermMonths"]].agg(["min", "max"]))
""")
    markdown("""
## 2. Définition de la cible avant le choix du modèle — phase B

**Cible principale : médiane non pondérée de la croissance annualisée du loyer effectif,
pour les transitions admissibles de baux consécutifs du même appartement commençant dans l'année.**

Pour chaque transition :
`growth_pct = ((current_rent / previous_rent) ** (1 / gap_years) - 1) * 100`

`gap_years = days_between_lease_starts / 365.25`

Une transition, une observation; un appartement peut contribuer plusieurs transitions. On ne mesure
ni le rendement d'un panier permanent de tous les logements, ni la hausse exacte des revenus du portefeuille.
La composition entre appartements comparables peut encore varier d'une année à l'autre : la méthode retire
le changement d'identité à l'intérieur d'une paire, pas tous les changements de population entre années.

Règles : prédécesseur immédiatement précédent; dates de début non ambiguës; prix actuel et précédent
strictement positifs pour **les deux** mesures; intervalle strict `0.5 < gap_years < 2.5`, conforme au starter.
La comparaison contractuel/effectif utilise les mêmes paires. Pas de suppression automatique des extrêmes.
Les premiers baux d'un immeuble récent n'ont pas de prédécesseur. Les petits groupes sont descriptifs;
les prévisions de sous-groupes nécessitent au moins 30 paires par année pour deux années dans la fenêtre
de trois ans, sinon repli explicite vers la référence globale. Ce seuil prudent est fixé, pas optimisé sur les erreurs.
""")
    markdown("""
## 3. Composition des baux — phase C, section 3 du starter

La médiane annuelle de `sRent` est un prix de l'ensemble des baux qui commencent dans l'année.
Sa variation peut provenir de logements différents, de leur taille ou de leur immeuble. On calcule les
effectifs et parts par immeuble, chambres, surface et loyer/pi². La première année observée n'est pas
automatiquement une date officielle d'ouverture. Les consignes indiquent l'ajout de trois immeubles
en 2023–2024; l'historique permet de vérifier l'arrivée des observations, pas la réception des bâtiments.
""")
    code("""
ANALYSIS_START_YEAR, LAST_OBSERVED_YEAR = 2019, 2025
window = leases.loc[leases.year.between(ANALYSIS_START_YEAR, LAST_OBSERVED_YEAR)].copy()
naive = window.groupby("year").agg(leases=("sRent", "size"), median_rent=("sRent", "median"))
naive["growth_pct"] = naive.median_rent.pct_change(fill_method=None) * 100
mix = window.assign(rent_per_sqft=window.sRent / window.sSqft).groupby("year").agg(
    leases=("sRent", "size"), median_sqft=("sSqft", "median"),
    two_plus_bed_share_pct=("sBeds", lambda values: values.ge(2).mean() * 100),
    median_rent_per_sqft=("rent_per_sqft", "median"), buildings=("sBuilding", "nunique"))
building_counts = pd.crosstab(window.year, window.sBuilding)
building_shares = building_counts.div(building_counts.sum(axis=1), axis=0) * 100
bedroom_counts = pd.crosstab(window.year, window.sBeds)
bedroom_shares = bedroom_counts.div(bedroom_counts.sum(axis=1), axis=0) * 100
display(naive.round(3))
display(mix.round(3))
display(building_counts)
display(building_shares.round(2))
display(bedroom_counts)
display(bedroom_shares.round(2))
display(leases.groupby("sBuilding").year.min().rename("first_observed_year").to_frame())

figure, axes = plt.subplots(1, 2, figsize=(14, 6))
building_shares.plot.bar(stacked=True, ax=axes[0], colormap="tab20", width=0.8)
axes[0].set(title="Composition par immeuble", xlabel="Année du début de bail", ylabel="Part des baux (%)")
axes[0].legend(title="Immeuble", fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=3)
bedroom_shares.plot.bar(stacked=True, ax=axes[1], colormap="Set2", width=0.8)
axes[1].set(title="Composition par nombre de chambres", xlabel="Année du début de bail", ylabel="Part des baux (%)")
axes[1].legend(title="Chambres", fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=4)
figure.tight_layout()
plt.show()

figure, axes = plt.subplots(1, 2, figsize=(12, 4))
mix.median_sqft.plot(marker="o", ax=axes[0], color=COLORS["contractual"])
axes[0].set(title="Surface médiane des baux", xlabel="Année", ylabel="Superficie (pi²)")
mix.median_rent_per_sqft.plot(marker="o", ax=axes[1], color=COLORS["effective"])
axes[1].set(title="Loyer contractuel par superficie", xlabel="Année", ylabel="Médiane ($ / pi² / mois)")
figure.tight_layout()
plt.show()
""")
    markdown("""
## 4. Comparer chaque appartement à lui-même — phase D

On trie sur la clé sûre et le début de bail, puis on décale d'une ligne les dates et **les deux prix**
dans chaque appartement. Les paires sont créées avant toute séparation renouvellement/relocation.
Des débuts identiques avec des valeurs contradictoires arrêtent le calcul; une suppression des doublons
exacts est comptabilisée. Les exclusions sont mutuellement exclusives et leur total doit égaler les entrées.

La fonction ci-dessous est la même implémentation que celle testée dans `equinoxe.py`.
Les valeurs limites, la longueur de l'année et les noms de colonnes sont configurés au chargement.
""")
    code(inspect.getsource(equinoxe.consecutive_pairs))
    code("""
def same_unit_growth(df, price_col="sRent", min_gap=MIN_GAP_YEARS, max_gap=MAX_GAP_YEARS):
    pairs_result, accounting_result, excluded_result = consecutive_pairs(df, min_gap, max_gap)
    return pairs_result.assign(growth_pct=pairs_result[price_col + "_growth"])

pairs, pair_accounting, excluded = consecutive_pairs(leases)
display(pd.Series(pair_accounting).to_frame("count"))
display(pd.Series({"distinct_paired_apartments": pairs.groupby(UNIT_KEY).ngroups,
                   "extract_apartments": listings.hUnit.nunique(),
                   "paired_apartment_share_pct": pairs.hUnit.nunique() / listings.hUnit.nunique() * 100}).to_frame("value"))
annual_growth = pairs.groupby("year").agg(pairs=("hUnit", "size"),
    apartments=("hUnit", "nunique"), contractual_pct=("sRent_growth", "median"),
    effective_pct=("sRentEffective_growth", "median"))
display(annual_growth.round(4))
display(excluded.groupby(["sRenewal", "gap_years"]).size().rename("excluded_transitions").to_frame())

comparison = naive[["growth_pct"]].rename(columns={"growth_pct": "naive_contractual"}).join(
    annual_growth[["contractual_pct", "effective_pct"]])
figure, axis = plt.subplots()
for column, label, color, style in [
    ("naive_contractual", "Médianes annuelles : composition variable", COLORS["naive"], "--"),
    ("contractual_pct", "Même appartement : contractuel", COLORS["contractual"], "-"),
    ("effective_pct", "Même appartement : effectif", COLORS["effective"], "-"),
]:
    axis.plot(comparison.index, comparison[column], marker="o", linestyle=style, color=color, label=label)
axis.axhline(0, color="grey", linewidth=0.8)
axis.set(title="Effet de composition et croissance à unité constante", xlabel="Année du nouveau bail", ylabel="Croissance (%)")
axis.legend(fontsize=9)
figure.tight_layout()
plt.show()
display(Markdown(f"En 2023, la médiane annuelle augmente de **{naive.loc[2023, 'growth_pct']:.2f} %**, "
    f"contre **{annual_growth.loc[2023, 'contractual_pct']:.2f} %** à appartement constant en contractuel "
    f"et **{annual_growth.loc[2023, 'effective_pct']:.2f} %** en effectif. "
    "Une part accrue de baux d'immeubles plus chers peut augmenter la médiane globale sans hausse équivalente pour un logement donné. "
    "La différence entre ces statistiques ne constitue pas une décomposition causale exacte."))
""")
    markdown("""
### Sensibilité aux baux d'environ six mois

Les 62 exclusions courtes sont espacées de 182 jours : `182 / 365.25 ≈ 0.4983`, juste sous le seuil
du starter. Elles comprennent des renouvellements et des relocations, sans doublon exact démontré.
On conserve la cible stricte pour la comparaison officielle, puis on calcule une sensibilité descriptive
avec un seuil de 0.49. Cette variante n'est pas choisie pour améliorer le backtest et n'est pas mélangée
au résultat principal. L'annualisation d'une très courte transition amplifierait le bruit, ce qui motive le filtre.
""")
    code("""
SIX_MONTH_SENSITIVITY_MIN_GAP = 0.49
sensitivity_pairs, sensitivity_accounting, unused_excluded = consecutive_pairs(leases, min_gap=SIX_MONTH_SENSITIVITY_MIN_GAP)
sensitivity = annual_growth[["pairs", "effective_pct"]].rename(columns={"pairs": "strict_pairs", "effective_pct": "strict_effective_pct"}).join(
    sensitivity_pairs.groupby("year").agg(including_six_month_pairs=("hUnit", "size"),
        including_six_month_effective_pct=("sRentEffective_growth", "median")))
sensitivity["difference_pp"] = sensitivity.including_six_month_effective_pct - sensitivity.strict_effective_pct
display(sensitivity.round(4))
""")
    markdown("""
## 5. Concessions : prix contractuel et prix effectif — phase E

`sRentEffective` est notre mesure initiale, **sans la présenter comme une collecte de cash vérifiée**.
Le rabais de chaque bail est `100 × (1 - effectif / contractuel)`. Sa médiane diffère de la différence
entre les deux médianes de prix : on calcule les deux pour éviter une confusion.

PromoPay est un avantage promotionnel ponctuel, souvent d'un mois, de l'ordre d'un mois de loyer.
On ne soustrait pas son montant chaque mois du bail. Les codes sont tronqués et de casse variable :
`freerent` = loyer gratuit; `freepark` = stationnement; `freelock` = casier; `freeappl` = électroménagers;
`Indem` = indemnité; `Referenc` = référencement; `Freeothe` = divers; `PromoPay` = promotion.
La durée renseignée de 12 mois pour d'autres codes ne suffit pas à prouver que chaque montant est mensuel.

La table n'a pas de clé explicite de bail. On analyse ses montants/durées séparément, sans les attribuer
automatiquement à chaque bail de l'unité. Pas de reconstruction ni de réconciliation monétaire prétendument
exacte : cela risquerait les doubles comptes avec le loyer effectif fourni et les jointures plusieurs-à-plusieurs.
""")
    code("""
lease_discounts = leases.assign(discount_pct=(1 - leases.sRentEffective / leases.sRent) * 100,
                                discount_cad=leases.sRent - leases.sRentEffective)
discount_year = lease_discounts.groupby("year").agg(leases=("sRent", "size"),
    concession_share_pct=("sConcession", lambda values: values.mean() * 100),
    median_contractual=("sRent", "median"), median_effective=("sRentEffective", "median"),
    median_per_lease_discount_pct=("discount_pct", "median"), median_discount_cad=("discount_cad", "median"))
discount_year["ratio_of_medians_discount_pct"] = (1 - discount_year.median_effective / discount_year.median_contractual) * 100
display(discount_year.round(3))
display(lease_discounts.groupby(["year", "sBuilding"]).agg(leases=("sRent", "size"),
    concession_share_pct=("sConcession", lambda values: values.mean() * 100),
    median_discount_pct=("discount_pct", "median")).round(3))
display(lease_discounts.groupby(["year", "sRenewal"]).agg(leases=("sRent", "size"),
    concession_share_pct=("sConcession", lambda values: values.mean() * 100),
    median_discount_pct=("discount_pct", "median")).round(3))
concession_types = concessions.groupby("sChargeCode").agg(records=("sAmount", "size"),
    median_amount_cad=("sAmount", "median"), median_months=("sMonths", "median"),
    min_months=("sMonths", "min"), max_months=("sMonths", "max"))
display(concession_types.round(2))
display(concessions.loc[concessions.sChargeCode.eq("PromoPay")].groupby("sMonths").size().rename("PromoPay_records").to_frame())
display(concessions.assign(year=concessions.sDateFrom.dt.year).groupby(["year", "sBuilding"]).agg(
    concession_records=("sAmount", "size"), median_signed_amount_cad=("sAmount", "median")).round(2))
display(pd.Series({"negative_amount_records": int(concessions.sAmount.lt(0).sum()),
    "concession_end_dates_after_2025": int(concessions.sDateTo.gt(pd.Timestamp("2025-12-31")).sum()),
    "flag_zero_but_discount_positive": int((lease_discounts.sConcession.eq(0) & lease_discounts.discount_pct.gt(0)).sum()),
    "flag_one_but_discount_zero": int((lease_discounts.sConcession.eq(1) & lease_discounts.discount_pct.eq(0)).sum())}).to_frame("count"))

figure, axes = plt.subplots(1, 2, figsize=(12, 4.8))
for column, color, label in [("contractual_pct", COLORS["contractual"], "Contractuel"),
                             ("effective_pct", COLORS["effective"], "Effectif")]:
    axes[0].plot(annual_growth.index, annual_growth[column], marker="o", color=color, label=label)
axes[0].set(title="Croissance sur les mêmes paires", xlabel="Année", ylabel="Médiane annualisée (%)")
axes[0].legend()
axes[1].plot(discount_year.index, discount_year.median_per_lease_discount_pct, marker="o", color=COLORS["effective"])
axes[1].set(title="Rabais effectif par bail", xlabel="Année", ylabel="Rabais médian (%)")
figure.tight_layout()
plt.show()
display(Markdown(f"En 2025 : **{annual_growth.loc[2025, 'contractual_pct']:.2f} % contractuel** et "
    f"**{annual_growth.loc[2025, 'effective_pct']:.2f} % effectif**. "
    "La divergence est compatible avec des avantages plus importants : un prix au bail plus élevé ne garantit pas le même gain net. "
    "Ces agrégats seuls ne permettent pas d'attribuer causalement toute la différence aux concessions."))
""")
    markdown("""
## 6. Renouvellements, relocations et loyers affichés — phase F

La classification vient du **nouveau** bail, après appariement. Un locataire qui renouvelle et une
unité relouée ne répondent pas aux mêmes mécanismes de marché. On affiche nombres de paires et
croissances par année/type/province. Les faibles effectifs ne donnent pas un taux représentatif à eux seuls.

L'historique des prix affichés est irrégulier : ni panel mensuel complet ni loyer signé. Aucun mois manquant
n'est remplacé par zéro. Le dernier prix affiché connu à chaque cutoff peut être ancien; sa staleness
est calculée en jours depuis le premier jour du mois renseigné. La date de publication CRM du relevé
n'est pas fournie : disponibilité au mois indiqué est une hypothèse de diagnostic, pas un prédicteur utilisé.
Les prix courants des listings sont exclus des modèles et des backtests.
""")
    code("""
type_growth = pairs.groupby(["year", "sRenewal"]).agg(pairs=("hUnit", "size"),
    contractual_pct=("sRent_growth", "median"), effective_pct=("sRentEffective_growth", "median"))
province_type_growth = pairs.groupby(["year", "sState", "sRenewal"]).agg(pairs=("hUnit", "size"),
    contractual_pct=("sRent_growth", "median"), effective_pct=("sRentEffective_growth", "median"))
display(type_growth.round(4))
display(province_type_growth.round(4))
figure, axis = plt.subplots()
for renewal, label, color in [(1, "Renouvellement", COLORS["contractual"]), (0, "Relocation", COLORS["effective"])]:
    selected = type_growth.xs(renewal, level="sRenewal")
    axis.plot(selected.index, selected.effective_pct, marker="o", color=color, label=label)
    for year, row in selected.loc[selected.index >= 2021].iterrows():
        axis.annotate(f"n={int(row.pairs)}", (year, row.effective_pct), xytext=(0, 7), textcoords="offset points", fontsize=8)
axis.set(title="Croissance effective selon le nouveau bail", xlabel="Année", ylabel="Médiane annualisée (%)")
axis.legend()
figure.tight_layout()
plt.show()

asking_counts = asking.groupby(UNIT_KEY).size()
display(pd.Series({"observations": len(asking), "apartments": len(asking_counts),
    "mean_observations_per_apartment": asking_counts.mean(), "maximum_observations": asking_counts.max(),
    "first_month": asking.date.min().strftime("%Y-%m"), "last_month": asking.date.max().strftime("%Y-%m")}).to_frame("value"))
asking_cutoffs = []
for cutoff_year in [2022, 2023, 2024, 2025]:
    snapshot = latest_asking(asking, pd.Timestamp(cutoff_year, 12, 31))
    asking_cutoffs.append({"cutoff_year": cutoff_year, "units_with_prior_asking": len(snapshot),
        "median_age_days": snapshot.age_days.median(), "p90_age_days": snapshot.age_days.quantile(0.9),
        "older_than_one_year_share_pct": snapshot.age_days.gt(DAYS_PER_YEAR).mean() * 100})
display(pd.DataFrame(asking_cutoffs).round(2))
""")
    markdown("""
## 7. Information publique datée et cadre provincial — phase G

Les valeurs publiques transcrites sont chargées depuis `docs/public_signals.json`. Chaque ligne comporte
géographie, variable, unité, période et date de publication. La bibliographie détaillée donne les URL,
éditeurs, date de consultation (2026-10-03), limites et usages. Ce tableau est un fichier public versionné,
donc l'exécution ne dépend pas d'un téléchargement en direct.

On simule le 31 décembre 2025. Le rapport SCHL 2025 était publié le 11 décembre; l'IPC de décembre
2025 ne l'était que le 19 janvier 2026 et est exclu. Le rapport SCHL 2023 publié le 31 janvier 2024
n'était pas disponible pour prévoir 2024 au 31 décembre 2023. Les séries historiques complètes par
vintage ne sont pas assemblées : **les backtests utilisent les données internes seules**, sans coefficient
extérieur prétendument validé. Les statistiques extérieures sont intégrées comme contexte et diagnostics datés.

La SCHL observe un marché qui se détend : inoccupation 2025 de 2.9 % à Montréal et 3.0 % à Ottawa.
Les loyers moyens deux chambres ($1 346 et $1 926) et leur croissance (7.2 % et 3.4 %) ne sont pas notre
médiane de transitions annualisées, et ne mesurent pas identiquement les concessions. L'IPC loyers de
septembre 2025 distingue Québec (9.6 %) et Ontario (3.5 %); ces lectures provinciales sont volontairement
datées, pas présentées comme les plus récentes. L'IPC loyers national ralentit à 4.7 % en novembre.
Ces signaux peuvent coexister avec une progression effective plus modérée dans l'extrait.

**Ontario :** la ligne directrice 2026 de 2.1 %, annoncée le 30 juin 2025, comporte notamment une exemption
pour la première occupation résidentielle après le 15 novembre 2018 et ne plafonne pas le prix d'une unité
vacante lors de la nouvelle location. Les premières observations de The Met sont récentes, mais ne prouvent
pas sa première occupation légale. Son assujettissement exact reste à vérifier; aucun plafonnement automatique.

**Québec :** les calculs TAL sont conditionnels, pas un plafond universel. Les immeubles construits/changés
d'affectation depuis cinq ans ou moins peuvent relever de restrictions à la fixation, selon la section F
et les conditions du bail, avec exigences supplémentaires pour certains bâtiments/baux après février 2024.
La réforme annoncée le 17 décembre 2025 utilise notamment une moyenne de l'IPC **général** sur trois ans
pour les avis concernés dès 2026. L'IPC général n'est pas l'IPC loyers. Le taux numérique publié en janvier
2026 n'entre pas dans notre information. Dates officielles, avis, charges et section F sont absents : impossible
d'en déduire une hausse légalement admissible par appartement. Les pages TAL actuelles servent à vérifier
les conditions, pas à fabriquer un vintage historique.
""")
    code("""
external = pd.DataFrame(json.loads((ROOT / "docs" / "public_signals.json").read_text(encoding="utf-8")))
external_at_cutoff = available_external(external, "2025-12-31")
display(external_at_cutoff)
display(pd.DataFrame([{"forecast_year": year, "external_rows_available": len(available_external(external, pd.Timestamp(year - 1, 12, 31)))}
                      for year in [2023, 2024, 2025, 2026]]))
""")
    markdown("""
## 8. Trois méthodes prédéclarées, une logique temporelle — phases H et I

1. **Année précédente** : médiane globale observée en année précédente.
2. **Moyenne récente** : moyenne arithmétique des médianes globales des trois années précédentes.
   On donne un poids égal aux années, pas aux nombres de baux. Trois ans limitent la dépendance à un seul
   millésime sans extrapoler loin dans un régime ancien. Si moins d'années existent, le diagnostic le montre;
   sans aucune paire récente, le calcul s'arrête.
3. **Distribution segmentée** : un seul essai d'amélioration, par province et type. Dans les groupes
   suffisamment documentés (30 paires/an dans au moins deux années), on donne un poids égal aux
   distributions annuelles, puis les parts des groupes viennent des paires de l'année précédente seulement.
   On calcule la médiane du mélange pondéré de **toutes ces valeurs**, pas la moyenne des médianes de groupes.
   Un groupe récent insuffisant reçoit la référence globale. Un groupe absent à la coupure ne reçoit pas un
   poids futur inventé; s'il apparaît en 2026, cette hypothèse de composition peut échouer.

Toutes prédisent la **même cible observée non pondérée**. La pondération du candidat est une hypothèse sur
la distribution future, pas un changement de cible en indice à composition fixe. Pas de recherche massive
d'hyperparamètres, de XGBoost ou de coefficients externes arbitraires.

Pour prévoir l'année Y : on retient les baux dont début **et signature** sont au plus tard le 31 décembre Y−1,
puis on construit leurs paires. Un bail signé avant la coupure mais commençant après est exclu par choix
conservateur. Les prix affichés sont filtrés au même cutoff pour les diagnostics seulement. Les sources publiques
sont filtrées sur la publication, ce qui conserve à juste titre une règle future déjà annoncée.
""")
    code(inspect.getsource(equinoxe.forecast))
    markdown("""
### Comparer prévision et réalisation sans changer d'agrégat

Le calcul de réalisation utilise les baux connus à la fin de Y, construit les prédécesseurs sur tout
l'historique admissible, puis sélectionne les transitions débutant en Y. Le bail antérieur peut donc venir
d'une année précédente. L'erreur signée est `prévision - observation`; l'erreur absolue et la MAE sont
en **points de pourcentage**, pas une « précision de classification ».
""")
    code(inspect.getsource(equinoxe.evaluate))
    code("""
DEVELOPMENT_YEARS = (2023, 2024, 2025)
development_rows = []
for method in METHODS:
    for year in DEVELOPMENT_YEARS:
        detail = evaluate(leases, year, method=method, asking=asking, external=external)
        development_rows.append({key: detail[key] for key in ["method", "target_year", "prediction_pct", "observed_pct",
            "error_pp", "absolute_error_pp", "training_leases", "training_pairs", "observed_pairs", "observed_units",
            "available_external_rows"]})
development = pd.DataFrame(development_rows)
method_scores = development.groupby("method").absolute_error_pp.mean().rename("mae_pp").sort_values().to_frame()
display(development.round(4))
display(method_scores.round(4))
""")
    markdown("""
### Choix du modèle et limites de la validation

On retient **la moyenne récente** pour la prévision centrale. Le gain du mélange segmenté est faible
sur seulement trois années; il ajoute des seuils et une hypothèse de stabilité des parts. Cette comparaison
ne suffit pas à conclure qu'il généralise mieux. Le choix privilégie une méthode facile à reproduire et
à expliquer, tout en conservant les résultats du candidat. Les seuils et la fenêtre n'ont pas été ajustés
pour chercher le meilleur score.

Ces trois années servent à comparer et expliquer les méthodes : **backtests de développement**, pas
ensemble indépendant de test. Les prévisions individuelles respectent le cutoff, mais notre décision de
méthode intervient après examen des trois résultats. L'extrait actuel ne fournit pas de versions anciennes
du CRM; on suppose que les données historiques n'ont pas été révisées depuis. Les résultats futurs peuvent
être différents, notamment pour les immeubles récents et les changements de politique de concessions.
""")
    code("""
SELECTED_METHOD = "recent_mean"
forecast_diagnostics = {}

def estimate_2026(leases, asking, external=None, method=SELECTED_METHOD):
    detail = forecast(leases, 2026, method=method, asking=asking, external=external)
    forecast_diagnostics.clear()
    forecast_diagnostics.update(detail)
    return float(detail["prediction_pct"])

def backtest(leases, target_year, method=SELECTED_METHOD, asking=None, external=None):
    return evaluate(leases, target_year, method=method, asking=asking, external=external)

selected_validation = pd.DataFrame([
    {key: value for key, value in backtest(leases, year, asking=asking, external=external).items()
     if key in ["target_year", "cutoff", "prediction_pct", "observed_pct", "error_pp", "absolute_error_pp", "observed_pairs", "observed_units"]}
    for year in DEVELOPMENT_YEARS
])
display(selected_validation.round(4))
selected_mae = float(selected_validation.absolute_error_pp.mean())
display(Markdown(f"MAE de développement du modèle retenu : **{selected_mae:.3f} points de pourcentage**."))
figure, axis = plt.subplots()
axis.plot(selected_validation.target_year, selected_validation.observed_pct, "o-", color=COLORS["effective"], label="Cible observée")
axis.plot(selected_validation.target_year, selected_validation.prediction_pct, "s--", color=COLORS["contractual"], label="Prévision à la coupure")
axis.set(title="Backtests de développement : moyenne récente", xlabel="Année prédite", ylabel="Croissance effective annualisée (%)", xticks=DEVELOPMENT_YEARS)
axis.legend()
figure.tight_layout()
plt.show()
""")
    markdown("""
## 9. Prévision 2026 et sous-groupes — phase J

Les prévisions par type/province/immeuble ci-dessous utilisent la même idée de moyenne des médianes
annuelles, avec seuil de soutien et repli explicite. Elles sont des diagnostics distincts; leur moyenne
pondérée n'est pas la médiane globale et ne sert pas à la reconstituer. Westpark, à histoire courte,
peut recevoir un repli : ce n'est pas une validation spécifique de cet immeuble. Aucun poids de
composition 2026 ni prix futur n'est utilisé.
""")
    code(inspect.getsource(equinoxe.group_forecasts))
    code(r"""
effective_forecast = estimate_2026(leases, asking, external)
contractual_forecast = forecast(leases, 2026, method=SELECTED_METHOD, price_col="sRent")["prediction_pct"]
type_forecast = group_forecasts(leases, 2026, ["sRenewal"])
province_forecast = group_forecasts(leases, 2026, ["sState", "sRenewal"])
building_forecast = group_forecasts(leases, 2026, ["sBuilding"])
for grouping, result in [(["sRenewal"], type_forecast), (["sState", "sRenewal"], province_forecast), (["sBuilding"], building_forecast)]:
    contractual_groups = group_forecasts(leases, 2026, grouping, price_col="sRent").rename(columns={"prediction_pct": "contractual_prediction_pct"})
    joined = result.merge(contractual_groups[grouping + ["contractual_prediction_pct"]], on=grouping, validate="one_to_one")
    display(joined.round(4))
display(pd.Series({key: value for key, value in forecast_diagnostics.items()
    if key in ["target_year", "cutoff", "method", "prediction_pct", "training_leases", "training_pairs", "available_external_rows",
               "asking_units_at_cutoff", "asking_median_age_days"]}).to_frame("diagnostic"))
display(Markdown(f"### Prévision centrale 2026 : **{effective_forecast:.2f} %**\n\n"
    "Cible : médiane non pondérée de la croissance annualisée du loyer effectif sur les transitions admissibles "
    f"de baux consécutifs du même appartement commençant en 2026. Comparaison contractuelle : **{contractual_forecast:.2f} %**. "
    "Il s'agit d'une prévision de variation de prix des transitions représentées, pas d'une hausse exacte du revenu total."))

recent_realizations = annual_growth.loc[2026 - HISTORY_YEARS:2025, "effective_pct"]
scenarios = pd.DataFrame([
    {"scenario": "Bas : retour au régime récent le plus faible", "effective_growth_pct": recent_realizations.min()},
    {"scenario": "Central : moyenne des trois régimes récents", "effective_growth_pct": effective_forecast},
    {"scenario": "Haut : persistance du régime récent le plus fort", "effective_growth_pct": recent_realizations.max()},
])
display(scenarios.round(3))
six_month_recent_mean = float(sensitivity.loc[2023:2025, "including_six_month_effective_pct"].mean())
display(Markdown(f"Sensibilité descriptive aux intervalles de 182 jours : référence trois ans **{six_month_recent_mean:.2f} %**, "
    f"soit **{six_month_recent_mean - effective_forecast:+.3f} point** par rapport à la cible stricte."))
""")
    markdown("""
### Hypothèses et incertitude

Les scénarios bas/haut réutilisent le minimum/maximum des médianes 2023–2025, comme hypothèses de
retour/persistance d'un régime observé. **Ce n'est ni un intervalle de confiance ni une borne probable garantie.**
Un choc ou une nouvelle politique de concessions peut sortir de cette plage. La détente SCHL et le
ralentissement national de l'IPC loyers soutiennent un scénario prudent; les signaux Québec/Ontario restent
différents, d'où les diagnostics provinciaux. On n'a pas converti ces signaux en points de croissance ajoutés.

Limites : seulement trois années de validation; échantillon de transitions différent chaque année;
immeubles récents peu documentés; prix affichés rares et parfois anciens; sens exact des concessions
non réconcilié avec les cash-flows; dossiers juridiques et dates officielles absents; pas de vrai test indépendant;
pas de versions historiques du CRM. Les prédictions de sous-groupes n'ont pas chacune une validation dédiée.
Le modèle est une règle statistique recalculée, sans paramètres entraînés à sauvegarder : aucun fichier
de modèle n'est requis pour le reproduire.
""")
    markdown("""
## 10. Vérifications, confidentialité et références — phase de remise

Les tests du dépôt utilisent uniquement des fixtures synthétiques : clé sûre, annualisation, seuils stricts,
comptabilité des exclusions, cardinalité, cutoffs, groupes rares, agrégation et cohérence des fonctions.
Le script d'exécution lance un kernel neuf, vérifie les sorties et conserve une copie exécutée locale ignorée.
Le notebook partagé est sans sorties par défaut; avec `--share-aggregates`, seules les sorties agrégées
vérifiées sont transférées dans ce notebook. Aucun identifiant d'appartement, adresse, lien CRM ou table
de lignes privées ne doit être exporté. Les graphiques utilisent uniquement des agrégats annuels/de groupes.

**Références :** consulter la liste complète ci-dessous et `docs/REFERENCES.md`. Les sources originales
du défi sont citées mais jamais redistribuées. Assistance IA : OpenAI Codex / ChatGPT, 2026-10-03,
pour recherche publique, code, explications, tests synthétiques et documentation. Calculs vérifiés localement;
aucune donnée CRM envoyée à la recherche web. L'équipe reste responsable de la revue avant remise.
""")
    code("""
display(Markdown((ROOT / "docs" / "REFERENCES.md").read_text(encoding="utf-8")))
assert isinstance(effective_forecast, float)
assert forecast_diagnostics["cutoff"] == "2025-12-31"
assert selected_validation.observed_pairs.gt(0).all()
assert np.isclose(effective_forecast, np.mean(list(forecast_diagnostics["annual_history"].values())))
assert pairs["gap_years"].gt(MIN_GAP_YEARS).all() and pairs["gap_years"].lt(MAX_GAP_YEARS).all()
assert not pairs.duplicated(UNIT_KEY + ["sLeaseFrom"]).any()
assert audit_checks.loc[audit_checks.check.isin(["unmatched_unit_keys", "hUnit_key_disagreement"]), "count"].eq(0).all()
print("Vérifications finales réussies : calculs locaux, cutoffs et cible cohérents.")
""")
    nbformat.validate(notebook)
    destination = ROOT / "notebooks" / "equinoxe_analysis.ipynb"
    destination.parent.mkdir(exist_ok=True)
    nbformat.write(notebook, destination)
    print(f"Built {len(notebook.cells)} cells from {len(original.cells)} starter cells; outputs cleared.")


if __name__ == "__main__":
    build()
