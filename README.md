# OTT Finder API (backend)

FastAPI service for the OTT Finder catalog. It stores movies, streaming platforms, and OTT dates, and it can estimate an OTT date when one has not been announced.

The React app in `ott-movies` is the client. This API owns the database.

## Stack

- Python 3.13+
- FastAPI + Uvicorn
- SQLAlchemy
- SQLite (`ott.db`) locally; **PostgreSQL** for durable production
- Alembic migrations
- JWT (admin login) + PBKDF2 password hashes (stdlib, Workers-safe)

## Overview

On startup the API:

1. Creates tables if they do not exist
2. Seeds an admin user, platforms, and a few sample movies

Public users can list and view movies. Admins can create and update titles, set platform availability, and record or predict an OTT date.

The predictor is a heuristic (`heuristic-v1`): it uses historical theatrical-to-OTT lag for the same language/country when possible, otherwise a language default (about 60–75 days).

## Prerequisites

- Python 3.13+ (3.11+ may work; 3.13 is what this repo was set up with)

## Start locally

From this folder. `uvicorn` is installed **inside the virtualenv**, so a bare `uvicorn` command fails with `command not found` until the venv is active.

First-time setup:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[local]"
cp .env.example .env
```

Every later start (venv must be activated — your prompt usually shows `(.venv)`):

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000 --app-dir src
```

Or skip activate and call the venv Python directly:

```bash
.venv/bin/python -m uvicorn app.main:app --reload --port 8000 --app-dir src
```

- API: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Keep this running while you use the frontend at [http://localhost:5173](http://localhost:5173).

## Environment

Copy `.env.example` to `.env` (never commit `.env`):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Local: `sqlite:///./ott.db`. Production: `postgresql://USER:PASSWORD@HOST:5432/ott_radar` |
| `JWT_SECRET` | Sign admin tokens |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Seeded on first start if no users exist |
| `CORS_ORIGINS` | Allowed browser origins, comma-separated |

Default admin: `admin@ott.local` / `admin123`

## How the database is connected

`DATABASE_URL` is loaded in `app/config.py`. `app/db.py` builds a SQLAlchemy engine.

| Environment | Store | Why |
|---|---|---|
| Local | SQLite file `ott.db` | Zero extra services |
| Production API | **PostgreSQL** | Durable, works with existing SQLAlchemy models |
| Cloudflare Python Workers | In-memory SQLite fallback | No disk; not durable |

**D1 is not used.** D1 would replace SQLAlchemy sessions with Worker bindings. Postgres keeps the current FastAPI/ORM architecture. On Cloudflare, pair Postgres with [Hyperdrive](https://developers.cloudflare.com/hyperdrive/) later, or run this API on a host that supports Postgres (Render, Railway, Fly).

Startup still creates missing tables/indexes and seeds sample data. For a new Postgres database, also run migrations:

```bash
pip install -e ".[postgres]"
alembic upgrade head
```

If local SQLite already exists from before Alembic:

```bash
alembic stamp head
```

Tables: `users`, `platforms`, `movies`, `movie_availability`, `ott_dates`. Indexes cover title, language, country, theatrical date, OTT status, and availability FKs (needed for prediction and discovery queries).

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
src/entry.py           Cloudflare Worker → FastAPI (ASGI)
pyproject.toml         dependencies (Cloudflare + local)
```

Cloudflare Workers cannot use `requirements.txt` (pywrangler). Local `uvicorn` is an optional extra: `pip install -e ".[local]"`. Password hashing uses stdlib PBKDF2, not bcrypt.

SQLite files still will not persist on Workers; a D1 (or other hosted) database is required for a real Cloudflare deploy.

## Git

Ignored: `.env`, `.venv/`, `*.db`, `__pycache__/`. Keep `.env.example` and `pyproject.toml` in git.
