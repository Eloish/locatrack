-- =========================================================
-- CLEANUP SILVER SCHEMA
-- =========================================================
DROP TABLE IF EXISTS silver.fact_transactions CASCADE;
DROP TABLE IF EXISTS silver.fact_revenus CASCADE;
DROP TABLE IF EXISTS silver.fact_loyers CASCADE;

DROP TABLE IF EXISTS silver.bridge_commune_observatoire CASCADE;
DROP TABLE IF EXISTS silver.bridge_observatoire_agglomeration CASCADE;

DROP TABLE IF EXISTS silver.dim_commune CASCADE;
DROP TABLE IF EXISTS silver.dim_observatoire CASCADE;
DROP TABLE IF EXISTS silver.dim_agglomeration CASCADE;

DROP TABLE IF EXISTS silver.dim_temps CASCADE;
DROP TABLE IF EXISTS silver.dim_type_bien CASCADE;

-- =========================================================
-- SCHEMAS
-- =========================================================
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- =========================================================
-- DIMENSIONS
-- =========================================================

-- DIM OBSERVATOIRE
CREATE TABLE silver.dim_observatoire (
    observatory_b VARCHAR(10) PRIMARY KEY
);

-- DIM AGGLOMERATION
CREATE TABLE silver.dim_agglomeration (
    id_agglomeration SERIAL PRIMARY KEY,
    nom_agglomeration VARCHAR(255) UNIQUE
);

-- DIM COMMUNE
CREATE TABLE silver.dim_commune (
    code_insee        VARCHAR(6) PRIMARY KEY,
    nom_commune       VARCHAR(255),
    code_postal       VARCHAR(5),
    code_departement  VARCHAR(3),
    region            VARCHAR(255)
);

-- DIM TEMPS
CREATE TABLE silver.dim_temps (
    annee INTEGER PRIMARY KEY
);

-- DIM TYPE BIEN
CREATE TABLE silver.dim_type_bien (
    type_bien VARCHAR(100) PRIMARY KEY
);

-- =========================================================
-- BRIDGES
-- =========================================================

-- OBSERVATOIRE ↔ AGGLOMERATION (N-N)
CREATE TABLE silver.bridge_observatoire_agglomeration (
    observatory_b      VARCHAR(10),
    id_agglomeration   INTEGER,

    PRIMARY KEY (observatory_b, id_agglomeration),

    FOREIGN KEY (observatory_b)
        REFERENCES silver.dim_observatoire(observatory_b),

    FOREIGN KEY (id_agglomeration)
        REFERENCES silver.dim_agglomeration(id_agglomeration)
);

-- COMMUNE ↔ OBSERVATOIRE (N-N)
CREATE TABLE silver.bridge_commune_observatoire (
    code_insee     VARCHAR(6),
    observatory_b  VARCHAR(10),

    PRIMARY KEY (code_insee, observatory_b),

    FOREIGN KEY (code_insee)
        REFERENCES silver.dim_commune(code_insee),

    FOREIGN KEY (observatory_b)
        REFERENCES silver.dim_observatoire(observatory_b)
);

-- =========================================================
-- FACT TABLES
-- =========================================================

-- FACT LOYERS (grain = observatoire)
CREATE TABLE silver.fact_loyers
(
    id SERIAL PRIMARY KEY,

    observatory_b VARCHAR(10) NOT NULL,
    annee INTEGER NOT NULL,

    type_habitat VARCHAR(100),
    nombre_pieces VARCHAR(50),

    loyer_median FLOAT,
    loyer_mensuel_median FLOAT,
    loyer_median_m2 FLOAT,
    nombre_observations FLOAT,

    FOREIGN KEY (observatory_b)
        REFERENCES silver.dim_observatoire(observatory_b),

    FOREIGN KEY (annee)
        REFERENCES silver.dim_temps(annee)
);

-- FACT REVENUS (grain = commune)
CREATE TABLE silver.fact_revenus (
    id             SERIAL PRIMARY KEY,
    code_insee     VARCHAR(6),
    annee          INTEGER,
    revenu_median  FLOAT,
    revenu_mensuel FLOAT,

    FOREIGN KEY (code_insee)
        REFERENCES silver.dim_commune(code_insee),

    FOREIGN KEY (annee)
        REFERENCES silver.dim_temps(annee)
);

-- FACT TRANSACTIONS (grain = commune)
CREATE TABLE silver.fact_transactions (
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
    nature_culture  VARCHAR(10),


    FOREIGN KEY (code_insee)
        REFERENCES silver.dim_commune(code_insee),

    FOREIGN KEY (annee)
        REFERENCES silver.dim_temps(annee)
);