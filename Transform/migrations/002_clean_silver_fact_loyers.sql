/*
================================================================================
NOM DU SCRIPT : 001_clean_silver_fact_loyers.sql
DATE          : 2026-06-05
OBJET         : Normalisation et nettoyage de la table silver.fact_loyers
CONTEXTE      : 
  - 1. Correction de l'encodage (AgglomÚration -> Agglomération)
  - 2. Transformation des valeurs NULL en "Ensemble" pour la lisibilité métier
================================================================================
*/

-- 1. Correction de l'encodage des noms d'agglomérations
UPDATE silver.fact_loyers 
SET nom_agglomeration = REPLACE(nom_agglomeration, 'AgglomÚration', 'Agglomération')
WHERE nom_agglomeration LIKE '%AgglomÚration%';

-- 2. Normalisation des données de synthèse
-- Transformation des NULL en "Ensemble" pour faciliter le dashboarding
UPDATE silver.fact_loyers 
SET type_habitat = 'Ensemble' 
WHERE type_habitat IS NULL;

-- 3. Vérification finale
-- Vérification que le nettoyage est complet
SELECT 'Nulls restants:' as check_name, count(*) as count
FROM silver.fact_loyers
WHERE type_habitat IS NULL;