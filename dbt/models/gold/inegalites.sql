{{ config(materialized='table') }}

-- Classement des villes par accessibilité locative
-- Répond à la question : "quelle ville est la plus accessible pour un revenu de X€/mois ?"

WITH revenus_obs AS (
    SELECT
        bco.observatory_b,
        fr.annee,
        PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY fr.revenu_median) AS revenu_d1,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fr.revenu_median) AS revenu_median,
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
        type_habitat,
        AVG(loyer_mensuel_median) AS loyer_mensuel_moyen
    FROM silver.fact_loyers
    WHERE loyer_mensuel_median IS NOT NULL
      AND type_habitat IS NOT NULL
    GROUP BY observatory_b, annee, type_habitat
),

agglo AS (
    SELECT
        boa.observatory_b,
        da.nom_agglomeration
    FROM silver.bridge_observatoire_agglomeration boa
    JOIN silver.dim_agglomeration da ON boa.id_agglomeration = da.id_agglomeration
),

accessibilite AS (
    SELECT
        r.observatory_b,
        a.nom_agglomeration,
        r.annee,
        l.type_habitat,

        ROUND(r.revenu_d1::numeric, 2)            AS revenu_d1,
        ROUND(r.revenu_median::numeric, 2)         AS revenu_median,
        ROUND(r.revenu_d9::numeric, 2)            AS revenu_d9,
        ROUND((r.revenu_d9 / NULLIF(r.revenu_d1, 0))::numeric, 2) AS ratio_d9_d1,
        ROUND(r.revenu_median_moyen::numeric, 2)  AS revenu_median_moyen,
        ROUND(l.loyer_mensuel_moyen::numeric, 2)  AS loyer_mensuel_moyen,

        -- Taux d'effort par profil (loyer / revenu mensuel)
        ROUND((l.loyer_mensuel_moyen / NULLIF(r.revenu_d1 / 12, 0) * 100)::numeric, 1)
            AS taux_effort_modeste_pct,
        ROUND((l.loyer_mensuel_moyen / NULLIF(r.revenu_median / 12, 0) * 100)::numeric, 1)
            AS taux_effort_median_pct,
        ROUND((l.loyer_mensuel_moyen / NULLIF(r.revenu_d9 / 12, 0) * 100)::numeric, 1)
            AS taux_effort_aise_pct,

        -- Part du loyer annuel sur le revenu annuel
        ROUND((l.loyer_mensuel_moyen * 12 / NULLIF(r.revenu_median_moyen, 0) * 100)::numeric, 2)
            AS part_loyer_annuel_pct,

        -- Évolution revenus avec LAG
        LAG(r.revenu_median_moyen) OVER (
            PARTITION BY r.observatory_b ORDER BY r.annee
        ) AS revenu_annee_precedente,
        ROUND(
            ((r.revenu_median_moyen - LAG(r.revenu_median_moyen) OVER (
                PARTITION BY r.observatory_b ORDER BY r.annee
            )) / NULLIF(LAG(r.revenu_median_moyen) OVER (
                PARTITION BY r.observatory_b ORDER BY r.annee
            ), 0) * 100)::numeric, 2
        ) AS evolution_revenu_pct,

        -- Évolution loyers avec LAG
        LAG(l.loyer_mensuel_moyen) OVER (
            PARTITION BY r.observatory_b, l.type_habitat ORDER BY r.annee
        ) AS loyer_annee_precedente,
        ROUND(
            ((l.loyer_mensuel_moyen - LAG(l.loyer_mensuel_moyen) OVER (
                PARTITION BY r.observatory_b, l.type_habitat ORDER BY r.annee
            )) / NULLIF(LAG(l.loyer_mensuel_moyen) OVER (
                PARTITION BY r.observatory_b, l.type_habitat ORDER BY r.annee
            ), 0) * 100)::numeric, 2
        ) AS evolution_loyer_pct

    FROM revenus_obs r
    JOIN loyers_obs l   ON r.observatory_b = l.observatory_b AND r.annee = l.annee
    LEFT JOIN agglo a   ON r.observatory_b = a.observatory_b
)

SELECT
    observatory_b,
    nom_agglomeration,
    annee,
    type_habitat,
    revenu_d1,
    revenu_median,
    revenu_d9,
    ratio_d9_d1,
    revenu_median_moyen,
    loyer_mensuel_moyen,
    taux_effort_modeste_pct,
    taux_effort_median_pct,
    taux_effort_aise_pct,
    part_loyer_annuel_pct,
    revenu_annee_precedente,
    evolution_revenu_pct,
    loyer_annee_precedente,
    evolution_loyer_pct,

    -- Classement accessibilité pour profil modeste (D1)
    RANK() OVER (
        PARTITION BY annee, type_habitat
        ORDER BY taux_effort_modeste_pct ASC
    ) AS rang_accessibilite_modeste,

    -- Classement accessibilité pour profil médian
    RANK() OVER (
        PARTITION BY annee, type_habitat
        ORDER BY taux_effort_median_pct ASC
    ) AS rang_accessibilite_median,

    -- Classement accessibilité pour profil aisé (D9)
    RANK() OVER (
        PARTITION BY annee, type_habitat
        ORDER BY taux_effort_aise_pct ASC
    ) AS rang_accessibilite_aise

FROM accessibilite
