{{ config(materialized='table') }}

-- Score de tension locative composite
-- Combine 3 signaux : volume de transactions, évolution du prix, ratio loyer/revenu
-- Score final normalisé entre 0 (détendu) et 100 (très tendu)
-- Limité aux 5 dernières années (≥ 2020) pour limiter la charge mémoire sur les données DVF

WITH transactions AS (
    SELECT
        ft.code_insee,
        dc.nom_commune,
        dc.code_departement,
        ft.annee,
        ft.type_local,
        COUNT(*)                                   AS nb_transactions,
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ft.prix_m2)::numeric, 2) AS prix_m2_moyen,
        ROUND(SUM(ft.valeur_fonciere)::numeric, 2) AS volume_total
    FROM silver.fact_transactions ft
    JOIN silver.dim_commune dc ON ft.code_insee = dc.code_insee
    WHERE ft.valeur_fonciere IS NOT NULL
      AND ft.type_local IN ('Appartement', 'Maison')
      AND ft.annee >= 2020
    GROUP BY ft.code_insee, dc.nom_commune, dc.code_departement, ft.annee, ft.type_local
    HAVING COUNT(*) >= 10
),

-- Signal 1 : évolution du prix au m² (LAG)
avec_evolution AS (
    SELECT
        *,
        LAG(prix_m2_moyen) OVER (
            PARTITION BY code_insee, type_local ORDER BY annee
        ) AS prix_m2_precedent,
        CASE
            WHEN LAG(prix_m2_moyen) OVER (
                PARTITION BY code_insee, type_local ORDER BY annee
            ) < 500 THEN NULL
            WHEN annee - LAG(annee) OVER (
                PARTITION BY code_insee, type_local ORDER BY annee
            ) > 1 THEN NULL
            -- Seuil médiane : les deux années doivent avoir au moins 25 transactions (médiane observée)
            WHEN LAG(nb_transactions) OVER (
                PARTITION BY code_insee, type_local ORDER BY annee
            ) < 25 THEN NULL
            WHEN nb_transactions < 25 THEN NULL
            ELSE ROUND(
                (prix_m2_moyen - LAG(prix_m2_moyen) OVER (
                    PARTITION BY code_insee, type_local ORDER BY annee
                )) / NULLIF(LAG(prix_m2_moyen) OVER (
                    PARTITION BY code_insee, type_local ORDER BY annee
                ), 0) * 100
            ::numeric, 2)
        END AS hausse_prix_pct
    FROM transactions
),

-- Signal 2 : ratio loyer/revenu par commune (depuis gold.ratio_loyer_revenu)
tension_locative AS (
    SELECT
        bco.code_insee,
        r.annee,
        AVG(r.ratio_tension_pct) AS ratio_tension_pct
    FROM {{ ref('ratio_loyer_revenu') }} r
    JOIN silver.bridge_commune_observatoire bco ON r.observatory_b = bco.observatory_b
    GROUP BY bco.code_insee, r.annee
),

-- Signal 3 : volume de transactions normalisé par commune
volume_normalise AS (
    SELECT
        code_insee,
        annee,
        type_local,
        nb_transactions,
        PERCENT_RANK() OVER (
            PARTITION BY annee, type_local
            ORDER BY nb_transactions
        ) * 100 AS percentile_volume
    FROM transactions
),

-- Assemblage du score composite
score_composite AS (
    SELECT
        t.code_insee,
        t.nom_commune,
        t.code_departement,
        t.annee,
        t.type_local,
        t.nb_transactions,
        t.volume_total,
        t.prix_m2_moyen,
        e.hausse_prix_pct,
        tl.ratio_tension_pct,
        vn.percentile_volume,

        -- Score composite : poids adaptés selon disponibilité des données OLL
        ROUND(
            CASE WHEN tl.ratio_tension_pct IS NULL THEN
                -- Sans données OLL : redistribution sur hausse prix (60%) et volume (40%)
                  COALESCE(LEAST(GREATEST(e.hausse_prix_pct, 0), 20), 0) / 20 * 100 * 0.60
                + COALESCE(vn.percentile_volume, 50) * 0.40
            ELSE
                -- Avec données OLL : 40% ratio loyer/revenu, 35% hausse prix, 25% volume
                  LEAST(tl.ratio_tension_pct, 100) * 0.40
                + COALESCE(LEAST(GREATEST(e.hausse_prix_pct, 0), 20), 0) / 20 * 100 * 0.35
                + COALESCE(vn.percentile_volume, 50) * 0.25
            END::numeric, 1
        ) AS score_tension

    FROM avec_evolution e
    JOIN transactions t ON t.code_insee = e.code_insee
                       AND t.annee = e.annee
                       AND t.type_local = e.type_local
    LEFT JOIN tension_locative tl ON tl.code_insee = t.code_insee
                                 AND tl.annee = t.annee
    LEFT JOIN volume_normalise vn ON vn.code_insee = t.code_insee
                                 AND vn.annee = t.annee
                                 AND vn.type_local = t.type_local
)

SELECT
    code_insee,
    nom_commune,
    code_departement,
    annee,
    type_local,
    nb_transactions,
    volume_total,
    prix_m2_moyen,
    hausse_prix_pct,
    ratio_tension_pct,
    score_tension,
    -- Catégorie lisible
    CASE
        WHEN score_tension >= 75 THEN 'Très tendu'
        WHEN score_tension >= 50 THEN 'Tendu'
        WHEN score_tension >= 25 THEN 'Modéré'
        ELSE 'Détendu'
    END AS categorie_tension
FROM score_composite
