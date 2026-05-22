-- Migration 001
-- Date : 2026-05-XX
-- Description : Correction faute de frappe dans staging.loyers_2014
-- La colonne "nombre_obsservations" (2 s) → "nombre_observations" (1 s)
-- Découvert lors de l'exploration des données

ALTER TABLE staging.loyers_2014 RENAME COLUMN nombre_obsservations TO nombre_observations;