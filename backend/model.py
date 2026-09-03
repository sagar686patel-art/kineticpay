import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

MODEL_PATH = os.path.join(os.path.dirname(__file__), "underwriting_model.joblib")

def generate_training_data(samples=1000):
    np.random.seed(42)
    # Feature 1: Avg active hours/day (3.0 - 12.0)
    avg_hours = np.random.uniform(3.0, 12.0, samples)
    # Feature 2: Weekly earnings volatility (standard deviation, 50 - 600)
    volatility = np.random.uniform(50.0, 600.0, samples)
    # Feature 3: Avg daily trips (5 - 35)
    trips_per_day = np.random.uniform(5, 35, samples)
    # Feature 4: Avg daily earnings ($20 - $180 or ₹400 - ₹3000)
    daily_avg_earnings = (avg_hours * 120) + (trips_per_day * 40) - (volatility * 0.2) + np.random.normal(0, 50, samples)
    daily_avg_earnings = np.clip(daily_avg_earnings, 300, 3500)

    # Label: Safe Micro-Credit Cap = function of steady velocity and low relative volatility
    credit_limit = (daily_avg_earnings * 3.0) + (avg_hours * 150) - (volatility * 1.5)
    credit_limit = np.clip(credit_limit, 1000, 15000)

    df = pd.DataFrame({
        "avg_hours": avg_hours,
        "volatility": volatility,
        "trips_per_day": trips_per_day,
        "daily_avg_earnings": daily_avg_earnings,
        "credit_limit": credit_limit
    })
    return df

def train_and_save_model():
    data = generate_training_data()
    X = data[["avg_hours", "volatility", "trips_per_day", "daily_avg_earnings"]]
    y = data["credit_limit"]

    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(X, y)
    joblib.dump(model, MODEL_PATH)
    print("Underwriting model trained and saved.")

def predict_credit_limit(avg_hours: float, volatility: float, trips: float, daily_avg: float) -> float:
    if not os.path.exists(MODEL_PATH):
        train_and_save_model()
    model = joblib.load(MODEL_PATH)
    features = np.array([[avg_hours, volatility, trips, daily_avg]])
    pred = model.predict(features)[0]
    return float(round(pred, 2))

if __name__ == "__main__":
    train_and_save_model()
