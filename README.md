# LocaTrack

**LocaTrack** est un outil d'analyse du marché locatif et immobilier français. Il agrège des données publiques (DVF, observatoires des loyers, INSEE Filosofi) dans une base de données structurée et les expose via un dashboard interactif.

---

## Fonctionnalités

- **Carte interactive** — visualisation par commune des prix au m², tensions locatives et hausses de prix
- **Comparaison d'agglomérations** — loyers médians, taux d'effort, score de tension, évolution temporelle
- **Recherche personnalisée** — trouvez les communes accessibles selon votre revenu et vos critères

---

## Prérequis

- [Docker](https://www.docker.com/) et Docker Compose
- Les fichiers de données bronze dans `data/bronze/` (DVF, loyers OLL, INSEE, référentiels géographiques)

---

## Lancement rapide

### Dashboard seul (si la base est déjà peuplée)

```bash
docker compose up postgres dashboard
```

Ouvrir ensuite : **http://localhost:8501**

### Pipeline complet + dashboard

```bash
# 1. Construire les images
docker compose build

# 2. Lancer le pipeline (ingestion → staging → silver → gold)
docker compose --profile pipeline run pipeline python pipeline.py

# 3. Lancer le dashboard
docker compose up dashboard
```

---

## Structure du projet

```
locatrack/
├── ingestion/        # Téléchargement et validation des sources brutes (bronze)
├── staging/          # Chargement des fichiers bronze en base PostgreSQL
├── transform/        # Nettoyage et modélisation silver (schéma en flocon de neige)
├── dbt/              # Modèles gold (indicateurs métier via dbt)
├── dashboard/        # Application Streamlit (accueil + 3 vues)
├── tests/            # Validation qualité Great Expectations
├── utils/            # Connexion DB, config, loader, validators
├── scripts/          # Outils de maintenance (reset run_log, force reload)
├── sql/              # Initialisation des schémas PostgreSQL
├── data/
│   ├── bronze/       # Données sources brutes (non versionnées)
│   └── referentiel/  # Fichiers de référence géographique
├── pipeline.py       # Orchestration Luigi (toutes les étapes)
├── docker-compose.yml
├── Dockerfile.pipeline
├── Dockerfile.dashboard
└── DOCUMENTATION_DONNEES.md  # Documentation complète des données
```

---

## Architecture des données

Le pipeline suit une architecture **médaillon** en 4 couches :

```
Bronze          Staging         Silver              Gold
──────────      ───────────     ──────────────      ──────────────────
Fichiers        Tables raw      Flocon de neige     Indicateurs métier
parquet/csv  →  PostgreSQL   →  nettoyé + validé →  (dbt)
                               GE validé
```

### Sources intégrées

| Source | Contenu | Années |
|--------|---------|--------|
| **DVF** (data.gouv.fr) | Transactions immobilières | 2021–2025 |
| **OLL** (observatoires des loyers) | Loyers médians par agglomération | 2014–2025 |
| **INSEE Filosofi** | Revenus médians par commune | 2017–2021 |
| **Référentiels géo** | Communes, UU2020, départements, régions | — |

---

## Pipeline — commandes utiles

```bash
# Relancer depuis une étape spécifique
docker compose --profile pipeline run pipeline python pipeline.py --from-step staging
docker compose --profile pipeline run pipeline python pipeline.py --from-step silver
docker compose --profile pipeline run pipeline python pipeline.py --from-step gold

# Vider le run_log pour forcer le rechargement
docker compose --profile pipeline run pipeline python scripts/reset_run_log.py          # tout
docker compose --profile pipeline run pipeline python scripts/reset_run_log.py staging  # staging seulement
docker compose --profile pipeline run pipeline python scripts/reset_run_log.py silver   # silver seulement

# Relancer uniquement le mapping UU ↔ agglomération
docker compose --profile pipeline run pipeline python transform/silver_ref_geo.py

# Relancer uniquement les modèles gold (dbt)
docker compose --profile pipeline run pipeline dbt run --project-dir dbt --profiles-dir dbt
```

---

## Documentation des données

La documentation complète des sources, filtres, indicateurs et choix méthodologiques est disponible dans [`DOCUMENTATION_DONNEES.md`](DOCUMENTATION_DONNEES.md).

---

## Auteur

Elodie Ishimwe — Université Aix-Marseille, TER S8 2025–2026
