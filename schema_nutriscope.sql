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
DROP TABLE IF EXISTS products_food_groups CASCADE;

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

    quantity VARCHAR(255),

    ingredients_text TEXT,

    main_category VARCHAR(255),

    pnns_group_1 VARCHAR(64) NOT NULL,

    pnns_group_2 VARCHAR(255),

    created_at TIMESTAMP NOT NULL,

    last_modified_at TIMESTAMP NOT NULL,

    image_url TEXT,

    image_small_url TEXT,

    image_ingredients_url TEXT,

    image_ingredients_small_url TEXT,

    image_nutrition_url TEXT,

    image_nutrition_small_url TEXT,

    -- Code-barres officiel : EAN-8, UPC-A ou EAN-13 (cf. src/schema.py)
    CONSTRAINT chk_product_code
        CHECK (code ~ '^([0-9]{8}|[0-9]{12}|[0-9]{13})$'),

    CONSTRAINT chk_product_pnns_group_1
        CHECK (pnns_group_1 IN (
            'Beverages', 'Cereals and potatoes', 'Composite foods', 'Fat and sauces',
            'Fish Meat Eggs', 'Fruits and vegetables', 'Milk and dairy products',
            'Salty snacks', 'Sugary snacks', 'Alcoholic beverages', 'Baby foods', 'unknown'
        ))

);


/* =====================================================
   TABLE NUTRITION
   ===================================================== */

CREATE TABLE nutrition (

    product_code VARCHAR(50)
        PRIMARY KEY,

    energy_100g NUMERIC(12,4),

    energy_kcal_100g NUMERIC(12,4),

    fat_100g NUMERIC(12,4),

    saturated_fat_100g NUMERIC(12,4),

    carbohydrates_100g NUMERIC(12,4),

    sugars_100g NUMERIC(12,4),

    fiber_100g NUMERIC(12,4),

    proteins_100g NUMERIC(12,4),

    salt_100g NUMERIC(12,4),

    sodium_100g NUMERIC(12,4),

    fruits_vegetables_legumes_100g NUMERIC(12,4),

    CONSTRAINT fk_nutrition_produit
        FOREIGN KEY (product_code)
        REFERENCES products(code),

    -- Bornes métier (cf. src/schema.py) : la base refuse ce que le nettoyage aurait laissé passer
    CONSTRAINT chk_energy CHECK (energy_100g BETWEEN 0 AND 3765.6),
    CONSTRAINT chk_energy_kcal CHECK (energy_kcal_100g BETWEEN 0 AND 900),
    CONSTRAINT chk_fat CHECK (fat_100g BETWEEN 0 AND 100),
    CONSTRAINT chk_saturated_fat CHECK (saturated_fat_100g BETWEEN 0 AND 100),
    CONSTRAINT chk_carbohydrates CHECK (carbohydrates_100g BETWEEN 0 AND 100),
    CONSTRAINT chk_sugars CHECK (sugars_100g BETWEEN 0 AND 100),
    CONSTRAINT chk_fiber CHECK (fiber_100g BETWEEN 0 AND 100),
    CONSTRAINT chk_proteins CHECK (proteins_100g BETWEEN 0 AND 100),
    CONSTRAINT chk_salt CHECK (salt_100g BETWEEN 0 AND 100),
    CONSTRAINT chk_sodium CHECK (sodium_100g BETWEEN 0 AND 40),
    CONSTRAINT chk_fruits_vegetables_legumes CHECK (fruits_vegetables_legumes_100g BETWEEN 0 AND 100),
    CONSTRAINT chk_sugars_within_carbohydrates CHECK (sugars_100g <= carbohydrates_100g + 0.5),
    CONSTRAINT chk_saturated_within_fat CHECK (saturated_fat_100g <= fat_100g + 0.5)

);


/* =====================================================
   TABLE SCORE
   ===================================================== */

CREATE TABLE score (

    product_code VARCHAR(50)
        PRIMARY KEY,

    nutriscore INTEGER,

    nutriscore_grade VARCHAR(16),

    nova_group SMALLINT,

    environmental_score_grade VARCHAR(16),

    CONSTRAINT fk_product_score
        FOREIGN KEY (product_code)
        REFERENCES products(code),

    CONSTRAINT chk_nutriscore_grade
        CHECK (nutriscore_grade IN ('a', 'b', 'c', 'd', 'e', 'not-applicable')),

    CONSTRAINT chk_environmental_score_grade
        CHECK (environmental_score_grade IN ('a-plus', 'a', 'b', 'c', 'd', 'e', 'f', 'not-applicable'))

);

/* =====================================================
   TABLE PRODUCT_FOOD_GROUP
   ===================================================== */

CREATE TABLE products_food_groups (

    product_code VARCHAR(50),

    food_group_id INTEGER,

    PRIMARY KEY (
        product_code,
        food_group_id
    ),

    CONSTRAINT fk_pfg_product
        FOREIGN KEY (product_code)
        REFERENCES products(code),

    CONSTRAINT fk_pfg_category
        FOREIGN KEY (food_group_id)
        REFERENCES food_groups(id)

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