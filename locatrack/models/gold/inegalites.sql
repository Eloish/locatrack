{{ config(materialized='table') }}

WITH revenus_obs AS (
    SELECT
        bco.observatory_b,
        fr.annee,
        PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY fr.revenu_median) AS revenu_d1,
        PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY fr.revenu_median) AS revenu_d9,
        AVG(fr.revenu_median) AS revenu_median_moyen
    FROM silver.fact_revenus fr
    JOIN silver.bridge_commune_observatoire bco ON fr.code_insee = bco.code_insee
    WHERE fr.revenu_median IS NOT NULL
    GROUP BY bco.observatory_b, fr.annee
),

loyers_obs AS (
    SELECT
        observatory_b,
        annee,
        AVG(loyer_mensuel_median) AS loyer_mensuel_moyen
    FROM silver.fact_loyers
    WHERE loyer_mensuel_median IS NOT NULL
    GROUP BY observatory_b, annee
)

SELECT
    r.observatory_b,
    r.annee,
    ROUND(r.revenu_d1::numeric, 2)          AS revenu_d1,
    ROUND(r.revenu_d9::numeric, 2)          AS revenu_d9,
    ROUND((r.revenu_d9 / NULLIF(r.revenu_d1, 0))::numeric, 2) AS ratio_d9_d1,
    ROUND(r.revenu_median_moyen::numeric, 2) AS revenu_median_moyen,
    ROUND(l.loyer_mensuel_moyen::numeric, 2) AS loyer_mensuel_moyen,
    ROUND(
        (l.loyer_mensuel_moyen * 12 / NULLIF(r.revenu_median_moyen, 0) * 100)::numeric,
        2
    ) AS part_loyer_annuel_pct,
    LAG(r.revenu_median_moyen) OVER (
        PARTITION BY r.observatory_b ORDER BY r.annee
    ) AS revenu_annee_precedente,
    LAG(l.loyer_mensuel_moyen) OVER (
        PARTITION BY r.observatory_b ORDER BY r.annee
    ) AS loyer_annee_precedente,
    ROUND(
        ((r.revenu_median_moyen - LAG(r.revenu_median_moyen) OVER (
            PARTITION BY r.observatory_b ORDER BY r.annee
        )) / NULLIF(LAG(r.revenu_median_moyen) OVER (
            PARTITION BY r.observatory_b ORDER BY r.annee
        ), 0) * 100)::numeric,
        2
    ) AS evolution_revenu_pct,
    ROUND(
        ((l.loyer_mensuel_moyen - LAG(l.loyer_mensuel_moyen) OVER (
            PARTITION BY r.observatory_b ORDER BY r.annee
        )) / NULLIF(LAG(l.loyer_mensuel_moyen) OVER (
            PARTITION BY r.observatory_b ORDER BY r.annee
        ), 0) * 100)::numeric,
        2
    ) AS evolution_loyer_pct
FROM revenus_obs r
JOIN loyers_obs l ON r.observatory_b = l.observatory_b
                 AND r.annee = l.annee