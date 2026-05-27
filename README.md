# Breathe ESG — Carbon Data Ingestion & Review Platform

A multi-tenant Django REST + React application that ingests emissions data from three enterprise sources (SAP, utility portals, corporate travel), normalizes it to GHG Protocol scopes, and provides an analyst review dashboard with audit-ready locking.

## Architecture

```
┌─────────────┐    CSV Upload    ┌──────────────────┐    Normalize    ┌──────────────────┐
│  React SPA  │ ──────────────→  │  Django REST API  │ ─────────────→ │  PostgreSQL DB   │
│  (Vite)     │ ←────────────── │  (DRF + Parsers)  │ ←───────────── │  (Multi-tenant)  │
└─────────────┘   JSON API       └──────────────────┘   Query/Audit   └──────────────────┘
```

**Data flow**: CSV Upload → Parse & Validate → Raw Rows → Normalize (scope + CO₂e) → EmissionRecords → Analyst Review → Approve → Lock for Audit

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Create a PostgreSQL database named 'breathe_esg'
python manage.py migrate
python manage.py seed_emission_factors
python manage.py seed_plant_mappings
python manage.py seed_demo_data
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5173` and proxies API calls to `http://localhost:8000`.

### Demo Credentials

After running `seed_demo_data`:
- **Admin**: `admin` / `admin1234`
- **Analyst**: `analyst` / `analyst1234`
- **Viewer**: `viewer` / `viewer1234`
- **Super Admin**: `superadmin` / `superadmin1234` (seeded with `--with-superuser` flag)

## Key Features

- **Multi-tenancy** — Shared-schema isolation via `tenant_id` FK on all models
- **Three data sources** — SAP flat-file CSV, utility portal CSV, Concur-style travel CSV
- **GHG Protocol scopes** — Auto-classification: SAP→Scope 1, Utility→Scope 2, Travel→Scope 3
- **Review workflow** — `pending → reviewed → approved → locked` with bulk actions
- **Audit trail** — Every mutation logged with JSON diffs (who, what, when)
- **Emission factors** — Pre-seeded from EPA GHG Factors Hub and UK DEFRA
- **Analyst dashboard** — Summary cards, scope/source charts, filterable data table

## Documentation

| File | Contents | Grade Weight |
|------|----------|-------------|
| [MODEL.md](MODEL.md) | Data model design and justifications | 35% |
| [DECISIONS.md](DECISIONS.md) | Every ambiguity resolved | 25% |
| [SOURCES.md](SOURCES.md) | Research per data source | 20% |
| [TRADEOFFS.md](TRADEOFFS.md) | What we chose not to build | 10% |

## Sample Data

The `sample_data/` directory contains realistic test files with deliberate edge cases:

- `sap_fuel_export.csv` — 36 rows with German headers, mixed dates, duplicate rows, missing values
- `utility_meter_readings.csv` — 28 rows with non-calendar billing periods, estimated reads, suspicious values
- `travel_expense_report.csv` — 31 rows with IATA codes, multi-currency, missing distances

## Deployment

Configured for Render via `render.yaml`:

```bash
# One-click deploy
# Push to GitHub → Connect to Render → Blueprint deploy
```

## Tech Stack

**Backend**: Django 5.1, Django REST Framework, PostgreSQL, Whitenoise, Gunicorn  
**Frontend**: React 18, Vite, TanStack Table, Recharts, Axios, React Router  
**Deployment**: Render (Web Service + PostgreSQL + Static Site)
