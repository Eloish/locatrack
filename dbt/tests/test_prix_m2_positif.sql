-- Test : le prix au m² médian doit toujours être positif

SELECT *
FROM {{ ref('prix_m2_par_ville') }}
WHERE prix_m2_median IS NOT NULL
  AND prix_m2_median <= 0
