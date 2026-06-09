{{ config (materialized='table') }}

WITH
    loyers
    AS
    (
        SELECT
            observatory_b,
            annee,
            type_habitat,
            nombre_pieces,
            AVG(loyer_median_m2)      AS loyer_median_m2,
            AVG(loyer_mensuel_median) AS loyer_mensuel_median
        FROM silver.fact_loyers
        WHERE loyer_median_m2 IS NOT NULL
        GROUP BY observatory_b, annee, type_habitat, nombre_pieces
    ),

    communes
    AS
    (
        SELECT
            bco.observatory_b,
            bco.code_insee,
            dc.nom_commune
        FROM silver.bridge_commune_observatoire bco
            JOIN silver.dim_commune dc ON bco.code_insee = dc.code_insee
    ),

    revenus
    AS
    (
        SELECT
            fr.code_insee,
            fr.revenu_median,
            fr.revenu_mensuel
        FROM silver.fact_revenus fr
        WHERE fr.revenu_median IS NOT NULL
            AND fr.annee = 2021
    ),

    revenus_par_obs
    AS
    (
        SELECT
            c.observatory_b,
            AVG(r.revenu_median)  AS revenu_median_moyen,
            AVG(r.revenu_mensuel) AS revenu_mensuel_moyen
        FROM communes c
            JOIN revenus r ON c.code_insee = r.code_insee
        GROUP BY c.observatory_b
    )

SELECT
    l.observatory_b,
    l.annee,
    l.type_habitat,
    l.nombre_pieces,
    ROUND(l.loyer_median_m2::numeric, 2)      AS loyer_median_m2,
    ROUND(l.loyer_mensuel_median::numeric, 2) AS loyer_mensuel_median,
    ROUND(r.revenu_median_moyen::numeric, 2)  AS revenu_median_moyen,
    ROUND(r.revenu_mensuel_moyen::numeric, 2) AS revenu_mensuel_moyen,
    ROUND(
        (l.loyer_mensuel_median / NULLIF(r.revenu_mensuel_moyen, 0) * 100)
::numeric,
        2
    ) AS ratio_tension_pct
FROM loyers l
JOIN revenus_par_obs r ON l.observatory_b = r.observatory_b