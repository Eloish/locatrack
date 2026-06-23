# Documentation des données — LocaTrack

## Sources de données

### 1. DVF — Demandes de Valeurs Foncières (DGFiP)
- **Ce que c'est** : registre officiel de toutes les ventes immobilières en France, publié par la Direction Générale des Finances Publiques.
- **Granularité** : une ligne par lot vendu, par année (2021 à 2025).
- **Colonnes clés** : date de mutation, type de local, valeur foncière, surface bâtie, code commune, nombre de pièces.
- **Limites connues** : quand une copropriété est vendue en bloc, chaque lot génère une ligne avec le même prix total répété → doublons à dédupliquer.

### 2. OLL — Observatoires Locaux des Loyers
- **Ce que c'est** : enquêtes annuelles sur les loyers du parc privé, menées par des observatoires agréés par le gouvernement.
- **Granularité** : loyer médian par agglomération, type de logement (Appartement / Maison), nombre de pièces, année.
- **Colonnes clés** : loyer médian mensuel, loyer médian au m², identifiant agglomération.
- **Limites connues** : toutes les agglomérations ne publient pas chaque année → données manquantes pour certaines années.

### 3. INSEE Filosofi — Revenus des ménages
- **Ce que c'est** : données fiscales sur les revenus des ménages par commune, publiées par l'INSEE.
- **Granularité** : revenu médian, D1 (10% les plus modestes), D9 (10% les plus aisés), par commune et par année.
- **Colonnes clés** : revenu médian annuel, revenu mensuel, code INSEE commune.

### 4. Référentiels géographiques (INSEE)
- **dim_commune** : liste des communes françaises avec code INSEE, département, région, unité urbaine (UU2020).
- **dim_agglomeration** : liste des agglomérations OLL avec leur identifiant et nom.
- **bridge_commune_observatoire** : table de correspondance commune ↔ observatoire OLL.
- **mapping_uu_agglomeration** : correspondance unité urbaine ↔ agglomération OLL.

---

## Pipeline : de la source aux indicateurs

```
Sources brutes
    ↓ staging  (chargement brut, aucune transformation)
    ↓ silver   (nettoyage technique)
    ↓ gold     (calcul des indicateurs métier)
```

---

## Couche Silver — Nettoyage technique

### silver.fact_transactions (depuis DVF)

**Filtres appliqués et pourquoi :**

| Filtre | Pourquoi |
|--------|----------|
| `Nature_mutation = 'Vente'` | Exclut les donations, successions, expropriations — on ne veut que les ventes libres |
| `Type_local IN ('Maison', 'Appartement')` | Exclut les locaux commerciaux, dépendances, terrains — non comparables au résidentiel |
| `Surface_reelle_bati > 0` | Supprime les lignes sans surface (impossible de calculer un prix au m²) |
| `Valeur_fonciere > 0` | Supprime les ventes à 0 € (erreurs de saisie) |
| `prix_m2 entre 500 et 13 731 €` | Borne inférieure : en dessous de 500 €/m² c'est une erreur. Borne supérieure : 13 731 € = upper fence IQR calculé sur l'ensemble des données (valeur statistique, pas arbitraire) |
| `surface_bati >= 1 m²` | Supprime les surfaces aberrantes |

**Dédoublonnage DVF :**
Quand une copropriété est vendue en bloc, DVF génère N lignes identiques (une par lot) avec le même prix répété. On supprime les doublons sur la combinaison `(code_insee, annee, type_local, valeur_fonciere, surface_bati, nombre_pieces)`.

**Colonnes produites :** code_insee, annee, type_local, valeur_fonciere, surface_bati, surface_terrain, nombre_pieces, prix_m2, nature_culture.

---

### silver.fact_loyers (depuis OLL)

Chargement des loyers médians par agglomération, type de logement et nombre de pièces. Aucun filtre métier — nettoyage technique uniquement (valeurs NULL écartées).

---

### silver.fact_revenus (depuis Filosofi)

Chargement des revenus médians par commune et par année. Aucun filtre métier.

---

## Couche Gold — Indicateurs métier

### gold.prix_m2_par_ville

**Objectif :** prix au m² agrégé par commune, type de bien et année.

**Filtres :**
- `HAVING COUNT(*) >= 10` : au moins 10 transactions pour qu'un agrégat soit représentatif.

**Indicateurs calculés :**

| Indicateur | Formule | Pourquoi |
|------------|---------|----------|
| `prix_m2_median` | `PERCENTILE_CONT(0.5)` sur prix_m2 | La médiane est robuste aux ventes atypiques (VEFA, biens de luxe), contrairement à la moyenne |
| `prix_m2_moyen` | `AVG(prix_m2)` | Complément pour comparaison |
| `evolution_annuelle_pct` | `(médiane N - médiane N-1) / médiane N-1 × 100` | Variation d'une année à l'autre |
| `moving_avg_3ans` | Moyenne glissante sur 3 ans (ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) | Lisse les variations annuelles pour révéler la tendance de fond |

---

### gold.dynamisme_marche

**Objectif :** score de tension locative composite par commune, type de bien et année.

**Filtres :**
- `HAVING COUNT(*) >= 10` : minimum 10 transactions pour qu'une commune apparaisse.
- Pour `hausse_prix_pct` uniquement : les deux années comparées doivent avoir **≥ 25 transactions** (seuil = médiane nationale observée). En dessous, la médiane d'une année à l'autre est trop instable pour être fiable.

**Indicateurs calculés :**

| Indicateur | Formule | Pourquoi |
|------------|---------|----------|
| `prix_m2_moyen` | `PERCENTILE_CONT(0.5)` — médiane | Robuste aux outliers |
| `hausse_prix_pct` | `(médiane N - médiane N-1) / médiane N-1 × 100` | NULL si gap d'année > 1, si prix précédent < 500 €/m², ou si une des deux années a < 25 transactions |
| `score_tension` | Moyenne pondérée de 3 signaux (voir ci-dessous) | Indicateur synthétique 0–100 |

**Composition du score de tension :**

| Signal | Poids | Ce que ça mesure |
|--------|-------|-----------------|
| Ratio loyer / revenu | 40% | Pression financière sur les ménages |
| Hausse des prix au m² (capée à 20%) | 35% | Dynamisme / spéculation du marché |
| Volume de transactions (percentile) | 25% | Activité du marché |

**Lecture du score :**
- 0–25 : Détendu
- 25–50 : Modéré
- 50–75 : Tendu
- 75–100 : Très tendu

---

### gold.ratio_loyer_revenu

**Objectif :** ratio loyer / revenu par agglomération, type de logement et nombre de pièces.

**Indicateurs calculés :**

| Indicateur | Formule |
|------------|---------|
| `loyer_mensuel_median` | Médiane des loyers mensuels OLL |
| `revenu_mensuel_moyen` | Moyenne des revenus mensuels Filosofi des communes de l'agglomération |
| `ratio_tension_pct` | `loyer_mensuel_median / revenu_mensuel_moyen × 100` |

> **Note :** le revenu utilisé est fixé à la dernière année disponible dans Filosofi (données fiscales publiées avec 2 ans de décalage). Les loyers sont mis à jour chaque année par l'OLL.

---

### gold.inegalites

**Objectif :** taux d'effort par profil de revenu et évolution des loyers / revenus dans le temps.

**Indicateurs calculés :**

| Indicateur | Formule | Profil |
|------------|---------|--------|
| `taux_effort_modeste_pct` | `loyer_mensuel / (revenu_D1 / 12) × 100` | 10% les plus modestes |
| `taux_effort_median_pct` | `loyer_mensuel / (revenu_median / 12) × 100` | Ménage médian |
| `taux_effort_aise_pct` | `loyer_mensuel / (revenu_D9 / 12) × 100` | 10% les plus aisés |
| `evolution_loyer_pct` | `(loyer N - loyer N-1) / loyer N-1 × 100` | NULL si gap d'année > 1 |
| `evolution_revenu_pct` | `(revenu N - revenu N-1) / revenu N-1 × 100` | NULL si gap d'année > 1 |

> **Seuil d'alerte :** un taux d'effort > 33% signifie qu'un ménage dépense plus d'un tiers de son revenu pour se loger — seuil conventionnel utilisé par les politiques du logement en France.

---

## Choix méthodologiques importants

| Choix | Justification |
|-------|---------------|
| Médiane plutôt que moyenne pour les prix | La moyenne est tirée vers le haut par quelques biens très chers (VEFA, biens de luxe). La médiane représente mieux le prix "typique". |
| Seuil 500–13 731 €/m² en silver | 500 €/m² = plancher réaliste. 13 731 €/m² = upper fence IQR calculé sur l'ensemble des transactions. Ces bornes sont des décisions de qualité de données, pas des filtres métier. |
| HAVING >= 10 en gold | En dessous de 10 transactions, un agrégat n'est pas statistiquement représentatif d'un marché. |
| Seuil 25 transactions pour la hausse | La hausse compare deux médianes : avec peu de ventes, une seule transaction atypique peut faire varier la médiane de plusieurs centaines de pourcents. 25 = médiane nationale du nb de transactions, justifiable statistiquement. |
| LAG NULL si gap > 1 an | Si une commune n'a pas de données en 2022 (moins de 10 ventes, filtrée), le LAG comparerait 2021 à 2023 comme si c'était une variation annuelle — ce serait trompeur. |
| Poids adaptatifs dans score de tension | Quand une commune n'a pas de données OLL (hors périmètre des observatoires), le signal ratio loyer/revenu est absent. Plutôt que d'imputer une valeur par défaut (50%), on redistribue son poids sur les deux autres signaux : hausse prix 60%, volume 40%. |
| Filtre `annee >= 2020` dans dynamisme_marche | Le modèle travaille sur 5 ans de données DVF. Charger toutes les années en une seule requête avec window functions provoque un crash mémoire dans l'environnement Docker. Le filtre est un compromis technique sans impact métier (on conserve bien 5 ans). |

---

## Mapping UU ↔ Agglomération — Comment ça marche

Le problème central : les données de loyers (OLL) sont organisées par **agglomération** (ex : "Agglomération d'Arles"), mais les communes sont géocodées par **unité urbaine INSEE** (ex : UU2020 "Arles", code 00552). Ces deux référentiels ne parlent pas le même langage — il faut construire une table de correspondance.

### Étape 1 — Le vote des communes

Pour chaque paire (observatoire, agglomération), on regarde toutes les communes qui appartiennent à cet observatoire via `bridge_commune_observatoire`. Chaque commune a un code UU2020 dans `dim_commune`. On compte combien de communes "votent" pour chaque UU2020 — la logique : si 80% des communes d'une agglomération sont dans l'UU "Marseille-Aix-en-Provence", c'est probablement la bonne UU.

```
Observatoire B1300 + Agglomération de Marseille
  → communes du bridge : Marseille, Aix, Aubagne, ...
  → leurs UU2020 : 00759 (Marseille-Aix), 00759, 00759, ...
  → vote : UU 00759 gagne avec 95 communes
```

### Étape 2 — Le fuzzy match

Le vote donne des **candidats UU**, mais pas forcément le bon. On valide en comparant le nom de l'agglomération OLL avec le nom de l'UU candidate via un fuzzy match (`partial_ratio` de rapidfuzz).

Exemple : `"Agglomération d'Arles"` → normalisation → `"arles"` → comparé à `"Arles"` → score 100%.

La normalisation supprime les préfixes génériques : "Agglomération de", "Communauté d'agglomération", "Eurométropole de", etc.

### Étape 3 — Le fallback national

Quand le vote ne produit pas de bons candidats (score fuzzy < 70%), on cherche dans **toutes les UU de France**. C'est le cas d'Arles : les communes de B1300 sont majoritairement dans l'UU Marseille-Aix-en-Provence, donc le vote ne propose jamais l'UU Arles comme candidat. Le fallback cherche directement "arles" dans les 2 000 UU françaises et trouve l'UU correcte.

### Limites du mapping

- **Agglomérations rurales** : certaines agglomérations OLL couvrent des zones diffuses sans UU INSEE équivalente (ex : "Haut Var", "Communes hors TLV"). Le fuzzy match peut trouver une UU dont le nom ressemble mais qui géographiquement ne correspond pas.
- **DOM-TOM** : l'observatoire B9740 (La Réunion) regroupe plusieurs agglomérations sur une petite île — les UU INSEE ne correspondent pas bien aux découpages OLL locaux.
- **Changements de nomenclature** : "Agglomération de Marseille" (avant 2016) et "Agglomération d'Aix-Marseille" (après 2016) sont deux entrées distinctes dans les données OLL, toutes deux mappées sur la même UU INSEE.

---

## Limites du projet

### Limites techniques

| Limite | Impact | Piste d'amélioration |
|--------|--------|----------------------|
| Données Filosofi bloquées à 2021 | Le ratio loyer/revenu utilise des revenus de 2021 même pour les loyers 2024 | Mettre à jour quand l'INSEE publie les données 2022-2023 |
| Pas de mise à jour incrémentielle DVF | Recharger DVF recharge toutes les années | Implémenter un filtre par année dans `run_log` |
| Mapping UU-agglomération par fuzzy match | Quelques erreurs résiduelles possibles (score 70-80%) | Enrichir le fichier d'overrides manuels |
| Score de tension = proxy | Pas de vraies données offre/demande (délai de vente, nb biens disponibles) | Intégrer SeLoger API ou données DVF sur les biens retirés |
| DOM-TOM peu fiables | Données DVF et OLL de moindre qualité en outre-mer | Ajouter un filtre ou un avertissement sur la carte |

### Ce qui n'est pas dans le périmètre

- **Données de location** : DVF ne contient que les ventes, pas les mises en location.
- **Évolution en temps réel** : les données sont annuelles, pas en temps réel.
- **Prédiction** : le projet est descriptif, pas prédictif.
