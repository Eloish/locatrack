-- =========================================================
-- CLEANUP SILVER SCHEMA
-- =========================================================
DROP TABLE IF EXISTS silver.fact_transactions CASCADE;
DROP TABLE IF EXISTS silver.fact_revenus CASCADE;
DROP TABLE IF EXISTS silver.fact_loyers CASCADE;

DROP TABLE IF EXISTS silver.bridge_commune_observatoire CASCADE;

DROP TABLE IF EXISTS silver.dim_commune CASCADE;
DROP TABLE IF EXISTS silver.dim_observatoire CASCADE;
DROP TABLE IF EXISTS silver.dim_agglomeration CASCADE;
DROP TABLE IF EXISTS silver.dim_temps CASCADE;
DROP TABLE IF EXISTS silver.dim_type_bien CASCADE;
DROP TABLE IF EXISTS silver.mapping_communes CASCADE;

-- =========================================================
-- SCHEMAS
-- =========================================================
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- =========================================================
-- DIMENSIONS
-- =========================================================

CREATE TABLE silver.dim_observatoire (
    observatory_b VARCHAR(20) PRIMARY KEY
);

CREATE TABLE silver.dim_agglomeration (
    id_agglomeration  SERIAL PRIMARY KEY,
    nom_agglomeration VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE silver.dim_commune (
    code_insee       VARCHAR(6)   PRIMARY KEY,
    nom_commune      VARCHAR(255),
    code_postal      VARCHAR(5),
    code_departement VARCHAR(3),
    region           VARCHAR(255)
);

CREATE TABLE silver.dim_temps (
    annee INTEGER PRIMARY KEY
);

CREATE TABLE silver.dim_type_bien (
    type_bien VARCHAR(100) PRIMARY KEY
);

-- =========================================================
-- BRIDGES
-- =========================================================

-- COMMUNE ↔ OBSERVATOIRE (N-N)
-- Une commune peut être couverte par plusieurs observatoires
-- Un observatoire couvre plusieurs communes
CREATE TABLE silver.bridge_commune_observatoire (
    code_insee    VARCHAR(6)  NOT NULL,
    observatory_b VARCHAR(20) NOT NULL,

    PRIMARY KEY (code_insee, observatory_b),

    FOREIGN KEY (code_insee)
        REFERENCES silver.dim_commune(code_insee),

    FOREIGN KEY (observatory_b)
        REFERENCES silver.dim_observatoire(observatory_b)
);

-- =========================================================
-- FACT TABLES
-- =========================================================

-- FACT LOYERS
-- Grain : observatoire + agglomération + année + type_habitat + nombre_pieces
-- id_agglomeration est FK directe : un observatoire peut publier des loyers
-- pour plusieurs agglomérations distinctes (ex: B1300 → Aix-Marseille ET Arles)
CREATE TABLE silver.fact_loyers (
    observatory_b        VARCHAR(20)  NOT NULL,
    id_agglomeration     INTEGER      NOT NULL,
    annee                INTEGER      NOT NULL,
    type_habitat         VARCHAR(100) NOT NULL,  -- 'Ensemble' si global
    nombre_pieces        VARCHAR(50)  NOT NULL,  -- 'Tous' si global

    loyer_mensuel_median FLOAT,
    loyer_median_m2      FLOAT,
    nombre_observations  FLOAT,

    PRIMARY KEY (observatory_b, id_agglomeration, annee, type_habitat, nombre_pieces),

    FOREIGN KEY (observatory_b)
        REFERENCES silver.dim_observatoire(observatory_b),

    FOREIGN KEY (id_agglomeration)
        REFERENCES silver.dim_agglomeration(id_agglomeration)
);

-- FACT REVENUS
-- Grain : commune + année
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

-- FACT TRANSACTIONS (DVF)
-- Grain : transaction individuelle par commune + année
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
