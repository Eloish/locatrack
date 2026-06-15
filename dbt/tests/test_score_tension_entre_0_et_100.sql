-- Test : le score de tension composite doit être entre 0 et 100

SELECT *
FROM {{ ref('dynamisme_marche') }}
WHERE score_tension IS NOT NULL
  AND (score_tension < 0 OR score_tension > 100)
