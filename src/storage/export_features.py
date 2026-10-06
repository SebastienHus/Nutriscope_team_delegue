import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
import pandas as pd

# 7 nutriments clés requis
NUTRIENT_COLS = [
    "energy-kcal_100g",
    "fat_100g",
    "saturated-fat_100g",
    "carbohydrates_100g",
    "sugars_100g",
    "proteins_100g",
    "salt_100g",
]

TARGET_GRADE = "nutriscore_grade"
TARGET_SCORE = "nutriscore_score"
ID_COL = "code"
CATEGORY_COL = "group"


def get_git_commit():
    """Récupère le hash du commit Git courant si disponible."""
    try:
        commit = (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode("ascii")
            .strip()
        )
        return commit
    except Exception:
        return "unknown"


def compute_sha256(filepath):
    """Calcule le hash SHA-256 du fichier généré."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def main():
    parser = argparse.ArgumentParser(
        description="Export de features filtrées et nettoyées pour la prédiction du Nutri-Score."
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Chemin vers le fichier ou dossier Parquet d'entrée.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=".",
        help="Dossier de destination pour le fichier parquet et schema.json.",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force l'écrasement si le fichier destination existe déjà.",
    )

    args = parser.parse_args()

    date_str = datetime.now().strftime("%Y%m%d")
    output_filename = f"features_nutriscore_{date_str}.parquet"
    output_parquet_path = os.path.join(args.output_dir, output_filename)
    output_schema_path = os.path.join(args.output_dir, "schema.json")

    # Vérification de l'existence du fichier
    if os.path.exists(output_parquet_path) and not args.force:
        print(
            f"Erreur : Le fichier '{output_parquet_path}' existe déjà. Utilisez --force pour l'écraser.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Chargement des données depuis '{args.input}'...")
    df = pd.read_parquet(args.input)

    # 1. Filtrage sur le grade Nutri-Score (a-e)
    valid_grades = ["a", "b", "c", "d", "e"]
    df = df[df[TARGET_GRADE].astype(str).str.lower().isin(valid_grades)].copy()
    df[TARGET_GRADE] = df[TARGET_GRADE].astype(str).str.lower()

    # 2. Filtrage sur la présence obligatoire des 7 nutriments clés
    for col in NUTRIENT_COLS:
        if col not in df.columns:
            df[col] = float("nan")
    df = df.dropna(subset=NUTRIENT_COLS).copy()

    # 3. Filtrage de cohérence physique
    coherence_mask = (
        (df["sugars_100g"] <= df["carbohydrates_100g"])
        & (df["saturated-fat_100g"] <= df["fat_100g"])
        & (df["energy-kcal_100g"] > 0)
        & (df["sugars_100g"] >= 0)
        & (df["carbohydrates_100g"] >= 0)
        & (df["saturated-fat_100g"] >= 0)
        & (df["fat_100g"] >= 0)
    )
    df = df[coherence_mask].copy()

    # 4. Calcul des ratios
    df["ratio_sugars_carbs"] = df.apply(
        lambda r: r["sugars_100g"] / r["carbohydrates_100g"]
        if r["carbohydrates_100g"] > 0
        else 0.0,
        axis=1,
    )
    df["ratio_satfat_fat"] = df.apply(
        lambda r: r["saturated-fat_100g"] / r["fat_100g"]
        if r["fat_100g"] > 0
        else 0.0,
        axis=1,
    )
    df["ratio_energy_fat"] = df.apply(
        lambda r: (r["fat_100g"] * 9.0) / r["energy-kcal_100g"]
        if r["energy-kcal_100g"] > 0
        else 0.0,
        axis=1,
    )

    # Colonnes sélectionnées pour l'export
    selected_cols = [
        ID_COL,
        CATEGORY_COL,
        *NUTRIENT_COLS,
        "additives_n",
        "nova_group",
        "ratio_sugars_carbs",
        "ratio_satfat_fat",
        "ratio_energy_fat",
        TARGET_SCORE,
        TARGET_GRADE
    ]
    
    for col in selected_cols:
        if col not in df.columns:
            df[col] = None

    df_out = df[selected_cols].copy()

    # Sauvegarde du fichier parquet
    os.makedirs(args.output_dir, exist_ok=True)
    df_out.to_parquet(output_parquet_path, index=False)
    print(f"Export Parquet réussi : {output_parquet_path}")

    # Répartition de la cible
    target_counts = df_out[TARGET_GRADE].value_counts().to_dict()
    target_dist = df_out[TARGET_GRADE].value_counts(normalize=True).to_dict()
    target_summary = {
        grade: {
            "count": int(target_counts.get(grade, 0)),
            "percentage": round(float(target_dist.get(grade, 0.0)) * 100, 2),
        }
        for grade in valid_grades
    }

    # Description des colonnes & politique de gestion des manquants pour le TP 14
    columns_meta = [
        {
            "name": "code",
            "type": "string",
            "unit": None,
            "description": "Identifiant unique du produit (code-barres).",
            "missing_pct": round(df_out["code"].isnull().mean() * 100, 2),
            "missing_policy_tp14": "Identifiant obligatoire (suppression si absent).",
        },
        {
            "name": "rayon",
            "type": "string / categorical",
            "unit": None,
            "description": "Rayon / catégorie du produit.",
            "missing_pct": round(df_out["rayon"].isnull().mean() * 100, 2),
            "missing_policy_tp14": "Imputation par catégorie 'Inconnu' ou One-Hot Encoding avec catégorie manquante.",
        },
        {
            "name": "energy-kcal_100g",
            "type": "float",
            "unit": "kcal",
            "description": "Énergie pour 100g.",
            "missing_pct": round(
                df_out["energy-kcal_100g"].isnull().mean() * 100, 2
            ),
            "missing_policy_tp14": "Filtré à l'export (0%). Imputation par médiane par rayon si applicable.",
        },
        {
            "name": "fat_100g",
            "type": "float",
            "unit": "g",
            "description": "Lipides pour 100g.",
            "missing_pct": round(df_out["fat_100g"].isnull().mean() * 100, 2),
            "missing_policy_tp14": "Filtré à l'export (0%). Imputation par médiane par rayon.",
        },
        {
            "name": "saturated-fat_100g",
            "type": "float",
            "unit": "g",
            "description": "Acides gras saturés pour 100g.",
            "missing_pct": round(
                df_out["saturated-fat_100g"].isnull().mean() * 100, 2
            ),
            "missing_policy_tp14": "Filtré à l'export (0%). Imputation par médiane par rayon.",
        },
        {
            "name": "carbohydrates_100g",
            "type": "float",
            "unit": "g",
            "description": "Glucides pour 100g.",
            "missing_pct": round(
                df_out["carbohydrates_100g"].isnull().mean() * 100, 2
            ),
            "missing_policy_tp14": "Filtré à l'export (0%). Imputation par médiane par rayon.",
        },
        {
            "name": "sugars_100g",
            "type": "float",
            "unit": "g",
            "description": "Sucres pour 100g.",
            "missing_pct": round(
                df_out["sugars_100g"].isnull().mean() * 100, 2
            ),
            "missing_policy_tp14": "Filtré à l'export (0%). Imputation par médiane par rayon.",
        },
        {
            "name": "proteins_100g",
            "type": "float",
            "unit": "g",
            "description": "Protéines pour 100g.",
            "missing_pct": round(
                df_out["proteins_100g"].isnull().mean() * 100, 2
            ),
            "missing_policy_tp14": "Filtré à l'export (0%). Imputation par médiane par rayon.",
        },
        {
            "name": "salt_100g",
            "type": "float",
            "unit": "g",
            "description": "Sel pour 100g.",
            "missing_pct": round(df_out["salt_100g"].isnull().mean() * 100, 2),
            "missing_policy_tp14": "Filtré à l'export (0%). Imputation par médiane par rayon.",
        },
        {
            "name": "additives_n",
            "type": "float / int",
            "unit": "count",
            "description": "Nombre d'additifs.",
            "missing_pct": round(
                df_out["additives_n"].isnull().mean() * 100, 2
            ),
            "missing_policy_tp14": "Imputation par 0 (hypothèse d'absence d'additif).",
        },
        {
            "name": "nova_group",
            "type": "float / int",
            "unit": "group (1-4)",
            "description": "Groupe NOVA de transformation.",
            "missing_pct": round(df_out["nova_group"].isnull().mean() * 100, 2),
            "missing_policy_tp14": "Imputation par la mode par rayon ou classe dédiée.",
        },
        {
            "name": "ratio_sugars_carbs",
            "type": "float",
            "unit": "ratio [0-1]",
            "description": "Part des sucres dans les glucides (sugars / carbohydrates).",
            "missing_pct": round(
                df_out["ratio_sugars_carbs"].isnull().mean() * 100, 2
            ),
            "missing_policy_tp14": "Valeur fixée à 0 si glucides = 0.",
        },
        {
            "name": "ratio_satfat_fat",
            "type": "float",
            "unit": "ratio [0-1]",
            "description": "Part des acides gras saturés dans les lipides (saturated-fat / fat).",
            "missing_pct": round(
                df_out["ratio_satfat_fat"].isnull().mean() * 100, 2
            ),
            "missing_policy_tp14": "Valeur fixée à 0 si lipides = 0.",
        },
        {
            "name": "ratio_energy_fat",
            "type": "float",
            "unit": "ratio",
            "description": "Part de l'énergie issue des lipides (9 * fat / energy-kcal).",
            "missing_pct": round(
                df_out["ratio_energy_fat"].isnull().mean() * 100, 2
            ),
            "missing_policy_tp14": "Valeur fixée à 0 si énergie = 0.",
        },
        {
            "name": "nutriscore_score",
            "type": "float / int",
            "unit": "points",
            "description": "Score numérique continu du Nutri-Score.",
            "missing_pct": round(
                df_out["nutriscore_score"].isnull().mean() * 100, 2
            ),
            "missing_policy_tp14": "Cible secondaire pour modèle de régression.",
        },
        {
            "name": "nutriscore_grade",
            "type": "string",
            "unit": "grade (a-e)",
            "description": "Classe du Nutri-Score (A à E) - Cible principale.",
            "missing_pct": round(
                df_out["nutriscore_grade"].isnull().mean() * 100, 2
            ),
            "missing_policy_tp14": "Cible principale (0% manquant requis).",
        },
    ]

    schema_data = {
        "nom": output_filename,
        "date_de_gel": datetime.now().isoformat(),
        "source": "Open Food Facts / NutriScope Data",
        "commit_git": get_git_commit(),
        "nombre_de_lignes": len(df_out),
        "sha256": compute_sha256(output_parquet_path),
        "cible": TARGET_GRADE,
        "identifiant": ID_COL,
        "filtres_appliques": [
            "nutriscore_grade présent et valide (a, b, c, d, e)",
            "Présence obligatoire des 7 nutriments clés",
            "Cohérence physique : sucres_100g <= carbohydrates_100g",
            "Cohérence physique : saturated-fat_100g <= fat_100g",
            "Cohérence physique : energy-kcal_100g > 0",
            "Nutriments >= 0",
        ],
        "repartition_cible": target_summary,
        "colonnes": columns_meta,
        "licence": "Open Database License (ODbL)",
        "usage_prevu": "Jeu de données de features nettoyé pour l'entraînement des modèles de classification/régression du Nutri-Score (TP 14).",
    }

    with open(output_schema_path, "w", encoding="utf-8") as f:
        json.dump(schema_data, f, ensure_ascii=False, indent=2)

    print(f"Génération du fichier schema.json réussie : {output_schema_path}")


if __name__ == "__main__":
    main()