-- Test : le ratio loyer/revenu doit être entre 1% et 200%
-- Un ratio hors de cette plage indique une erreur de données

SELECT *
FROM {{ ref('ratio_loyer_revenu') }}
WHERE ratio_tension_pct IS NOT NULL
  AND (ratio_tension_pct < 1 OR ratio_tension_pct > 200)
