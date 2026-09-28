"""LightGBM model: cross-validated via the time-based folds from validation.py
before ever being trained on all the data. See docs/plan.md step 4.

Kept separate from train.py -- that file's baseline model has a different
artifact type (a small lookup table) and a different `main()` entry point;
this one produces a LightGBM Booster and needs its own evaluation loop.

Usage:
    python src/train_lgbm.py
"""
import lightgbm as lgb
import polars as pl

from config import TARGET
from db import connect_clean
from features import CATEGORICAL_COLUMNS, FEATURE_COLUMNS, build_matrix, fit_encoders
from validation import FOLDS, load_fold, rmse, rmse_by_airport

LGBM_PARAMS = {
    "objective": "regression",
    "metric": "rmse",
    "verbosity": -1,
    "seed": 42,
}


def train_on_fold(con, fold_name: str):
    fold = load_fold(con, fold_name)
    encoders = fit_encoders(fold.train)

    X_train = build_matrix(fold.train, encoders)
    y_train = fold.train[TARGET].to_numpy()
    X_val = build_matrix(fold.val, encoders)
    y_val = fold.val[TARGET].to_numpy()

    categorical_idx = [FEATURE_COLUMNS.index(c) for c in CATEGORICAL_COLUMNS]
    train_set = lgb.Dataset(
        X_train.to_numpy(), label=y_train, feature_name=FEATURE_COLUMNS, categorical_feature=categorical_idx
    )
    val_set = lgb.Dataset(X_val.to_numpy(), label=y_val, reference=train_set)

    booster = lgb.train(
        LGBM_PARAMS,
        train_set,
        num_boost_round=1000,
        valid_sets=[val_set],
        callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False), lgb.log_evaluation(period=0)],
    )

    preds = pl.Series(booster.predict(X_val.to_numpy(), num_iteration=booster.best_iteration))
    score = rmse(pl.Series(y_val), preds)

    return booster, score, fold, preds


def main() -> None:
    con = connect_clean()
    for fold_name in FOLDS:
        booster, score, fold, preds = train_on_fold(con, fold_name)
        print(f"=== fold={fold_name}  RMSE={score:.1f}s  best_iteration={booster.best_iteration} ===")
        print(rmse_by_airport(fold.val, preds))

        importance = pl.DataFrame(
            {"feature": FEATURE_COLUMNS, "gain": booster.feature_importance(importance_type="gain")}
        ).sort("gain", descending=True)
        print(importance)
        print()


if __name__ == "__main__":
    main()
