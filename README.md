# KineticPay

KineticPay is a financial-stability platform for gig workers. It helps workers manage volatile daily earnings through income smoothing, a volatility vault, micro-advances, and parametric downtime protection.

## Problem

Gig workers earn differently every day, but their expenses remain fixed. Bad weather, low demand, incentives, and platform changes can create sudden income gaps.

Traditional credit products are not designed around daily earnings. KineticPay helps workers stabilize cash flow before a low-income day becomes a financial crisis.

## Solution

KineticPay provides:

- Income smoothing across high- and low-earning shifts
- A Volatility Vault that stores a portion of high earnings
- Automatic top-ups during low-income shifts
- Responsible micro-advances based on activity and earnings signals
- Transparent 8% shift-based repayment
- Parametric weather downtime payout simulation
- Shift ledger and cash-flow dashboard

## Key Features

### 1. Volatility Vault

When a worker earns more than the target income, part of the surplus is saved in the Volatility Vault.

When a worker earns less than the target income, the Vault can top up the payout if funds are available.

### 2. Micro-Advance

KineticPay calculates an estimated credit limit using:

- Average active hours
- Earnings volatility
- Average trips completed
- Average daily earnings

### 3. Split Repayment

When a worker has an active advance, 8% of the stabilized shift payout is automatically used for repayment.

### 4. Parametric Downtime Shield

The prototype simulates an automatic weather-related payout to the Volatility Vault during severe rainfall conditions.

### 5. Transparent Ledger

Every shift records:

- Raw earnings
- Vault contribution or withdrawal
- Loan repayment
- Final deposited payout

## Tech Stack

### Frontend

- HTML
- CSS
- JavaScript
- Tailwind CSS
- Chart.js

### Backend

- Python
- FastAPI
- SQLite
- Pandas
- Scikit-learn
- Joblib

## Project Structure

```text
kineticpay/
│
├── frontend/
│   ├── index.html
│   ├── dashboard.html
│   ├── app.js
│   └── styles.css
│
├── backend/
│   ├── app.py
│   ├── database.py
│   ├── model.py
│   ├── requirements.txt
│   └── kineticpay.db
│
└── README.md
