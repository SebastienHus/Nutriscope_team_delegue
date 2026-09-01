/* =====================================================
   NUTRISCOPE V1
   CREATION COMPLETE DE LA BASE
   ===================================================== */


/* =====================================================
   ETAPE 1 : SUPPRESSION DES TABLES
   SCRIPT REJOUABLE
   ===================================================== */

DROP TABLE IF EXISTS products_countries CASCADE;
DROP TABLE IF EXISTS products_traces CASCADE;
DROP TABLE IF EXISTS products_allergens CASCADE;
DROP TABLE IF EXISTS products_labels CASCADE;
DROP TABLE IF EXISTS products_additives CASCADE;
DROP TABLE IF EXISTS products_brands CASCADE;
DROP TABLE IF EXISTS products_categories CASCADE;

DROP TABLE IF EXISTS score CASCADE;
DROP TABLE IF EXISTS nutrition CASCADE;
DROP TABLE IF EXISTS products CASCADE;

DROP TABLE IF EXISTS countries CASCADE;
DROP TABLE IF EXISTS traces CASCADE;
DROP TABLE IF EXISTS allergens CASCADE;
DROP TABLE IF EXISTS labels CASCADE;
DROP TABLE IF EXISTS additives CASCADE;
DROP TABLE IF EXISTS brands CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS food_groups CASCADE;

/* =====================================================
   BESOIN DU SCHEMA PAR DEFAUT POUR PSYCOPG
   ===================================================== */

CREATE SCHEMA IF NOT EXISTS public;
SET search_path TO public;

/* =====================================================
   TABLE FOOD GROUP
   ===================================================== */

CREATE TABLE food_groups (

    id SERIAL PRIMARY KEY,

    name VARCHAR(255)
    NOT NULL
    UNIQUE

);


/* =====================================================
   TABLE CATEGORY
   ===================================================== */

CREATE TABLE categories (

    id SERIAL PRIMARY KEY,

    name VARCHAR(255)
    NOT NULL
    UNIQUE,

    parent_id INTEGER,

    CONSTRAINT fk_category_parent
        FOREIGN KEY (parent_id)
        REFERENCES categories(id)

);


/* =====================================================
   TABLE MARQUE
   ===================================================== */

CREATE TABLE brands (

    id SERIAL PRIMARY KEY,

    name VARCHAR(255)
    NOT NULL
    UNIQUE

);


/* =====================================================
   TABLE ADDITIF
   ===================================================== */

CREATE TABLE additives (

    id SERIAL PRIMARY KEY,

    name VARCHAR(255)
    NOT NULL
    UNIQUE

);


/* =====================================================
   TABLE LABEL
   ===================================================== */

CREATE TABLE labels (

    id SERIAL PRIMARY KEY,

    name VARCHAR(255)
    NOT NULL
    UNIQUE

);


/* =====================================================
   TABLE ALLERGENE
   ===================================================== */

CREATE TABLE allergens (

    id SERIAL PRIMARY KEY,

    name VARCHAR(255)
    NOT NULL
    UNIQUE

);


/* =====================================================
   TABLE TRACE
   ===================================================== */

CREATE TABLE traces (

    id SERIAL PRIMARY KEY,

    name VARCHAR(255)
    NOT NULL
    UNIQUE

);


/* =====================================================
   TABLE PAYS
   ===================================================== */

CREATE TABLE countries (

    id SERIAL PRIMARY KEY,

    name VARCHAR(255)
    NOT NULL
    UNIQUE

);


/* =====================================================
   TABLE PRODUIT
   ===================================================== */

CREATE TABLE products (

    code VARCHAR(50) PRIMARY KEY,

    name TEXT,

    quantity VARCHAR(100),

    ingredients_text TEXT,

    -- completeness NUMERIC(10,2),

    -- no_nutrition_data BOOLEAN,

    -- nutriscore_data_complete BOOLEAN,

    image_url TEXT,

    image_small_url TEXT,

    image_ingredients_url TEXT,

    image_ingredients_small_url TEXT,

    image_nutrition_url TEXT,

    image_nutrition_small_url TEXT,

    food_group_id INTEGER,

    CONSTRAINT fk_product_food_group
        FOREIGN KEY (food_group_id)
        REFERENCES food_groups(id)

);


/* =====================================================
   TABLE NUTRITION
   ===================================================== */

CREATE TABLE nutrition (

    product_code VARCHAR(50)
        PRIMARY KEY,

    energy_100g NUMERIC(12,4),

    fat_100g NUMERIC(12,4),

    saturated_fat_100g NUMERIC(12,4),

    sugars_100g NUMERIC(12,4),

    fiber_100g NUMERIC(12,4),

    proteins_100g NUMERIC(12,4),

    salt_100g NUMERIC(12,4),

    fruits_vegetables_legumes_100g NUMERIC(12,4),

    CONSTRAINT fk_nutrition_produit
        FOREIGN KEY (product_code)
        REFERENCES products(code)

);


/* =====================================================
   TABLE SCORE
   ===================================================== */

CREATE TABLE score (

    product_code VARCHAR(50)
        PRIMARY KEY,

    nutriscore_score INTEGER,

    nutriscore_grade CHAR(1),

    nova_group SMALLINT,

    environmental_score_grade CHAR(1),

    CONSTRAINT fk_product_score
        FOREIGN KEY (product_code)
        REFERENCES products(code)

);


/* =====================================================
   TABLE PRODUIT_CATEGORY
   ===================================================== */

CREATE TABLE products_categories (

    product_code VARCHAR(50),

    category_id INTEGER,

    PRIMARY KEY (
        product_code,
        category_id
    ),

    CONSTRAINT fk_pc_product
        FOREIGN KEY (product_code)
        REFERENCES products(code),

    CONSTRAINT fk_pc_category
        FOREIGN KEY (category_id)
        REFERENCES categories(id)

);


/* =====================================================
   TABLE PRODUIT_MARQUE
   ===================================================== */

CREATE TABLE products_brands (

    product_code VARCHAR(50),

    brand_id INTEGER,

    PRIMARY KEY (
        product_code,
        brand_id
    ),

    CONSTRAINT fk_pb_product
        FOREIGN KEY (product_code)
        REFERENCES products(code),

    CONSTRAINT fk_pb_brand
        FOREIGN KEY (brand_id)
        REFERENCES brands(id)

);


/* =====================================================
   TABLE PRODUIT_ADDITIF
   ===================================================== */

CREATE TABLE products_additives (

    product_code VARCHAR(50),

    additive_id INTEGER,

    PRIMARY KEY (
        product_code,
        additive_id
    ),

    CONSTRAINT fk_pa_product
        FOREIGN KEY (product_code)
        REFERENCES products(code),

    CONSTRAINT fk_pa_additive
        FOREIGN KEY (additive_id)
        REFERENCES additives(id)

);


/* =====================================================
   TABLE PRODUIT_LABEL
   ===================================================== */

CREATE TABLE products_labels (

    product_code VARCHAR(50),

    label_id INTEGER,

    PRIMARY KEY (
        product_code,
        label_id
    ),

    CONSTRAINT fk_pl_product
        FOREIGN KEY (product_code)
        REFERENCES products(code),

    CONSTRAINT fk_pl_label
        FOREIGN KEY (label_id)
        REFERENCES labels(id)

);


/* =====================================================
   TABLE PRODUIT_ALLERGENE
   ===================================================== */

CREATE TABLE products_allergens (

    product_code VARCHAR(50),

    allergen_id INTEGER,

    PRIMARY KEY (
        product_code,
        allergen_id
    ),

    CONSTRAINT fk_pall_product
        FOREIGN KEY (product_code)
        REFERENCES products(code),

    CONSTRAINT fk_pall_allergene
        FOREIGN KEY (allergen_id)
        REFERENCES allergens(id)

);


/* =====================================================
   TABLE PRODUIT_TRACE
   ===================================================== */

CREATE TABLE products_traces (

    product_code VARCHAR(50),

    trace_id INTEGER,

    PRIMARY KEY (
        product_code,
        trace_id
    ),

    CONSTRAINT fk_pt_produit
        FOREIGN KEY (product_code)
        REFERENCES products(code),

    CONSTRAINT fk_pt_trace
        FOREIGN KEY (trace_id)
        REFERENCES traces(id)

);


/* =====================================================
   TABLE PRODUIT_PAYS
   ===================================================== */

CREATE TABLE products_countries (

    product_code VARCHAR(50),

    country_id INTEGER,

    PRIMARY KEY (
        product_code,
        country_id
    ),

    CONSTRAINT fk_pco_product
        FOREIGN KEY (product_code)
        REFERENCES products(code),

    CONSTRAINT fk_pco_countries
        FOREIGN KEY (country_id)
        REFERENCES countries(id)

);


/* =====================================================
   INDEX CONSEILLES
   ===================================================== */

CREATE INDEX idx_product_name
ON products(name);

CREATE INDEX idx_brand_name
ON brands(name);

CREATE INDEX idx_category_name
ON categories(name);

CREATE INDEX idx_additive_name
ON additives(name);

CREATE INDEX idx_label_name
ON labels(name);

CREATE INDEX idx_country_name
ON countries(name);

CREATE INDEX idx_food_group_name
ON food_groups(name);


/* =====================================================
   FIN DU SCRIPT
   ===================================================== */