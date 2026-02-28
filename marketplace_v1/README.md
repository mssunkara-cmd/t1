# marketplace_v1

Scaffold for a single-tenant marketplace + dashboard application.

## Layout

- `backend/`: Flask + SQLAlchemy + Alembic
- `frontend/`: React + TypeScript + Vite

## Backend quick start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app wsgi db upgrade
python wsgi.py
```

## Frontend quick start

```bash
cd frontend
npm install
npm run dev
```
