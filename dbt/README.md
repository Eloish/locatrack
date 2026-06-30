# dbt — Couche Gold de LocaTrack

Ce projet dbt construit les **modèles Gold** de LocaTrack à partir des tables Silver
de la base PostgreSQL. Chaque modèle est une table analytique prête à être consommée
par le dashboard Streamlit.

## Modèles (`models/gold/`)

| Modèle | Description |
|--------|-------------|
| `prix_m2_par_ville` | Prix médian au m² par commune, type de bien et année, avec évolution annuelle (LAG) et moyenne glissante sur 3 ans |
| `ratio_loyer_revenu` | Ratio loyer médian / revenu mensuel moyen par agglomération, type de logement et nombre de pièces |
| `dynamisme_marche` | Score de tension locative composite (0–100) par commune, à partir de 3 signaux (ratio loyer/revenu, hausse des prix, volume de transactions) |
| `inegalites` | Taux d'effort par profil de revenu (modeste D1, médian, aisé D9) et évolution loyers/revenus dans le temps |
| `evolution_tension` | Évolution temporelle du ratio de tension par agglomération |

## Commandes

```bash
# Construire tous les modèles gold
dbt run --project-dir dbt --profiles-dir dbt

# Construire un seul modèle
dbt run --project-dir dbt --profiles-dir dbt --select dynamisme_marche

# Lancer les tests dbt
dbt test --project-dir dbt --profiles-dir dbt
```

En contexte Docker, préfixer par :
`docker compose --profile pipeline run pipeline ...`

La connexion à la base est définie dans `profiles.yml` (cible `dev`, schéma `gold`).
