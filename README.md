# Pharmacy_Inventory_System
### AUTHOR : KAKYUBYA SARAH MISHA 

A full stack pharmacy inventory system that combines a Django REST API , a React dashboard and a Jupyter AI/ML notebook to automate stock management ,predict demand and prevent medicine expiry waste. 

Project Overview 
A traditional pharmacy stock management relies on manual tracking which leads to expired medicines sitting on shelves, stockouts of high demand drugs and no visibility into who made changes. This system solves all those problems by integrating :
#  A web dashboard where staff log in
 and manage stock in real time .
# A role-based access sytem that
separates staff ( adding stock ) and managers (editing and deleting)
# A machine learning notebook that
predicts demand risk and sorts inventory using FEFO logic 

Pharmacy_Inventory_System/
│
├── pharmacy_project/          # Django project settings & URLs
├── inventory/                 # Django app: models, views, serializers, admin
│   ├── models.py              # Medicine, InventoryLog, UserProfile
│   ├── views.py               # REST API views with role enforcement
│   ├── serializers.py         # DRF serializers
│   └── admin.py               # Django admin configuration
│
├── frontend/                  # React application
│   └── src/
│       └── App.js             # Login, dashboard, add stock, export PDF
│
├── Pharmacy_Inventory_System.ipynb   # Jupyter AI/ML analysis notebook
├── db.sqlite3                 # Django SQLite database
└── README.md

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 6, Django REST Framework, Token Authentication |
| Frontend | React.js, Axios, jsPDF |
| Database | SQLite (Django ORM) |
| AI / ML | PyTorch, Scikit-learn, Pandas, Matplotlib, Seaborn |
| Dataset | [Pharma Sales Data — Kaggle](https://www.kaggle.com/datasets/milanzdravkovic/pharma-sales-data) |


## 🤖 AI & Machine Learning (Jupyter Notebook)

The notebook contains four analytical layers built on the Kaggle Pharma Sales dataset:

### 1. Demand Forecasting — Linear Regression
Predicts weekly sales volume per drug category using historical daily sales data across 8 ATC drug classifications.

### 2. High-Demand Risk Classification — PyTorch Neural Network
A feedforward neural network trained to classify whether a drug is at **high demand risk** on any given day based on month, weekday, and day features. Evaluated using a confusion matrix and ROC-AUC curve.

### 3. Stock Quantity Prediction — Random Forest Regressor
Predicts the exact quantity of stock likely to be sold, giving managers a data-driven basis for reorder decisions.

### 4. FEFO Prioritization — First-to-Expire, First-Out
Automatically sorts the inventory so that medicines closest to expiry are flagged for dispensing first, with a visual expiry monitor showing:
- 🔴 Critical zone (≤ 30 days or already expired)
- 🔵 Stable stock (> 30 days remaining)

### 5. Daily Action Plan Alerts
Generates a prioritised action report each day:
```
--- 📋 DAILY PHARMACY ACTION PLAN ---
🔴 ACTION REQUIRED: Insulin      | Stock:   5 | Expiry: 2026-03-15
🟢 STABLE:          Amoxicillin  | Stock:  50 | Expiry: 2026-12-01
```
## 🔗 How the Three Components Connect

```
Kaggle CSV Dataset
       ↓
Jupyter Notebook (AI/ML Analysis)
  - Trains demand forecasting models
  - Applies FEFO sorting logic
  - Generates reorder alerts
       ↓
Django Backend (REST API)
  - Stores live inventory in SQLite
  - Enforces role-based permissions
  - Tracks who added each stock entry
       ↓
React Frontend (Dashboard)
  - Staff log in and add stock
  - Manager edits and deletes
  - All users export PDF reports
```
The Jupyter notebook can also connect directly to Django's `db.sqlite3` to run AI analysis on live pharmacy data, closing the loop between real-time stock management and intelligent forecasting.

## 📊 Dataset

**Source:** Pharma Sales Data — Kaggle
**URL:** https://www.kaggle.com/datasets/milanzdravkovic/pharma-sales-data


