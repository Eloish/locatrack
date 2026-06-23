{{ config(materialized='table') }}

WITH base AS (
    SELECT
        ft.code_insee,
        dc.nom_commune,
        dc.code_departement,
        ft.annee,
        ft.type_local,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ft.prix_m2) AS prix_m2_median,
        ROUND(AVG(ft.prix_m2)::numeric, 2)                      AS prix_m2_moyen,
        COUNT(*)                                                 AS nb_transactions,
        ROUND(AVG(ft.surface_bati)::numeric, 2)                 AS surface_moyenne
    FROM silver.fact_transactions ft
    JOIN silver.dim_commune dc ON ft.code_insee = dc.code_insee
    WHERE ft.prix_m2 IS NOT NULL
      AND ft.type_local IS NOT NULL
    GROUP BY ft.code_insee, dc.nom_commune, dc.code_departement, ft.annee, ft.type_local
    HAVING COUNT(*) >= 10
),

avec_lag AS (
    SELECT
        *,
        -- Prix année précédente
        LAG(prix_m2_median) OVER (
            PARTITION BY code_insee, type_local
            ORDER BY annee
        ) AS prix_m2_annee_precedente,

        -- Évolution annuelle en %
        ROUND(
            (
                (
                    prix_m2_median
                    - LAG(prix_m2_median) OVER (
                        PARTITION BY code_insee, type_local ORDER BY annee
                    )
                ) / NULLIF(
                    LAG(prix_m2_median) OVER (
                        PARTITION BY code_insee, type_local ORDER BY annee
                    ), 0
                ) * 100
            )::numeric, 2
        ) AS evolution_annuelle_pct,

        -- Moving average sur 3 ans
        ROUND(
            AVG(prix_m2_median::numeric) OVER (
                PARTITION BY code_insee, type_local
                ORDER BY annee
                ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
            ), 2
        ) AS moving_avg_3ans
    FROM base
)

SELECT
    code_insee,
    nom_commune,
    code_departement,
    annee,
    type_local,
    ROUND(prix_m2_median::numeric, 2)   AS prix_m2_median,
    prix_m2_moyen,
    nb_transactions,
    surface_moyenne,
    ROUND(prix_m2_annee_precedente::numeric, 2) AS prix_m2_annee_precedente,
    evolution_annuelle_pct,
    moving_avg_3ans
FROM avec_lag
