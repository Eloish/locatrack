{{ config (materialized='table') }}

WITH
    base
    AS
    (
        SELECT
            observatory_b,
            annee,
            type_habitat,
            nombre_pieces,
            ratio_tension_pct
        FROM {{ ref
    ('ratio_loyer_revenu') }}
    WHERE ratio_tension_pct IS NOT NULL
)

SELECT
    observatory_b,
    annee,
    type_habitat,
    nombre_pieces,
    ratio_tension_pct,
    LAG(ratio_tension_pct) OVER (
        PARTITION BY observatory_b, type_habitat, nombre_pieces
        ORDER BY annee
    ) AS ratio_annee_precedente,
    ROUND(
        (ratio_tension_pct - LAG(ratio_tension_pct) OVER (
            PARTITION BY observatory_b, type_habitat, nombre_pieces
            ORDER BY annee
        ))
::numeric,
        2
    ) AS evolution_ratio
FROM base