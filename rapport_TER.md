# LocaTrack — Observatoire intelligent du marché locatif français
## Rapport de TER — Master Informatique, parcours SID
**Elodie Ishimwe** — Université Aix-Marseille, année 2025–2026
Encadrant : Jérémy GROS — Data Platform Manager, NAOS

---

## 1. Présentation du sujet

### 1.1 Objectifs généraux

La tension locative est l'un des enjeux sociaux majeurs en France. En 2026, de nombreuses métropoles françaises font face à une pression croissante sur le marché du logement : les loyers augmentent plus vite que les revenus, les transactions immobilières s'accélèrent dans certaines zones, et les ménages modestes se trouvent progressivement exclus des centres urbains.

Pourtant, les données permettant d'analyser cette situation objectivement existent — elles sont publiques, gratuites, et produites par des organismes officiels. Le problème est qu'elles sont **dispersées entre plusieurs sources hétérogènes** : les transactions immobilières (DVF, publiées par la DGFiP), les loyers médians par agglomération (OLL, publiés par les observatoires agréés), et les revenus des ménages par commune (INSEE Filosofi).

LocaTrack se positionne comme un **pipeline de données open source** qui ingère, transforme et analyse ces trois sources pour répondre à une question centrale :

> *Dans quelles villes françaises le rapport loyer / revenu médian est-il le plus défavorable aux locataires, et comment cette tension évolue-t-elle depuis 5 ans ?*

L'objectif final est un dashboard interactif permettant à tout utilisateur — journaliste, chercheur, collectivité locale ou simple citoyen — de visualiser la tension locative sur une carte, de comparer des agglomérations, et de trouver les villes  les plus accessibles selon son profil de revenu.

### 1.2 Analyse du sujet

La tension locative constitue un enjeu majeur pour de nombreux territoires français. Dans les zones les plus attractives, la demande de logements dépasse souvent l'offre disponible, ce qui entraîne une augmentation des loyers et rend l'accès au logement plus difficile pour une partie de la population. Cette situation a des conséquences économiques et sociales importantes, notamment pour les ménages aux revenus modestes qui consacrent une part croissante de leurs ressources au logement.

Bien que de nombreuses données publiques permettent d'étudier ce phénomène, leur exploitation reste complexe. Les informations relatives aux loyers, aux revenus des ménages et aux transactions immobilières sont produites par différents organismes selon des méthodes et des périmètres géographiques distincts. Cette dispersion rend difficile l'obtention d'une vision globale et cohérente de la tension locative à l'échelle nationale.

Le projet LocaTrack cherche à répondre à plusieurs questions essentielles. Quelles sont les communes où la pression locative est la plus forte ? Comment cette pression évolue-t-elle au fil des années ? Quelle est la relation entre les loyers pratiqués et les revenus des ménages ? Existe-t-il des différences significatives entre les territoires français en matière d'accessibilité au logement ? Répondre à ces questions nécessite de croiser et d'analyser des données provenant de sources variées afin de produire des indicateurs fiables et comparables.

La réalisation d'un tel observatoire soulève également plusieurs défis. Il est nécessaire d'intégrer des données hétérogènes, de garantir leur cohérence et de mettre en place des traitements permettant leur rapprochement malgré des niveaux de granularité différents. L'objectif est de transformer ces données brutes en informations exploitables afin de fournir une vision claire et objective de la tension locative en France.

La problématique centrale du projet peut ainsi être formulée de la manière suivante :

**Comment construire un observatoire fiable et reproductible de la tension locative française à partir de sources de données publiques hétérogènes afin de produire des indicateurs pertinents et accessibles à tous les utilisateurs ?**

---

## 2. État de l'art

### 2.1 Les sources et observatoires du marché immobilier

En France, plusieurs organismes produisent des données permettant d'analyser le marché immobilier et locatif. La Direction Générale des Finances Publiques (DGFiP) met à disposition la base des Demandes de Valeurs Foncières (DVF), qui recense l'ensemble des transactions immobilières enregistrées sur le territoire. De son côté, l'INSEE publie de nombreux indicateurs socio-économiques, notamment les revenus médians des ménages à travers la base Filosofi. Les Observatoires Locaux des Loyers (OLL) fournissent quant à eux des informations détaillées sur les loyers pratiqués dans plusieurs agglomérations françaises.

Ces différentes sources constituent une base riche pour l'analyse du logement, mais elles sont publiées séparément et ne proposent pas de vision consolidée de la tension locative.

### 2.2 Les plateformes d'analyse immobilière existantes

Plusieurs acteurs proposent aujourd'hui des outils d'analyse du marché immobilier. Parmi les plus connus figurent :

- SeLoger ;
- Meilleurs Agents ;
- FNAIM ;
- Bien'ici.

Ces plateformes mettent à disposition des cartes de prix, des estimations immobilières et des indicateurs de marché permettant de suivre l'évolution des prix de vente ou des loyers.

Cependant, les méthodologies de calcul utilisées sont souvent propriétaires et peu documentées. De plus, les données exploitées ne sont pas toujours publiques, ce qui limite la reproductibilité des analyses.

### 2.3 Les outils de visualisation territoriale

Des organismes publics proposent également des outils de visualisation de données territoriales, notamment l'INSEE ou les plateformes open data des collectivités locales. Ces outils permettent d'explorer certains indicateurs démographiques, économiques ou immobiliers.

Néanmoins, ils se concentrent généralement sur une seule source de données à la fois et ne permettent pas de croiser facilement les revenus, les loyers et les transactions immobilières dans un même environnement d'analyse.

### 2.4 Limites des solutions existantes

L'analyse des solutions existantes met en évidence plusieurs limites :

- les données sont dispersées entre plusieurs organismes ;
- les indicateurs sont rarement calculés à partir de sources entièrement ouvertes ;
- les méthodologies de calcul sont parfois peu transparentes ;
- les outils existants ne permettent pas toujours de relier les loyers aux revenus des ménages — or c'est précisément ce croisement (le loyer rapporté au revenu du ménage) qui définit la tension locative et constitue l'angle original de LocaTrack ;
- il n'existe pas de solution open source proposant une vision unifiée de la tension locative à partir des données publiques disponibles.

C'est dans cet espace laissé libre que se positionne LocaTrack : un observatoire entièrement open source, reproductible, qui croise les trois sources publiques au niveau de la commune.

---

## 3. Solution proposée

### 3.1 Technologies utilisées

La réalisation de LocaTrack s'appuie sur un ensemble d'outils standards de l'ingénierie des données, choisis pour leur robustesse et leur caractère open source.

**Python** est le langage principal du pipeline. Pandas est utilisé pour les transformations tabulaires, psycopg2 et SQLAlchemy pour la communication avec PostgreSQL. rapidfuzz est utilisé pour le fuzzy matching dans le mapping UU-agglomération.

**PostgreSQL** est la base de données relationnelle centrale. Elle stocke les couches Silver et Gold. Le schéma en étoile (fait + dimensions) est adapté aux requêtes analytiques du dashboard.

**dbt (data build tool)** est utilisé pour les transformations Gold. dbt permet d'écrire les modèles analytiques en SQL pur, avec versioning, documentation et tests intégrés. Chaque modèle Gold est un fichier `.sql` versionné sur Git.

**Luigi** (Spotify) est le framework d'orchestration du pipeline. Il définit les dépendances entre tâches (StagingDVF doit précéder SilverFactTransactions, etc.) et garantit l'idempotence via une table `pipeline_run_log` en base.

**Great Expectations** est utilisé pour la qualité des données. Des suites de tests vérifient la complétude, les types, les plages de valeurs et les contraintes d'unicité sur les couches Bronze et Silver.

**Streamlit** est le framework de visualisation. Il permet de construire rapidement des dashboards interactifs en Python, avec des composants natifs (cartes, graphiques, tableaux, filtres).

**Docker et Docker Compose** assurent le packaging et la reproductibilité. L'ensemble du projet (pipeline + base de données + dashboard) se lance en deux commandes.

### 3.2 Architecture générale

LocaTrack implémente une architecture **médaillon en quatre couches** :

```
Bronze → Staging → Silver → Gold → Dashboard
```

**Bronze** : fichiers sources bruts (CSV, Parquet, XLS) stockés localement dans `data/bronze/`. Aucune transformation. C'est la source de vérité immuable.

**Staging** : chargement brut des fichiers en base PostgreSQL, sans transformation métier. Les tables staging reflètent fidèlement la structure des fichiers sources.

**Silver** : nettoyage, typage, déduplication et modélisation en schéma en étoile. C'est ici que les filtres métier sont appliqués (exclusion des mutations non-ventes, des prix aberrants, des surfaces nulles) et que les tables de référence sont construites (dim_commune, dim_agglomeration, bridge_commune_observatoire).

**Gold** : indicateurs analytiques calculés en SQL via dbt. Chaque modèle Gold est une table prête à être consommée par le dashboard.

### 3.3 Schéma en étoile Silver

Le schéma en étoile de la couche Silver s'organise autour de trois tables de faits :

- `fact_transactions` : une ligne par transaction DVF nettoyée, avec prix_m2, code_insee, annee, type_local
- `fact_loyers` : une ligne par (observatoire, agglomération, type_habitat, nombre_pièces, année), avec loyer_médian
- `fact_revenus` : une ligne par (code_insee, année), avec revenu_médian, D1, D9

Et quatre tables de dimension :

- `dim_commune` : code INSEE, nom, département, région, unité urbaine (UU2020)
- `dim_agglomeration` : identifiant OLL, nom
- `bridge_commune_observatoire` : correspondance commune ↔ observatoire OLL
- `mapping_uu_agglomeration` : correspondance UU2020 ↔ agglomération OLL (construite automatiquement)

### 3.4 Le mapping UU-agglomération

C'est le problème technique central du projet.

**Qu'est-ce qu'une UU2020 ?** L'unité urbaine 2020 (UU2020) est un découpage géographique défini par l'INSEE : c'est une commune ou un ensemble de communes formant une zone bâtie continue (sans coupure de plus de 200 mètres entre constructions) et comptant au moins 2 000 habitants. Chaque commune française est rattachée à une seule UU2020, identifiée par un code (ex : `00759` pour l'unité urbaine de Marseille-Aix-en-Provence). C'est le référentiel géographique de l'INSEE pour désigner une « agglomération » au sens statistique.

**Le problème.** Les loyers OLL sont publiés par agglomération au sens des observatoires (ex : « Agglomération d'Arles »), qui ne coïncide pas avec le découpage UU2020 de l'INSEE. Il faut donc établir automatiquement la correspondance entre les deux référentiels. La solution adoptée combine trois mécanismes.

**Étape 1 — Vote des communes (présélection des UU candidates).** Pour chaque observatoire, on récupère toutes ses communes via `bridge_commune_observatoire`, et on relève le code UU2020 de chacune (porté par `dim_commune`). On compte combien de communes appartiennent à chaque UU2020 : on obtient ainsi la liste des UU présentes dans le périmètre de l'observatoire, classées par nombre de communes. Ce vote ne dépend que de l'observatoire : toutes les agglomérations rattachées à un même observatoire partagent donc la même liste d'UU candidates.

**Étape 2 — Fuzzy match (sélection de la bonne UU pour chaque agglomération).** C'est cette étape qui distingue les agglomérations entre elles. Pour chaque agglomération, on compare son nom (ex : « Agglomération d'Arles ») à celui de chaque UU candidate via la mesure `partial_ratio` de rapidfuzz, après normalisation (suppression des préfixes génériques : « Agglomération de », « Communauté d'agglomération », « Eurométropole de », etc.). L'UU dont le nom ressemble le plus à celui de l'agglomération est retenue.

**Étape 3 — Fallback national.** Quand aucune UU candidate du vote n'atteint un score de 70 %, on élargit la recherche à la liste complète des 2 568 unités urbaines françaises. C'est le cas d'Arles : les communes de l'observatoire B1300 appartiennent majoritairement à l'UU Marseille-Aix-en-Provence, si bien que l'UU d'Arles n'apparaît jamais parmi les candidats du vote. Le fallback recherche directement « arles » dans l'ensemble des UU et retrouve la bonne correspondance (score 100 %). Le résultat du fallback n'est retenu que s'il est strictement meilleur que celui du vote.

Ce mécanisme produit 80 correspondances avec un score fuzzy moyen de 94,7 % et aucun cas restant sous le seuil de 70 %. Si de nouveaux cas limites apparaissaient (nouvelle agglomération mal nommée, par exemple), un mécanisme d'overrides manuels pourrait être réintroduit pour forcer la correspondance sans modifier l'algorithme.

### 3.5 Indicateurs Gold

**ratio_loyer_revenu** : loyer médian mensuel OLL / revenu mensuel moyen Filosofi des communes de l'agglomération × 100. Représente le pourcentage du revenu qu'un ménage médian consacre au loyer.

**prix_m2_par_ville** : prix médian au m² par commune, type de bien et année, avec évolution annuelle (LAG) et moyenne glissante sur 3 ans.

**dynamisme_marche** : score de tension composite 0–100, calculé à partir de trois signaux :
- Ratio loyer/revenu (40% du poids quand disponible)
- Hausse des prix au m² capée à 20% (35%)
- Volume de transactions en percentile national (25%)

Quand les données OLL ne sont pas disponibles pour une commune (hors périmètre des observatoires), les poids sont redistribués : hausse prix 60%, volume 40%.

**inegalites** : taux d'effort par profil de revenu (modeste D1, médian, aisé D9) et évolution des loyers et revenus dans le temps.

### 3.6 Dashboard Streamlit

Le dashboard comprend trois pages :

**Carte** : carte choroplèthe interactive des communes françaises, avec choix de l'indicateur (score de tension, prix au m², hausse des prix, évolution), filtres par année, type de bien et région.

**Comparaison** : graphiques d'évolution temporelle des loyers médians, taux d'effort et inégalités pour une agglomération sélectionnée.

**Recherche** : module "trouver la ville la plus accessible" — l'utilisateur entre son revenu mensuel, son type de logement, le nombre de pièces et un département, et obtient toutes les communes triées par taux d'effort.

---

## 4. Expérimentations et résultats

### 4.1 Données chargées

| Source | Volume | Période |
|--------|--------|---------|
| DVF | ~4,8 millions de transactions après nettoyage (4 788 385) | 2021–2025 |
| OLL (loyers) | 6 481 lignes (agglomération × type × pièces × année) | 2014–2025 |
| INSEE Filosofi (revenus) | 157 094 lignes (commune × année) | 2017–2021 |
| Communes françaises | 35 485 communes | — |
| Unités urbaines (UU2020) | 2 568 UU | — |

### 4.2 Résultats du mapping

- **80 agglomérations OLL** mappées sur leur UU2020 correspondante
- **Score fuzzy moyen : 94,7%**
- **0 cas ambigus** (score < 70%) après introduction du fallback national
- **47 correspondances** établies directement par le vote, **33 par le fallback national** (dont Arles, Brest, Toulon, Draguignan, Sète, Mâcon, Montbéliard, Alès)

### 4.3 Résultats Gold

- **~11 200 communes** analysées dans le score de tension pour l'année 2025 (communes avec ≥ 10 transactions DVF), soit 14 502 observations en distinguant le type de bien (appartement / maison)
- **Score de tension moyen national : 23,5 / 100** (sur les données 2025)
- **302 communes** classées "très tendues" (score ≥ 75) en 2025
- **77 333 lignes** dans prix_m2_par_ville (commune × type × année)
- **5 827 lignes** dans ratio_loyer_revenu (agglomération × type × pièces × année)

### 4.4 Validation qualité

Les tests Great Expectations vérifient sur chaque couche :
- Bronze : présence des colonnes obligatoires, types, absence de valeurs nulles sur les clés
- Silver : unicité des clés primaires, plages de valeurs (prix_m2 entre 500 et 13 731 €, surfaces > 0), intégrité référentielle

### 4.5 Reproductibilité

Le pipeline complet (ingestion → staging → silver → gold → dashboard) se lance en trois commandes :

```bash
docker compose build
docker compose --profile pipeline run pipeline python pipeline.py
docker compose up dashboard
```

Testé sur Windows 11 avec Docker Desktop. Temps de traitement complet : environ 45 minutes (dont ~35 min pour le chargement DVF 5 ans).

---

## 5. Conclusion

### 5.1 Bilan du projet

LocaTrack répond aux objectifs fixés dans le sujet : pipeline d'ingestion multi-sources, architecture Bronze/Silver/Gold, indicateurs analytiques, dashboard interactif, qualité des données et packaging Docker. Les trois sources de données publiques sont intégrées et exploitables.

Le résultat le plus significatif est la construction automatique du mapping UU-agglomération, qui résout un problème de réconciliation d'entités entre deux nomenclatures indépendantes sans recours à une correspondance manuelle exhaustive. Ce mécanisme (vote + fuzzy match + fallback national) produit un score de confiance moyen de 94,7% sur 80 agglomérations.

### 5.2 Difficultés rencontrées

**Le mapping géographique** a été la difficulté principale. Le problème n'était pas visible au début : le pipeline tournait sans erreur, mais les résultats dans le dashboard étaient silencieusement faux (Arles apparaissait dans l'agglomération de Marseille, des communes du département 13 manquaient). Déboguer ce type d'erreur "silencieuse" a nécessité de remonter la chaîne de transformation étape par étape.

**Les contraintes Docker** ont posé des problèmes inattendus : crash PostgreSQL sur les requêtes DVF lourdes (OOM), buffer des prints Python non flushé dans les containers, images non reconstruites après modification du code. Ces problèmes ont ralenti le cycle debug-test.

**L'hétérogénéité des fichiers sources** : les fichiers XLS des zonages utilisent un encodage cp1252 non standard, les fichiers DVF varient en structure selon les années, les fichiers OLL sont distribués dans des formats différents selon les observatoires.

### 5.3 Ce que j'aurais fait différemment

Avec l'expérience de ce projet, j'aurais commencé par cartographier précisément les référentiels géographiques avant d'écrire une seule ligne de code de transformation. La plupart des bugs rencontrés avaient pour source une hypothèse incorrecte sur la correspondance entre deux tables de référence.

J'aurais également mis en place les tests Great Expectations dès la couche Silver, et non à la fin du projet. Un test qui vérifie que le nombre d'agglomérations mappées est cohérent aurait détecté le bug du mapping en quelques minutes plutôt qu'en plusieurs sessions de débogage.

### 5.4 Limites et perspectives

| Limite | Piste d'amélioration |
|--------|----------------------|
| Données Filosofi bloquées à 2021 | Mettre à jour quand l'INSEE publie les millésimes 2022-2023 |
| Pas de mise à jour incrémentielle DVF | Implémenter une détection de changement par hash de fichier |
| Score de tension = proxy sans données offre/demande réelles | Intégrer un flux d'annonces immobilières (délai de vente, nb biens disponibles) |
| DOM-TOM : données de moindre qualité | Ajouter un avertissement sur la carte pour les départements 971-976 |
| Mapping UU-agglomération par fuzzy match | Enrichir progressivement le fichier d'overrides manuels pour les cas limites |

---

## 6. Annexes

### Annexe A — Schéma de la base de données Silver

```
staging.communes_geo     staging.uu2020
         ↓                      ↓
silver.dim_commune ←────────────┘
         ↓
silver.bridge_commune_observatoire
         ↓
silver.mapping_uu_agglomeration ←── silver.dim_agglomeration ←── silver.fact_loyers
         ↓
silver.fact_revenus          silver.fact_transactions
         ↓                           ↓
         └──────────── gold ──────────┘
```

### Annexe B — Commandes utiles

```bash
# Relancer uniquement le mapping UU-agglomération
docker compose --profile pipeline run pipeline python transform/silver_ref_geo.py

# Relancer uniquement les modèles gold
docker compose --profile pipeline run pipeline dbt run --project-dir dbt --profiles-dir dbt

# Vider le run_log pour forcer le rechargement d'une couche
docker compose --profile pipeline run pipeline python scripts/reset_run_log.py silver

# Voir les logs du pipeline
docker compose --profile pipeline logs pipeline
```

### Annexe C — Composition du score de tension

| Signal | Poids (avec OLL) | Poids (sans OLL) | Normalisation |
|--------|-----------------|-----------------|---------------|
| Ratio loyer/revenu | 40% | 0% | Valeur brute, capée à 100 |
| Hausse des prix au m² | 35% | 60% | Capée à 20% → ramenée sur 100 |
| Volume de transactions | 25% | 40% | Percentile national |

---

## 7. Bibliographie

- **DGFiP** — Demandes de Valeurs Foncières (DVF). https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres/

- **DHUP / OLAP** — Résultats nationaux des observatoires locaux des loyers. https://www.data.gouv.fr/fr/datasets/resultats-nationaux-des-observatoires-locaux-des-loyers/

- **INSEE** — Filosofi : Structure et distribution des revenus, inégalité des niveaux de vie. https://www.insee.fr/fr/statistiques/serie/001694056

- **INSEE** — Unités urbaines 2020. https://www.insee.fr/fr/information/4802589

- **dbt Labs** — dbt Core Documentation. https://docs.getdbt.com/docs/introduction

- **Spotify / Luigi** — Luigi : a Python module that helps you build complex pipelines. https://github.com/spotify/luigi

- **Great Expectations** — Documentation officielle. https://docs.greatexpectations.io/

- **Streamlit** — Documentation officielle. https://docs.streamlit.io/

- **rapidfuzz** — Rapid fuzzy string matching. https://github.com/maxbachmann/RapidFuzz

- **FNAIM** — Baromètre national des loyers. https://www.fnaim.fr/

- **Charmes, E., Hellier, E.** (2021). *Les métropoles et leurs périphéries*. La Documentation française. (contexte sur la tension locative en France)
