import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

class GroupMedianImputer(BaseEstimator, TransformerMixin):
    def __init__(self, target_cols, group_col):
        self.target_cols = target_cols
        self.group_col = group_col
        
    def fit(self, X, y=None):
        # Calcule les médianes par groupe pour toutes les colonnes cibles d'un coup
        self.group_medians_ = X.groupby(self.group_col)[self.target_cols].median()
        self.global_medians_ = X[self.target_cols].median()
        return self
        
    def transform(self, X):
        X_out = X.copy()
        
        for col in self.target_cols:
            mask_na = X_out[col].isna()
            if mask_na.any():
                mapped = X_out.loc[mask_na, self.group_col].map(self.group_medians_[col])
                X_out.loc[mask_na, col] = mapped.fillna(self.global_medians_[col])
                
        return X_out