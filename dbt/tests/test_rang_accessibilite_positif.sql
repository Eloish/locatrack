-- Test : les classements RANK doivent être >= 1

SELECT *
FROM {{ ref('inegalites') }}
WHERE rang_accessibilite_modeste < 1
   OR rang_accessibilite_median < 1
   OR rang_accessibilite_aise < 1
