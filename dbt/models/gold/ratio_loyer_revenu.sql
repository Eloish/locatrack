{{ config(materialized='table') }}

WITH loyers AS (
    SELECT
        fl.observatory_b,
        fl.id_agglomeration,
        fl.annee,
        fl.type_habitat,
        fl.nombre_pieces,
        AVG(fl.loyer_median_m2)      AS loyer_median_m2,
        AVG(fl.loyer_mensuel_median) AS loyer_mensuel_median
    FROM silver.fact_loyers fl
    WHERE fl.loyer_median_m2 IS NOT NULL
    GROUP BY fl.observatory_b, fl.id_agglomeration, fl.annee, fl.type_habitat, fl.nombre_pieces
),

revenus_par_obs AS (
    SELECT
        bco.observatory_b,
        AVG(fr.revenu_median)  AS revenu_median_moyen,
        AVG(fr.revenu_mensuel) AS revenu_mensuel_moyen
    FROM silver.fact_revenus fr
    JOIN silver.bridge_commune_observatoire bco ON fr.code_insee = bco.code_insee
    WHERE fr.revenu_median IS NOT NULL
      AND fr.annee = (SELECT MAX(annee) FROM silver.fact_revenus)
    GROUP BY bco.observatory_b
)

SELECT
    l.observatory_b,
    da.nom_agglomeration,
    l.annee,
    l.type_habitat,
    l.nombre_pieces,
    ROUND(l.loyer_median_m2::numeric, 2)      AS loyer_median_m2,
    ROUND(l.loyer_mensuel_median::numeric, 2) AS loyer_mensuel_median,
    ROUND(r.revenu_median_moyen::numeric, 2)  AS revenu_median_moyen,
    ROUND(r.revenu_mensuel_moyen::numeric, 2) AS revenu_mensuel_moyen,
    ROUND(
        (l.loyer_mensuel_median / NULLIF(r.revenu_mensuel_moyen, 0) * 100)::numeric, 2
    ) AS ratio_tension_pct
FROM loyers l
JOIN silver.dim_agglomeration da ON l.id_agglomeration = da.id_agglomeration
JOIN revenus_par_obs r           ON l.observatory_b = r.observatory_b
