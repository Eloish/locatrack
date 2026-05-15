CREATE SCHEMA
IF NOT EXISTS silver;
CREATE SCHEMA
IF NOT EXISTS gold;

CREATE TABLE
IF NOT EXISTS silver.dim_agglomeration
(
    code_unite_urbaine   VARCHAR
(10) PRIMARY KEY,
    nom_unite_urbaine    VARCHAR
(255),
    nom_agglomeration    VARCHAR
(255)
);

CREATE TABLE
IF NOT EXISTS silver.dim_commune
(
    code_insee           VARCHAR
(5) PRIMARY KEY,
    nom_commune          VARCHAR
(255),
    code_postal          VARCHAR
(5),
    code_departement     VARCHAR
(3),
    region               VARCHAR
(255),
    code_unite_urbaine   VARCHAR
(10) REFERENCES silver.dim_agglomeration
(code_unite_urbaine),
    latitude             FLOAT,
    longitude            FLOAT,
    population           INTEGER
);

CREATE TABLE
IF NOT EXISTS silver.dim_temps
(
    annee                INTEGER PRIMARY KEY
);

CREATE TABLE
IF NOT EXISTS silver.dim_type_bien
(
    type_bien            VARCHAR
(50) PRIMARY KEY
);

CREATE TABLE
IF NOT EXISTS silver.fact_tension_locative
(
    id                      SERIAL PRIMARY KEY,
    code_unite_urbaine      VARCHAR
(10) REFERENCES silver.dim_agglomeration
(code_unite_urbaine),
    annee                   INTEGER REFERENCES silver.dim_temps
(annee),
    type_bien               VARCHAR
(50) REFERENCES silver.dim_type_bien
(type_bien),
    loyer_mensuel_median    FLOAT,
    loyer_median_m2         FLOAT,
    revenu_mensuel_median   FLOAT,
    ratio_tension           FLOAT,
    prix_m2_median          FLOAT,
    nombre_observations     FLOAT
);