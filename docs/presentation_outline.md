# Présentation au jury — Collection Équinoxe, CodeML 2026

Chiffres recalculés depuis les fichiers vérifiés et le notebook exécuté. Utiliser uniquement les graphiques agrégés du notebook : aucun aperçu CRM, identifiant d'appartement ou donnée individuelle dans les diapositives.

## 1. Question et cible — 45 secondes

« Pour 2026, nous prévoyons **2,46 %** : la **médiane non pondérée des variations annualisées de loyer effectif sur les transitions admissibles de baux consécutifs du même appartement commençant en 2026**. »

Comparaison contractuelle : **4,24 %**. Ce n'est pas la hausse exacte du revenu total du portefeuille. L'extrait et ses transitions ne permettent pas de calculer l'occupation ou le rôle total de loyers.

## 2. Pourquoi la médiane annuelle trompe — 60 secondes

Visuels : croissance naïve / même appartement; parts des baux par immeuble; composition par chambres et surface.

- En 2023 : **10,85 %** de variation de médiane contractuelle annuelle, contre **2,29 %** contractuel et **2,02 %** effectif à appartement constant.
- Des observations d'immeubles plus chers changent la composition. La médiane globale peut croître sans hausse équivalente pour un logement donné.
- Première observation ≠ ouverture officielle. La différence entre ces statistiques n'est pas une décomposition causale exacte du mix.

## 3. Appariement et annualisation — 60 secondes

Visuel : formule et comptabilité des exclusions, sans exemple individuel.

- Clé : `sPropCode` + `sUnitCode`, cohérente avec `hUnit`. Site + numéro produit **248 lignes en collision**.
- **4 302 baux = 1 061 premiers baux + 62 intervalles courts exclus + 3 179 paires**, représentant **890 appartements**.
- Règle stricte du starter : 0,5 < années entre débuts < 2,5; prix positifs pour les deux mesures.
- Les 62 intervalles sont de 182 jours, sans duplicata prouvé. Sensibilité les incluant : référence 2026 **2,53 %**, contre **2,46 %** avec la règle stricte.

## 4. Concessions et gain effectif — 60 secondes

Visuels : croissance contractuelle/effective et rabais médian par bail.

- En 2025 : **7,04 %** contractuel versus **3,58 %** effectif sur les mêmes **780 paires**.
- Rabais médian individuel effectif/contractuel : **10,31 %** en 2025.
- **1 494 PromoPay**, dont **1 318 d'un mois** et **176 de deux mois**; montant médian **−1 356,60 $**. Ce montant n'est pas à déduire chaque mois du bail.
- Distinguer stationnement, casier, électroménagers, loyer gratuit, indemnités et référencement. Pas de clé explicite de bail : pas de reconstruction qui double-compte les avantages.
- Le loyer effectif est celui fourni, pas une collecte de cash réconciliée.

## 5. Renouvellements, relocations et provinces — 75 secondes

Visuel : croissance effective par type avec effectifs; tableau provincial du notebook.

| Transitions 2025 | Paires | Contractuel | Effectif |
|---|---:|---:|---:|
| Renouvellements | 473 | 6,41 % | 2,91 % |
| Relocations | 307 | 8,98 % | 5,74 % |

Diagnostics 2026 : **2,17 %** renouvellements, **3,39 %** relocations. Ne pas les additionner ou les moyenner pour reconstituer la médiane globale.

Ontario : ligne directrice conditionnelle 2026 de **2,1 %**, annoncée avant coupure; exemption de première occupation résidentielle après le 15 novembre 2018. Les premières données de The Met ne prouvent pas cette date légale. Aucun plafond automatique.

Québec : fixation TAL selon conditions, avec possibles restrictions des immeubles récents/section F. La réforme annoncée en décembre 2025 est connue; le taux numérique publié en janvier 2026 est exclu. Le taux admissible juridiquement n'est pas notre statistique observée.

## 6. Marché public et backtests — 90 secondes

Sources : SCHL publiée le 11 décembre 2025 (Montréal/Ottawa), IPC loyers Québec/Ontario et communiqué national de novembre, TAL et Ontario. Définitions, URL, périodes et dates dans `docs/REFERENCES.md`.

La SCHL indique une détente des marchés : inoccupation **2,9 % Montréal / 3,0 % Ottawa**. Ces taux ne sont **pas** ceux de JADCO. L'IPC provincial et les moyennes SCHL mesurent autre chose que nos transitions effectives; pas de substitution ou coefficient inventé. Ce contexte soutient la prudence du scénario central.

Modèle retenu : moyenne des trois médianes globales précédentes. Début et signature ≤ coupure; bail pré-signé commençant après exclu. La réalisation conserve un prédécesseur d'une année antérieure. Prix actuels des listings et publications futures exclus.

| Année | Prévision | Observé | Erreur signée | Erreur absolue | Paires observées |
|---|---:|---:|---:|---:|---:|
| 2023 | 3,716 % | 2,019 % | +1,697 pt | 1,697 pt | 416 |
| 2024 | 3,383 % | 1,772 % | +1,611 pt | 1,611 pt | 698 |
| 2025 | 2,792 % | 3,575 % | −0,783 pt | 0,783 pt | 780 |

**MAE : 1,364 point de pourcentage**, contre **1,540** pour l'année précédente. Le candidat par distributions province/type atteint **1,289**, gain de **0,075 point** : trop peu d'années pour justifier ses hypothèses supplémentaires.

Ces années servent au choix et à la présentation : **backtests de développement**, pas test indépendant. Intégration publique contextuelle; ni modèle extérieur ajusté ni panel de vintages historiques complet.

## 7. Prévision 2026 et limites — 75 secondes

| Hypothèse de régime | Croissance effective |
|---|---:|
| Bas : retour au régime récent le plus faible | 1,77 % |
| Central : moyenne des médianes 2023–2025 | **2,46 %** |
| Haut : persistance du régime récent le plus fort | 3,58 % |

Scénarios de régimes historiques, **sans couverture probabiliste garantie**. Un choc peut dépasser cette plage.

Diagnostics par immeuble : Daniel-Johnson **2,69 %**, Le Carlyle **2,62 %**, Lévesque **2,61 %**, Saint-Elzéar **2,41 %**, The Met **2,64 %**. Westpark **2,46 % par repli global**, faute de deux années atteignant 30 paires. Les sous-groupes n'ont pas chacun une validation indépendante.

Limites : peu d'années, histoires courtes, composition changeante, loyers affichés clairsemés (**3,64 observations/appartement** en moyenne, maximum **12**), concessions partiellement interprétées, dossiers juridiques absents, pas de versions historiques CRM. Priorité future : confirmer ces éléments et mesurer 2026 quand disponible.

## Dernière diapositive — reproductibilité et références

Kernel neuf; **10 tests synthétiques réussis**; intégrité des originaux revérifiée; sorties agrégées examinées; données hors dépôt. Pas de modèle appris à sérialiser : règle recalculée.

Sources du défi et références publiques dans le notebook et `docs/REFERENCES.md`. Assistance IA : OpenAI Codex / ChatGPT, 2026-10-03, pour code, recherche publique, explications, vérifications et documentation. Calculs locaux; aucune ligne CRM dans les recherches web.
