import pandas as pd
import numpy as np
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder, OrdinalEncoder
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.ensemble import RandomForestRegressor
# from sklearn.tree import DecisionTreeRegressor
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from options import RANDOM_SEED

# TODO: sortir metrics à partir de shap et matplotlib pour l'analyse du test

def train(df: pd.DataFrame, target: str, ordinals: dict[str, list[str]], regressor=None):

    regressor = regressor or RandomForestRegressor(
        n_estimators=100, random_state=RANDOM_SEED
    )

    y = df[target]
    X = df.drop(columns=[y.name])

    numeric_features = X.select_dtypes(include=["int64", "float64"]).columns.to_list()
    categorical_features = X.select_dtypes(include=["str", "object"]).columns.to_list()
    ordinal_features = list(ordinals.keys())

    # Filtre 
    categorical_features = list(set(categorical_features) - set(ordinal_features))

    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()) # Normalisation
    ])

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="constant", fill_value="missing")), # remplace NaN par missing
        ("onehot", OneHotEncoder(handle_unknown="ignore"))
    ])

    ordinal_orders = [ordinals[feat] for feat in ordinal_features]
    ordinal_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("ordinal", OrdinalEncoder(categories=ordinal_orders))
    ])

    preprocessor = ColumnTransformer(transformers=[
        ("num", numeric_transformer, numeric_features),
        ("cat", categorical_transformer, categorical_features)
        ("ord", ordinal_transformer, categorical_features)
    ])

    # TODO: créer colonne d'état pour train ou test et exporter dans les features
    # Stratification importante pour avoir la même proportion de test entre les différentes classes
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    rf_pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("regressor", regressor)
    ])

    rf_pipeline.fit(X_train, y_train)
    y_pred_rf = rf_pipeline.predict(X_test)

    print(f"MAE : {mean_absolute_error(y_test, y_pred_rf):.2}")
    print(f"R² : {r2_score(y_test, y_pred_rf):.2%}")

def save_model(ml_pipeline, filename, destination):
    model_filename = f"{filename}.pcl"
    joblib.dump(ml_pipeline, os.path.join(destination, model_filename))

