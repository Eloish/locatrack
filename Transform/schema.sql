-- =====================
-- SCHEMAS
-- =====================
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- =====================
-- SILVER TABLES
-- =====================

-- Dimension agglomération
CREATE TABLE IF NOT EXISTS silver.dim_agglomeration (
    nom_agglomeration VARCHAR(255) PRIMARY KEY,
    observatory_b     VARCHAR(10)
);

-- Dimension commune
CREATE TABLE IF NOT EXISTS silver.dim_commune (
    code_insee        VARCHAR(6) PRIMARY KEY,
    nom_commune       VARCHAR(255),
    code_postal       VARCHAR(5),
    code_departement  VARCHAR(3),
    region            VARCHAR(255),
    nom_agglomeration VARCHAR(255) REFERENCES silver.dim_agglomeration(nom_agglomeration),
    latitude          FLOAT,
    longitude         FLOAT,
    population        INTEGER
);

-- Dimension temps
CREATE TABLE IF NOT EXISTS silver.dim_temps (
    annee INTEGER PRIMARY KEY
);

-- Dimension type de bien
CREATE TABLE IF NOT EXISTS silver.dim_type_bien (
    type_bien VARCHAR(100) PRIMARY KEY
);

-- Fait loyers (depuis OLAP)
CREATE TABLE IF NOT EXISTS silver.fact_loyers (
    id                      SERIAL PRIMARY KEY,
    nom_agglomeration       VARCHAR(255),
    annee                   INTEGER,
    type_habitat            VARCHAR(100),
    nombre_pieces           VARCHAR(50),
    loyer_mensuel_median    FLOAT,
    loyer_median_m2         FLOAT,
    nombre_observations     FLOAT
);

-- Fait revenus (depuis INSEE)
CREATE TABLE IF NOT EXISTS silver.fact_revenus (
    id             SERIAL PRIMARY KEY,
    code_insee     VARCHAR(6),
    annee          INTEGER,
    revenu_median  FLOAT,
    revenu_mensuel FLOAT
);

-- Fait transactions immobilières (depuis DVF)
CREATE TABLE IF NOT EXISTS silver.fact_transactions (
    id              SERIAL PRIMARY KEY,
    code_insee      VARCHAR(6),
    annee           INTEGER,
    type_local      VARCHAR(100),
    nature_mutation VARCHAR(100),
    valeur_fonciere FLOAT,
    surface_bati    FLOAT,
    surface_terrain FLOAT,
    nombre_pieces   FLOAT,
    prix_m2         FLOAT,
    nature_culture  VARCHAR(10)
);