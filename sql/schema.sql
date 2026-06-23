-- Initialisation des schémas PostgreSQL
-- Les tables sont créées par schema_silver.sql (02)
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS pipeline;
