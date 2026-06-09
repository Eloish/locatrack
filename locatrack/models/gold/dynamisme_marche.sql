{{ config(materialized='table') }}

SELECT
    ft.code_insee,
    dc.nom_commune,
    ft.annee,
    ft.type_local,
    COUNT(*)                                AS nb_transactions,
    ROUND(SUM(ft.valeur_fonciere)::numeric, 2) AS volume_total,
    ROUND(AVG(ft.valeur_fonciere)::numeric, 2) AS valeur_moyenne,
    ROUND(AVG(ft.surface_bati)::numeric, 2)    AS surface_moyenne
FROM silver.fact_transactions ft
JOIN silver.dim_commune dc ON ft.code_insee = dc.code_insee
WHERE ft.valeur_fonciere IS NOT NULL
  AND ft.type_local IS NOT NULL
GROUP BY
    ft.code_insee,
    dc.nom_commune,
    ft.annee,
    ft.type_local