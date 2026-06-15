-- Test de volumétrie : les tables gold doivent avoir des données
-- Ce test échoue si une table gold est vide

WITH comptages AS (
    SELECT 'prix_m2_par_ville'  AS modele, COUNT(*) AS nb FROM {{ ref('prix_m2_par_ville') }}
    UNION ALL
    SELECT 'ratio_loyer_revenu' AS modele, COUNT(*) AS nb FROM {{ ref('ratio_loyer_revenu') }}
    UNION ALL
    SELECT 'dynamisme_marche'   AS modele, COUNT(*) AS nb FROM {{ ref('dynamisme_marche') }}
    UNION ALL
    SELECT 'inegalites'         AS modele, COUNT(*) AS nb FROM {{ ref('inegalites') }}
)

SELECT modele, nb
FROM comptages
WHERE nb = 0
