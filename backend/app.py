import os
import base64
import binascii
import hashlib
import hmac
import sqlite3
from datetime import date
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from database import get_db, init_db
from model import predict_credit_limit, train_and_save_model

# Initialize SQLite database and train ML model if missing
init_db()
MODEL_PATH = os.path.join(os.path.dirname(__file__), "underwriting_model.joblib")
if not os.path.exists(MODEL_PATH):
    train_and_save_model()

app = FastAPI(title="KineticPay Engine")

# Configure CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Schemas
class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)
    platform: str = Field(min_length=2, max_length=50)

class UserLogin(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)

class ShiftData(BaseModel):
    user_id: int = Field(gt=0)
    raw_earnings: float = Field(ge=0, le=100_000)
    active_hours: float = Field(gt=0, le=24)
    trips: int = Field(ge=0, le=500)

class MicroAdvanceRequest(BaseModel):
    user_id: int = Field(gt=0)
    requested_amount: float = Field(gt=0, le=100_000)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return "pbkdf2_sha256$310000$%s$%s" % (
        base64.b64encode(salt).decode(), base64.b64encode(digest).decode()
    )


def verify_password(password: str, stored_password: str) -> bool:
    """Verify hashed passwords, while supporting a one-time legacy migration."""
    try:
        scheme, iterations, salt_b64, digest_b64 = stored_password.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), base64.b64decode(salt_b64), int(iterations)
        )
        return hmac.compare_digest(base64.b64encode(digest).decode(), digest_b64)
    except (ValueError, TypeError, binascii.Error):
        return hmac.compare_digest(password, stored_password)


def credit_limit_for_user(cursor, user_id: int) -> float:
    cursor.execute("""
        SELECT raw_earnings, active_hours, trips_completed
        FROM shift_earnings WHERE user_id=? ORDER BY id DESC LIMIT 10
    """, (user_id,))
    shifts = cursor.fetchall()
    if not shifts:
        return predict_credit_limit(8.0, 150.0, 15.0, 1200.0)
    raw_history = [s["raw_earnings"] for s in shifts]
    avg_h = sum(s["active_hours"] for s in shifts) / len(shifts)
    avg_trips = sum(s["trips_completed"] for s in shifts) / len(shifts)
    daily_avg = sum(raw_history) / len(raw_history)
    volatility = float(pd.Series(raw_history).std()) if len(raw_history) > 1 else 100.0
    return predict_credit_limit(avg_h, volatility, avg_trips, daily_avg)

# Routes
@app.post("/api/register")
def register(user: UserRegister):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password, full_name, platform) VALUES (?, ?, ?, ?)",
            (user.username, hash_password(user.password), user.full_name.strip(), user.platform.strip())
        )
        conn.commit()
        user_id = cursor.lastrowid
    except Exception:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists.")
    conn.close()
    return {"message": "User registered successfully", "user_id": user_id}

@app.post("/api/login")
def login(creds: UserLogin):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password, full_name, platform, buffer_balance, active_loan FROM users WHERE username=?", (creds.username,))
    user = cursor.fetchone()
    if not user or not verify_password(creds.password, user["password"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    if not user["password"].startswith("pbkdf2_sha256$"):
        cursor.execute("UPDATE users SET password=? WHERE id=?", (hash_password(creds.password), user["id"]))
        conn.commit()
    result = dict(user)
    result.pop("password", None)
    conn.close()
    return result

@app.post("/api/simulate-shift")
def simulate_shift(shift: ShiftData):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT buffer_balance, active_loan FROM users WHERE id=?", (shift.user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    buffer_bal = user["buffer_balance"]
    active_loan = user["active_loan"]

    baseline_target = 1200.0
    raw = shift.raw_earnings
    vault_diff = 0.0
    smoothed = raw

    # 1. Income Smoothing Logic
    if raw > baseline_target * 1.15:
        vault_diff = (raw - baseline_target) * 0.60
        smoothed = raw - vault_diff
        buffer_bal += vault_diff
    elif raw < baseline_target * 0.85:
        needed = baseline_target - raw
        withdrawal = min(needed, buffer_bal)
        vault_diff = -withdrawal
        smoothed = raw + withdrawal
        buffer_bal -= withdrawal

    # 2. Split-Withholding Loan Repayment (8% cut if loan exists)
    loan_repayment = 0.0
    if active_loan > 0:
        loan_repayment = min(smoothed * 0.08, active_loan)
        active_loan -= loan_repayment
        smoothed -= loan_repayment

    cursor.execute("""
        INSERT INTO shift_earnings (user_id, shift_date, raw_earnings, smoothed_payout, vault_diff, active_hours, trips_completed)
        VALUES (?, DATE('now'), ?, ?, ?, ?, ?)
    """, (shift.user_id, raw, smoothed, vault_diff, shift.active_hours, shift.trips))

    cursor.execute("UPDATE users SET buffer_balance=?, active_loan=? WHERE id=?", (buffer_bal, active_loan, shift.user_id))
    conn.commit()
    conn.close()

    return {
        "raw_earnings": raw,
        "smoothed_payout": round(smoothed, 2),
        "vault_diff": round(vault_diff, 2),
        "loan_deduction": round(loan_repayment, 2),
        "new_buffer_balance": round(buffer_bal, 2),
        "remaining_loan": round(active_loan, 2)
    }

@app.get("/api/user-stats/{user_id}")
def user_stats(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT buffer_balance, active_loan FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    cursor.execute("""
        SELECT id, raw_earnings, smoothed_payout, vault_diff, active_hours, trips_completed 
        FROM shift_earnings WHERE user_id=? ORDER BY id DESC LIMIT 10
    """, (user_id,))
    shifts = cursor.fetchall()

    raw_history = [s["raw_earnings"] for s in shifts][::-1]
    smoothed_history = [s["smoothed_payout"] for s in shifts][::-1]

    if shifts:
        avg_h = sum(s["active_hours"] for s in shifts) / len(shifts)
        avg_trips = sum(s["trips_completed"] for s in shifts) / len(shifts)
        daily_avg = sum(s["raw_earnings"] for s in shifts) / len(shifts)
        volatility = float(pd.Series(raw_history).std()) if len(raw_history) > 1 else 100.0
    else:
        avg_h, avg_trips, daily_avg, volatility = 8.0, 15.0, 1200.0, 150.0

    credit_limit = credit_limit_for_user(cursor, user_id)
    conn.close()

    ledger = [
        {
            "id": s["id"],
            "raw": s["raw_earnings"],
            "smoothed": s["smoothed_payout"],
            "vault_diff": s["vault_diff"],
            "loan_deducted": round(max(0, s["raw_earnings"] - s["vault_diff"] - s["smoothed_payout"]), 2)
        }
        for s in shifts
    ]

    return {
        "buffer_balance": round(user["buffer_balance"], 2),
        "active_loan": round(user["active_loan"], 2),
        "pre_approved_credit": credit_limit,
        "raw_history": raw_history,
        "smoothed_history": smoothed_history,
        "ledger": ledger
    }

@app.post("/api/request-advance")
def request_advance(req: MicroAdvanceRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT active_loan FROM users WHERE id=?", (req.user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    credit_limit = credit_limit_for_user(cursor, req.user_id)
    available_credit = max(0, credit_limit - user["active_loan"])
    if req.requested_amount > available_credit:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Requested advance exceeds available credit of ₹{available_credit:.2f}."
        )
    new_loan = user["active_loan"] + req.requested_amount
    cursor.execute("UPDATE users SET active_loan=? WHERE id=?", (new_loan, req.user_id))
    conn.commit()
    conn.close()
    return {"message": "Disbursal successful", "active_loan": new_loan, "available_credit": available_credit - req.requested_amount}

@app.post("/api/parametric-claim/{user_id}")
def parametric_claim(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT buffer_balance FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    event_key = f"rainfall-{date.today().isoformat()}"
    payout_amt = 350.0
    try:
        cursor.execute(
            "INSERT INTO insurance_claims (user_id, event_key, payout) VALUES (?, ?, ?)",
            (user_id, event_key, payout_amt)
        )
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail="Today's weather claim has already been settled.")
    new_balance = user["buffer_balance"] + payout_amt
    cursor.execute("UPDATE users SET buffer_balance=? WHERE id=?", (new_balance, user_id))
    conn.commit()
    conn.close()
    return {"message": "Parametric weather claim approved", "payout": payout_amt, "new_buffer": new_balance}
