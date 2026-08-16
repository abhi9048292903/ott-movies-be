# OTT Finder API (backend)

FastAPI service for the OTT Finder catalog. It stores movies, streaming platforms, and OTT dates, and it can estimate an OTT date when one has not been announced.

The React app in `ott-movies` is the client. This API owns the database.

## Stack

- Python 3.13+
- FastAPI + Uvicorn
- SQLAlchemy
- SQLite (`ott.db`) for local development
- JWT (admin login) + bcrypt (password hashes)

## Overview

On startup the API:

1. Creates tables if they do not exist
2. Seeds an admin user, platforms, and a few sample movies

Public users can list and view movies. Admins can create and update titles, set platform availability, and record or predict an OTT date.

The predictor is a heuristic (`heuristic-v1`): it uses historical theatrical-to-OTT lag for the same language/country when possible, otherwise a language default (about 60–75 days).

## Prerequisites

- Python 3.13+ (3.11+ may work; 3.13 is what this repo was set up with)

## Start locally

From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

- API: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Keep this running while you use the frontend at [http://localhost:5173](http://localhost:5173).

## Environment

Copy `.env.example` to `.env` (never commit `.env`):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Default `sqlite:///./ott.db` (file in this folder) |
| `JWT_SECRET` | Sign admin tokens |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Seeded on first start if no users exist |
| `CORS_ORIGINS` | Allowed browser origins, comma-separated |

Default admin: `admin@ott.local` / `admin123`

## How the database is connected

`DATABASE_URL` is loaded in `app/config.py`. `app/db.py` builds a SQLAlchemy engine and session. For SQLite it resolves `./ott.db` to an absolute path next to this README.

Routes use `get_db()` so each request gets a session that is closed afterward. Tables are defined in `app/models.py`: `users`, `platforms`, `movies`, `movie_availability`, `ott_dates`.

## Main endpoints

| Method | Path | Auth |
|---|---|---|
| `GET` | `/health` | No |
| `POST` | `/auth/login` | No |
| `GET` | `/platforms` | No |
| `GET` | `/movies` | No (query: `q`, `platform`, `status`) |
| `GET` | `/movies/{id}` | No |
| `POST` | `/movies` | Admin JWT |
| `PUT` | `/movies/{id}` | Admin JWT |
| `POST` | `/movies/{id}/predict` | Admin JWT |

## Project layout

```
app/
  main.py              FastAPI app, CORS, startup seed
  config.py            settings from .env
  db.py                engine + sessions
  models.py            tables
  auth.py              JWT + password helpers
  routers/auth.py
  routers/movies.py
  services/seed.py
  services/predict.py
requirements.txt       local install (uvicorn)
```

## Git

Ignored: `.env`, `.venv/`, `*.db`, `__pycache__/`. Keep `.env.example` and `requirements.txt` in git.
