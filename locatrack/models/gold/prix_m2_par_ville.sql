{{ config(materialized='table') }}

SELECT
    ft.code_insee,
    dc.nom_commune,
    ft.annee,
    ft.type_local,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ft.prix_m2) AS prix_m2_median,
    ROUND(AVG(ft.prix_m2)::numeric, 2)                      AS prix_m2_moyen,
    COUNT(*)                                                 AS nb_transactions,
    ROUND(AVG(ft.surface_bati)::numeric, 2)                 AS surface_moyenne
FROM silver.fact_transactions ft
JOIN silver.dim_commune dc ON ft.code_insee = dc.code_insee
WHERE ft.prix_m2 IS NOT NULL
  AND ft.prix_m2 > 0
  AND ft.type_local IS NOT NULL
GROUP BY
    ft.code_insee,
    dc.nom_commune,
    ft.annee,
    ft.type_local