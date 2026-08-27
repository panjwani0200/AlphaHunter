import os
import pickle
import logging
import pandas as pd
import numpy as np

import sys

logger = logging.getLogger("uvicorn")

def get_model_path():
    if getattr(sys, 'frozen', False):
        if sys.platform == "win32":
            base_dir = os.path.join(os.environ.get("APPDATA", ""), "AlphaHunter")
        else:
            base_dir = os.path.join(os.path.expanduser("~"), ".alphahunter")
        os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, "xgb_model.pkl")
    return os.path.join(os.path.dirname(__file__), "xgb_model.pkl")

MODEL_PATH = get_model_path()

class MLScoringModel:
    def __init__(self) -> None:
        self.model = None
        self._trained = False
        self._feature_names = [
            "volume_ratio", "change_pct", "proximity", "atr_expansion", 
            "vwap_dist", "gap_pct", "delivery_ratio", "pcr", 
            "max_pain_dist", "sector_strength"
        ]

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the 10 engineered feature columns on historical candle DataFrame.
        """
        df = df.copy()
        
        # 1. Volume Ratio
        df["volume_ratio"] = df["volume"] / df["volume"].rolling(20).mean().fillna(1.0)
        
        # 2. Daily Change Pct
        df["change_pct"] = df["close"].pct_change().fillna(0.0) * 100.0
        
        # 3. Proximity to 52W High
        high_52w = df["high"].rolling(min(250, len(df)), min_periods=1).max()
        df["proximity"] = (df["close"] - high_52w) / high_52w
        
        # 4. ATR Expansion
        tr = np.maximum(
            df["high"] - df["low"],
            np.maximum(
                abs(df["high"] - df["close"].shift(1)),
                abs(df["low"] - df["close"].shift(1))
            )
        ).fillna(0.0)
        atr = tr.rolling(14, min_periods=1).mean()
        df["atr_expansion"] = atr / atr.rolling(20, min_periods=1).mean().fillna(1.0)
        
        # 5. VWAP Distance (Estimated using rolling cumulative volume-price)
        tp = (df["high"] + df["low"] + df["close"]) / 3.0
        vwap = (tp * df["volume"]).rolling(20, min_periods=1).sum() / df["volume"].rolling(20, min_periods=1).sum().fillna(1.0)
        df["vwap_dist"] = (df["close"] - vwap) / vwap.fillna(1.0)
        
        # 6. Gap %
        df["gap_pct"] = ((df["open"] - df["close"].shift(1)) / df["close"].shift(1)).fillna(0.0) * 100.0
        
        # 7. Delivery ratio
        if "delivery_percent" not in df.columns:
            df["delivery_percent"] = 0.35  # Neutral default
        df["delivery_ratio"] = df["delivery_percent"].fillna(0.35)
        
        # 8. PCR (Defaults to neutral 0.9)
        df["pcr"] = 0.9
        
        # 9. Max Pain Distance
        df["max_pain_dist"] = 0.0
        
        # 10. Sector Strength
        df["sector_strength"] = 50.0
        
        return df

    def load_or_train(self, snapshots_list: list) -> None:
        """
        Load XGBoost model from disk or train on historical snapshots.
        """
        if os.path.exists(MODEL_PATH):
            try:
                with open(MODEL_PATH, "rb") as f:
                    self.model = pickle.load(f)
                self._trained = True
                logger.info("Successfully loaded pre-trained XGBoost ML model.")
                return
            except Exception as e:
                logger.warning(f"Failed to load XGBoost model from disk: {e}. Retraining...")

        self.train_on_snapshots(snapshots_list)

    def train_on_snapshots(self, snapshots_list: list) -> None:
        if not snapshots_list:
            logger.warning("No snapshot data available to train the ML model.")
            return

        features_data = []
        labels = []

        logger.info("Extracting features and training XGBoost model on historical data...")

        for snap in snapshots_list:
            candles = snap.candles
            if len(candles) < 30:
                continue

            df = pd.DataFrame([c.model_dump() for c in candles])
            df = self.calculate_indicators(df)
            
            close_prices = df["close"].values
            
            # Target Labeling: Move >= 1.5% in the next 2 sessions
            for i in range(20, len(df) - 2):
                # Features list matching self._feature_names
                row_features = [
                    float(df.loc[i, "volume_ratio"]),
                    float(df.loc[i, "change_pct"]),
                    float(df.loc[i, "proximity"]),
                    float(df.loc[i, "atr_expansion"]),
                    float(df.loc[i, "vwap_dist"]),
                    float(df.loc[i, "gap_pct"]),
                    float(df.loc[i, "delivery_ratio"]),
                    float(df.loc[i, "pcr"]),
                    float(df.loc[i, "max_pain_dist"]),
                    float(df.loc[i, "sector_strength"]),
                ]
                
                # Check forward 2 days
                future_highs = df["high"].values[i + 1 : i + 3]
                entry_close = close_prices[i]
                max_future_move = ((np.max(future_highs) - entry_close) / entry_close) * 100.0
                label = 1 if max_future_move >= 1.5 else 0

                features_data.append(row_features)
                labels.append(label)

        if len(features_data) < 80:
            logger.warning("Too few data points to train XGBoost ML model. Using fallback probability heuristics.")
            return

        try:
            X = np.array(features_data)
            y = np.array(labels)
            
            # Train XGBoost model
            from xgboost import XGBClassifier
            model = XGBClassifier(
                n_estimators=80,
                max_depth=4,
                learning_rate=0.08,
                random_state=42,
                eval_metric="logloss"
            )
            model.fit(X, y)
            
            with open(MODEL_PATH, "wb") as f:
                pickle.dump(model, f)
            
            self.model = model
            self._trained = True
            logger.info(f"XGBoost ML model trained successfully on {len(X)} samples and saved to disk.")
        except Exception as e:
            logger.error(f"Error training XGBoost ML model: {e}")

    def predict_probability(
        self, 
        volume_ratio: float, 
        change_percent: float, 
        last_price: float, 
        week52_high: float | None,
        atr_expansion: float = 1.0,
        vwap_dist: float = 0.0,
        gap_pct: float = 0.0,
        delivery_ratio: float = 0.35,
        pcr: float = 0.9,
        max_pain_dist: float = 0.0,
        sector_strength: float = 50.0
    ) -> float:
        """
        Returns predicted probability (0.0 to 1.0) of a successful swing movement.
        """
        if not self._trained or not self.model:
            # Fallback heuristic
            prob = 0.5
            if volume_ratio > 1.8:
                prob += 0.12
            if change_percent > 1.5:
                prob += 0.08
            if delivery_ratio > 0.45:
                prob += 0.05
            return min(0.95, max(0.05, prob))

        try:
            high_52w = week52_high or last_price
            proximity = (last_price - high_52w) / high_52w
            
            features = np.array([[
                volume_ratio,
                change_percent,
                proximity,
                atr_expansion,
                vwap_dist,
                gap_pct,
                delivery_ratio,
                pcr,
                max_pain_dist,
                sector_strength
            ]])
            
            prob_success = self.model.predict_proba(features)[0][1]
            return float(prob_success)
        except Exception as e:
            logger.warning(f"Failed to run XGBoost model prediction: {e}. Falling back to default probability.")
            return 0.5

ml_scoring_model = MLScoringModel()
