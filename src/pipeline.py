"""
Pipeline complet de nettoyage — TP 9
Exécution end-to-end : lecture → nettoyage → rapport → export
"""

import pandas as pd
import traceback
import sys
from pathlib import Path
from cleaning import clean, DEFAULT_STRATEGY
from report import generate_report


def main(
    csv_in: str = "data/echantillon_france.csv",
    csv_out: str = "data/echantillon_france_propre.csv",
    report_path: str = "docs/data/rapport_nettoyage.md"
):
    """
    Pipeline complet de nettoyage.

    Args:
        chemin_entree : CSV brut
        chemin_sortie : CSV nettoyé
        chemin_rapport : Rapport Markdown
    """

    print("=" * 80)
    print("PIPELINE NETTOYAGE — NutriScope TP 9")
    print("=" * 80)

    # Étape 1 : Lecture
    print(f"\n[1/4] Lecture de {csv_in}...")
    try:
        df_rough = pd.read_csv(csv_in)
        print(f"  ✓ {len(df_rough):,} lignes chargées")
        print(f"  ✓ {len(df_rough.columns)} colonnes")
    except FileNotFoundError:
        print(f"  ✗ Fichier introuvable: {csv_in}")
        return 1
    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        return 1

    # Étape 2 : Nettoyage
    print("\n[2/4] Nettoyage appliqué...")
    try:
        df_clean, reports = clean(df_rough, DEFAULT_STRATEGY)
        print(f"  ✓ Pipeline exécuté: {len(reports)} règles appliquées")

        for report in reports:
            status = "✓" if report.lines_changed == 0 else "○"
            print(f"    {status} {report.rule}: {report.lines_changed} lignes touchées")

        print(f"  ✓ Résultat: {len(df_clean):,} lignes ({len(df_clean)/len(df_rough)*100:.1f}%)")
    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        traceback.print_exc()
        return 1

    # Étape 3 : Rapport
    print("\n[3/4] Génération du rapport...")
    try:
        report_text = generate_report(df_rough, df_clean, reports, report_path)
        print(f"  ✓ Rapport généré ({len(report_text)} caractères)")
    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        traceback.print_exc()
        return 1

    # Étape 4 : Export
    print("\n[4/4] Export des données et rapport...")
    try:
        # CSV nettoyé
        df_clean.to_csv(csv_out, index=False)
        print(f"  ✓ CSV exporté: {csv_out}")

        # Rapport
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"  ✓ Rapport exporté: {report_path}")
    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        return 1

    # Résumé final
    print("\n" + "=" * 80)
    print("✅ PIPELINE COMPLÉTÉ AVEC SUCCÈS")
    print("=" * 80)
    print(f"  • Données brutes: {len(df_rough):,} lignes")
    print(f"  • Données nettoyées: {len(df_clean):,} lignes ({len(df_clean)/len(df_rough)*100:.1f}%)")
    print(f"  • Colonnes: {len(df_rough.columns)} → {len(df_clean.columns)}")
    print(f"\n  Fichiers générés:")
    print(f"    - {csv_out}")
    print(f"    - {report_path}")
    print("\nCommandes de test:")
    print(f"  $ head {csv_out}")
    print(f"  $ cat {report_path}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    # Utilisation
    # python pipeline.py [chemin_entree] [chemin_sortie] [chemin_rapport]

    if len(sys.argv) > 1:
        csv_in = sys.argv[1]
        csv_out = sys.argv[2] if len(sys.argv) > 2 else "data/echantillon_france_propre.csv"
        report_path = sys.argv[3] if len(sys.argv) > 3 else "data/docs/rapport_nettoyage.md"
        sys.exit(main(csv_in, csv_out, report_path))
    else:
        # Valeurs par défaut
        sys.exit(main())
