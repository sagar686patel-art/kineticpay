import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().with_name("kineticpay.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        platform TEXT NOT NULL,
        buffer_balance REAL DEFAULT 0.0,
        active_loan REAL DEFAULT 0.0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # One weather event can only be settled once per operator.  The event key
    # keeps this extensible when real weather-provider events are introduced.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS insurance_claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        event_key TEXT NOT NULL,
        payout REAL NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, event_key),
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    # Earnings & Shift Ledger
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shift_earnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        shift_date TEXT NOT NULL,
        raw_earnings REAL NOT NULL,
        smoothed_payout REAL NOT NULL,
        vault_diff REAL NOT NULL,
        active_hours REAL NOT NULL,
        trips_completed INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    # Repair rows created by the original field-order bug: SQLite stored the
    # ISO date in user_id and the numeric user id in shift_date.  This only
    # matches that impossible shape, so valid ledger records are untouched.
    cursor.execute("""
        UPDATE shift_earnings
        SET user_id = CAST(shift_date AS INTEGER), shift_date = user_id
        WHERE typeof(user_id) = 'text'
          AND user_id GLOB '????-??-??'
          AND shift_date GLOB '[0-9]*'
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
